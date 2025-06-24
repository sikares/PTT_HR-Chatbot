import streamlit as st
import os
from dotenv import load_dotenv
import bcrypt
from functools import wraps
import json
from pathlib import Path
from datetime import datetime, timedelta

load_dotenv()

AUTH_STORE_PATH = Path("data") / "auth_state.json"
AUTH_STORE_PATH.parent.mkdir(exist_ok=True)

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
    
    auth_data = load_auth_data()
    if auth_data:
        if 'expiry' in auth_data and datetime.fromisoformat(auth_data['expiry']) > datetime.now():
            st.session_state.authenticated = True
            st.session_state.username = auth_data.get('username')

def load_auth_data():
    try:
        if AUTH_STORE_PATH.exists():
            with open(AUTH_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None

def save_auth_data(username: str):
    try:
        expiry = (datetime.now() + timedelta(hours=24)).isoformat()
        auth_data = {
            'username': username,
            'expiry': expiry
        }
        with open(AUTH_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving auth state: {e}")

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
                                save_auth_data(username)
                                st.success("✅ Login successful! Redirecting...")
                                st.query_params.clear()
                                st.rerun()
                            else:
                                st.error("❌ Incorrect username or password")
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")

def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    try:
        AUTH_STORE_PATH.unlink()
    except Exception:
        pass
    st.success("👋 Logged out successfully! Redirecting...")
    st.query_params.clear()
    st.rerun()

def show_logout_button():
    if st.session_state.get('authenticated', False):
        with st.sidebar:
            if st.session_state.get('username'):
                st.markdown(f"✨ Logged in as: {st.session_state['username']}")
            if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
                logout()