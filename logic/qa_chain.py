from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chat_models import ChatOpenAI
from typing import Optional
from core.vector_store import QdrantVectorStore
from langchain_community.embeddings import HuggingFaceEmbeddings
from typing import List, Dict, Any
import os

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

def get_qa_chain(vectordb: QdrantVectorStore, model_name: str = "gpt-4.1-nano") -> Optional[RetrievalQA]:
    if vectordb is None:
        raise ValueError("Vector database is empty or not initialized")

    try:
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        # Set the API key in the environment
        os.environ["OPENAI_API_KEY"] = openai_api_key

        response_schemas = [
            ResponseSchema(name="answer", description="คำตอบของคำถาม"),
            ResponseSchema(name="note", description="หมายเหตุเพิ่มเติมหรือเว้นว่าง"),
        ]

        parser = StructuredOutputParser.from_response_schemas(response_schemas)

        prompt = PromptTemplate(
            template=DEFAULT_PROMPT_TEMPLATE + "\n\n" + parser.get_format_instructions(),
            input_variables=["context", "question"]
        )

        llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.2,
            max_tokens=1000,
            openai_api_key=openai_api_key  # Pass the API key directly
        )

        class CustomRetriever:
            def __init__(self, vector_store: QdrantVectorStore):
                self.vector_store = vector_store
            
            def get_relevant_documents(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
                query_embedding = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                    model_kwargs={"device": "cpu"}
                ).embed_query(query)
                
                results = self.vector_store.search_vectors(query_embedding, top_k=k)
                return [r.payload for r in results]

        retriever = CustomRetriever(vectordb)
        
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
