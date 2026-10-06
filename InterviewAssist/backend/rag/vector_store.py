import json
import uuid
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from config import STORAGE_DIR
from rag.embeddings import EmbeddingService
from rag.knowledge_classifier import KnowledgeClassifier

class VectorStore:
    def __init__(self, api_key: Optional[str] = None):
        self.storage_file = STORAGE_DIR / "knowledge_base.json"
        self.embedding_service = EmbeddingService(api_key=api_key)
        self.documents: Dict[str, Dict[str, Any]] = {}  # doc_id -> doc info
        self.chunks: List[Dict[str, Any]] = []           # all chunk dicts
        self.vectors: Optional[np.ndarray] = None        # matrix of chunk embeddings
        self._load_from_disk()

    def set_api_key(self, api_key: str):
        self.embedding_service = EmbeddingService(api_key=api_key)

    def _load_from_disk(self):
        if self.storage_file.exists():
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", {})
                    self.chunks = data.get("chunks", [])
                    
                if self.chunks:
                    texts = [c["text"] for c in self.chunks]
                    self.embedding_service.local_vectorizer.fit_transform(texts)
                    self.vectors = self.embedding_service.local_vectorizer.transform(texts)
            except Exception as e:
                print(f"Warning: Could not load knowledge base from disk: {e}")
                self.documents = {}
                self.chunks = []
                self.vectors = None

    def _save_to_disk(self):
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump({
                    "documents": self.documents,
                    "chunks": self.chunks,
                    "updated_at": datetime.datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save knowledge base to disk: {e}")

    async def add_document(self, title: str, source: str, file_type: str, chunks: List[Dict[str, Any]]) -> str:
        doc_id = str(uuid.uuid4())[:8]
        
        doc_info = {
            "id": doc_id,
            "title": title,
            "source": source,
            "file_type": file_type,
            "chunk_count": len(chunks),
            "added_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Attach doc_id to each chunk
        for c in chunks:
            c["doc_id"] = doc_id
            c["doc_title"] = title
            
        self.documents[doc_id] = doc_info
        self.chunks.extend(chunks)
        
        # Rebuild vector index
        texts = [c["text"] for c in self.chunks]
        self.embedding_service.local_vectorizer.fit_transform(texts)
        self.vectors = self.embedding_service.local_vectorizer.transform(texts)
        
        self._save_to_disk()
        return doc_id

    def delete_document(self, doc_id: str) -> bool:
        if doc_id not in self.documents:
            return False
            
        del self.documents[doc_id]
        self.chunks = [c for c in self.chunks if c.get("doc_id") != doc_id]
        
        if self.chunks:
            texts = [c["text"] for c in self.chunks]
            self.embedding_service.local_vectorizer.fit_transform(texts)
            self.vectors = self.embedding_service.local_vectorizer.transform(texts)
        else:
            self.vectors = None
            
        self._save_to_disk()
        return True

    def reconcile_with_disk(self, uploads_dir: Optional[Path] = None, workspace_dir: Optional[Path] = None) -> bool:
        """
        Reconciles in-memory documents with physical files on disk.
        If any document points to a file that was removed from disk,
        it purges that document and its chunks from memory and persists the clean state.
        Returns True if any dead documents were pruned.
        """
        if not self.documents:
            return False

        from config import UPLOADS_DIR, WORKSPACE_DIR
        up_dir = uploads_dir or UPLOADS_DIR
        ws_dir = workspace_dir or WORKSPACE_DIR

        dead_doc_ids = []
        for doc_id, doc in list(self.documents.items()):
            source = doc.get("source", "")
            title = doc.get("title", "")
            file_type = doc.get("file_type", "")
            
            # 1. Check if it's a workspace markdown file
            if file_type == "markdown" and (source.startswith("0") or source.startswith("1") or source.startswith("2") or source.startswith("3") or source.startswith("4") or source == "README.md"):
                file_path = ws_dir / source
                if not file_path.exists():
                    dead_doc_ids.append(doc_id)
            # 2. Check if it was an uploaded file (not a web URL)
            elif file_type != "web_url":
                fname = source or title
                file_path = up_dir / fname
                if not file_path.exists():
                    dead_doc_ids.append(doc_id)

        if dead_doc_ids:
            for did in dead_doc_ids:
                if did in self.documents:
                    del self.documents[did]
            self.chunks = [c for c in self.chunks if c.get("doc_id") not in dead_doc_ids]
            if self.chunks:
                texts = [c["text"] for c in self.chunks]
                self.embedding_service.local_vectorizer.fit_transform(texts)
                self.vectors = self.embedding_service.local_vectorizer.transform(texts)
            else:
                self.vectors = None
            self._save_to_disk()
            print(f"[VectorStore] Pruned {len(dead_doc_ids)} removed documents from vector memory.")
            return True
        return False

    def get_documents(self) -> List[Dict[str, Any]]:
        self.reconcile_with_disk()
        return list(self.documents.values())

    def get_knowledge_areas(self) -> List[Dict[str, Any]]:
        """Dynamically detects and returns knowledge areas based on indexed documents."""
        self.reconcile_with_disk()
        return KnowledgeClassifier.discover_areas(self.get_documents(), self.chunks)

    def clear(self):
        """Clears in-memory store and saves empty state."""
        self.documents = {}
        self.chunks = []
        self.vectors = None
        self._save_to_disk()

    def get_stats(self) -> Dict[str, Any]:
        total_words = sum(c.get("word_count", 0) for c in self.chunks)
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "total_words": total_words
        }

    async def search(self, query: str, top_k: int = 5, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Performs semantic cosine similarity search over ingested knowledge chunks.
        """
        if not self.chunks or self.vectors is None or self.vectors.shape[0] == 0:
            return []

        # Vectorize query
        q_vec = self.embedding_service.local_vectorizer.transform([query])
        
        # Compute cosine similarity
        similarities = np.dot(self.vectors, q_vec.T).flatten()
        
        # Filter by doc_id if requested
        valid_indices = []
        for idx, chunk in enumerate(self.chunks):
            if doc_id is None or chunk.get("doc_id") == doc_id:
                valid_indices.append(idx)
                
        if not valid_indices:
            return []

        valid_similarities = [(idx, float(similarities[idx])) for idx in valid_indices]
        valid_similarities.sort(key=lambda x: x[1], reverse=True)
        
        top_results = []
        for idx, score in valid_similarities[:top_k]:
            chunk = self.chunks[idx].copy()
            chunk["score"] = round(score, 4)
            top_results.append(chunk)
            
        return top_results
