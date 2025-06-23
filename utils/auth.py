import streamlit as st
import os
from dotenv import load_dotenv
import bcrypt
from functools import wraps

load_dotenv()

def get_credentials():
    username = os.getenv('HR_USERNAME')
    password_hash = os.getenv('HR_PASSWORD_HASH')

    if not username or not password_hash:
        st.error("❌ Authentication credentials not configured properly")
        st.stop()

    return username, password_hash

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def check_password(input_password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            input_password.encode('utf-8'),
            stored_hash.encode('utf-8')
        )
    except Exception:
        return False

def initialize_auth_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None

def is_authenticated() -> bool:
    initialize_auth_state()
    return st.session_state.get('authenticated', False)

def require_auth():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                show_login_form()
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def show_login_form():
    initialize_auth_state()

    st.markdown("# 🏢 PTT HR Feedback Chatbot")
    st.markdown("### Please log in to use the system")

    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                username = st.text_input(
                    "👤 Username",
                    placeholder="Enter your username",
                    key="username_input"
                )
                password = st.text_input(
                    "🔑 Password",
                    type="password",
                    placeholder="Enter your password",
                    key="password_input"
                )

                if st.form_submit_button("🚀 Login", use_container_width=True):
                    if not username or not password:
                        st.error("❌ Please fill in both username and password")
                    else:
                        try:
                            env_username, env_password_hash = get_credentials()

                            if username == env_username and check_password(password, env_password_hash):
                                st.session_state.authenticated = True
                                st.session_state.username = username
                                st.success("✅ Login successful! Redirecting...")
                                st.query_params.clear()
                                st.rerun()
                            else:
                                st.error("❌ Incorrect username or password")
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")

def logout():
    for key in ['authenticated', 'username']:
        st.session_state.pop(key, None)

    st.success("👋 Logged out successfully! Redirecting...")
    st.query_params.clear()
    st.rerun()

def show_logout_button():
    if st.session_state.get('authenticated', False):
        with st.sidebar:
            if st.session_state.get('username'):
                st.caption(f"🙋 Logged in as: {st.session_state['username']}")

            if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
                logout()
