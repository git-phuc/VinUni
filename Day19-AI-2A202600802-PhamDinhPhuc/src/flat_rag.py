import os
import json
from qdrant_client.models import Distance, VectorParams, PointStruct
from config import client, qdrant_client, EMBEDDING_MODEL, OUTPUT_DIR
from src.indexing import call_openai_chat

class FlatRAG:
    def __init__(self, chunks):
        self.chunks = chunks
        self.collection_name = "tech_company_chunks"
        self.embeddings = None
        self.cache_path = os.path.join(OUTPUT_DIR, "flat_rag_embeddings_cache.json")
        
        # 1. Load or Generate Embeddings
        self._load_or_generate_embeddings()
        
        # 2. Setup Qdrant Collection & Upsert
        self._setup_qdrant()
        
    def _load_or_generate_embeddings(self):
        if os.path.exists(self.cache_path):
            print("Loading chunk embeddings from cache...")
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self.embeddings = json.load(f)
        else:
            print("Generating embeddings using OpenAI API...")
            self.embeddings = {}
            batch_size = 100
            for i in range(0, len(self.chunks), batch_size):
                batch_chunks = self.chunks[i:i+batch_size]
                texts = [c["text"] for c in batch_chunks]
                
                try:
                    response = client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=texts
                    )
                    for idx, data in enumerate(response.data):
                        chunk_id = batch_chunks[idx]["chunk_id"]
                        self.embeddings[chunk_id] = data.embedding
                except Exception as e:
                    print(f"Error generating embeddings for batch starting at {i}: {e}")
                    
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.embeddings, f)
                
    def _setup_qdrant(self):
        print(f"Checking Qdrant collection: {self.collection_name}...")
        try:
            exists = qdrant_client.collection_exists(self.collection_name)
        except Exception:
            # Fallback if collection_exists is not supported in this version
            exists = False
            try:
                cols = qdrant_client.get_collections().collections
                exists = any(c.name == self.collection_name for c in cols)
            except Exception as e:
                print(f"Error listing collections: {e}")
                
        if exists:
            try:
                count = qdrant_client.count(self.collection_name).count
                if count >= len(self.chunks) - 10:
                    print(f"Collection {self.collection_name} already exists with {count} points. Skipping recreate/upsert.")
                    return
            except Exception as e:
                print(f"Error counting points in {self.collection_name}: {e}. Recreating...")
                
            print(f"Collection {self.collection_name} already exists. Recreating to ensure fresh data...")
            qdrant_client.delete_collection(self.collection_name)
            
        print(f"Creating collection {self.collection_name}...")
        qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
        )
        
        # Prepare points for upsert
        points = []
        for idx, chunk in enumerate(self.chunks):
            chunk_id = chunk["chunk_id"]
            vector = self.embeddings.get(chunk_id)
            if not vector:
                continue
                
            points.append(
                PointStruct(
                    id=idx,
                    vector=vector,
                    payload={
                        "chunk_id": chunk_id,
                        "doc_id": chunk["doc_id"],
                        "title": chunk["title"],
                        "link": chunk["link"],
                        "text": chunk["text"]
                    }
                )
            )
            
        # Upsert points in batches of 100
        batch_size = 100
        print(f"Upserting {len(points)} points into Qdrant collection in batches of {batch_size}...")
        import time
        for i in range(0, len(points), batch_size):
            batch_points = points[i:i+batch_size]
            qdrant_client.upsert(
                collection_name=self.collection_name,
                points=batch_points
            )
            time.sleep(0.2)
        print("Qdrant setup completed successfully.")
        
    def retrieve(self, query, top_k=5):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=query
            )
            query_emb = response.data[0].embedding
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            return []
            
        # Perform vector search in Qdrant
        try:
            response = qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_emb,
                limit=top_k
            )
            
            retrieved_chunks = []
            for hit in response.points:
                payload = hit.payload
                retrieved_chunks.append({
                    "chunk_id": payload.get("chunk_id"),
                    "doc_id": payload.get("doc_id"),
                    "title": payload.get("title"),
                    "link": payload.get("link"),
                    "text": payload.get("text")
                })
            return retrieved_chunks
        except Exception as e:
            print(f"Error searching in Qdrant: {e}")
            return []
            
    def answer(self, query):
        retrieved = self.retrieve(query)
        context = "\n\n".join([f"Source: {c['title']} ({c['doc_id']})\n{c['text']}" for c in retrieved])
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer the user's question using the provided search context. If the information is not present, say that you don't know based on the context. Do not make up facts."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ]
        
        response = call_openai_chat(messages)
        return response.choices[0].message.content, retrieved
