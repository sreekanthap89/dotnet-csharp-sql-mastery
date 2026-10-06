import re
import math
import numpy as np
from typing import List, Dict, Any, Optional
import httpx

class LocalSemanticVectorizer:
    """
    High-performance semantic TF-IDF and n-gram vectorizer with cosine normalization.
    Runs 100% locally, instantly, cross-platform with zero external API calls.
    """
    def __init__(self, max_features: int = 1536):
        self.max_features = max_features
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.is_fitted = False

    def _tokenize(self, text: str) -> List[str]:
        # Lowercase, alphanumeric words, plus keep programming terms (like c#, .net, async, etc.)
        cleaned = text.lower()
        cleaned = re.sub(r'[^\w\s\.\#\+\-]', ' ', cleaned)
        tokens = cleaned.split()
        
        # Add word unigrams and bigrams for rich semantic coverage
        grams = []
        for i, t in enumerate(tokens):
            if len(t) > 1:
                grams.append(t)
            if i < len(tokens) - 1:
                grams.append(f"{t}_{tokens[i+1]}")
        return grams

    def fit_transform(self, corpus: List[str]) -> np.ndarray:
        doc_freq = {}
        n_docs = len(corpus)
        if n_docs == 0:
            return np.zeros((0, self.max_features), dtype=np.float32)

        tokenized_corpus = [self._tokenize(doc) for doc in corpus]
        
        # Count document frequencies
        for tokens in tokenized_corpus:
            seen = set(tokens)
            for token in seen:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        # Select top features by frequency
        sorted_tokens = sorted(doc_freq.items(), key=lambda x: x[1], reverse=True)[:self.max_features]
        self.vocabulary = {token: idx for idx, (token, _) in enumerate(sorted_tokens)}
        
        # Compute smoothed IDF
        self.idf = {
            token: math.log((1 + n_docs) / (1 + doc_freq[token])) + 1.0
            for token in self.vocabulary
        }
        self.is_fitted = True

        return self.transform(corpus)

    def transform(self, texts: List[str]) -> np.ndarray:
        n_docs = len(texts)
        n_features = len(self.vocabulary) if self.vocabulary else self.max_features
        matrix = np.zeros((n_docs, n_features), dtype=np.float32)
        
        if not self.is_fitted or not self.vocabulary:
            return matrix

        for doc_idx, text in enumerate(texts):
            tokens = self._tokenize(text)
            term_counts = {}
            for t in tokens:
                if t in self.vocabulary:
                    term_counts[t] = term_counts.get(t, 0) + 1
                    
            for token, count in term_counts.items():
                col = self.vocabulary[token]
                # TF * IDF
                matrix[doc_idx, col] = (1.0 + math.log(count)) * self.idf[token]

        # L2-normalize rows for instant cosine distance via dot product
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


class EmbeddingService:
    """
    Embedding service orchestrator.
    Uses Gemini Embeddings API if key is provided; otherwise seamlessly falls back
    to LocalSemanticVectorizer for guaranteed offline reliability.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.local_vectorizer = LocalSemanticVectorizer()

    async def get_embeddings(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 768), dtype=np.float32)

        # Try Gemini API if key is available
        if self.api_key:
            try:
                # Direct REST call to Gemini Embeddings endpoint
                url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={self.api_key}"
                requests_payload = {
                    "requests": [
                        {"model": "models/text-embedding-004", "content": {"parts": [{"text": t[:2000]}]}}
                        for t in texts[:20]  # batch in chunks
                    ]
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=requests_payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        embeddings = [e["values"] for e in data.get("embeddings", [])]
                        if len(embeddings) == len(texts[:20]):
                            arr = np.array(embeddings, dtype=np.float32)
                            norms = np.linalg.norm(arr, axis=1, keepdims=True)
                            norms[norms == 0] = 1.0
                            return arr / norms
            except Exception:
                # Graceful fallback to local vectorizer
                pass

        # Local semantic vectorizer
        if not self.local_vectorizer.is_fitted:
            return self.local_vectorizer.fit_transform(texts)
        return self.local_vectorizer.transform(texts)
