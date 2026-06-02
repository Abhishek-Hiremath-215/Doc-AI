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

## 🎨 Portfolio & Resume Demo Mode

To make this project easily evaluable on a resume portfolio, DocAI features a premium **Dual-Mode Architecture** built directly into the frontend. 

- **🕹️ Live Mode**: Connects directly to the FastAPI backend, PostgreSQL, PostgreSQL/Neo4j database, and external vector embeddings (fully operational in a local/cloud environment).
- **✨ Demo Mode (Recruiter Friendly)**: Completely bypasses backend dependencies, running fully client-side using a simulated mock database with **LocalStorage persistence**! This allows the entire platform (including database CRUD, organization creation, file uploading, workspace permissions, user activation, and chatbot chat sessions) to run statically on platforms like **Netlify**!

### ⚡ Recruiter Quick Login
When evaluated in Demo Mode, the login screen displays a series of custom cards designed for instant, frictionless evaluation:
* **Super Admin**: Explores global system overview and organization controls.
* **Organization Admin**: Manages workspace documents, users, and compliance rules.
* **Regular User**: Focuses on document ingestion and intelligent RAG chat queries.

Recruiters can click any profile to **pre-fill credentials and automatically log in with one click**!

### 🎛️ Dynamic Environment Switcher
A premium, glassmorphic floating toggle widget is rendered globally at the bottom-right corner of the app. Users can seamlessly switch between Live and Demo modes, automatically cleaning up sessions and re-initializing the environment.

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
