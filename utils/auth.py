import streamlit as st
import os
from dotenv import load_dotenv
import hashlib
import time

load_dotenv()

SESSION_TIMEOUT = 28800

def get_credentials():
    username = os.getenv('HR_USERNAME')
    password = os.getenv('HR_PASSWORD_HASH')

    if not username or not password:
        st.error("❌ Authentication credentials not found in .env file")
        st.stop()
    
    return username, password

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def check_credentials(username: str, password: str) -> bool:
    try:
        env_username, env_password = get_credentials()
        
        username_match = username == env_username
        
        input_password_hash = hash_password(password)
        stored_password_hash = hash_password(env_password)
        
        return username_match and (input_password_hash == stored_password_hash)
    except Exception as e:
        st.error(f"Error checking credentials: {e}")
        return False

def initialize_auth_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'login_time' not in st.session_state:
        st.session_state.login_time = None

def is_session_expired() -> bool:
    if 'login_time' not in st.session_state or st.session_state.login_time is None:
        return True
    
    current_time = time.time()
    return (current_time - st.session_state.login_time) > SESSION_TIMEOUT

def show_login_form():
    initialize_auth_state()
    
    if st.session_state.authenticated and is_session_expired():
        st.warning("⏰ Your session has expired. Please login again.")
        logout()

    st.markdown("# 🏢 PTT HR Feedback Chatbot")
    st.markdown("### Please login to continue")
    
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
                
                login_button = st.form_submit_button(
                    "🚀 Login", 
                    use_container_width=True
                )
                
                if login_button:
                    if not username or not password:
                        st.error("❌ Please enter both username and password")
                    elif check_credentials(username, password):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.login_time = time.time()
                        st.success("✅ Login successful! Redirecting...")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")

def logout():
    keys_to_keep = []
    
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    
    st.session_state.authenticated = False
    st.session_state.login_time = None
    
    st.success("👋 Logged out successfully!")
    time.sleep(1)
    st.rerun()

def require_auth():
    def decorator(func):
        def wrapper(*args, **kwargs):
            initialize_auth_state()
            if not st.session_state.authenticated or is_session_expired():
                show_login_form()
                return None
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator

def show_logout_button():
    if st.session_state.get('authenticated', False):
        with st.sidebar:
            if st.session_state.get('login_time'):
                time_logged_in = int(time.time() - st.session_state.login_time)
                hours = time_logged_in // 3600
                minutes = (time_logged_in % 3600) // 60
                st.caption(f"⏱️ Logged in: {hours}h {minutes}m")
            
            if st.button("🚪 Logout", use_container_width=True):
                logout()

def is_authenticated() -> bool:
    initialize_auth_state()
    
    if st.session_state.get('authenticated', False) and not is_session_expired():
        return True
    
    if st.session_state.get('authenticated', False) and is_session_expired():
        st.session_state.authenticated = False
        st.session_state.login_time = None
    
    return False