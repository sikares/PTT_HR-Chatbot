from datetime import datetime
import streamlit as st
from typing import Dict, List, Any

def init_session_state():
    defaults = {
        'authenticated': False,
        'password_changed_date': None,
        'vectordb': None,
        'qa_chain': None,
        'data_sources': {},
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
    if 'data_sources' not in st.session_state:
        st.session_state.data_sources = {}
    
    st.session_state.data_sources.update(file_info)