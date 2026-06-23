import os
import json
from qdrant_client.models import Distance, VectorParams, PointStruct
from config import client, qdrant_client, EMBEDDING_MODEL, OUTPUT_DIR
from src.indexing import call_openai_chat, normalize_entity_name

class GraphRAG:
    def __init__(self, graph, chunks):
        self.graph = graph
        self.chunks = chunks
        self.collection_name = "tech_company_entities"
        self.embeddings = {}
        self.cache_path = os.path.join(OUTPUT_DIR, "graph_entities_embeddings_cache.json")
        
        # Build dictionary lookup for chunks
        self.chunk_dict = {c["chunk_id"]: c for c in chunks}
        
        # 1. Load or Generate Entity Embeddings
        self._load_or_generate_entity_embeddings()
        
        # 2. Setup Qdrant Entity Collection & Upsert
        self._setup_qdrant_entities()
        
    def _load_or_generate_entity_embeddings(self):
        if os.path.exists(self.cache_path):
            print("Loading entity embeddings from cache...")
            with open(self.cache_path, "r", encoding="utf-8") as f:
                self.embeddings = json.load(f)
        else:
            print("Generating entity embeddings using OpenAI API...")
            self.embeddings = {}
            nodes = list(self.graph.nodes())
            
            batch_size = 100
            for i in range(0, len(nodes), batch_size):
                batch_nodes = nodes[i:i+batch_size]
                texts = [f"{node}: {self.graph.nodes[node].get('description', '')}" for node in batch_nodes]
                
                try:
                    response = client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=texts
                    )
                    for idx, data in enumerate(response.data):
                        self.embeddings[batch_nodes[idx]] = data.embedding
                except Exception as e:
                    print(f"Error generating entity embeddings: {e}")
                    
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.embeddings, f)
                
    def _setup_qdrant_entities(self):
        print(f"Checking Qdrant entity collection: {self.collection_name}...")
        try:
            exists = qdrant_client.collection_exists(self.collection_name)
        except Exception:
            exists = False
            try:
                cols = qdrant_client.get_collections().collections
                exists = any(c.name == self.collection_name for c in cols)
            except Exception as e:
                print(f"Error listing entity collections: {e}")
                
        if exists:
            try:
                count = qdrant_client.count(self.collection_name).count
                if count >= len(self.graph.nodes()) - 10:
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
        
        # Prepare points
        points = []
        for idx, node in enumerate(self.graph.nodes()):
            vector = self.embeddings.get(node)
            if not vector:
                continue
                
            points.append(
                PointStruct(
                    id=idx,
                    vector=vector,
                    payload={
                        "entity_name": node,
                        "type": self.graph.nodes[node].get("type", "General"),
                        "description": self.graph.nodes[node].get("description", "")
                    }
                )
            )
            
        # Upsert in batches of 100
        batch_size = 100
        print(f"Upserting {len(points)} entities into Qdrant in batches of {batch_size}...")
        import time
        for i in range(0, len(points), batch_size):
            batch_points = points[i:i+batch_size]
            qdrant_client.upsert(
                collection_name=self.collection_name,
                points=batch_points
            )
            time.sleep(0.25)
        print("Qdrant entity setup completed.")
        
    def retrieve_start_nodes(self, query, threshold=0.72, top_k=3):
        # 1. LLM-based entity extraction
        llm_entities = self.extract_query_entities_llm(query)
        if llm_entities:
            print(f"  LLM Extracted starting entities: {llm_entities}")
            return llm_entities
            
        # 2. Qdrant semantic search
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=query
            )
            query_emb = response.data[0].embedding
            
            search_response = qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_emb,
                limit=top_k,
                score_threshold=threshold
            )
            
            vector_entities = [hit.payload.get("entity_name") for hit in search_response.points]
            if vector_entities:
                print(f"  Qdrant semantic start nodes: {vector_entities}")
                return vector_entities
        except Exception as e:
            print(f"Error doing vector search for start nodes: {e}")
            
        # 3. Fallback: string matching
        query_lower = query.lower()
        string_entities = [node for node in self.graph.nodes() if node.lower() in query_lower]
        if string_entities:
            print(f"  Fallback string start nodes: {string_entities}")
            return string_entities
            
        return []
        
    def extract_query_entities_llm(self, query):
        messages = [
            {"role": "system", "content": "You extract key entities mentioned in a query for looking up in a knowledge graph. Return exactly a JSON object with one key: 'entities' containing a list of strings representing the key entities."},
            {"role": "user", "content": f"""Identify the main entities (companies, people, products, concepts, laws) in the following query that would be the best entry points in a knowledge graph. Return ONLY a JSON object.
Examples:
- "Who co-founded OpenAI?" -> {{"entities": ["OpenAI"]}}
- "What is the relationship between Volvo and Polestar?" -> {{"entities": ["Volvo", "Polestar"]}}
- "How did the Inflation Reduction Act impact EV leasing?" -> {{"entities": ["Inflation Reduction Act"]}}

Query: {query}"""}
        ]
        
        try:
            response = call_openai_chat(messages, json_mode=True)
            result = json.loads(response.choices[0].message.content)
            entities = result.get("entities", [])
            normalized_entities = [normalize_entity_name(e) for e in entities]
            return [ne for ne in normalized_entities if ne in self.graph]
        except Exception as e:
            print(f"Error extracting query entities with LLM: {e}")
            return []
            
    def traverse_graph(self, start_nodes, max_hop=2):
        if not start_nodes:
            return ""
            
        retrieved_nodes = set(start_nodes)
        retrieved_edges = []
        chunk_ids = set()
        
        # Hop 1
        hop1_nodes = set()
        for node in start_nodes:
            for target in self.graph.successors(node):
                hop1_nodes.add(target)
                relations = self.graph[node][target].get("relations", [])
                chunks = self.graph[node][target].get("chunk_ids", [])
                retrieved_edges.append((node, target, relations))
                chunk_ids.update(chunks)
            for source in self.graph.predecessors(node):
                hop1_nodes.add(source)
                relations = self.graph[source][node].get("relations", [])
                chunks = self.graph[source][node].get("chunk_ids", [])
                retrieved_edges.append((source, node, relations))
                chunk_ids.update(chunks)
                
        retrieved_nodes.update(hop1_nodes)
        
        # Hop 2
        if max_hop >= 2:
            hop2_nodes = set()
            for node in hop1_nodes:
                for target in self.graph.successors(node):
                    if target not in retrieved_nodes:
                        hop2_nodes.add(target)
                        relations = self.graph[node][target].get("relations", [])
                        chunks = self.graph[node][target].get("chunk_ids", [])
                        retrieved_edges.append((node, target, relations))
                        chunk_ids.update(chunks)
                for source in self.graph.predecessors(node):
                    if source not in retrieved_nodes:
                        hop2_nodes.add(source)
                        relations = self.graph[source][node].get("relations", [])
                        chunks = self.graph[source][node].get("chunk_ids", [])
                        retrieved_edges.append((source, node, relations))
                        chunk_ids.update(chunks)
            retrieved_nodes.update(hop2_nodes)
            
        # Build textual context
        context_parts = []
        
        # Node descriptions
        context_parts.append("### Relevant Entities Descriptions:")
        for node in retrieved_nodes:
            ntype = self.graph.nodes[node].get("type", "General")
            desc = self.graph.nodes[node].get("description", "No description available.")
            context_parts.append(f"- {node} ({ntype}): {desc}")
            
        # Edges
        context_parts.append("\n### Relationships & Facts:")
        dedup_edges = []
        seen = set()
        for u, v, rels in retrieved_edges:
            edge_key = (u, v)
            if edge_key not in seen:
                seen.add(edge_key)
                dedup_edges.append((u, v, rels))
                
        for u, v, rels in dedup_edges:
            rel_str = ", ".join(rels)
            context_parts.append(f"- ({u}) --[{rel_str}]--> ({v})")
            
        # Include original texts of the chunks related to the connections
        retrieved_chunk_texts = []
        # Get top 6 chunks to avoid cluttering LLM's context window
        for cid in list(chunk_ids)[:6]:
            chunk_data = self.chunk_dict.get(cid)
            if chunk_data:
                retrieved_chunk_texts.append(f"Source Document: {chunk_data['title']} ({chunk_data['doc_id']})\n{chunk_data['text']}")
                
        if retrieved_chunk_texts:
            context_parts.append("\n### Relevant Source Text Details:")
            context_parts.append("\n\n".join(retrieved_chunk_texts))
            
        return "\n".join(context_parts)
        
    def answer(self, query):
        start_nodes = self.retrieve_start_nodes(query)
        
        if not start_nodes:
            return "No matching entities found in the knowledge graph to answer this question. Please try a query related to the companies or topics in the dataset.", ""
            
        graph_context = self.traverse_graph(start_nodes)
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer the user's question using the provided knowledge graph relationships, descriptions, and source text details. Provide a comprehensive, structured response. If the context does not contain the answer, state that you don't know based on the context."},
            {"role": "user", "content": f"Knowledge Graph Context:\n{graph_context}\n\nQuestion: {query}"}
        ]
        
        response = call_openai_chat(messages)
        return response.choices[0].message.content, graph_context
