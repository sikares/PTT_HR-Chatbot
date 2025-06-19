from datetime import datetime
import streamlit as st
from typing import Dict, Any
import json
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

DATA_SOURCES_PATH = DATA_DIR / "data_sources.json"

def load_data_sources() -> Dict[str, Any]:
    try:
        if DATA_SOURCES_PATH.exists():
            with open(DATA_SOURCES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

                for key, val in data.items():
                    if isinstance(val, dict) and "uploaded_at" in val and isinstance(val["uploaded_at"], str):
                        val["uploaded_at"] = datetime.fromisoformat(val["uploaded_at"])
                return data
    except Exception as e:
        st.error(f"Error loading data sources: {e}")
    return {}

def save_data_sources(data: Dict[str, Any]):
    def default_converter(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)

    with open(DATA_SOURCES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=default_converter)

def init_session_state():
    defaults = {
        'vectordb': None, 
        'qa_chain': None,
        'all_chunks': [],
        'chat_history': [],
        'data_sources': load_data_sources(),
        'current_file': None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def update_data_sources(file_info: Dict[str, Any]):
    if 'data_sources' not in st.session_state or not st.session_state.data_sources:
        st.session_state.data_sources = {}

    st.session_state.data_sources.update(file_info)
    save_data_sources(st.session_state.data_sources)