from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain.schema import BaseRetriever, Document
from core.vector_store import QdrantVectorStore
from typing import Optional, List
from pydantic import BaseModel
from logic.embedding import get_embedding_model

DEFAULT_MODEL_NAME = "supachai/llama-3-typhoon-v1.5"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_K = 5

TEMPLATE = """คุณเป็นผู้ช่วยฝ่ายทรัพยากรบุคคลของ PTT โปรดใช้ข้อมูลต่อไปนี้เพื่อตอบคำถามเกี่ยวกับ feedback ของพนักงาน
หากไม่แน่ใจหรือไม่มีข้อมูล ให้ตอบว่า 'ขออภัย ไม่พบข้อมูลที่เกี่ยวข้อง'

ข้อมูลที่เกี่ยวข้อง:
{context}

คำถาม:
{question}

กรุณาตอบในรูปแบบภาษาไทยที่เป็นธรรมชาติ สุภาพ และเข้าใจง่าย โดย:
1. ใช้ภาษาที่สุภาพเหมาะสม
2. อธิบายให้ชัดเจน
3. เพิ่มรายละเอียดที่เกี่ยวข้องหากมี
"""

class CustomRetriever(BaseRetriever, BaseModel):
    vector_store: QdrantVectorStore

    def get_relevant_documents(self, query: str) -> List[Document]:
        query_embedding = get_embedding_model().embed_query(query)
        results = self.vector_store.search_vectors(
            query_vector=query_embedding,
            top_k=DEFAULT_TOP_K
        )
        
        documents = []
        for result in results:
            if hasattr(result, 'payload') and isinstance(result.payload, dict):
                doc = Document(
                    page_content=result.payload.get('text', ''),
                    metadata={
                        'score': getattr(result, 'score', None),
                        'source': result.payload.get('source', '')
                    }
                )
                documents.append(doc)
        return documents

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        return await super().aget_relevant_documents(query)

def get_qa_chain(vectordb: QdrantVectorStore, model_name: str = DEFAULT_MODEL_NAME) -> Optional[RetrievalQA]:
    if not vectordb:
        raise ValueError("Vector database is empty or not initialized")

    try:
        prompt = PromptTemplate(
            template=TEMPLATE,
            input_variables=["context", "question"]
        )

        llm = OllamaLLM(
            model=model_name,
            temperature=DEFAULT_TEMPERATURE
        )

        retriever = CustomRetriever(vector_store=vectordb)

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )

        return qa_chain

    except Exception as e:
        print(f"Error creating QA chain: {e}")
        return None