from langchain.text_splitter import CharacterTextSplitter

def create_text_chunks(df_processed, selected_columns):
    text_chunks = []
    
    for idx, row in df_processed.iterrows():
        row_text = []
        for col in selected_columns:
            value = str(row[col]).strip()
            if value and value != 'nan' and value != 'ไม่มีข้อมูล':
                row_text.append(f"{col}: {value}")
        
        if row_text:
            chunk_text = "\n".join(row_text)
            text_chunks.append(chunk_text)
    
    return text_chunks

def chunk_texts_intelligently(text_chunks, chunk_size=1000, chunk_overlap=200):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    
    final_chunks = []
    
    for text in text_chunks:
        if len(text) <= chunk_size:
            final_chunks.append(text)
        else:
            sub_chunks = text_splitter.split_text(text)
            final_chunks.extend(sub_chunks)
    
    return final_chunks
