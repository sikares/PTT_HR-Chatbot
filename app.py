import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import shelve
from dotenv import load_dotenv
import time
import uuid

load_dotenv()

from logic.data_processing import clean_and_process_data
from logic.chunking import create_text_chunks, chunk_texts_intelligently
from logic.embedding import get_embedding_model
from logic.qa_chain import get_qa_chain
from utils.session import init_session_state, update_data_sources, load_data_sources, save_data_sources
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

def save_processed_chunks(chunks: List[str]):
    import json
    with open(DATA_DIR / "processed_chunks.json", "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

def load_processed_chunks() -> List[str]:
    import json
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

    upload_dir = DATA_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    for file in uploaded_files:
        file.seek(0, 2)
        size_mb = file.tell() / (1024 * 1024)
        file.seek(0)
        if size_mb > MAX_UPLOAD_SIZE_MB:
            st.error(f"❌ {file.name} file size is larger than {MAX_UPLOAD_SIZE_MB} MB")
            continue

        save_path = upload_dir / file.name
        try:
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
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
            new_chunks.extend(chunks)

            file_info[file.name] = {
                "upload_date": datetime.now().isoformat(),
                "rows": len(processed_data),
                "chunks": len(chunks),
                "filename": file.name
            }

            st.success(f"✅ Processed {file.name} ({len(chunks)} chunks)")
        except Exception as e:
            st.error(f"❌ Failed to process {file.name}: {str(e)}")
            if save_path.exists():
                save_path.unlink()
            continue

    if new_chunks:
        new_chunks = chunk_texts_intelligently(new_chunks)

    return new_chunks, file_info

def reload_all_chunks_from_sources() -> List[str]:
    all_chunks = []
    for filename in st.session_state.data_sources.keys():
        filepath = DATA_DIR / filename
        if not filepath.exists():
            st.warning(f"File {filename} not found in data folder")
            continue
        try:
            df = pd.read_excel(filepath)
            processed_data = clean_and_process_data(df, SELECTED_COLUMNS)
            chunks = create_text_chunks(processed_data, SELECTED_COLUMNS)
            all_chunks.extend(chunks)
        except Exception as e:
            st.error(f"Unable to load file {filename}: {str(e)}")
    return all_chunks

def refresh_vector_store(chunks: List[str]):
    if not chunks:
        st.session_state.vectordb = None
        st.session_state.qa_chain = None
        return
    try:
        vector_store = QdrantVectorStore()
        embeddings = get_embedding_model()
        vectors = embeddings.embed_documents(chunks)
        vector_store.insert_vectors(vectors, payloads=[{"text": chunk} for chunk in chunks])
        st.session_state.vectordb = vector_store
        st.session_state.qa_chain = get_qa_chain(vector_store)
        st.success(f"✅ Successfully created vector store with {len(chunks)} chunks")
    except Exception as e:
        st.error(f"❌ Failed to refresh vector store: {str(e)}")
        st.session_state.vectordb = None
        st.session_state.qa_chain = None

def get_chat_name(messages: List[Dict]) -> str:
    for msg in messages:
        if msg["role"] == "user" and msg["content"].strip():
            text = msg["content"].strip()
            return (text[:30] + "...") if len(text) > 30 else text
    return "New Chat"

def main():
    st.set_page_config(page_title="PTT HR Chatbot", page_icon="icon/ptt.ico", layout="wide")
    init_session_state()
    all_chats = load_all_chats()

    if "active_chat_id" not in st.session_state:
        if all_chats:
            st.session_state.active_chat_id = next(iter(all_chats))
        else:
            new_id = str(uuid.uuid4())
            st.session_state.active_chat_id = new_id
            all_chats.setdefault(new_id, [])
            save_all_chats(all_chats)

    if st.session_state.active_chat_id in all_chats:
        st.session_state.messages = all_chats[st.session_state.active_chat_id]
    else:
        st.session_state.messages = []

    if not st.session_state.data_sources:
        st.session_state.data_sources = load_data_sources()
    if not st.session_state.all_chunks:
        st.session_state.all_chunks = load_processed_chunks()

    st.title("PTT HR Feedback Chatbot 🤖")
    st.markdown("Analyze employee feedback data with AI")

    with st.sidebar:
        st.header("💬 Chats")
        sorted_chat_ids = [st.session_state.active_chat_id] + [
            cid for cid in all_chats.keys() if cid != st.session_state.active_chat_id
        ]

        for chat_id in sorted_chat_ids:
            messages = all_chats.get(chat_id, [])
            chat_name = get_chat_name(messages)
            is_active = (chat_id == st.session_state.active_chat_id)
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

        def has_user_input(messages: List[Dict]) -> bool:
            return any(msg["role"] == "user" and msg["content"].strip() for msg in messages)

        if st.button("➕ New Chat"):
            current_messages = all_chats.get(st.session_state.active_chat_id, [])
            if not has_user_input(current_messages):
                st.warning("⚠️ Please enter a message in the current chat before starting a new one.")
            else:
                new_id = str(uuid.uuid4())
                st.session_state.active_chat_id = new_id
                all_chats.setdefault(new_id, [])
                save_all_chats(all_chats)
                st.rerun()

        st.markdown("---")

        st.header("📂 Data Management")
        uploaded_files = st.file_uploader("Upload Excel Files", type=["xlsx", "xls"], accept_multiple_files=True)

        if uploaded_files and st.button("Process Files"):
            with st.spinner("Processing files..."):
                new_chunks, file_info = process_uploaded_files(uploaded_files)
                if new_chunks:
                    st.session_state.all_chunks.extend(new_chunks)
                    update_data_sources(file_info)
                    st.session_state.data_sources.update(file_info)
                    save_data_sources(st.session_state.data_sources)
                    save_processed_chunks(st.session_state.all_chunks)
                    refresh_vector_store(st.session_state.all_chunks)
                    st.success("✅ Data processing complete!")

        st.subheader("📋 Uploaded Files")
        if st.session_state.data_sources:
            for filename, info in st.session_state.data_sources.items():
                with st.expander(f"📄 {filename}"):
                    st.write(f"📅 Uploaded: {info.get('upload_date', '-')}")
                    st.write(f"📊 Rows: {info.get('rows', 0):,}")
                    st.write(f"🧹 Chunks: {info.get('chunks', 0):,}")
                    if st.button(f"🗑️ Delete {filename}", key=f"del_file_{filename}"):
                        del st.session_state.data_sources[filename]
                        save_data_sources(st.session_state.data_sources)
                        file_path = DATA_DIR / "uploads" / filename
                        if file_path.exists():
                            try:
                                file_path.unlink()
                            except Exception as e:
                                st.error(f"Error deleting file {filename} from disk: {str(e)}")
                        st.session_state.all_chunks = reload_all_chunks_from_sources()
                        save_processed_chunks(st.session_state.all_chunks)
                        refresh_vector_store(st.session_state.all_chunks)
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
                    time.sleep(0.01)
            except Exception as e:
                full_response = f"Sorry, I encountered an error: {str(e)}"
                message_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        all_chats[st.session_state.active_chat_id] = st.session_state.messages
        save_all_chats(all_chats)

    if not st.session_state.data_sources:
        st.info("👆 Please upload Excel files using the sidebar to start chatting with your data!")


if __name__ == "__main__":
    main()
