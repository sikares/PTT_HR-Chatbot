from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List
import pandas as pd

def create_text_chunks(df_processed: pd.DataFrame, selected_columns: List[str]) -> List[str]:
    text_chunks = []

    for idx, row in df_processed.iterrows():
        row_text = []
        for col in selected_columns:
            value = str(row.get(col, "")).strip()
            if value and value.lower() != 'nan' and value != 'ไม่มีข้อมูล' and not pd.isna(value):
                row_text.append(f"{col}: {value}")

        if row_text:
            chunk_text = "\n".join(row_text)
            text_chunks.append(chunk_text)

    return text_chunks

def chunk_texts_intelligently(
    text_chunks: List[str],
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
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