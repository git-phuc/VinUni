import os
import json
import time
import concurrent.futures
from tqdm import tqdm
from config import client, OPENAI_MODEL, OUTPUT_DIR

# Helper function to call OpenAI with retry and exponential backoff
def call_openai_chat(messages, json_mode=False, max_retries=5):
    backoff = 1.0
    for attempt in range(max_retries):
        try:
            response_format = {"type": "json_object"} if json_mode else None
            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                response_format=response_format,
                temperature=0.0
            )
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(backoff)
            backoff *= 2.0

def extract_triples_from_chunk(chunk):
    text = chunk["text"]
    chunk_id = chunk["chunk_id"]
    
    messages = [
        {"role": "system", "content": "You are a professional knowledge graph extractor. Extract entities and relationships from the text as JSON."},
        {"role": "user", "content": f"""Analyze the following text and extract entities and relationships (triples).
Format the output as a JSON object with exactly two keys:
1. "triples": a list of objects, each containing:
   - "subject": the name of the source entity (e.g., "OpenAI")
   - "relation": the relationship verb/concept in uppercase with underscores (e.g., "FOUNDED_BY", "ACQUIRED", "PARTNERED_WITH", "DEVELOPED", "COMPETES_WITH", "REVENUE_2023", "GROWTH_RATE")
   - "object": the name of the target entity (e.g., "Sam Altman")
2. "entities": a list of objects, each containing:
   - "name": the entity name
   - "type": the entity category (e.g., "Company", "Person", "Product", "Technology", "Location", "Sector", "FinancialMetric", "Date")
   - "description": a brief description or context of this entity from the text

Rules:
- Standardize entity names to their common names (e.g. "OpenAI Inc.", "openai" -> "OpenAI", "Tesla Motors" -> "Tesla", "U.S." -> "United States").
- Relationships must be clear and direct.
- Extract only factual information present in the text.

Text to analyze:
{text}
"""}
    ]
    
    try:
        response = call_openai_chat(messages, json_mode=True)
        result = json.loads(response.choices[0].message.content)
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        return chunk_id, result, prompt_tokens, completion_tokens
    except Exception as e:
        print(f"Error extracting from chunk {chunk_id}: {e}")
        return chunk_id, {"triples": [], "entities": []}, 0, 0

def normalize_entity_name(name):
    n = name.strip()
    n_lower = n.lower()
    if n_lower in ["openai inc.", "openai inc", "openai"]:
        return "OpenAI"
    if n_lower in ["tesla inc.", "tesla inc", "tesla motor", "tesla motors", "tesla"]:
        return "Tesla"
    if n_lower in ["microsoft corp", "microsoft corp.", "microsoft corporation", "microsoft"]:
        return "Microsoft"
    if n_lower in ["google inc.", "google inc", "google llc", "google"]:
        return "Google"
    if n_lower in ["apple inc.", "apple inc", "apple"]:
        return "Apple"
    if n_lower in ["nvidia corp", "nvidia corporation", "nvidia"]:
        return "NVIDIA"
    if n_lower in ["polestar automotive holding uk plc", "polestar plc", "polestar holding", "polestar"]:
        return "Polestar"
    if n_lower in ["volvo cars", "volvo car corporation", "volvo car", "volvo"]:
        return "Volvo"
    if n_lower in ["geely holding group", "geely holding", "geely"]:
        return "Geely"
    if n_lower in ["kelley blue book", "kelley blue book counts", "kelley blue book estimates", "kbb"]:
        return "Kelley Blue Book"
    if n_lower in ["inflation reduction act", "inflation reduction act (ira)", "ira"]:
        return "Inflation Reduction Act"
    if n_lower in ["sam altman", "samuel altman"]:
        return "Sam Altman"
    if n_lower in ["elon musk", "elon reeve musk"]:
        return "Elon Musk"
    if n_lower in ["stephanie valdez streaty", "stephanie streaty"]:
        return "Stephanie Valdez Streaty"
    # Fallback to stripping quotes
    if len(n) > 1 and ((n[0] == '"' and n[-1] == '"') or (n[0] == "'" and n[-1] == "'")):
        n = n[1:-1]
    return n

def build_knowledge_graph_model(chunks):
    cache_path = os.path.join(OUTPUT_DIR, "extracted_triples_cache.json")
    
    if os.path.exists(cache_path):
        print("Loading extracted triples from cache...")
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        triples_by_chunk = cache_data["triples_by_chunk"]
        total_prompt_tokens = cache_data["total_prompt_tokens"]
        total_completion_tokens = cache_data["total_completion_tokens"]
        build_time = cache_data["build_time"]
    else:
        print("Extracting triples using OpenAI API in parallel...")
        start_time = time.time()
        triples_by_chunk = {}
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        # Parallel extraction
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            future_to_chunk = {executor.submit(extract_triples_from_chunk, chunk): chunk for chunk in chunks}
            for future in tqdm(concurrent.futures.as_completed(future_to_chunk), total=len(chunks), desc="Extracting Triples"):
                chunk_id, result, prompt_tokens, completion_tokens = future.result()
                triples_by_chunk[chunk_id] = result
                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                
        build_time = time.time() - start_time
        
        # Save cache
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({
                "triples_by_chunk": triples_by_chunk,
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "build_time": build_time
            }, f, indent=2, ensure_ascii=False)
            
    return triples_by_chunk, total_prompt_tokens, total_completion_tokens, build_time
