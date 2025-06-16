import streamlit as st 
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import json
import os
from typing import List, Dict, Any

from auth.credentials import check_credentials, password_expired, validate_password_change
from logic.data_processing import clean_and_process_data
from logic.chunking import create_text_chunks, chunk_texts_intelligently
from utils.session import init_session_state
from core.embedding import create_vector_store
from core.qa_chain import get_qa_chain

def save_data_sources(data_sources: Dict[str, Any]):
    os.makedirs("data", exist_ok=True)
    with open("data/data_sources.json", "w", encoding="utf-8") as f:
        json.dump(data_sources, f, ensure_ascii=False, indent=2, default=str)

def load_data_sources() -> Dict[str, Any]:
    try:
        if os.path.exists("data/data_sources.json"):
            with open("data/data_sources.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading data sources: {e}")
    return {}

def save_processed_chunks(chunks: List[str]):
    os.makedirs("data", exist_ok=True)
    with open("data/processed_chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

def load_processed_chunks() -> List[str]:
    try:
        if os.path.exists("data/processed_chunks.json"):
            with open("data/processed_chunks.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading processed chunks: {e}")
    return []

def main():
    load_dotenv()
    st.set_page_config(
        page_title="PTT HR Chatbot",
        page_icon="icon/ptt.ico",
    )
    init_session_state()

    if "data_sources" not in st.session_state:
        st.session_state.data_sources = load_data_sources()
    
    if "all_chunks" not in st.session_state:
        st.session_state.all_chunks = load_processed_chunks()
        
    if st.session_state.all_chunks and 'vectordb' not in st.session_state:
        try:
            st.session_state.vectordb = create_vector_store(st.session_state.all_chunks)
            st.session_state.qa_chain = get_qa_chain(st.session_state.vectordb)
        except Exception as e:
            print(f"Error initializing vector store: {e}")

    if not st.session_state.authenticated:
        st.title("PTT HR Chatbot Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")

            if submit_button:
                if check_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.password_changed_date = datetime.now()
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Access denied.")
        return

    if password_expired(st.session_state.password_changed_date):
        st.warning("Your password has expired. Please change your password.")
        with st.form("password_change_form"):
            old_password = st.text_input("Old Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            change_button = st.form_submit_button("Change Password")

            if change_button:
                valid, msg = validate_password_change(old_password, new_password, confirm_password)
                if valid:
                    st.session_state.password_changed_date = datetime.now()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        return

    st.header("PTT HR Chatbot")
    st.markdown("""
    This chatbot allows you to ask questions about your uploaded Excel data.
    Upload Excel files and type in a question to get answers.
    """)

    user_question = st.text_input("Enter your question about the Excel data:")

    with st.sidebar:
        st.markdown('<div class="header">📁 Upload Excel Files</div>', unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Choose Excel files",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            help="Upload Excel files containing feedback data"
        )

        selected_columns = [
            "ที่มาของ Feedback",
            "BU",
            "ประเภท Feedback",
            "รายละเอียด Feedback",
            "แนวทางการดำเนินการ",
            "รายละเอียด Status"
        ]

        valid_files = []
        if uploaded_files:
            for file in uploaded_files:
                try:
                    df = pd.read_excel(file, engine='openpyxl' if file.name.endswith('.xlsx') else 'xlrd')
                    missing = [col for col in selected_columns if col not in df.columns]
                    if missing:
                        st.error(f"❌ `{file.name}` is missing columns: {', '.join(missing)}")
                    else:
                        valid_files.append((file.name, df))
                        st.success(f"✅ `{file.name}` is ready ({len(df)} rows)")
                        st.dataframe(df.head(5))
                except Exception as e:
                    st.error(f"❌ Cannot read file `{file.name}`: {str(e)}")

        if valid_files and st.button("⚙️ Process Data"):
            new_chunks = []

            with st.spinner("Processing all files..."):
                for name, df in valid_files:
                    processed = clean_and_process_data(df, selected_columns)
                    chunks = create_text_chunks(processed, selected_columns)
                    new_chunks.extend(chunks)

                    st.session_state.data_sources[name] = {
                        "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "rows": len(processed)
                    }

                st.session_state.all_chunks.extend(new_chunks)
                
                st.session_state.all_chunks = chunk_texts_intelligently(st.session_state.all_chunks)
                
                save_data_sources(st.session_state.data_sources)
                save_processed_chunks(st.session_state.all_chunks)
                
                st.session_state.vectordb = create_vector_store(st.session_state.all_chunks)
                st.session_state.qa_chain = get_qa_chain(st.session_state.vectordb)
                
                st.success(f"📦 Successfully created {len(st.session_state.all_chunks)} chunks")

        st.subheader("📋 Uploaded Files")

        if st.session_state.data_sources:
            for filename, info in st.session_state.data_sources.items():
                with st.expander(f"📄 {filename}"):
                    st.write(f"📅 Uploaded on: {info.get('upload_date', '-')}")
                    st.write(f"📊 Rows: {info.get('rows', 0):,}")
                    if st.button(f"🗑️ Delete {filename}", key=f"del_{filename}"):
                        del st.session_state.data_sources[filename]
                        save_data_sources(st.session_state.data_sources)
                        
                        if not st.session_state.data_sources:
                            st.session_state.all_chunks = []
                            save_processed_chunks([])
                            if 'vectordb' in st.session_state:
                                del st.session_state.vectordb
                            if 'qa_chain' in st.session_state:
                                del st.session_state.qa_chain
                        
                        st.success(f"✅ Deleted {filename}")
                        st.rerun()
        else:
            st.info("No files uploaded yet.")

    if st.session_state.qa_chain and user_question:
        with st.spinner("Searching for the answer..."):
            try:
                answer = st.session_state.qa_chain.run(user_question)
                st.markdown("### Your Answer:")
                st.write(answer)
                
                if "chat_history" not in st.session_state:
                    st.session_state.chat_history = []
                    
                st.session_state.chat_history.append({
                    "role": "user", 
                    "content": user_question,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": answer,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                
            except Exception as e:
                st.error(f"Error answering question: {e}")
    
    if "chat_history" in st.session_state and st.session_state.chat_history:
        st.subheader("💭 Chat History")
        
        for chat in reversed(st.session_state.chat_history[-10:]):
            if chat["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(f"**You** ({chat.get('timestamp', '')}):")
                    st.markdown(chat['content'])
            else:
                with st.chat_message("assistant"):
                    st.markdown(f"**Bot** ({chat.get('timestamp', '')}):")
                    st.markdown(chat['content'])
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()

def process_files(valid_files: List, selected_columns: List[str]):
    with st.spinner("⚙️ Processing files..."):
        new_chunks = []
        
        for filename, df in valid_files:
            try:
                processed_data = clean_and_process_data(df, selected_columns)
                
                st.session_state.data_sources[filename] = {
                    'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'rows': len(processed_data),
                    'columns': selected_columns
                }
                
                text_chunks = create_text_chunks(processed_data, selected_columns)
                new_chunks.extend(text_chunks)
                
                st.success(f"✅ Processed {filename} successfully ({len(text_chunks):,} chunks)")
                
            except Exception as e:
                st.error(f"❌ Error processing {filename}: {str(e)}")
        
        if new_chunks:
            st.session_state.all_chunks.extend(new_chunks)
            
            st.session_state.all_chunks = chunk_texts_intelligently(st.session_state.all_chunks)
            
            save_data_sources(st.session_state.data_sources)
            save_processed_chunks(st.session_state.all_chunks)
            
            st.session_state.vectordb = create_vector_store(st.session_state.all_chunks)
            st.session_state.qa_chain = get_qa_chain(st.session_state.vectordb)
            
            st.success(f"🎉 Data added successfully! Total {len(st.session_state.all_chunks):,} chunks")
            st.rerun()

def rebuild_chunks():
    if not st.session_state.data_sources:
        st.session_state.all_chunks = []
        if 'vectordb' in st.session_state:
            del st.session_state.vectordb
        if 'qa_chain' in st.session_state:
            del st.session_state.qa_chain
        save_processed_chunks([])
        return
    
    st.session_state.all_chunks = []
    if 'vectordb' in st.session_state:
        del st.session_state.vectordb
    if 'qa_chain' in st.session_state:
        del st.session_state.qa_chain
    save_processed_chunks([])
    
    st.warning("⚠️ Please upload files again to recreate the data")

if __name__ == "__main__":
    main()