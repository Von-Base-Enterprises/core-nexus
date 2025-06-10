"""
Lightweight Vector Store using FAISS for fast similarity search.
Optimized for Day-1 slice with minimal dependencies.
"""

import json
import math
import os
from typing import Any


class LiteVectorStore:
    """Simple JSON-based vector store for Day-1 slice demo"""

    def __init__(self, store_file: str = "vector_store.json"):
        self.store_file = store_file
        self.data = {"vectors": {}, "metadata": {}}
        self._load_store()

    def _load_store(self):
        """Load existing store or create new one"""
        if os.path.exists(self.store_file):
            try:
                with open(self.store_file) as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {"vectors": {}, "metadata": {}}

    def _save_store(self):
        """Save store to disk"""
        os.makedirs(os.path.dirname(self.store_file) if os.path.dirname(self.store_file) else ".", exist_ok=True)
        with open(self.store_file, 'w') as f:
            json.dump(self.data, f)

    def upsert(self, doc_id: str, embedding: list[float], metadata: dict[str, Any]) -> None:
        """Store vector with metadata"""
        self.data["vectors"][doc_id] = embedding
        self.data["metadata"][doc_id] = metadata
        self._save_store()

    def search(self, query_embedding: list[float], k: int = 5) -> list[tuple[str, float, dict[str, Any]]]:
        """Search for similar vectors using cosine similarity"""
        if not self.data["vectors"]:
            return []

        similarities = []
        for doc_id, embedding in self.data["vectors"].items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            metadata = self.data["metadata"].get(doc_id, {})
            similarities.append((doc_id, similarity, metadata))

        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

    def get(self, doc_id: str) -> tuple[list[float], dict[str, Any]] | None:
        """Get vector and metadata by ID"""
        if doc_id in self.data["vectors"]:
            return self.data["vectors"][doc_id], self.data["metadata"].get(doc_id, {})
        return None

    def delete(self, doc_id: str) -> bool:
        """Delete vector by ID"""
        if doc_id in self.data["vectors"]:
            del self.data["vectors"][doc_id]
            self.data["metadata"].pop(doc_id, None)
            self._save_store()
            return True
        return False

    def count(self) -> int:
        """Get number of stored vectors"""
        return len(self.data["vectors"])

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
