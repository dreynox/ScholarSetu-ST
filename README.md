# ScholarSetu (MoTA Unified Scholarship Platform)

**Smart India Hackathon (SIH) — SIH26238**  
*Unified Scholarship Mobile & Web Application for Tribal Students (Ministry of Tribal Affairs)*

---

## 📁 Project Structure

```text
ScholarSetu-ST/
├── backend/                  # FastAPI Python backend service
│   ├── app/                  # Application source code
│   │   ├── core/             # Configuration, security & dependencies
│   │   ├── db/               # Supabase database clients
│   │   ├── models/           # Domain data models
│   │   ├── routes/           # REST API route handlers
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # Business logic layer
│   │   ├── utils/            # Shared utilities & error handlers
│   │   └── main.py           # FastAPI entrypoint & middleware
│   ├── tests/                # Pytest test suite
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── README.md             # Backend detailed documentation
│
├── frontend/                 # Vite + React + Tailwind CSS client
│   ├── public/               # Static assets
│   ├── src/                  # Source code (components, pages, services, etc.)
│   ├── package.json          # Frontend dependencies & scripts
│   ├── vite.config.js        # Vite build & dev config
│   └── tailwind.config.js    # Tailwind CSS config
│
├── database/                 # SQL schemas & database migration scripts
├── ai/                       # AI models, agents, and OCR processing pipelines
├── docs/                     # Documentation & team dev logs
│   └── notes/                # Progress milestones and sprint notes
└── .gitignore                # Global git ignore configuration
```

---

## 🚀 Quick Start Guide

### 1. Backend (FastAPI + Supabase)

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate      # Windows (PowerShell/CMD)
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment variables:
   ```bash
   cp .env.example .env
   ```
5. Run the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   API Docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

### 2. Frontend (React + Vite)

1. Open a terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
   The application will run at [http://localhost:3000](http://localhost:3000).
