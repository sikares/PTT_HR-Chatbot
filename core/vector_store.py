from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Optional, Dict, Any
import uuid
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vector_store.log'),
        logging.StreamHandler()
    ]
)

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
DEFAULT_COLLECTION_NAME = "ptt_hr_feedback"
VECTOR_SIZE = 384
DEFAULT_TOP_K = 5

class QdrantVectorStore:
    def __init__(self, host: str = QDRANT_HOST, port: int = QDRANT_PORT, collection_name: str = DEFAULT_COLLECTION_NAME):
        logging.info(f"Initializing QdrantVectorStore with host={host}, port={port}, collection={collection_name}")
        self.collection_name = collection_name
        self.client = QdrantClient(host=host, port=port)
        try:
            self._create_collection_if_not_exists()
            logging.info(f"Successfully initialized collection {self.collection_name}")
        except Exception as e:
            logging.error(f"Failed to initialize collection: {str(e)}")
            raise

    def _create_collection_if_not_exists(self):
        logging.info(f"Checking if collection {self.collection_name} exists")
        try:
            existing_collections = self.client.get_collections().collections
            collection_names = [c.name for c in existing_collections]
            logging.debug(f"Existing collections: {collection_names}")
            
            if self.collection_name not in collection_names:
                logging.info(f"Creating new collection {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=VECTOR_SIZE,
                        distance=models.Distance.COSINE
                    )
                )
                logging.info(f"Successfully created collection {self.collection_name}")
            else:
                logging.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logging.error(f"Error checking/creating collection: {str(e)}")
            raise

    def search_vectors(self, query_vector: List[float], top_k: int = DEFAULT_TOP_K) -> List[models.ScoredPoint]:
        logging.info(f"Starting vector search with top_k={top_k}")
        logging.debug(f"Query vector length: {len(query_vector)}")
        
        if len(query_vector) != VECTOR_SIZE:
            logging.error(f"Query vector dimension mismatch! Expected {VECTOR_SIZE}, got {len(query_vector)}")
            raise ValueError(f"Query vector size {len(query_vector)} does not match expected {VECTOR_SIZE}")

        if any(x is None or not isinstance(x, float) for x in query_vector):
            logging.error("Query vector contains invalid entries")
            raise ValueError("Query vector contains non-float or None values")
        
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            logging.info(f"Search completed successfully. Found {len(results)} results")
            return results
        except Exception as e:
            logging.error(f"Error during search operation: {str(e)}", exc_info=True)
            raise

    def insert_vectors(
        self,
        vectors: List[List[float]],
        ids: Optional[List[str]] = None,
        payloads: Optional[List[Dict[str, Any]]] = None
    ):
        logging.info(f"Inserting {len(vectors)} vectors into collection {self.collection_name}")
        if not vectors:
            logging.info("No vectors to insert")
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
            logging.info(f"Successfully inserted {len(vectors)} vectors")
        except Exception as e:
            logging.error(f"Error inserting vectors: {str(e)}")

    def count_vectors(self) -> int:
        logging.info(f"Getting vector count for collection {self.collection_name}")
        try:
            info = self.get_collection_info()
            if info:
                logging.info(f"Collection {self.collection_name} has {info.points_count} vectors")
                return info.points_count
            logging.info(f"Collection {self.collection_name} has no vectors")
            return 0
        except Exception as e:
            logging.error(f"Error counting vectors: {str(e)}")
            return 0

    def delete_vectors(self, ids: List[str]):
        logging.info(f"Deleting {len(ids)} vectors from collection {self.collection_name}")
        try:
            if ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(
                        points=ids
                    )
                )
                logging.info(f"Successfully deleted {len(ids)} vectors")
        except Exception as e:
            logging.error(f"Error deleting vectors: {str(e)}")
            raise e

    def get_collection_info(self):
        logging.info(f"Getting info for collection {self.collection_name}")
        try:
            return self.client.get_collection(self.collection_name)
        except Exception as e:
            logging.error(f"Error getting collection info: {str(e)}")
            return None

    def collection_exists(self) -> bool:
        logging.info(f"Checking if collection {self.collection_name} exists")
        try:
            existing_collections = self.client.get_collections().collections
            exists = self.collection_name in [c.name for c in existing_collections]
            logging.info(f"Collection {self.collection_name} exists: {exists}")
            return exists
        except Exception as e:
            logging.error(f"Error checking collection existence: {str(e)}")
            return False

    def delete_by_filename(self, filename: str):
        logging.info(f"Deleting vectors by filename {filename} from collection {self.collection_name}")
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
                logging.info(f"Successfully deleted vectors by filename {filename}")
        except Exception as e:
            logging.error(f"Error deleting by filename: {str(e)}", exc_info=True)
            raise e