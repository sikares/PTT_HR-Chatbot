from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
from typing import List, Optional

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

def create_vector_store(chunks: List[str], collection_name: str = "ptt_hr_feedback") -> Qdrant:
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"}
    )
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        vectorstore = Qdrant.from_texts(
            texts=chunks,
            embedding=embeddings,
            collection_name=collection_name,
            client=client
        )
        return vectorstore
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return None

def update_vector_store(new_chunks: List[str], vectordb: Optional[Qdrant] = None, collection_name: str = "ptt_hr_feedback") -> Optional[Qdrant]:
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"}
    )
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

        if vectordb is None:
            return create_vector_store(new_chunks, collection_name=collection_name)

        vectordb.add_texts(new_chunks, embedding=embeddings)
        return vectordb
    except Exception as e:
        print(f"Error updating vector store: {e}")
        return None