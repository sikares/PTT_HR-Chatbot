import streamlit as st
import pandas as pd
from dotenv import load_dotenv

def main():
    load_dotenv()
    st.set_page_config(
        page_title="PTT HR Chatbot",
        page_icon="icon/ptt.ico",
    )
    
    st.header("PTT HR Chatbot")
    st.markdown("""
    This is a simple chatbot that can answer questions about your Excel data.
    Upload Excel files and ask questions about their contents.
    """)
    
    st.text_input("Enter your question about the Excel data:")

    with st.sidebar:
        st.header("Your Documents")
        uploaded_files = st.file_uploader(
            "Upload Excel Files", 
            type=["xlsx"], 
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
                    df = pd.read_excel(uploaded_file)
                except Exception as e:
                    st.error(f"Cannot read {uploaded_file.name}: {e}")
                    continue

                st.subheader(f"Preview of Raw Data: {uploaded_file.name}")
                st.dataframe(df.head(10))

                if all(col in df.columns for col in selected_columns):
                    valid_files.append((uploaded_file.name, df))
                else:
                    invalid_files.append(uploaded_file.name)

        if invalid_files:
            st.warning(f"❌ These files are missing required columns: {', '.join(invalid_files)}")

        can_process = uploaded_files and not invalid_files

        if not can_process:
            st.info("📎 Please upload files that contain all required columns to enable processing.")

        if st.button("Process", disabled=not can_process):
            all_docs = []
            with st.spinner("Processing..."):
                for filename, df in valid_files:
                    df_sel = df[selected_columns].copy()
                    for col in selected_columns:
                        if col != "รายละเอียด Status":
                            df_sel[col] = df_sel[col].fillna(method="ffill")

                    filtered_df = df_sel.dropna(how="all").drop_duplicates()

                    # After clean & filter
                    st.subheader(f"📄 Cleaned Data Preview: {filename}")
                    st.dataframe(filtered_df)

                    for _, row in filtered_df.iterrows():
                        content = " | ".join(str(value) for value in row if pd.notnull(value))
                        all_docs.append(content)

            st.success(f"✅ Successfully processed {len(all_docs)} rows from uploaded files.")

if __name__ == "__main__":
    main()