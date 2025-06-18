import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import shelve

from logic.data_processing import clean_and_process_data
from logic.chunking import create_text_chunks, chunk_texts_intelligently
from logic.embedding import create_vector_store, update_vector_store, get_embedding_model
from logic.qa_chain import get_qa_chain
from utils.session import init_session_state, update_data_sources, load_data_sources, save_data_sources
from utils.evaluation import evaluate_qa_chain, calculate_metrics, TEST_QUESTIONS
from core.vector_store import QdrantVectorStore

USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

SELECTED_COLUMNS = [
    "DD.MM.YYYY",
    "ที่มาของ Feedback",
    "BU",
    "บคญ./บทญ.",
    "ประเภท Feedback",
    "รายละเอียด Feedback",
    "แนวทางการดำเนินการ",
    "สถานะการแจ้ง Process Owner ",
    "รายละเอียด Status"
]

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_SIZE_MB = 20

def load_chat_history():
    try:
        with shelve.open("ptt_chat_history") as db:
            return db.get("messages", [])
    except Exception as e:
        st.error(f"Error loading chat history: {e}")
        return []

def save_chat_history(messages):
    try:
        with shelve.open("ptt_chat_history") as db:
            db["messages"] = messages
    except Exception as e:
        st.error(f"Error saving chat history: {e}")

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
                st.error(
                    f"❌ File '{file.name}' is missing required columns: {', '.join(missing_columns)}. "
                    "File will be skipped."
                )
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

def display_evaluation_results(eval_df: pd.DataFrame):
    st.subheader("📝 Evaluation Results")
    st.dataframe(eval_df[["question", "expected", "actual", "match"]])

    metrics = calculate_metrics(eval_df)
    st.markdown(f"**Accuracy:** {metrics['accuracy']:.2%} ({metrics['correct_answers']}/{metrics['total_questions']})")

def main():
    st.set_page_config(
        page_title="PTT HR Chatbot",
        page_icon="icon/ptt.ico",
        layout="wide"
    )
    
    init_session_state()

    if "messages" not in st.session_state:
        st.session_state.messages = load_chat_history()

    if not st.session_state.data_sources:
        st.session_state.data_sources = load_data_sources()
    if not st.session_state.all_chunks:
        st.session_state.all_chunks = load_processed_chunks()

    st.title("PTT HR Feedback Chatbot 🤖")
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
                    st.write(f"🧩 Chunks: {info.get('chunks', 0):,}")

                    if st.button(f"🗑️ Delete {filename}", key=f"del_{filename}"):
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

        st.markdown("---")
        
        st.header("💬 Chat Controls")
        if st.button("🗑️ Delete Chat History"):
            st.session_state.messages = []
            save_chat_history([])
            st.success("Chat history deleted!")
            st.rerun()
        
        if st.session_state.messages:
            user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
            bot_messages = len([m for m in st.session_state.messages if m["role"] == "assistant"])
            st.info(f"💬 Messages: {user_messages} questions, {bot_messages} responses")

        st.markdown("---")
        
        st.header("⚙️ Evaluation")
        if st.button("Run Evaluation on Test Questions"):
            if st.session_state.qa_chain:
                with st.spinner("Evaluating..."):
                    eval_df = evaluate_qa_chain(st.session_state.qa_chain, TEST_QUESTIONS)
                    st.session_state.eval_results = eval_df
                    display_evaluation_results(eval_df)
            else:
                st.warning("Please process data first to create QA chain.")

        if "eval_results" in st.session_state:
            display_evaluation_results(st.session_state.eval_results)

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
                full_response = response["result"]
                
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                full_response = f"Sorry, I encountered an error while processing your question: {str(e)}"
                message_placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        save_chat_history(st.session_state.messages)

    if not st.session_state.data_sources:
        st.info("👆 Please upload Excel files using the sidebar to start chatting with your data!")

if __name__ == "__main__":
    main()