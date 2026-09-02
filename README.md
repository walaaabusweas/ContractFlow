


# ContractFlow AI 📜🤖

An automated legal contract review and analysis platform powered by advanced AI agent workflows and Retrieval-Augmented Generation (RAG). ContractFlow AI streamlines legal document processing by extracting clauses, validating terms, categorizing risks, and providing deep insights through a serverless backend architecture.

---

## 🚀 Key Features

* **Automated Contract Review**: Deeply analyzes legal texts, identifies clauses, and flags potential risks or anomalies.
* **Agentic Workflows & RAG**: Uses **LangGraph** and **LangChain** to orchestrate multi-step review workflows, ensuring context-aware retrieval and accurate information extraction.
* **Vector & Relational Storage**: Combines **PostgreSQL with pgvector**, **ChromaDB**, and **Redis** for efficient semantic search, caching, and state persistence.
* **Serverless & Scalable Backend**: Built with **FastAPI** and containerized using **Docker**, deployed seamlessly on **AWS Lambda** (via Amazon ECR/S3) and **Render**.
* **Interactive UI**: Features an intuitive, user-friendly **Gradio** interface for smooth document uploading and analysis management.

---

## 🛠️ Tech Stack

* **Core Language:** Python 3.10+
* **AI & Orchestration:** LangGraph, LangChain, OpenAI / Qwen / Anthropic LLMs
* **Databases & Vector Storage:** PostgreSQL (`pgvector`), ChromaDB, Redis
* **Backend & API:** FastAPI, Serverless Architecture
* **Deployment & Cloud:** Docker, AWS Lambda, Amazon ECR, Amazon S3, Render
* **Frontend UI:** Gradio

---

## ⚙️ Architecture Overview

[ User / Gradio UI ] 
        │
        ▼
[ FastAPI Backend ] ──> [ Redis (State & Caching) ]
        │
        ▼
[ LangGraph / LangChain Agent Workflow ]
        ├──> [ ChromaDB / pgvector (Vector Search & RAG) ]
        └──> [ LLM Inference (OpenAI / Qwen / Claude) ]

---

## Getting Started
Prerequisites
- Docker & Docker Compose (Recommended)
- Python 3.10+ (if running locally without Docker)
- PostgreSQL with pgvector extension installed
- Redis instance running



### Installation & Running

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/ContractFlow-AI.git
   cd ContractFlow-AI
   ```

2. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your required credentials:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   DATABASE_URL=postgresql://user:password@localhost:5432/contractflow
   REDIS_URL=redis://localhost:6379
   ```

3. **Run using Docker Compose (Recommended):**
   The application is fully containerized and manages dependencies automatically through Docker and configuration files:
   ```bash
   docker-compose up --build
   ```

4. **Running Locally (Alternative):**
   If you prefer to run it locally using your `pyproject.toml` dependencies:
   ```bash
   pip install .
   python main.py
   ```

---

## 💡 Use Cases
* **Legal Teams & Law Firms:** Speed up the preliminary contract review process.
* **Enterprise Procurement:** Quickly scan vendor agreements for compliance and risk factors.
* **Freelancers & Small Businesses:** Understand complex legal clauses without expensive legal overhead.

---

## 👩‍💻 Author
**Walaa khaled**  
*Computer Engineering Graduate | AI Engineer & iOS Developer*  

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.