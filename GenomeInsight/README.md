# GenomeInsight

Privacy-first health-tech application that analyzes genome (VCF) and blood test data to provide personalized health insights, risk scores, and AI-generated recommendations.

## Features

- **Genome Analysis** — Upload VCF files from 23andMe, AncestryDNA, Nebula Genomics, etc. Variants are parsed, annotated via ClinVar/Ensembl/GWAS APIs, and scored across health risk categories.
- **Blood Test Tracking** — Upload PDF or CSV blood test results. 60+ biomarkers are auto-parsed with delta tracking over time.
- **Genome-Blood Cross-Referencing** — Correlates genetic variants (APOE, TCF7L2, MTHFR, etc.) with blood markers for deeper insights.
- **AI Reports** — GPT-powered narrative health reports with risk context and actionable recommendations.
- **Privacy-First** — AES-256-GCM envelope encryption for uploaded files. JWT authentication with refresh tokens.

> **Disclaimer:** GenomeInsight is for informational and educational purposes only. It is NOT medical advice and should NOT be used to diagnose, treat, or prevent any disease. Always consult a qualified healthcare provider.

## Architecture

```
GenomeInsight/
├── backend/              # Flask REST API
│   ├── app/
│   │   ├── api/          # Blueprints (auth, genome, blood)
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── services/     # Genome analyzer, report generator
│   │   ├── tasks/        # Celery async tasks
│   │   └── utils/        # VCF parser, blood parser, encryption
│   ├── tests/            # Pytest test suite (106 tests)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # React 18 SPA
│   ├── src/
│   │   ├── components/   # Login, Register, Dashboard, Upload, Report
│   │   ├── contexts/     # AuthContext (JWT management)
│   │   └── services/     # Axios API client with auto-refresh
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── .env.example
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Redis (for Celery task queue)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env: set SECRET_KEY, MASTER_KEY, and optionally API keys

# Run the development server
flask run
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
# Opens at http://localhost:3000 (proxies API to :5000)
```

### Running Tests

```bash
# Backend (from backend/)
pytest -v

# Frontend (from frontend/)
npm test
```

## Docker Deployment

```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env with production values

# 2. Build and run all services
docker compose up --build -d

# Access at http://localhost
# API at http://localhost:5000
```

Services:
| Service | Port | Description |
|---------|------|-------------|
| frontend | 80 | Nginx serving React SPA + API proxy |
| backend | 5000 | Flask/Gunicorn REST API |
| redis | 6379 | Celery message broker |
| celery | — | Background task worker |

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Login (returns JWT) |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Invalidate tokens |

### Genome
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/genome/upload` | Upload VCF file |
| GET | `/api/v1/genome/uploads` | List user uploads |
| GET | `/api/v1/genome/analysis/:id` | Analysis status/details |
| GET | `/api/v1/genome/analysis/:id/risks` | Risk category scores |
| GET | `/api/v1/genome/analysis/:id/recommendations` | Health recommendations |
| GET | `/api/v1/genome/analysis/:id/report` | AI-generated report |

### Blood
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/blood/upload` | Upload blood test (PDF/CSV) |
| GET | `/api/v1/blood/uploads` | List blood uploads |
| GET | `/api/v1/blood/history` | Blood test history |
| POST | `/api/v1/blood/analyze-changes` | Delta analysis + genome insights |
| GET | `/api/v1/blood/trends` | Marker trends over time |

## Security

- JWT access + refresh tokens with configurable expiry
- AES-256-GCM envelope encryption for uploaded files
- CORS configured per-environment with credentials support
- Rate limiting: 5/hour genome uploads, 10/hour blood uploads
- Filename sanitization against path traversal
- Security headers: X-Content-Type-Options, X-Frame-Options, HSTS (production)
- MAX_CONTENT_LENGTH defense-in-depth for uploads

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | JWT signing key |
| `MASTER_KEY` | Yes | — | Encryption master key (base64) |
| `FLASK_ENV` | No | development | `development`, `testing`, `production` |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated origins |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/0` | Redis URL |
| `OPENAI_API_KEY` | No | — | For AI report generation |
| `NCBI_API_KEY` | No | — | For ClinVar/NCBI lookups |

## Tech Stack

**Backend:** Flask, SQLAlchemy, Celery, Redis, PyJWT, cryptography, cyvcf2, httpx

**Frontend:** React 18, Material-UI 5, React Router 6, Axios, Recharts, react-dropzone

**Infrastructure:** Docker, Nginx, Gunicorn, SQLite (dev) / PostgreSQL (prod)
