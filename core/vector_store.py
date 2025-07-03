from pinecone import Pinecone, ServerlessSpec
from typing import List, Optional, Dict, Any
import uuid
import logging
import os

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vector_store.log'),
        logging.StreamHandler()
    ]
)

DEFAULT_INDEX_NAME = "ptt-hr-feedback"
VECTOR_SIZE = 384
DEFAULT_TOP_K = 5

class PineconeVectorStore:
    def __init__(self, index_name: str = DEFAULT_INDEX_NAME):
        logging.info(f"Initializing PineconeVectorStore with index={index_name}")
        self.index_name = index_name
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        spec = ServerlessSpec(cloud="aws", region="us-east-1")
        if self.index_name not in [i.name for i in self.pc.list_indexes()]:
            self.pc.create_index(name=self.index_name, dimension=VECTOR_SIZE, metric="cosine", spec=spec)
        self.index = self.pc.Index(self.index_name)
        logging.info(f"Successfully initialized Pinecone index {self.index_name}")

    def search_vectors(self, query_vector: List[float], top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        logging.info(f"Starting vector search with top_k={top_k}")
        logging.debug(f"Query vector length: {len(query_vector)}")
        if len(query_vector) != VECTOR_SIZE:
            logging.error(f"Query vector dimension mismatch! Expected {VECTOR_SIZE}, got {len(query_vector)}")
            raise ValueError(f"Query vector size {len(query_vector)} does not match expected {VECTOR_SIZE}")
        results = self.index.query(vector=query_vector, top_k=top_k, include_metadata=True)
        logging.info(f"Search completed successfully. Found {len(results.matches)} results")
        return results.matches

    def insert_vectors(
        self,
        vectors: List[List[float]],
        ids: Optional[List[str]] = None,
        payloads: Optional[List[Dict[str, Any]]] = None
    ):
        logging.info(f"Inserting {len(vectors)} vectors into index {self.index_name}")
        if not vectors:
            logging.info("No vectors to insert")
            return
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        if payloads is None:
            payloads = [{} for _ in vectors]
        to_upsert = list(zip(ids, vectors, payloads))
        self.index.upsert(vectors=to_upsert)
        logging.info(f"Successfully inserted {len(vectors)} vectors")

    def delete_vectors(self, ids: List[str]):
        logging.info(f"Deleting {len(ids)} vectors from index {self.index_name}")
        if ids:
            self.index.delete(ids=ids)
            logging.info(f"Successfully deleted {len(ids)} vectors")
