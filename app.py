import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import shelve
from dotenv import load_dotenv
import time
import uuid
import hashlib

load_dotenv()

from logic.data_processing import clean_and_process_data
from logic.chunking import create_text_chunks, chunk_texts_intelligently
from logic.embedding import get_embedding_model
from logic.qa_chain import get_qa_chain
from utils.session import init_session_state, update_data_sources, load_data_sources, save_data_sources
from utils.auth import require_auth, show_logout_button, is_authenticated, show_login_form, is_admin, show_admin_panel
from core.vector_store import QdrantVectorStore

USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

SELECTED_COLUMNS = [
    "ที่มาของ Feedback",
    "BU",
    "บคญ./บทญ.",
    "ประเภท Feedback",
    "รายละเอียด Feedback",
    "แนวทางการดำเนินการ",
    "สถานะการแจ้ง Process Owner ",
    "Status",
    "รายละเอียด Status"
]

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_SIZE_MB = 20
CHAT_DB = "ptt_chat_history_sessions"

def load_all_chats() -> Dict[str, List[Dict]]:
    try:
        with shelve.open(CHAT_DB) as db:
            return db.get("chats", {})
    except Exception as e:
        st.error(f"Error loading chat sessions: {e}")
        return {}

def save_all_chats(chats: Dict[str, List[Dict]]):
    try:
        with shelve.open(CHAT_DB) as db:
            db["chats"] = chats
    except Exception as e:
        st.error(f"Error saving chat sessions: {e}")

def get_file_hash(file_content: bytes) -> str:
    return hashlib.md5(file_content).hexdigest()

def initialize_vector_store():
    try:
        vector_store = QdrantVectorStore()
        st.session_state.vectordb = vector_store
        
        data_sources = load_data_sources()
        if data_sources:
            st.session_state.qa_chain = get_qa_chain(vector_store)
            st.session_state.data_sources = data_sources
        else:
            st.session_state.qa_chain = None
            
    except Exception as e:
        st.error(f"Error initializing vector store: {e}")
        st.session_state.vectordb = None
        st.session_state.qa_chain = None

def process_uploaded_files(uploaded_files: List) -> Tuple[List[str], Dict[str, Any]]:
    new_chunks = []
    file_info = {}
    vector_store = st.session_state.vectordb

    upload_dir = DATA_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    for file in uploaded_files:
        file.seek(0, 2)
        size_mb = file.tell() / (1024 * 1024)
        file.seek(0)
        if size_mb > MAX_UPLOAD_SIZE_MB:
            st.error(f"❌ {file.name} file size is larger than {MAX_UPLOAD_SIZE_MB} MB")
            continue

        file_content = file.getbuffer()
        file_hash = get_file_hash(file_content)
        
        if file.name in st.session_state.data_sources:
            existing_hash = st.session_state.data_sources[file.name].get('file_hash', '')
            if existing_hash == file_hash:
                st.info(f"📄 {file.name} already exists with same content. Skipping.")
                continue

        save_path = upload_dir / file.name
        try:
            with open(save_path, "wb") as f:
                f.write(file_content)
        except Exception as e:
            st.error(f"❌ Failed to save {file.name}: {str(e)}")
            continue

        try:
            df = pd.read_excel(save_path)
            missing_columns = [col for col in SELECTED_COLUMNS if col not in df.columns]
            if missing_columns:
                st.error(f"❌ File '{file.name}' is missing required columns: {', '.join(missing_columns)}. File will be skipped.")
                if save_path.exists():
                    save_path.unlink()
                continue

            processed_data = clean_and_process_data(df, SELECTED_COLUMNS)
            chunks = create_text_chunks(processed_data, SELECTED_COLUMNS)
            chunks = chunk_texts_intelligently(chunks)
            
            embeddings = get_embedding_model()
            vectors = embeddings.embed_documents(chunks)
            
            chunk_ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
            payloads = [{"text": chunk, "filename": file.name, "original_id": f"{file.name}_{i}"} for i, chunk in enumerate(chunks)]
            
            vector_store.insert_vectors(vectors, ids=chunk_ids, payloads=payloads)
            
            new_chunks.extend(chunks)

            file_info[file.name] = {
                "upload_date": datetime.now().isoformat(),
                "rows": len(processed_data),
                "chunks": len(chunks),
                "filename": file.name,
                "file_hash": file_hash,
                "chunk_ids": chunk_ids
            }

            st.success(f"✅ Processed {file.name} ({len(chunks)} chunks)")
        except Exception as e:
            st.error(f"❌ Failed to process {file.name}: {str(e)}")
            if save_path.exists():
                save_path.unlink()
            continue

    return new_chunks, file_info

def delete_file_from_vector_store(filename: str):
    try:
        vector_store = st.session_state.vectordb
        if filename in st.session_state.data_sources:
            chunk_ids = st.session_state.data_sources[filename].get('chunk_ids', [])
            if chunk_ids:
                vector_store.delete_vectors(chunk_ids)
        
        file_path = DATA_DIR / "uploads" / filename
        if file_path.exists():
            file_path.unlink()
            
    except Exception as e:
        st.error(f"Error deleting file from vector store: {e}")

def get_chat_name(messages: List[Dict]) -> str:
    for msg in messages:
        if msg["role"] == "user" and msg["content"].strip():
            text = msg["content"].strip()
            return (text[:30] + "...") if len(text) > 30 else text
    return "New Chat"

def is_chat_empty(messages: List[Dict]) -> bool:
    return not any(msg["role"] == "user" and msg["content"].strip() for msg in messages)

def find_empty_chat(all_chats: Dict[str, List[Dict]]) -> str:
    for chat_id, messages in all_chats.items():
        if is_chat_empty(messages):
            return chat_id
    return None

def get_most_recent_chat(all_chats: Dict[str, List[Dict]]) -> str:
    if not all_chats:
        return None
    
    non_empty_chats = [chat_id for chat_id, messages in all_chats.items() if messages]
    if non_empty_chats:
        return non_empty_chats[0]
    
    return next(iter(all_chats))

def initialize_active_chat():
    all_chats = load_all_chats()
    
    if "active_chat_id" not in st.session_state:
        if all_chats:
            most_recent_chat = get_most_recent_chat(all_chats)
            if most_recent_chat:
                st.session_state.active_chat_id = most_recent_chat
            else:
                st.session_state.active_chat_id = next(iter(all_chats))
        else:
            new_id = str(uuid.uuid4())
            st.session_state.active_chat_id = new_id
            all_chats[new_id] = []
            save_all_chats(all_chats)
    
    return all_chats

@require_auth()
def main_app():
    if is_admin():
        show_admin_panel()
        return
    
    init_session_state()
    
    if not st.session_state.vectordb:
        initialize_vector_store()
    
    all_chats = initialize_active_chat()

    if st.session_state.active_chat_id in all_chats:
        st.session_state.messages = all_chats[st.session_state.active_chat_id]
    else:
        st.session_state.messages = []

    st.title("🏢 PTT HR Feedback Chatbot")
    st.markdown("Analyze employee feedback data with AI")

    with st.sidebar:
        show_logout_button()
        
        st.header("💬 Chats")

        if st.button("➕ New Chat"):
            empty_chat_id = find_empty_chat(all_chats)
            
            if empty_chat_id:
                st.session_state.active_chat_id = empty_chat_id
                st.info("✨ Switched to existing empty chat")
            else:
                new_id = str(uuid.uuid4())
                st.session_state.active_chat_id = new_id
                all_chats[new_id] = []
                save_all_chats(all_chats)
                st.success("✨ Created new chat")
            
            st.rerun()

        sorted_chat_ids = [st.session_state.active_chat_id] + [
            cid for cid in all_chats.keys() if cid != st.session_state.active_chat_id
        ]

        for chat_id in sorted_chat_ids:
            messages = all_chats.get(chat_id, [])
            chat_name = get_chat_name(messages)
            is_active = (chat_id == st.session_state.active_chat_id)
            if is_chat_empty(messages):
                chat_name = f"💭 {chat_name}"
            
            display_label = chat_name + (" (Active)" if is_active else "")
            cols = st.columns([4, 1])

            if cols[0].button(display_label, key=f"load_{chat_id}"):
                st.session_state.active_chat_id = chat_id
                st.rerun()

            if not is_active:
                if cols[1].button("🗑️", key=f"del_{chat_id}"):
                    st.session_state.chat_to_confirm_delete = chat_id
                    st.rerun()

            if st.session_state.get("chat_to_confirm_delete") == chat_id:
                with st.expander(f"⚠️ Confirm Delete Chat '{chat_name}'?"):
                    confirm_cols = st.columns(2)
                    if confirm_cols[0].button("✅ Yes, Delete", key=f"confirm_del_{chat_id}"):
                        del all_chats[chat_id]
                        save_all_chats(all_chats)

                        if st.session_state.active_chat_id == chat_id:
                            if all_chats:
                                st.session_state.active_chat_id = next(iter(all_chats))
                            else:
                                new_id = str(uuid.uuid4())
                                st.session_state.active_chat_id = new_id
                                all_chats.setdefault(new_id, [])
                                save_all_chats(all_chats)

                        st.session_state.pop("chat_to_confirm_delete", None)
                        st.rerun()

                    if confirm_cols[1].button("❌ Cancel", key=f"cancel_del_{chat_id}"):
                        st.session_state.pop("chat_to_confirm_delete", None)
                        st.rerun()

        st.markdown("---")

        st.header("📂 Data Management")
        uploaded_files = st.file_uploader("Upload Excel Files", type=["xlsx", "xls"], accept_multiple_files=True)

        if uploaded_files and st.button("Process Files"):
            with st.spinner("Processing files..."):
                new_chunks, file_info = process_uploaded_files(uploaded_files)
                if file_info:
                    update_data_sources(file_info)
                    st.session_state.data_sources.update(file_info)
                    save_data_sources(st.session_state.data_sources)
                    
                    if not st.session_state.qa_chain:
                        st.session_state.qa_chain = get_qa_chain(st.session_state.vectordb)
                    
                    st.success("✅ Data processing complete!")

        st.markdown("---")

        st.subheader("📋 Uploaded Files")
        if st.session_state.data_sources:
            for filename, info in st.session_state.data_sources.items():
                with st.expander(f"📄 {filename}"):
                    uploaded = info.get('upload_date', '-')
                    try:
                        uploaded_time = datetime.fromisoformat(uploaded).strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        uploaded_time = uploaded 
                    st.write(f"🕒 Uploaded Time: {uploaded_time}")

                    if st.button(f"🗑️ Delete {filename}", key=f"del_file_{filename}"):
                        st.session_state.file_to_confirm_delete = filename
                        st.rerun()

                if st.session_state.get("file_to_confirm_delete") == filename:
                    confirm_cols = st.columns([1, 1])
                    st.warning(f"⚠️ Are you sure you want to delete '{filename}'?")
                    if confirm_cols[0].button("✅ Yes, Delete", key=f"confirm_del_file_{filename}"):
                        delete_file_from_vector_store(filename)
                        del st.session_state.data_sources[filename]
                        save_data_sources(st.session_state.data_sources)
                        
                        if not st.session_state.data_sources:
                            st.session_state.qa_chain = None

                        st.session_state.pop("file_to_confirm_delete", None)
                        st.success(f"✅ Deleted {filename}")
                        st.rerun()

                    if confirm_cols[1].button("❌ Cancel", key=f"cancel_del_file_{filename}"):
                        st.session_state.pop("file_to_confirm_delete", None)
                        st.rerun()
        else:
            st.info("No files uploaded yet")

    for message in st.session_state.messages:
        avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about the feedback data..."):
        if not st.session_state.qa_chain:
            st.warning("Please upload and process some data files first to enable the chatbot.")
            st.stop()
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_AVATAR):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            message_placeholder = st.empty()
            full_response = ""
            try:
                message_placeholder.markdown("Searching for answers... 🔍")
                response = st.session_state.qa_chain.invoke({"query": prompt})
                full_response = response["result"].replace("\n", "  \n")
                typed_response = ""
                for char in full_response:
                    typed_response += char
                    message_placeholder.markdown(typed_response)
                    time.sleep(0.005)
            except Exception as e:
                full_response = f"Sorry, I encountered an error: {str(e)}"
                message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        all_chats[st.session_state.active_chat_id] = st.session_state.messages
        save_all_chats(all_chats)

    if not st.session_state.data_sources:
        st.info("👆 Please upload Excel files using the sidebar to start chatting with your data!")

def main():
    st.set_page_config(page_title="PTT HR Chatbot", page_icon="icon/ptt.ico", layout="wide")

    if not is_authenticated():
        show_login_form()
        st.stop()

    main_app()

if __name__ == "__main__":
    main()