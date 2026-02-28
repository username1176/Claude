# GenomeInsight

Privacy-first health-tech application that analyzes genome (VCF), blood test, epigenetic, microbiome, and wearable device data to provide personalized cross-domain health insights, risk scores, and AI-generated recommendations.

## Features

- **Genome Analysis** — Upload VCF files from 23andMe, AncestryDNA, Nebula Genomics, etc. Variants are parsed, annotated via ClinVar/Ensembl/GWAS APIs, and scored across health risk categories.
- **Blood Test Tracking** — Upload PDF or CSV blood test results. 60+ biomarkers are auto-parsed with delta tracking over time.
- **Epigenetic Analysis** — Upload BED (histone ChIP-seq) or CSV (methylation array) data. Regions are annotated using ENCODE and Roadmap Epigenomics, then cross-referenced with genome variants.
- **Microbiome Analysis** — Upload BIOM, OTU table (CSV/TSV), or FASTQ files. Taxonomy classification, alpha diversity (Shannon, Simpson, Chao1), enterotype classification, phyla ratios, and cross-domain correlations with genome variants and blood markers.
- **Wearable Integration** — Connect Fitbit, Garmin, Oura, WHOOP, Polar, and other devices via Terra API. Daily activity, sleep, heart rate, HRV, SpO2, and stress data are synced automatically.
- **Cross-Domain Insights** — Unified correlator engine spanning all 5 domains. Detects multi-domain interactions (e.g., FTO variant + F/B ratio + low activity, MTHFR + epigenetic change + low Bifidobacterium, epigenetic gut-axis methylation + blood markers).
- **AI Reports** — GPT-powered narrative health reports with risk context and actionable recommendations.
- **Privacy-First** — AES-256-GCM envelope encryption for all uploaded files and OAuth tokens. JWT authentication with refresh tokens.

> **Disclaimer:** GenomeInsight is for informational and educational purposes only. It is NOT medical advice and should NOT be used to diagnose, treat, or prevent any disease. Microbiome analysis is an emerging science; results vary by sampling method, timing, diet, and medication. Always consult a qualified healthcare provider.

## Architecture

```
GenomeInsight/
├── backend/                  # Flask REST API
│   ├── app/
│   │   ├── api/              # Blueprints (auth, genome, blood, epigenetics, wearables, microbiome, analysis)
│   │   ├── models/           # SQLAlchemy models (user, genome, blood, epigenetics, wearable, microbiome)
│   │   ├── services/         # Genome analyzer, report generator, encryption
│   │   ├── tasks/            # Celery async tasks (genome, blood, epigenetics, wearable, microbiome)
│   │   └── utils/            # VCF parser, blood parser, epigenetics/microbiome analyzers, correlator
│   ├── tests/                # Pytest test suite (390+ tests)
│   ├── celery_worker.py      # Celery worker + Beat scheduler
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React 18 SPA
│   ├── src/
│   │   ├── components/       # Dashboard, Upload, Report, Wearables, Microbiome, UnifiedReport
│   │   ├── contexts/         # AuthContext (JWT management)
│   │   └── services/         # Axios API client with auto-refresh
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml        # 5 services: backend, frontend, redis, celery, celery-beat
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
# Edit .env: set SECRET_KEY, MASTER_ENCRYPTION_KEY, and optionally API keys

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

### Celery Workers (for background tasks)

```bash
# Terminal 1: Celery worker (processes tasks)
cd backend
celery -A celery_worker.celery worker --loglevel=info -Q default,analysis,wearables,insights

# Terminal 2: Celery Beat (schedules periodic tasks)
celery -A celery_worker.celery beat --loglevel=info
```

Scheduled tasks:
| Task | Schedule | Description |
|------|----------|-------------|
| `sync_all_active_connections` | Every 6 hours | Pull wearable data from Terra API |
| `generate_daily_insights` | Daily at 02:30 UTC | Cross-domain insight generation with unified correlator |
| `schedule_weekly_reanalysis` | Monday 03:00 UTC | Re-run microbiome cross-domain correlations |
| `check_and_reanalyze_stale` | Daily at 04:00 UTC | Re-analyze microbiome when new genome/blood/wearable data arrives |

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
# Edit .env with production values (see Environment Variables below)

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
| celery | — | Background task worker (genome, blood, epigenetics, wearable, microbiome analysis) |
| celery-beat | — | Periodic task scheduler (wearable sync, daily insights, microbiome re-analysis) |

### Cloud Scheduling Alternative

For cloud deployments, you can replace Celery Beat with platform-native schedulers:

- **AWS**: CloudWatch Events / EventBridge rules triggering ECS tasks or Lambda
- **GCP**: Cloud Scheduler triggering Cloud Run or Cloud Tasks
- **Azure**: Azure Functions Timer triggers

Configure these to call the `/api/v1/insights/generate` or `/api/v1/analysis/daily/generate` endpoints or invoke the Celery tasks directly.

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

### Epigenetics
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/epigenetics/upload` | Upload BED/CSV epigenetic data |
| GET | `/api/v1/epigenetics/uploads` | List epigenetic uploads |
| GET | `/api/v1/epigenetics/uploads/:id` | Upload detail with analysis |
| DELETE | `/api/v1/epigenetics/uploads/:id` | Delete upload |
| GET | `/api/v1/epigenetics/analysis/:id` | Analysis status/results |
| GET | `/api/v1/epigenetics/analysis/:id/regions` | Annotated regions (paginated) |
| GET | `/api/v1/epigenetics/analysis/:id/genome-overlay` | Genome cross-reference |
| POST | `/api/v1/epigenetics/uploads/:id/analyze` | Re-trigger analysis |

### Microbiome
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/microbiome/upload` | Upload BIOM/CSV/FASTQ microbiome data |
| GET | `/api/v1/microbiome/uploads` | List microbiome uploads |
| GET | `/api/v1/microbiome/uploads/:id` | Upload detail |
| DELETE | `/api/v1/microbiome/uploads/:id` | Delete upload |
| GET | `/api/v1/microbiome/analysis/:id` | Analysis status/results |
| GET | `/api/v1/microbiome/analysis/:id/taxa` | Taxonomy listing (paginated) |
| GET | `/api/v1/microbiome/analysis/:id/composition` | Phylum/genus composition |
| GET | `/api/v1/microbiome/analysis/:id/genome-correlation` | Genome cross-reference |
| POST | `/api/v1/microbiome/uploads/:id/analyze` | Re-trigger analysis |
| GET | `/api/v1/microbiome/analysis/:id/full` | Full cross-domain analysis |

### Wearables
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/wearables/providers` | List supported providers |
| POST | `/api/v1/wearables/connect` | Initiate OAuth connection |
| POST | `/api/v1/wearables/callback` | Handle OAuth callback |
| GET | `/api/v1/wearables/connections` | List active connections |
| DELETE | `/api/v1/wearables/connections/:id` | Disconnect device |
| POST | `/api/v1/wearables/connections/:id/sync` | Trigger manual sync |
| GET | `/api/v1/wearables/data` | Query historical wearable data |
| GET | `/api/v1/wearables/data/latest` | Get latest day's data |

### Insights
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/insights/daily` | Today's cross-domain insights |
| GET | `/api/v1/insights/history` | Insight history (paginated) |
| POST | `/api/v1/insights/generate` | Trigger insight generation |

### Unified Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analysis/daily` | Unified cross-domain daily analysis (all domains + correlations) |
| POST | `/api/v1/analysis/daily/generate` | Force re-generation of unified analysis |

## Security

- JWT access + refresh tokens with configurable expiry
- AES-256-GCM envelope encryption for uploaded files and OAuth tokens
- CORS configured per-environment with credentials support
- Rate limiting: 5/hour genome uploads, 10/hour blood uploads, 10/hour microbiome uploads
- Filename sanitization against path traversal
- Security headers: X-Content-Type-Options, X-Frame-Options, HSTS (production)
- MAX_CONTENT_LENGTH defense-in-depth for uploads
- Wearable OAuth tokens encrypted with per-user data encryption keys

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | JWT signing key |
| `MASTER_ENCRYPTION_KEY` | Yes | — | 64-char hex string for AES-256 master key |
| `FLASK_ENV` | No | development | `development`, `testing`, `production` |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated origins |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/1` | Redis URL for Celery broker |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/2` | Redis URL for Celery results |
| `OPENAI_API_KEY` | No | — | For AI report generation |
| `NCBI_API_KEY` | No | — | For ClinVar/NCBI lookups and microbiome taxonomy |
| `TERRA_API_KEY` | No | — | Terra API key for wearable integrations |
| `TERRA_DEV_ID` | No | — | Terra developer ID |
| `TERRA_REDIRECT_URI` | No | — | OAuth redirect URI (e.g., `http://localhost:3000/wearables`) |
| `MAX_MICROBIOME_FILE_SIZE_MB` | No | `200` | Maximum microbiome file upload size |
| `NMDC_API_BASE` | No | `https://api.microbiomedata.org` | NMDC API base URL for microbiome data enrichment |

### Wearable API Setup

1. Sign up at [tryterra.co](https://tryterra.co) to get `TERRA_API_KEY` and `TERRA_DEV_ID`
2. Configure the redirect URI in your Terra dashboard to match `TERRA_REDIRECT_URI`
3. Set these values in your `.env` file
4. Without these keys, wearable connections will use mock/demo data for development

### Microbiome & External API Notes

- **NMDC API**: The microbiome module optionally queries the National Microbiome Data Collaborative API for biosample enrichment. Public access is available but may be rate-limited. Set `NMDC_API_BASE` to customize the endpoint.
- **NCBI eUtils**: Taxonomy lookups use NCBI's public eUtils API. For high-volume usage, obtain a free API key from [NCBI](https://www.ncbi.nlm.nih.gov/account/) and set `NCBI_API_KEY` to increase rate limits from 3 to 10 requests/second.
- **Microbiome sampling**: Results vary significantly by collection method, timing, diet, and medications. A single sample provides a snapshot, not a definitive assessment.

## Tech Stack

**Backend:** Flask, SQLAlchemy, Celery, Redis, PyJWT, cryptography, cyvcf2, httpx, BioPython, scipy, oauthlib

**Frontend:** React 18, Material-UI 5, React Router 6, Axios, Recharts, react-dropzone

**Infrastructure:** Docker, Nginx, Gunicorn, Celery Beat, SQLite (dev) / PostgreSQL (prod)
