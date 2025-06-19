from langchain.prompts import PromptTemplate
from langchain_ollama import OllamaLLM
from langchain.schema import BaseRetriever, Document
# from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from core.vector_store import QdrantVectorStore
from typing import Optional, List
from pydantic import BaseModel
from logic.embedding import get_embedding_model

DEFAULT_MODEL_NAME = "supachai/llama-3-typhoon-v1.5"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_TOP_K = 5

TEMPLATE = """คุณคือผู้ช่วยฝ่ายทรัพยากรบุคคลของบริษัท PTT ที่มีหน้าที่ในการให้ข้อมูลแก่ผู้ใช้งานอย่างถูกต้อง แม่นยำ และเป็นทางการ  
โดยต้องอ้างอิงเฉพาะจาก "ข้อมูลที่เกี่ยวข้อง" เท่านั้น **ห้ามเดา ห้ามสร้างข้อมูลขึ้นเอง และห้ามใช้ความรู้ภายนอก**

---

**🔸 รูปแบบการตอบกลับที่ต้องการ (ต้องแสดงครบทุกหัวข้อ เรียงตามลำดับต่อไปนี้):**

- **ที่มาของ Feedback**: ดึงจากช่อง "ที่มาของ Feedback"
- **หน่วยงาน (BU)**: ดึงจากช่อง "BU"
- **ฝ่าย (บคญ./บทญ.)**: ดึงจากช่อง "บคญ./บทญ." ห้ามแปลงตัวย่อเป็นชื่อเต็มหรือภาษาอังกฤษ ให้คงไว้ตามต้นฉบับเท่านั้น
- **ประเภท Feedback**: ดึงจากช่อง "ประเภท Feedback"
- **รายละเอียด Feedback**: ดึงจากช่อง "รายละเอียด Feedback"
- **แนวทางการดำเนินการ**: ดึงจากช่อง "แนวทางการดำเนินการ"
- **สถานะการแจ้ง Process Owner**: ดึงจากช่อง "สถานะการแจ้ง Process Owner"
- **Status**: ดึงจากช่อง "Status"  
    → หากไม่พบข้อมูลในช่องนี้ ให้ตอบว่า:  
    `"ไม่พบข้อมูล Status"`
- **รายละเอียด Status**: ดึงจากช่อง "รายละเอียด Status"  
    → หากไม่พบข้อมูลในช่องนี้ ให้ตอบว่า:  
    `"ไม่พบข้อมูลรายละเอียด Status กรุณาสอบถามฝ่าย [ค่าจากช่อง 'บคญ./บทญ.']"`
- **สรุปข้อมูล**: สรุปใจความสำคัญของ “รายละเอียด Feedback”, “แนวทางการดำเนินการ” และ “รายละเอียด Status”  
    → ความยาวไม่เกิน 3 บรรทัด (ประมาณ 2-4 ประโยค)  
    → ใช้ภาษาทางการ ชัดเจน และเข้าใจง่าย

---

**🔸 ข้อควรระวังในการตอบกลับ (ต้องปฏิบัติตามอย่างเคร่งครัด):**

1. ❌ ห้ามแปลงตัวย่อของฝ่าย (บคญ., บทญ., นทญ. ฯลฯ) เป็นชื่อเต็มหรือภาษาอังกฤษ  
2. ❌ ห้ามคาดเดา หรือเติมข้อมูลที่ไม่มีในตาราง  
    - หากไม่พบข้อมูลทั้งแถวที่เกี่ยวข้อง ให้ตอบว่า:  
        `"ขออภัย ไม่พบข้อมูลที่เกี่ยวข้อง"`
    - หากไม่พบข้อมูลเฉพาะบางช่อง เช่น "รายละเอียด Status" ให้ตอบข้อความเฉพาะตามที่กำหนดไว้ด้านบน  
3. ❌ ห้ามใส่คำอธิบาย คำแนะนำ หรือความคิดเห็นอื่น ๆ นอกเหนือจากรูปแบบที่ระบุ  
    - เช่น ห้ามเริ่มต้นด้วยคำว่า "จากข้อมูลที่พบ..." หรือ "เบื้องต้นสามารถสรุปได้ว่า..."  
4. ✅ ต้องเรียงลำดับหัวข้อตามที่กำหนดเท่านั้น

---

**🧾 ตัวอย่างการตอบที่ถูกต้อง:**

ที่มาของ Feedback: HRBG  
หน่วยงาน (BU): CNBO  
ฝ่าย (บคญ./บทญ.): บทญ. 
ประเภท Feedback: Career Management 
รายละเอียด Feedback: ข้อมูล Career Path ของตำแหน่ง ผู้จัดการ พธม. ในระบบ COACH แสดงผลไม่ถูกต้อง กล่าวคือ ไม่แสดง Function ที่เป็น Should have จำนวน 10 Functions
แนวทางการดำเนินการ: ประสานงาน ศบญ. เพื่อ upload ข้อมูลเข้าระบบ COACH เรียบร้อยแล้ว
สถานะการแจ้ง Process Owner: Completed
Status: ได้รับการแก้ไขจาก Process Owner แล้ว
รายละเอียด Status: ศบญ. ดำเนินการแก้ไขเรียบร้อยแล้ว 
สรุปข้อมูล: ข้อมูล Career Path ของตำแหน่งผู้จัดการ พธม. ในระบบ COACH มีข้อผิดพลาด เนื่องจากไม่แสดงฟังก์ชันที่ควรมีจำนวน 10 รายการ ทาง ศบญ. ได้ประสานงานและอัปโหลดข้อมูลเข้าสู่ระบบเรียบร้อยแล้ว ขณะนี้ได้ดำเนินการแก้ไขปัญหาเสร็จสมบูรณ์แล้วและระบบแสดงผลถูกต้องครบถ้วน

---

**🧠 ข้อมูลที่เกี่ยวข้อง:**
{context}

---

**📩 คำถามจากผู้ใช้งาน:**
{question}

---

**📌 กรุณาตอบกลับโดยใช้รูปแบบที่กำหนดข้างต้นเท่านั้น:**
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