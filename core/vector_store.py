from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Optional, Dict, Any
import uuid

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
DEFAULT_COLLECTION_NAME = "ptt_hr_feedback"
VECTOR_SIZE = 384
DEFAULT_TOP_K = 5

class QdrantVectorStore:
    def __init__(self, host: str = QDRANT_HOST, port: int = QDRANT_PORT, collection_name: str = DEFAULT_COLLECTION_NAME):
        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port)
        self._create_collection_if_not_exists()

    def _create_collection_if_not_exists(self):
        existing_collections = self.client.get_collections().collections
        if self.collection_name not in [c.name for c in existing_collections]:
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = DEFAULT_TOP_K
    ) -> List[models.ScoredPoint]:
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k
        )
        return results

    def insert_vectors(
        self,
        vectors: List[List[float]],
        ids: Optional[List[str]] = None,
        payloads: Optional[List[Dict[str, Any]]] = None
    ):
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        if payloads is None:
            payloads = [{} for _ in vectors]

        points = [
            models.PointStruct(id=id_, vector=vector, payload=payload)
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]

        self.client.upsert(collection_name=self.collection_name, points=points)