from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from typing import List, Optional

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
DEFAULT_COLLECTION_NAME = "ptt_hr_feedback"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_MODEL_KWARGS = {"device": "cpu"}

def get_embedding_model() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs=EMBEDDING_MODEL_KWARGS
    )

def create_vector_store(chunks: List[str], collection_name: str = DEFAULT_COLLECTION_NAME) -> Qdrant:
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        vectorstore = Qdrant.from_texts(
            texts=chunks,
            embedding=get_embedding_model(),
            collection_name=collection_name,
            client=client
        )
        return vectorstore
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return None

def update_vector_store(new_chunks: List[str], vectordb: Optional[Qdrant] = None, collection_name: str = DEFAULT_COLLECTION_NAME) -> Optional[Qdrant]:
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        if vectordb is None:
            return create_vector_store(new_chunks, collection_name=collection_name)

        vectordb.add_texts(new_chunks, embedding=get_embedding_model())
        return vectordb
    except Exception as e:
        print(f"Error updating vector store: {e}")
        return None