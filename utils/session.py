from datetime import datetime
import streamlit as st

def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'password_changed_date' not in st.session_state:
        st.session_state.password_changed_date = datetime.now()
    if 'vectordb' not in st.session_state:
        st.session_state.vectordb = None
    if 'qa_chain' not in st.session_state:
        st.session_state.qa_chain = None
