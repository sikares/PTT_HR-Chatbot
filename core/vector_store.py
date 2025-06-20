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
        try:
            existing_collections = self.client.get_collections().collections
            collection_names = [c.name for c in existing_collections]
            
            if self.collection_name not in collection_names:
                self.client.recreate_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=VECTOR_SIZE,
                        distance=models.Distance.COSINE
                    )
                )
        except Exception as e:
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
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            return results
        except Exception as e:
            print(f"Error searching vectors: {e}")
            return []

    def insert_vectors(
        self,
        vectors: List[List[float]],
        ids: Optional[List[str]] = None,
        payloads: Optional[List[Dict[str, Any]]] = None
    ):
        if not vectors:
            return
            
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        if payloads is None:
            payloads = [{} for _ in vectors]

        points = [
            models.PointStruct(id=id_, vector=vector, payload=payload)
            for id_, vector, payload in zip(ids, vectors, payloads)
        ]

        try:
            self.client.upsert(collection_name=self.collection_name, points=points)
        except Exception as e:
            print(f"Error inserting vectors: {e}")
    def count_vectors(self) -> int:
        try:
            info = self.get_collection_info()
            if info:
                return info.points_count
            return 0
        except Exception as e:
            print(f"Error counting vectors: {e}")
            return 0

    def delete_vectors(self, ids: List[str]):
        try:
            if ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=ids
                    )
                )
        except Exception as e:
            print(f"Error deleting vectors: {e}")
            raise e

    def get_collection_info(self):
        try:
            return self.client.get_collection(self.collection_name)
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return None

    def collection_exists(self) -> bool:
        try:
            existing_collections = self.client.get_collections().collections
            return self.collection_name in [c.name for c in existing_collections]
        except Exception as e:
            print(f"Error checking collection existence: {e}")
            return False

    def delete_by_filename(self, filename: str):
        try:
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="filename",
                            match=models.MatchValue(value=filename)
                        )
                    ]
                ),
                limit=1000
            )
            
            point_ids = [point.id for point in scroll_result[0]]
            
            if point_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(points=point_ids)
                )
                
        except Exception as e:
            print(f"Error deleting by filename: {e}")
            raise e