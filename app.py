import streamlit as st
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from data_processing import clean_and_process_data
from chunking import create_text_chunks, chunk_texts_intelligently
from auth import check_credentials, password_expired, validate_password_change
from datetime import datetime

def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'password_changed_date' not in st.session_state:
        st.session_state.password_changed_date = datetime.now()

def main():
    load_dotenv()
    st.set_page_config(
        page_title="PTT HR Chatbot",
        page_icon="icon/ptt.ico",
    )
    init_session_state()

    if not st.session_state.authenticated:
        st.title("PTT HR Chatbot Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")

            if submit_button:
                if check_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.password_changed_date = datetime.now()
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Access denied.")
        return

    if password_expired(st.session_state.password_changed_date):
        st.warning("Your password has expired. Please change your password.")
        with st.form("password_change_form"):
            old_password = st.text_input("Old Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            change_button = st.form_submit_button("Change Password")

            if change_button:
                valid, msg = validate_password_change(old_password, new_password, confirm_password)
                if valid:
                    st.session_state.password_changed_date = datetime.now()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
        return

    st.header("PTT HR Chatbot")
    st.markdown("""
    This is a simple chatbot that can answer questions about your Excel data.
    Upload Excel files and ask questions about their contents.
    """)

    user_question = st.text_input("Enter your question about the Excel data:")

    with st.sidebar:
        st.header("Your Documents")
        uploaded_files = st.file_uploader(
            "Upload Excel Files", 
            type=["xlsx", "xls"], 
            accept_multiple_files=True
        )

        selected_columns = [
            "ที่มาของ Feedback",
            "BU",
            "ประเภท Feedback",
            "รายละเอียด Feedback",
            "แนวทางการดำเนินการ",
            "รายละเอียด Status"
        ]

        valid_files = []
        invalid_files = []

        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    df = pd.read_excel(
                        uploaded_file, 
                        engine='openpyxl' if uploaded_file.name.endswith('.xlsx') else 'xlrd'
                    )
                    st.subheader(f"Preview of Raw Data: {uploaded_file.name}")
                    st.dataframe(df.head(10))

                    missing_cols = [col for col in selected_columns if col not in df.columns]
                    if not missing_cols:
                        valid_files.append((uploaded_file.name, df))
                        st.success(f"✅ {uploaded_file.name} has all required columns")
                    else:
                        st.error(f"❌ {uploaded_file.name} is missing columns: {', '.join(missing_cols)}")
                        invalid_files.append(uploaded_file.name)
                except Exception as e:
                    st.error(f"Cannot read {uploaded_file.name}: {str(e)}")
                    invalid_files.append(uploaded_file.name)

        can_process = len(valid_files) > 0

        if st.button("Process", disabled=not can_process):
            all_text_chunks = []

            with st.spinner("Processing Excel files..."):
                for filename, df in valid_files:
                    try:
                        processed_data = clean_and_process_data(df, selected_columns)

                        st.subheader(f"📄 Processed Data Preview: {filename}")
                        st.dataframe(processed_data)
                        st.write(f"Rows after processing: {len(processed_data)}")

                        text_chunks = create_text_chunks(processed_data, selected_columns)
                        all_text_chunks.extend(text_chunks)

                        st.success(f"✅ Processed {len(text_chunks)} records from {filename}")

                    except Exception as e:
                        st.error(f"Error processing {filename}: {str(e)}")

            if all_text_chunks:
                final_chunks = chunk_texts_intelligently(all_text_chunks)

                st.success(f"✅ Successfully created {len(final_chunks)} chunks from {len(all_text_chunks)} records.")

                with st.expander("View Sample Chunks"):
                    for i, chunk in enumerate(final_chunks[:5]):
                        st.subheader(f"Chunk {i+1}")
                        st.text(chunk)
                        st.write(f"Length: {len(chunk)} characters")
                        st.write("---")

                with st.expander("Processing Statistics"):
                    chunk_lengths = [len(chunk) for chunk in final_chunks]
                    st.write(f"Total chunks: {len(final_chunks)}")
                    st.write(f"Average chunk length: {int(np.mean(chunk_lengths))} characters")
                    st.write(f"Min chunk length: {min(chunk_lengths)} characters")
                    st.write(f"Max chunk length: {max(chunk_lengths)} characters")
            else:
                st.warning("No valid data found to process.")

if __name__ == "__main__":
    main()
