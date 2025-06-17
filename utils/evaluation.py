import pandas as pd
from typing import Dict, List, Any
from langchain.chains.base import Chain

TEST_QUESTIONS = {
    "1": {
        "question": "ระบบ PTT Secondment System มีปัญหาอะไรบ้างที่ส่งผลต่อการใช้งานของ HRBP?",
        "answer": """ระบบ PTT Secondment System มีปัญหาหลายประการ เช่น
- ไม่รองรับการกรอกข้อมูลเงินเดือนแบบ Matrix ของบางบริษัท
- การประมาณการค่าอากรแสตมป์ต้องกรอกข้อมูลทั้งหมดก่อนจึงจะคำนวณได้
- การแสดงผลจำนวนอากรแสตมป์เป็นเงินบาทไม่ถูกต้องในบางขั้นตอน
- ไม่สามารถแก้ไขข้อมูลที่กรอกผิดพลาดได้เอง ต้องแจ้งทีม Digital ให้ลบข้อมูล
- เมนูข้อมูลไม่สื่อความหมาย ทำให้ผู้ใช้งานสับสน"""
    },
    "2": {
        "question": "มีข้อเสนอแนะใดบ้างเกี่ยวกับการปรับปรุงกระบวนการ Employee Engagement Survey?",
        "answer": """ข้อเสนอแนะในการปรับปรุง Employee Engagement Survey ได้แก่
- ควรระบุให้ชัดเจนว่าข้อคำถามต้องการให้พนักงานนึกถึงภาพรวมของ ปตท. หรือเฉพาะหน่วยงาน
- เพิ่มคำถามปลายเปิดในแต่ละข้อเพื่อเก็บข้อมูลเชิงลึก
- ปรับภาษาข้อคำถามให้เข้าใจง่ายขึ้น
- แสดงผลสัมพันธ์ของมิติต่าง ๆ กับคะแนนความผูกพัน
- เพิ่มการรายงานผลแยกกลุ่มพนักงานเข้าใหม่"""
    },
    "3": {
        "question": "ปัญหาของพนักงานระดับ 10 ที่ติดกรอบอัตรากำลังคืออะไร และมีแนวทางแก้ไขอย่างไร?",
        "answer": """ปัญหาคือพนักงานระดับ 10 มีจำนวนมาก แต่ตำแหน่งระดับ 11 มีจำกัด ทำให้เติบโตได้ยาก แนวทางแก้ไขที่เสนอได้แก่
- พิจารณาเพิ่มตำแหน่ง Specialist Track
- ปรับ Demand-Supply ให้สมดุล
- ทบทวนเกณฑ์การเลื่อนระดับ
- จัดทำแผน Career Endpoint เพื่อวางแผนการเติบโตจนเกษียณ"""
    },
    "4": {
        "question": "การบริหารพนักงาน Secondment กลับมาปฏิบัติงานที่ ปตท. มีความท้าทายอะไรบ้าง?",
        "answer": """ความท้าทายได้แก่
- กรอบอัตรากำลังของหน่วยงานมีจำกัด
- การ Matching ระหว่างความต้องการของหน่วยงานและพนักงาน Secondment
- การคำนวณเงิน PIR และค่าอากรแสตมป์ที่ซับซ้อน
- แนวทางแก้ไขคือจัดทำ Special Project เพื่อรองรับพนักงานที่กลับมาจากบริษัทที่ปิดกิจการ"""
    },
    "5": {
        "question": "มีข้อร้องเรียนใดบ้างเกี่ยวกับสวัสดิการของพนักงาน และ HR มีการแก้ไขอย่างไร?",
        "answer": """ข้อร้องเรียนเกี่ยวกับสวัสดิการ เช่น
- ขอให้มีสวัสดิการสำหรับคนโสดหรือสัตว์เลี้ยง
- การเบิกค่ารักษาพยาบาลสำหรับคู่สมรสเพศเดียวกัน
- การเพิ่มทางเลือกการลงทุนในกองทุนสำรองเลี้ยงชีพ
- การสื่อความเกี่ยวกับสวัสดิการที่ไม่ชัดเจน

การแก้ไข:
- ปรับนโยบายรองรับสมรสเท่าเทียม
- พิจารณาขยายสวัสดิการให้ครอบคลุมความหลากหลาย
- จัดทำสื่อความประจำปีเกี่ยวกับสวัสดิการ"""
    },
    "6": {
        "question": "ระบบ COACH มีปัญหาอะไรบ้างที่ส่งผลต่อการใช้งาน?",
        "answer": """ปัญหาของระบบ COACH ได้แก่
- การแสดงผล Career Path ไม่ถูกต้อง
- ไม่สามารถลาป่วยล่วงหน้าได้
- การเชื่อมโยงกับระบบ LMS สำหรับ IDP Plan ไม่สมบูรณ์
- การประเมิน Behavior KPI ไม่มีมาตรฐานที่ชัดเจน"""
    },
    "7": {
        "question": "แนวทางการปรับปรุงกระบวนการ Candidate Scoring มีอะไรบ้าง?",
        "answer": """แนวทางการปรับปรุงได้แก่
- ปรับสัดส่วนคะแนนสำหรับตำแหน่ง Secondment ให้สมดุล
- เพิ่มเกณฑ์การคัดกรองคู่เทียบที่คะแนนห่างเกิน 30 คะแนน
- แสดงคะแนนสัมภาษณ์เท่านั้นสำหรับตำแหน่งระดับ 11-13
- ปรับการคิดคะแนน Experience ให้สอดคล้องกับความต้องการตำแหน่ง"""
    },
    "8": {
        "question": "มีข้อเสนอแนะใดบ้างเกี่ยวกับการปรับปรุงระบบ HRAS?",
        "answer": """ข้อเสนอแนะได้แก่
- เพิ่มปุ่ม Refresh ข้อมูลเงินตำแหน่งผู้บริหารสูงสุด/เงิน PIR
- ปรับปรุงการแสดงผลวันที่มีผลใน Action SAP
- รวบรวมคำสั่งประเภทเดียวกันเป็น Lot เดียวกัน
- แก้ไขการแสดงชื่อหน่วยงานให้เป็นรูปแบบเดียวกัน"""
    },
    "9": {
        "question": "ปัญหาของพนักงานที่ช่วยปฏิบัติงานโครงการ POWER คืออะไร?",
        "answer": """ปัญหาคือ
- การประเมินผลงานไม่สอดคล้องกับภาระงานที่เพิ่มขึ้น
- ไม่มีวงเงินจัดสรรเพิ่มเติมสำหรับค่าตอบแทน
- แนวทางการบริหาร Career หลังจบโครงการไม่ชัดเจน"""
    },
    "10": {
        "question": "แนวทางการพัฒนาพนักงานกลุ่ม DM Pool และ VP Pool มีอะไรบ้าง?",
        "answer": """แนวทางได้แก่
- กำหนดเกณฑ์การปิด Gap ที่ชัดเจน
- แจ้งผล Ranking ให้ผู้บังคับบัญชาทราบตั้งแต่ปีแรก
- พิจารณาผลการปิด Gap ประกอบการคัด Pool ออก
- จัดอบรมหลักสูตร Mini LDP ตามสัดส่วน Demand-Supply"""
    }
}
def evaluate_qa_chain(qa_chain: Chain, test_cases: Dict[str, Dict[str, str]] = None) -> pd.DataFrame:
    test_cases = test_cases or TEST_QUESTIONS
    results = []

    for key, qa in test_cases.items():
        question = qa["question"]
        expected = qa["answer"]
        try:
            response = qa_chain.invoke({"query": question})
            actual_answer = response.get("result", "")
            source_docs = response.get("source_documents", [])

            sources = [doc.metadata.get("source", "") for doc in source_docs if hasattr(doc, "metadata")]
            sources_str = ", ".join(filter(None, sources))

            match = expected.lower() in actual_answer.lower()

            results.append({
                "question": question,
                "expected": expected,
                "actual": actual_answer,
                "source": sources_str,
                "match": match,
            })
        except Exception as e:
            results.append({
                "question": question,
                "expected": expected,
                "actual": f"Error: {str(e)}",
                "source": "",
                "match": False,
            })

    return pd.DataFrame(results)

def calculate_metrics(eval_results: pd.DataFrame) -> Dict[str, Any]:
    if eval_results.empty:
        return {
            "accuracy": 0.0,
            "total_questions": 0,
            "correct_answers": 0,
        }

    accuracy = eval_results["match"].mean()
    total = len(eval_results)
    correct = eval_results["match"].sum()

    return {
        "accuracy": accuracy,
        "total_questions": total,
        "correct_answers": correct,
    }