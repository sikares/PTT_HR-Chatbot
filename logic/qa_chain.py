from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.schema import BaseRetriever
from core.vector_store import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

DEFAULT_PROMPT_TEMPLATE = """
คุณเป็นผู้ช่วยฝ่ายทรัพยากรบุคคลของ PTT โปรดใช้ข้อมูลต่อไปนี้เพื่อตอบคำถามเกี่ยวกับ feedback ของพนักงาน
หากไม่แน่ใจหรือไม่มีข้อมูล ให้ตอบว่า 'ไม่พบข้อมูลที่เกี่ยวข้อง'

ข้อมูลที่เกี่ยวข้อง:
{context}

คำถาม: {question}
โปรดตอบกลับในรูปแบบ JSON ตามนี้เท่านั้น:
{{
    "answer": "<คำตอบ>",
    "note": "<หมายเหตุเพิ่มเติมหรือเว้นว่าง>"
}}
"""

DEFAULT_MODEL_NAME = "supachai/llama-3-typhoon-v1.5"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TOP_K = 5
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_MODEL_KWARGS = {"device": "cpu"}

def get_embedding_model() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs=EMBEDDING_MODEL_KWARGS
    )

def get_qa_chain(vectordb: QdrantVectorStore, model_name: str = DEFAULT_MODEL_NAME) -> Optional[RetrievalQA]:
    if vectordb is None:
        raise ValueError("Vector database is empty or not initialized")

    try:
        response_schemas = [
            ResponseSchema(name="answer", description="คำตอบของคำถาม"),
            ResponseSchema(name="note", description="หมายเหตุเพิ่มเติมหรือเว้นว่าง"),
        ]

        parser = StructuredOutputParser.from_response_schemas(response_schemas)

        prompt = PromptTemplate(
            template=DEFAULT_PROMPT_TEMPLATE + "\n\n" + parser.get_format_instructions(),
            input_variables=["context", "question"]
        )

        llm = OllamaLLM(
            model=model_name,
            temperature=DEFAULT_TEMPERATURE,
        )

        class CustomRetriever(BaseRetriever, BaseModel):
            vector_store: QdrantVectorStore

            def get_relevant_documents(self, query: str, **kwargs) -> List[Dict[str, Any]]:
                k = kwargs.get("k", DEFAULT_TOP_K)
                query_embedding = get_embedding_model().embed_query(query)

                results = self.vector_store.search_vectors(query_embedding, top_k=k)
                return [r.payload for r in results]

        retriever = CustomRetriever(vector_store=vectordb)

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={
                "prompt": prompt,
            }
        )
        return qa_chain
    except Exception as e:
        print(f"Error creating QA chain: {e}")
        return None
