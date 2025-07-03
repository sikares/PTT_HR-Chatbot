# 🏢 PTT HR Feedback Chatbot - Proof of Concept (PoC)

## Overview

A secure, private, and interactive chatbot system for analyzing and querying employee feedback data at PTT. Upload Excel files to process feedback, then interactively chat with your data using advanced AI and vector search technology (Pinecone) through an intuitive Streamlit interface.

---

## 📌 Key Features

✅ **Authentication**

- Supports 2 user types:
  - HR_Users (regular users)
  - HR_Admin (admins who can reset HR_Users passwords)
- Stores login status using session and JSON files

✅ **Admin Panel**

- Admins can reset HR_Users passwords via UI

✅ **Chat Session Management**

- Supports creating, switching, and deleting chats
- Saves chat history persistently using shelve database (`ptt_chat_history_sessions`)

✅ **Feedback File Management**

- Upload multiple Excel files (`.xlsx`, `.xls`)
- Validate important columns according to `SELECTED_COLUMNS`
- Process data, split text into chunks, create embeddings, and save vectors to Pinecone
- Display uploaded files with option to delete files

✅ **AI Chatbot**

- Answers questions about feedback using a Retrieval QA LLM
- User types questions in chat box, and the system responds with information from uploaded files

---

## 🚀 How to Use

### 1.) Clone / Install the project

```bash
git clone your-repo-url
cd your-project-folder
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 2️.) Create `.env` file

**Use the `test.py` script to generate password hashes, then update the `.env` file like this:**

```env
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key

HR_USERNAME=HR_Users
HR_PASSWORD_HASH=<hash from test.py>
HR_ADMIN_USERNAME=HR_Admin
HR_ADMIN_PASSWORD_HASH=<hash from test.py>
```

**Example `test.py` script to generate password hashes**

```python
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# Replace these with your desired passwords

admin_password = "your_admin_password"
admin_hash = hash_password(admin_password)

print("=== Password Hashes ===")
print(f"HR_Admin Password: {admin_password}")
print(f"HR_Admin Hash: {admin_hash}")
print()

hr_user_password = "your_user_password"
hr_user_hash = hash_password(hr_user_password)

print(f"HR_Users Password: {hr_user_password}")
print(f"HR_Users Hash: {hr_user_hash}")
print()

print("=== Updated .env file content ===")
print(f"HR_USERNAME=your_username_for_users")
print(f"HR_PASSWORD_HASH={hr_user_hash}")
print(f"HR_ADMIN_USERNAME=your_username_for_admin")
print(f"HR_ADMIN_PASSWORD_HASH={admin_hash}")
```

**Run the hash generator:**

`python test.py`

**Important Notes:**

- Replace all placeholder values (your_openai_key, your_pinecone_key, etc.) with your actual values
- Never commit real passwords to version control - only the hashes
- Keep your .env file in your .gitignore
- The example passwords should be changed to strong, unique passwords

### 3️.) Create upload directory

`mkdir -p data/uploads`

### 4️.) Run the app

`streamlit run app.py`

_Open the browser at URL, e.g., http://localhost:8501_

### 5️.) Login

At the first load, system asks for Username and Password:

- HR_Users → Access Chatbot page
- HR_Admin → Access Admin Panel to manage HR_Users passwords

### 6️.) การใช้งาน Chatbot

Upload Excel files containing columns:
`ที่มาของ Feedback`, `BU`, `บคญ./บทญ.`, `ประเภท Feedback`, `รายละเอียด Feedback`, `แนวทางการดำเนินการ`, `สถานะการแจ้ง Process Owner`, `Status`, `รายละเอียด Status`

- Click Process Files to process uploaded files
- Ask questions in chat, e.g.:
  - “หลักการคัดเข้า และคัดออก DM Pool”
  - “สามารถลาพักร้อนครึ่งวันได้หรือไม่”
- The system will search and respond immediately

### 7️.) การจัดการไฟล์

Uploaded files are listed in the Sidebar.

- You can delete files → This removes both the file and its Pinecone vectors

### 8️.) การจัดการแชท

In Sidebar > Chats:

- Create new chat `➕ New Chat`
- Switch between existing chats
- Delete chats with confirmation

---

## 🛡️ Important Considerations When Hiring Contractors

### 1️.) Data Security

Feedback may contain sensitive content (e.g., complaints) → NDA must be signed.

### 2️.) Code Ownership

Contracts must clearly state the source code belongs to the company/organization.

### 3️.) Contractor Expertise

Contractors should have experience in:

- Streamlit
- Pinecone or other VectorDB
- OpenAI API
- Excel file handling

### 4️.) Password Management

- Uses bcrypt hashing → fairly secure
- Password reset for HR_Users allowed only via HR_Admin

### 5️.) File and Data Management

- Feedback files and upload status stored on server → secure file handling required
- Backup policies and data retention schedules needed

### 6️.) System Scalability

- Current system suits PoC and small number of users
- For production and large organizations, architecture adjustments are needed, e.g., switching to a proper database or auth service

### 7️.) Maintenance Readiness

- Contractors should support system after delivery, including updates when Pinecone or OpenAI APIs change

## Project Structure

```
PTT_HR-Chatbot/
├── core/                     # Core system components
│   └── vector_store.py       # Vector storage implementation
├── data/                     # Data storage
├── icons/                    # Icon storage
│   └── ptt.ico               # PTT icon
├── logic/                    # Business logic
│   ├── chunking.py           # Document chunking logic
│   ├── data_processing.py    # Data cleaning and processing
│   ├── embedding.py          # Embedding implementation
│   └── qa_chain.py           # QA chain logic
├── utils/                    # Utility functions
│   ├── auth.py               # Authentication
│   └── session.py            # Session and file data management
├── .env                      # Environment variables file
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
└──  README.md                # Project documentation
```

### 🔗 Notes

This system is a Proof of Concept (PoC) designed to test feasibility.
It should **NOT** be used directly in production without thorough security and performance testing.

---

## Support

For any questions or issues, please contact:

- _Developer: Sikares Nuntipatsakul_
- _Email: sikares.n@gmail.com_

## License

This project is for internal use at PTT.

**_Last Updated: 2025-07-03_**
