import streamlit as st
import os
from dotenv import load_dotenv, set_key
import bcrypt
from functools import wraps
import json
from pathlib import Path
from datetime import datetime, timedelta

load_dotenv()

AUTH_STORE_PATH = Path("data") / "auth_state.json"
AUTH_STORE_PATH.parent.mkdir(exist_ok=True)
ENV_FILE_PATH = Path(".env")

def get_credentials():
    hr_username = os.getenv('HR_USERNAME')
    hr_password_hash = os.getenv('HR_PASSWORD_HASH')
    admin_username = os.getenv('HR_ADMIN_USERNAME')
    admin_password_hash = os.getenv('HR_ADMIN_PASSWORD_HASH')

    if not all([hr_username, hr_password_hash, admin_username, admin_password_hash]):
        st.error("❌ Authentication credentials not configured properly")
        st.stop()

    return {
        'hr_user': {'username': hr_username, 'password_hash': hr_password_hash},
        'admin': {'username': admin_username, 'password_hash': admin_password_hash}
    }

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

def update_hr_user_password(new_password: str) -> bool:
    try:
        new_hash = hash_password(new_password)
        set_key(ENV_FILE_PATH, 'HR_PASSWORD_HASH', new_hash)
        load_dotenv(override=True)
        return True
    except Exception as e:
        st.error(f"Error updating password: {e}")
        return False

def authenticate_user(username: str, password: str):
    credentials = get_credentials()
    
    if (username == credentials['hr_user']['username'] and 
        check_password(password, credentials['hr_user']['password_hash'])):
        return 'hr_user', username
    
    if (username == credentials['admin']['username'] and 
        check_password(password, credentials['admin']['password_hash'])):
        return 'admin', username
    
    return None, None

def initialize_auth_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_type' not in st.session_state:
        st.session_state.user_type = None
    
    auth_data = load_auth_data()
    if auth_data:
        if 'expiry' in auth_data and datetime.fromisoformat(auth_data['expiry']) > datetime.now():
            st.session_state.authenticated = True
            st.session_state.username = auth_data.get('username')
            st.session_state.user_type = auth_data.get('user_type')

def load_auth_data():
    try:
        if AUTH_STORE_PATH.exists():
            with open(AUTH_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return None
    return None

def save_auth_data(username: str, user_type: str):
    try:
        expiry = (datetime.now() + timedelta(hours=24)).isoformat()
        auth_data = {
            'username': username,
            'user_type': user_type,
            'expiry': expiry
        }
        with open(AUTH_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Error saving auth state: {e}")

def is_authenticated() -> bool:
    initialize_auth_state()
    return st.session_state.get('authenticated', False)

def is_admin() -> bool:
    return st.session_state.get('user_type') == 'admin'

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

def show_admin_panel():
    st.markdown("# 🔧 HR Admin Panel")
    st.markdown("### Change HR_Users Password")
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("change_password_form"):
                st.info("👤 Current Username: " + os.getenv('HR_USERNAME', 'HR_Users'))
                
                new_password = st.text_input(
                    "🔑 New Password for HR_Users",
                    type="password",
                    placeholder="Enter new password",
                    help="Password should be at least 8 characters long"
                )
                
                confirm_password = st.text_input(
                    "🔑 Confirm New Password",
                    type="password",
                    placeholder="Confirm new password"
                )
                
                if st.form_submit_button("✨ Update Password", use_container_width=True):
                    if not new_password or not confirm_password:
                        st.error("❌ Please fill in both password fields")
                    elif len(new_password) < 8:
                        st.error("❌ Password must be at least 8 characters long")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match")
                    else:
                        if update_hr_user_password(new_password):
                            st.success("✅ Password updated successfully!")
                            st.session_state.authenticated = False
                            st.session_state.username = None
                            st.session_state.user_type = None
                            try:
                                AUTH_STORE_PATH.unlink()
                            except Exception:
                                pass
                            st.rerun()
                        else:
                            st.error("❌ Failed to update password")
            
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                logout()

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
                            user_type, auth_username = authenticate_user(username, password)
                            
                            if user_type:
                                st.session_state.authenticated = True
                                st.session_state.username = auth_username
                                st.session_state.user_type = user_type
                                save_auth_data(auth_username, user_type)
                                
                                if user_type == 'admin':
                                    st.success("✅ Admin login successful!")
                                else:
                                    st.success("✅ Login successful!")
                                
                                st.query_params.clear()
                                st.rerun()
                            else:
                                st.error("❌ Incorrect username or password")
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")

def logout():
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.user_type = None
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
                user_type_display = "Admin" if is_admin() else "User"
                st.markdown(f"✨ Logged in as: {st.session_state['username']}")
            if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
                logout()