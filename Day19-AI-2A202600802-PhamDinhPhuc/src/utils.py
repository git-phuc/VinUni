import os
from tqdm import tqdm
from config import DATASET_DIR

def load_and_chunk_documents(chunk_size=4000, chunk_overlap=400):
    print("Loading and parsing documents...")
    files = [f for f in os.listdir(DATASET_DIR) if f.endswith(".txt")]
    files.sort(key=lambda x: int(x.replace("doc_", "").replace(".txt", "")))
    
    chunks = []
    
    for file_name in tqdm(files, desc="Parsing Files"):
        file_path = os.path.join(DATASET_DIR, file_name)
        
        # Read as bytes to check corruption
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
            
        # Decode as utf-8 (ignoring errors to prevent crash)
        content_str = raw_bytes.decode("utf-8", errors="replace")
        
        # Parse fields
        title = ""
        link = ""
        snippet = ""
        full_content = ""
        
        lines = content_str.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Title:"):
                title = line.replace("Title:", "").strip()
            elif line.startswith("Link:"):
                link = line.replace("Link:", "").strip()
            elif line.startswith("Snippet:"):
                snippet = line.replace("Snippet:", "").strip()
            elif line.startswith("Full Content:"):
                full_content = "\n".join(lines[i+1:]).strip()
                break
                
        doc_id = file_name.replace(".txt", "")
        
        # Check if the Full Content section contains replacement character or is empty, indicating corruption
        is_corrupted = "\uFFFD" in full_content or len(full_content) == 0 or full_content.count("\uFFFD") > 100
        
        if is_corrupted:
            # Fallback to Title and Snippet for corrupted files
            text_to_chunk = f"Title: {title}\nSnippet: {snippet}"
            print(f"  Note: {file_name} is marked as corrupted/binary. Using Title and Snippet fallback.")
        else:
            text_to_chunk = full_content
            
        # Perform chunking
        start = 0
        chunk_idx = 0
        while start < len(text_to_chunk):
            end = start + chunk_size
            chunk_text = text_to_chunk[start:end]
            
            chunks.append({
                "chunk_id": f"{doc_id}_c{chunk_idx}",
                "doc_id": doc_id,
                "title": title,
                "link": link,
                "text": chunk_text
            })
            
            if end >= len(text_to_chunk):
                break
            start += chunk_size - chunk_overlap
            chunk_idx += 1
            
    print(f"Total chunks generated: {len(chunks)}")
    return chunks
