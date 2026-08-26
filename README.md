# 🏥 MedIntel AI — Intelligent Healthcare Analytics & Clinical Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![RAG](https://img.shields.io/badge/AI-Clinical%20RAG-FF6F00?style=flat&logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Container-Docker-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**MedIntel AI** is an enterprise-grade clinical decision support and predictive analytics platform. It combines machine learning risk prediction models, retrieval-augmented generation (RAG) over medical guidelines (ADA, ACC/AHA, JNC-8), interactive SQL analytics, and role-based HIPAA-compliant audit governance.

---

## 🌟 Key Features

- **Predictive Risk Analytics**: Automated ML models for Diabetes Risk, Cardiac Risk, and 30-Day Hospital Readmission Risk.
- **Clinical RAG Assistant**: Knowledge base retrieval over clinical practice guidelines with inline document citations powered by `SentenceTransformers`/`FAISS` and `Google Gemini AI`.
- **SQL Analytics Explorer**: Interactive query engine for clinical analysts with safety filters preventing destructive operations.
- **Security & Data Governance**: Role-based access control (`Clinician`, `Analyst`, `Admin`), dynamic patient data anonymization/PHI masking, and automated immutable audit logging.
- **Docker Ready**: Fully containerized setup for simplified deployment.

---

## 🏗 System Architecture

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                      AWS Cloud                          │
                  │                                                         │
  ┌───────────┐   │   ┌──────────────┐      ┌──────────────┐   ┌─────────┐  │
  │ Clinician │───┼──▶│ AWS ALB / WAF│─────▶│  AWS ECS     │──▶│ AWS RDS │  │
  │ / Analyst │   │   └──────────────┘      │  (Fargate)   │   │ (Postgre│  │
  └───────────┘   │                         └──────┬───────┘   │  SQL)   │  │
                  │                                │           └─────────┘  │
                  │                                ▼                        │
                  │                         ┌──────────────┐                │
                  │                         │   AWS S3     │                │
                  │                         │  (Docs/ML)   │                │
                  │                         └──────────────┘                │
                  └─────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
├── data/
│   └── clinical_literature/       # Clinical guidelines & protocols (ADA, ACC/AHA, JNC8)
├── models/                        # ML risk models & FAISS vector store indexes (git-ignored)
├── src/
│   ├── app.py                     # Flask REST API server & routing
│   ├── data/                      # Synthetic patient data generator
│   ├── database/                  # SQLAlchemy models & DB connection setup
│   ├── ml/                        # Machine learning model training & evaluation
│   ├── rag/                       # Clinical RAG assistant & vector store indexing
│   ├── security/                  # RBAC authorization & audit logging
│   ├── static/                    # Dashboard UI styles & JavaScript
│   └── templates/                 # Single Page Application HTML templates
├── aws_architecture.md            # Cloud deployment reference guide
├── Dockerfile                     # Container build instructions
├── docker-compose.yml             # Local multi-container compose configuration
├── requirements.txt               # Python package dependencies
├── run.py                         # One-click startup script (Seeding + ML + Vector DB + Web Server)
├── .env.example                   # Environment configuration template
└── .gitignore                     # Git tracking exclusions
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ installed
- Virtual environment tool (`venv` or `conda`)

### 2. Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/medintel-ai.git
   cd medintel-ai
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Add your optional Google Gemini API key to `.env` if you wish to use generative LLM clinical summaries.

### 3. Run the Platform

Launch the complete application with a single command:
```bash
python run.py
```
This automatically:
- Initializes the SQLite database and seeds 500 synthetic patient records.
- Trains and evaluates all ML risk models.
- Builds the FAISS clinical vector store index.
- Launches the web server at `http://127.0.0.1:5000`.

---

## 🐳 Docker Deployment

To run the application using Docker Compose:

```bash
docker-compose up --build
```
Access the application dashboard at `http://localhost:5000`.

---

## 🔒 Security & Data Privacy Notice

> [!NOTE]
> All patient data generated and used in this demo project is synthetic and de-identified. No real Protected Health Information (PHI) is contained in this repository. Real-world deployments require HIPAA-compliant cloud infrastructure (KMS encryption, private subnet isolation, TLS 1.3).

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
