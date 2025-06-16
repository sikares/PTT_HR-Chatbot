from datetime import datetime
import streamlit as st
from typing import Dict, Any
import json
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def load_data_sources() -> Dict[str, Any]:
    try:
        filepath = DATA_DIR / "data_sources.json"
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                if "password_changed_date" in data and isinstance(data["password_changed_date"], str):
                    data["password_changed_date"] = datetime.fromisoformat(data["password_changed_date"])
                
                return data
    except Exception as e:
        st.error(f"Error loading data sources: {e}")
    return {}

def save_data_sources(data: Dict[str, Any]):
    def default_converter(o):
        if isinstance(o, datetime):
            return o.isoformat()
        return str(o)
    
    with open(DATA_DIR / "data_sources.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=default_converter)

def init_session_state():
    defaults = {
        'authenticated': False,
        'password_changed_date': None,
        'vectordb': None,
        'qa_chain': None,
        'data_sources': load_data_sources(),
        'all_chunks': [],
        'chat_history': [],
        'evaluation_results': None,
        'feedback_stats': None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_session_state():
    auth_state = {
        'authenticated': st.session_state.get('authenticated', False),
        'password_changed_date': st.session_state.get('password_changed_date')
    }
    
    st.session_state.clear()
    st.session_state.update(auth_state)
    init_session_state()

def update_data_sources(file_info: Dict[str, Any]):
    if 'data_sources' not in st.session_state or not st.session_state.data_sources:
        st.session_state.data_sources = {}
    
    st.session_state.data_sources.update(file_info)
