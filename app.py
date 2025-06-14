import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from langchain.text_splitter import CharacterTextSplitter

def chunk_row_texts(rows, chunk_size=1000, chunk_overlap=200):
    text_splitter = CharacterTextSplitter(
        separator="\n---\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    chunks = []
    current_chunk = []
    current_length = 0
    
    for row_text in rows:
        row_text = row_text.strip()
        if not row_text:
            continue
            
        if len(row_text) > chunk_size:
            sub_chunks = text_splitter.split_text(row_text)
            for sub_chunk in sub_chunks:
                if current_length + len(sub_chunk) > chunk_size and current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [sub_chunk]
                    current_length = len(sub_chunk)
                else:
                    current_chunk.append(sub_chunk)
                    current_length += len(sub_chunk)
        else:
            if current_length + len(row_text) > chunk_size and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [row_text]
                current_length = len(row_text)
            else:
                current_chunk.append(row_text)
                current_length += len(row_text)
    
    if current_chunk:
        chunks.append("\n".join(current_chunk))
    
    return chunks

def clean_and_process_data(df, selected_columns):
    df_sel = df[selected_columns].copy()
    
    for col in selected_columns:
        if col != "รายละเอียด Status":
            df_sel[col] = df_sel[col].fillna(method="ffill")
    
    df_sel["รายละเอียด Status"] = df_sel["รายละเอียด Status"].fillna("ไม่มีข้อมูล")
    
    filtered_df = df_sel.dropna(how="all").drop_duplicates()
    
    check_columns = [col for col in selected_columns if col != "รายละเอียด Status"]
    
    duplicates = filtered_df.duplicated(subset=check_columns, keep=False)
    
    condition = (
        ~duplicates |
        (filtered_df["รายละเอียด Status"] != "ไม่มีข้อมูล")
    )
    
    filtered_df = filtered_df[condition]
    
    filtered_df['group_id'] = (
        (filtered_df[check_columns] != filtered_df[check_columns].shift())
        .any(axis=1)
        .cumsum()
    )
    
    grouped = filtered_df.groupby('group_id')[selected_columns].agg(
        lambda x: '\n'.join(str(v) for v in x if pd.notna(v) and str(v).strip())
    )
    
    return grouped

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
    
    user_question = st.text_input("Enter your question about the Excel data:")

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
                    df = pd.read_excel(uploaded_file, engine='openpyxl')
                    
                    st.subheader(f"Preview of Raw Data: {uploaded_file.name}")
                    st.dataframe(df.head(10))

                    if all(col in df.columns for col in selected_columns):
                        valid_files.append((uploaded_file.name, df))
                    else:
                        missing_cols = [col for col in selected_columns if col not in df.columns]
                        st.error(f"Missing columns in {uploaded_file.name}: {', '.join(missing_cols)}")
                        invalid_files.append(uploaded_file.name)
                        
                except Exception as e:
                    st.error(f"Cannot read {uploaded_file.name}: {e}")
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
                    processed_data = clean_and_process_data(df, selected_columns)
                    
                    st.subheader(f"📄 Cleaned Data Preview: {filename}")
                    st.dataframe(processed_data)

                    for _, row in processed_data.iterrows():
                        content = "\n".join(f"{col}: {row[col]}" for col in selected_columns)
                        all_docs.append(content)

            chunks = chunk_row_texts(all_docs)

            st.success(f"✅ Successfully processed {len(chunks)} chunks from {len(all_docs)} rows.")
            
            with st.expander("View Sample Chunks"):
                for i, chunk in enumerate(chunks[1:]):
                    st.subheader(f"Chunk {i+1}")
                    st.text(chunk)

if __name__ == "__main__":
    main()