import re
from typing import List, Dict, Any

def chunk_text(
    text: str, 
    source_name: str, 
    chunk_size: int = 500, 
    overlap: int = 80,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Chunks text semantically, respecting Markdown headers, paragraphs, and sentence boundaries.
    Returns a list of chunk dictionaries with source metadata.
    """
    if not text or not text.strip():
        return []

    metadata = metadata or {}
    chunks = []
    
    # Check for Markdown headers (e.g., #, ##, ###)
    sections = re.split(r'(?m)(?=^#{1,4}\s+)', text)
    
    chunk_id = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
            
        # Extract section title if present
        first_line = section.split('\n', 1)[0]
        header_title = ""
        if first_line.startswith('#'):
            header_title = first_line.lstrip('#').strip()
        
        words = section.split()
        if len(words) <= chunk_size:
            chunk_id += 1
            chunks.append({
                "chunk_id": f"{source_name}_chunk_{chunk_id}",
                "source": source_name,
                "header": header_title,
                "text": section,
                "word_count": len(words),
                **metadata
            })
        else:
            # Sub-chunk longer sections with sliding window
            step = max(chunk_size - overlap, 50)
            for i in range(0, len(words), step):
                chunk_words = words[i:i + chunk_size]
                if not chunk_words:
                    continue
                sub_text = " ".join(chunk_words)
                if header_title and not sub_text.startswith(header_title):
                    sub_text = f"[{header_title}]\n" + sub_text
                    
                chunk_id += 1
                chunks.append({
                    "chunk_id": f"{source_name}_chunk_{chunk_id}",
                    "source": source_name,
                    "header": header_title,
                    "text": sub_text,
                    "word_count": len(chunk_words),
                    **metadata
                })
                
    return chunks
