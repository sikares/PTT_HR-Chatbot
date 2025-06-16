import streamlit as st
import pandas as pd
from datetime import datetime
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from auth.credentials import check_credentials, password_expired, validate_password_change
from logic.data_processing import clean_and_process_data
from logic.chunking import create_text_chunks, chunk_texts_intelligently
from core.embedding import create_vector_store, update_vector_store
from core.qa_chain import get_qa_chain
from utils.session import init_session_state, reset_session_state, update_data_sources
from utils.feedback import log_feedback, get_feedback_stats
from utils.evaluation import evaluate_qa_chain, calculate_metrics

SELECTED_COLUMNS = [
    "ที่มาของ Feedback",
    "BU",
    "ประเภท Feedback",
    "รายละเอียด Feedback",
    "แนวทางการดำเนินการ",
    "รายละเอียด Status"
]
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def save_data_sources(data_sources: Dict[str, Any]):
    with open(DATA_DIR / "data_sources.json", "w", encoding="utf-8") as f:
        json.dump(data_sources, f, ensure_ascii=False, indent=2, default=str)

def load_data_sources() -> Dict[str, Any]:
    try:
        if (DATA_DIR / "data_sources.json").exists():
            with open(DATA_DIR / "data_sources.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading data sources: {e}")
    return {}

def save_processed_chunks(chunks: List[str]):
    with open(DATA_DIR / "processed_chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

def load_processed_chunks() -> List[str]:
    try:
        if (DATA_DIR / "processed_chunks.json").exists():
            with open(DATA_DIR / "processed_chunks.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading processed chunks: {e}")
    return []

def process_uploaded_files(uploaded_files: List) -> Tuple[List[str], Dict[str, Any]]:
    new_chunks = []
    file_info = {}
    
    for file in uploaded_files:
        try:
            df = pd.read_excel(file)
            processed_data = clean_and_process_data(df, SELECTED_COLUMNS)
            chunks = create_text_chunks(processed_data, SELECTED_COLUMNS)
            new_chunks.extend(chunks)
            
            file_info[file.name] = {
                "upload_date": datetime.now().isoformat(),
                "rows": len(processed_data),
                "chunks": len(chunks)
            }
            
            st.success(f"✅ Processed {file.name} ({len(chunks)} chunks)")
        except Exception as e:
            st.error(f"❌ Failed to process {file.name}: {str(e)}")
    
    if new_chunks:
        new_chunks = chunk_texts_intelligently(new_chunks)
    
    return new_chunks, file_info

def display_chat_history():
    if "chat_history" not in st.session_state or not st.session_state.chat_history:
        return
    
    st.subheader("💬 Chat History")
    
    for i, chat in enumerate(reversed(st.session_state.chat_history[-10:])):
        with st.container():
            if chat["role"] == "user":
                st.markdown(f"**You**: {chat['content']}")
            else:
                cols = st.columns([0.9, 0.1])
                with cols[0]:
                    st.markdown(f"**Assistant**: {chat['content']}")
                with cols[1]:
                    if st.button("👍", key=f"like_{i}"):
                        log_feedback(
                            st.session_state.chat_history[-2]['content'],
                            chat['content'],
                            "like"
                        )
                        st.success("Thanks for your feedback!")
                    if st.button("👎", key=f"dislike_{i}"):
                        log_feedback(
                            st.session_state.chat_history[-2]['content'],
                            chat['content'],
                            "dislike"
                        )
                        st.error("We'll improve this answer!")

def main():
    st.set_page_config(
        page_title="PTT HR Chatbot",
        page_icon="icon/ptt.ico",
        layout="wide"
    )
    init_session_state()
    
    if "data_sources" not in st.session_state:
        st.session_state.data_sources = load_data_sources()
    if "all_chunks" not in st.session_state:
        st.session_state.all_chunks = load_processed_chunks()
    
    if not st.session_state.authenticated:
        show_login_page()
        return
    
    if password_expired(st.session_state.password_changed_date):
        show_password_change_page()
        return
    
    st.title("PTT HR Feedback Chatbot")
    st.markdown("Analyze employee feedback data with AI")
    
    with st.sidebar:
        st.header("📂 Data Management")
        uploaded_files = st.file_uploader(
            "Upload Excel Files",
            type=["xlsx", "xls"],
            accept_multiple_files=True
        )
        
        if uploaded_files and st.button("Process Files"):
            with st.spinner("Processing files..."):
                new_chunks, file_info = process_uploaded_files(uploaded_files)
                
                if new_chunks:
                    st.session_state.all_chunks.extend(new_chunks)
                    update_data_sources(file_info)
                    save_data_sources(st.session_state.data_sources)
                    save_processed_chunks(st.session_state.all_chunks)
                    
                    try:
                        if st.session_state.vectordb:
                            st.session_state.vectordb = update_vector_store(
                                new_chunks,
                                st.session_state.vectordb
                            )
                        else:
                            st.session_state.vectordb = create_vector_store(st.session_state.all_chunks)
                        
                        st.session_state.qa_chain = get_qa_chain(st.session_state.vectordb)
                        st.success("✅ Data processing complete!")
                    except Exception as e:
                        st.error(f"Failed to create QA chain: {str(e)}")
        
        st.subheader("📋 Uploaded Files")
        if st.session_state.data_sources:
            for filename, info in st.session_state.data_sources.items():
                with st.expander(f"📄 {filename}"):
                    st.write(f"📅 Uploaded: {info.get('upload_date', 'N/A')}")
                    st.write(f"📊 Rows: {info.get('rows', 0):,}")
                    st.write(f"🧩 Chunks: {info.get('chunks', 0):,}")
                    
                    if st.button(f"Delete {filename}", key=f"del_{filename}"):
                        del st.session_state.data_sources[filename]
                        save_data_sources(st.session_state.data_sources)
                        
                        st.session_state.all_chunks = []
                        for name, info in st.session_state.data_sources.items():
                            st.session_state.all_chunks.extend(info.get("chunks", []))
                        
                        save_processed_chunks(st.session_state.all_chunks)
                        
                        if st.session_state.all_chunks:
                            st.session_state.vectordb = create_vector_store(st.session_state.all_chunks)
                            st.session_state.qa_chain = get_qa_chain(st.session_state.vectordb)
                        else:
                            st.session_state.vectordb = None
                            st.session_state.qa_chain = None
                        
                        st.rerun()
        else:
            st.info("No files uploaded yet")
        
        if st.session_state.qa_chain and st.checkbox("Run Evaluation"):
            with st.spinner("Evaluating QA chain..."):
                eval_results = evaluate_qa_chain(st.session_state.qa_chain)
                metrics = calculate_metrics(eval_results)
                
                st.subheader("Evaluation Results")
                st.write(f"Accuracy: {metrics['accuracy']:.2%}")
                st.write(f"Correct Answers: {metrics['correct_answers']}/{metrics['total_questions']}")
                
                if st.checkbox("Show Detailed Results"):
                    st.dataframe(eval_results)
    
    user_question = st.chat_input("Ask about the feedback data...")
    
    if user_question and st.session_state.qa_chain:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question,
            "timestamp": datetime.now().isoformat()
        })
        
        with st.spinner("Searching for answers..."):
            try:
                response = st.session_state.qa_chain({"query": user_question})
                answer = response["result"]
                
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "timestamp": datetime.now().isoformat()
                })
                
                st.rerun()
            except Exception as e:
                st.error(f"Error answering question: {str(e)}")
    
    display_chat_history()

def show_login_page():
    st.title("PTT HR Chatbot Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.form_submit_button("Login"):
            if check_credentials(username, password):
                st.session_state.authenticated = True
                st.session_state.password_changed_date = datetime.now()
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")

def show_password_change_page():
    st.warning("Your password has expired. Please change your password.")
    
    with st.form("password_change_form"):
        old_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.form_submit_button("Change Password"):
            valid, message = validate_password_change(old_password, new_password, confirm_password)
            if valid:
                st.session_state.password_changed_date = datetime.now()
                st.success(message)
                st.rerun()
            else:
                st.error(message)

if __name__ == "__main__":
    main()