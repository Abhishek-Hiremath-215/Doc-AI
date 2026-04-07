# 🚀 DocAI: Advanced RAG SaaS Platform

DocAI is a high-performance, scalable **Retrieval-Augmented Generation (RAG)** platform designed for intelligent document interaction. It leverages a unique **Hybrid Graph-Vector** architecture to provide deeper, context-aware insights from your data.

![DocAI Banner](https://img.shields.io/badge/DocAI-RAG--SaaS-blueviolet?style=for-the-badge&logo=fastapi)

## 🌟 Key Features

- **🧠 Hybrid Retrieval**: Combines **Neo4j Knowledge Graphs** with **Qdrant Vector Embeddings** for superior accuracy and relationship-based discovery.
- **🏢 Multi-Tenancy & RBAC**: Advanced Role-Based Access Control (Super Admin, Org Admin, User) to manage organizations and project permissions securely.
- **💬 Contextual Chat**: Intelligent chat interface powered by **LangGraph** and **LangChain**, capable of maintaining long-running memory and complex workflows.
- **📁 Document Intelligence**: Support for PDF, CSV, and XLSX processing with automated metadata extraction.
- **🕸️ Integrated Scraper**: Built-in web scraping tools to ingest live data directly into your knowledge base.
- **📊 Dynamic Visualization**: Automated chart generation based on document data analysis.

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Backend** | FastAPI, Python 3.10+, SQLAlchemy, Pydantic |
| **Orchestration** | LangChain, LangGraph |
| **Vector DB** | Qdrant |
| **Graph DB** | Neo4j |
| **Relational DB** | PostgreSQL |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide Icons |
| **AI Models** | OpenAI GPT-4o/Llama 3.1, HuggingFace BGE Embeddings |

## 📂 Project Structure

```text
.
├── backend/                # FastAPI Application
│   ├── agents/             # AI Workflow Logic (LangGraph)
│   ├── api/                # REST API Endpoints
│   ├── core/               # Configuration & DB Initializations
│   ├── models/             # SQLAlchemy Database Models
│   └── services/           # Business Logic Layer
├── frontend/               # React SPA (Vite)
│   ├── src/components/     # Reusable UI Components
│   ├── src/pages/          # Page Views (Dashboards, Auth)
│   └── src/context/        # Global State Management
└── screenshots/            # UI Previews & Documentation Assets
```

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (for Neo4j and Qdrant)

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: .\venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your `.env` file (see `backend/core/config.py` for required variables).
5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

## 🔒 Security
DocAI implements strict security protocols:
- **JWT Authentication** for all API endpoints.
- **CORS** protection for frontend-backend communication.
- **Secret Scanning** integrated via GitHub Push Protection.
- **Environment Isolation** for all sensitive API keys.

---
Developed by [Abhishek Hiremath](https://github.com/Abhishek-Hiremath-215)
