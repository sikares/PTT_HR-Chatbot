from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA

def get_qa_chain(vectordb):
    llm = ChatOpenAI(
        temperature=0,
        model="gpt-4o-mini",
    )
    retriever = vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
    )