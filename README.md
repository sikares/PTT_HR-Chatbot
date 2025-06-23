# 🏢 PTT HR Feedback Chatbot

A secure, private, and interactive chatbot for analyzing and querying HR feedback data at PTT. Upload Excel files, process employee feedback, and chat with your data using advanced AI and vector search.

---

## Features

- **Secure Login**: Only authorized HR users can access the system.
- **Excel Upload**: Upload multiple Excel files containing feedback data.
- **Automated Data Cleaning**: Cleans, consolidates, and processes messy HR feedback data.
- **Semantic Search**: Uses embeddings and Qdrant vector database for fast, relevant retrieval.
- **Chatbot Interface**: Ask questions in natural language and get structured, referenced answers.
- **Chat History**: Multi-session chat history with easy switching and deletion.
- **Data Management**: View, delete, and manage uploaded files and their vector representations.
- **Configurable Prompt**: Ensures answers are always based on uploaded data, never hallucinated.
- **Runs Locally**: All data and processing stay on your machine or private server.

---

## Tech Stack

- **Python 3.9+**
- [Streamlit](https://streamlit.io/) (UI)
- [LangChain](https://python.langchain.com/) (LLM orchestration)
- [OpenAI API](https://platform.openai.com/) (LLM, e.g., GPT-4)
- [HuggingFace Sentence Transformers](https://www.sbert.net/) (Embeddings)
- [Qdrant](https://qdrant.tech/) (Vector DB, via Docker)
- [Pandas, openpyxl](https://pandas.pydata.org/) (Excel processing)
- [bcrypt, python-dotenv](https://pypi.org/project/bcrypt/) (Authentication)
- [Docker Compose](https://docs.docker.com/compose/) (for Qdrant)

---

## Getting Started

### 1. Clone the Repository

```sh
git clone https://github.com/sikares/PTT_HR-Chatbot.git
cd PTT_HR-Chatbot
```

### 2. Set Up Python Environment

```sh
python -m venv .venv
.venv\Scripts\activate   # On Windows
# Or: source .venv/bin/activate  # On Mac/Linux

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root (already present in this repo):

```
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
HR_USERNAME=YOUR_HR_USERNAME
HR_PASSWORD_HASH=YOUR_BCRYPT_HASHED_PASSWORD <bcrypt hash>
```

- To generate a bcrypt hash for a new password, use Python:
  ```python
  import bcrypt
  print(bcrypt.hashpw(b"yourpassword", bcrypt.gensalt()).decode())
  ```

### 4. Start Qdrant Vector Database

You must have [Docker](https://www.docker.com/products/docker-desktop/) installed.

```sh
cd qdrant
docker compose up -d
```

This will start Qdrant on `localhost:6333`.

### 5. Run the Chatbot

Back in the project root:

```sh
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Usage

1. **Login** with your HR credentials.
2. **Upload Excel files** (with required columns) via the sidebar.
3. **Process files** to clean and embed the data.
4. **Chat**: Ask questions about the feedback data in Thai or English.
5. **Manage chats and files**: Switch, delete, or create new chat sessions and manage uploaded files.

---

## Excel File Format

Your Excel files must contain the following columns:

- ที่มาของ Feedback
- BU
- บคญ./บทญ.
- ประเภท Feedback
- รายละเอียด Feedback
- แนวทางการดำเนินการ
- สถานะการแจ้ง Process Owner
- Status
- รายละเอียด Status

If any column is missing, the file will be rejected.

---

## Security

- **Authentication**: Only users with the correct username and bcrypt-hashed password (from `.env`) can access the app.
- **Data Privacy**: All uploaded files and vector data are stored locally. No data is sent to external servers except for LLM API calls.
- **Session Management**: Chat and file management is per user session.

---

## Customization

- **Prompt Template**: The prompt for the LLM is in `logic/qa_chain.py` and can be customized for your organization's needs.
- **Vector DB**: Qdrant settings can be changed in `core/vector_store.py`.
- **Authentication**: Usernames and password hashes are managed via `.env` and `config.yaml`.

---

## Troubleshooting

- **Qdrant not running**: Make sure Docker is running and `docker compose up -d` was successful.
- **OpenAI API errors**: Check your API key and usage limits.
- **File processing errors**: Ensure your Excel files have all required columns and are not corrupted.
- **Port conflicts**: Change the default ports in `docker-compose.yml` or Streamlit config if needed.

---

## License

This project is for internal use at PTT. For other use, please contact the authors.

---

## Acknowledgements

- [LangChain](https://python.langchain.com/)
- [Qdrant](https://qdrant.tech/)
- [Streamlit](https://streamlit.io/)
- [OpenAI](https://openai.com/)
- [HuggingFace](https://huggingface.co/)

---

## Contact

For support or questions, contact the HR
