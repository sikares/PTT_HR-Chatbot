from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from typing import Optional
from langchain_community.vectorstores import Chroma
import os

DEFAULT_PROMPT_TEMPLATE = """
คุณเป็นผู้ช่วยฝ่ายทรัพยากรบุคคลของ PTT โปรดใช้ข้อมูลต่อไปนี้เพื่อตอบคำถามเกี่ยวกับ feedback ของพนักงาน
หากไม่แน่ใจหรือไม่มีข้อมูล ให้ตอบว่า 'ไม่พบข้อมูลที่เกี่ยวข้อง'

ข้อมูลที่เกี่ยวข้อง:
{context}

คำถาม: {question}
คำตอบที่เป็นภาษาไทยที่ชัดเจนและเป็นมิตร:
"""

def get_qa_chain(vectordb: Chroma, model_name: str = "gpt-4o-mini") -> Optional[RetrievalQA]:
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OpenAI API key is not set in environment variables")
    
    if vectordb is None or len(vectordb.get()['documents']) == 0:
        raise ValueError("Vector database is empty or not initialized")

    try:
        llm = ChatOpenAI(
            model_name=model_name,
            temperature=0.2,
            max_tokens=1000,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        prompt = PromptTemplate(
            template=DEFAULT_PROMPT_TEMPLATE,
            input_variables=["context", "question"]
        )
        
        return RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectordb.as_retriever(search_kwargs={"k": 5}),
            chain_type_kwargs={"prompt": prompt},
            return_source_documents=True
        )
    except Exception as e:
        print(f"Error creating QA chain: {str(e)}")
        return None