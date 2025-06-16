from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

def create_vector_store(chunks):
    embeddings = OpenAIEmbeddings()
    vectordb = Chroma.from_texts(chunks, embeddings, collection_name="ptt_hr_feedback")
    return vectordb
