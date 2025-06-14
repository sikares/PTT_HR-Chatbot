import streamlit as st
import pandas as pd
from dotenv import load_dotenv

def main():
    load_dotenv()
    st.set_page_config(
        page_title="PTT HR Chatbot",
        page_icon="icon/ptt.ico",)
    
    st.header("PTT HR Chatbot")
    st.markdown("""
    This is a simple chatbot that can answer questions about your Excel data.
    Upload Excel files and ask questions about their contents.
    """)
    
    st.text_input("Enter your question about the Excel data:")

    with st.sidebar:
        st.subheader("Your Documents")
        uploaded_files = st.file_uploader("Upload Excel Files", type=["xlsx"], accept_multiple_files=True)
        
        all_docs = []
        if uploaded_files:
            for uploaded_file in uploaded_files:
                df = pd.read_excel(uploaded_file)

                selected_columns = [
                    "ที่มาของ Feedback",
                    "BU",
                    "ประเภท Feedback",
                    "รายละเอียด Feedback",
                    "แนวทางการดำเนินการ",
                    "รายละเอียด Status"
                ]

                if not all(col in df.columns for col in selected_columns):
                    st.error(f"{uploaded_file.name} is missing one or more required columns.")
                    continue

                filtered_df = df[selected_columns].dropna(how="all")
                
                for _, row in filtered_df.iterrows():
                    content = " | ".join(str(value) for value in row if pd.notnull(value))
                    all_docs.append(content)

                st.write(f"Preview of: {uploaded_file.name}")
                st.dataframe(filtered_df.head(6))

        if st.button("Process"):
            if not uploaded_files:
                st.warning("⚠️ Please upload at least one Excel file.")
            else:
                with st.spinner("Processing..."):
                    st.success(f"✅ Successfully processed {len(all_docs)} rows from uploaded files.")

if __name__ == "__main__":
    main()