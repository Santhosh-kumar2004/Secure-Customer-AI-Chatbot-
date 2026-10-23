# Secure Customer AI Chatbot

## About the Project

The Secure Customer AI Chatbot is an AI-powered chatbot designed to help customers get answers to their questions securely. It uses Retrieval-Augmented Generation (RAG) to retrieve relevant information and generate responses.

The project uses FastAPI for the backend, PostgreSQL for storing customer data and conversation history, and Ollama for local AI responses.

## Features

- Secure customer authentication using OTP.
- Customer-specific information retrieval.
- AI-powered responses using Ollama.
- Retrieval-Augmented Generation (RAG).
- Vector search using ChromaDB.
- Conversation history and memory.
- Invoice information retrieval.
- Invoice creation with confirmation.
- Database migrations using Alembic.
- API testing using Pytest.

## Technologies Used

- **Language:** Python 3.10
- **Backend:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Database Migrations:** Alembic
- **LLM:** Ollama (Llama 3.2)
- **Vector Database:** ChromaDB
- **Embeddings:** Sentence Transformers
- **Testing:** Pytest

## Project Structure

```text
Customer_AI_Chatbot/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth_service.py
│   ├── security.py
│   ├── llm_service.py
│   ├── vector_store.py
│   └── memory_service.py
├── migrations/
├── tests/
├── .gitignore
├── alembic.ini
├── requirements.txt
├── index_invoices.py
└── README.md
```

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Santhosh-kumar2004/Secure-Customer-AI-Chatbot-.git
cd Secure-Customer-AI-Chatbot-
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and configure your PostgreSQL connection and other required settings.

**Important:** Never upload your `.env` file or passwords to GitHub. Keep all secrets private.

### 5. Start PostgreSQL

Make sure PostgreSQL is installed and running. Create the database configured in your environment variables.

### 6. Run Database Migrations

```bash
alembic upgrade head
```

### 7. Start Ollama

Install Ollama and download the required model:

```bash
ollama pull llama3.2
```

Make sure the Ollama service is running.

### 8. Run the FastAPI Application

```bash
uvicorn app.main:app --reload
```

The API will be available at:

`http://127.0.0.1:8000`

Open the interactive API documentation:

`http://127.0.0.1:8000/docs`

## Running Tests

Run the automated tests with:

```bash
pytest -v
```

## How It Works

1. A customer authenticates with the application.
2. The chatbot identifies the customer's authorized information.
3. Relevant information is retrieved from the vector database.
4. Ollama generates a response based on the retrieved context.
5. Conversation history is stored for future reference.
6. Invoice-related actions can require customer confirmation before creation.

## Security

- Keep customer data isolated.
- Protect passwords, database credentials, and environment variables.
- Apply authentication and authorization before accessing customer-specific data.
- Never commit sensitive information to the repository.
