# GenomeInsight

Multi-domain genomic and health data analysis platform — inspired by Nebula Genomics and InsideTracker.

## Architecture

```
GenomeInsight/
├── backend/          # Flask API + Celery workers
│   ├── app/
│   │   ├── api/      # Blueprint routes (auth, genome, blood, epigenetics,
│   │   │             #   microbiome, wgs, healthspan, subscription, chat)
│   │   ├── models/   # SQLAlchemy 2.0 models
│   │   ├── services/ # File upload, auth, encryption
│   │   ├── tasks/    # Celery async tasks (analysis, emails)
│   │   └── utils/    # Analyzers (genome, blood, microbiome, WGS, ML, blockchain, chatbot)
│   ├── tests/        # pytest test suite
│   └── Dockerfile
├── frontend/         # React 18 + MUI + Tailwind (Wabi Sabi design)
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── contexts/    # Auth context
│   │   ├── services/    # API client (axios)
│   │   └── theme/       # Wabi Sabi MUI theme
│   └── Dockerfile
└── docker-compose.yml
```

## Features

### Core (Free Tier)
- VCF/VCF.GZ genome upload and variant analysis
- Blood panel upload with marker tracking
- Epigenetic data analysis (DNA methylation)
- Microbiome composition (16S/WGS)
- Wearable device integration (Garmin, Apple, Fitbit via Terra)
- Daily cross-domain health insights
- AES-256-GCM encryption at rest

### Premium Tier
- **InnerAge** — Biological age via PhenoAge (Levine 2018) + Horvath epigenetic clock + wearable metrics
- **Optimized Zones** — Personalized biomarker ranges adjusted by age, sex, genetics
- **Predictive Trends** — Prophet/ARIMA/linear cascade forecasting for biomarkers
- **Weekly Healthspan Reports** — Sleep, activity, nutrition, stress scoring
- **AI Health Chat** — LangChain + OpenAI GPT-4o conversational agent with user data context
- **WGS Analysis** — FASTQ/BAM upload, variant calling, ancestry inference
- **Blockchain Data Ownership** — ERC-721 NFT minting for health data (Ethereum/Sepolia)
- **Weekly Email Reports** — SendGrid transactional emails for premium subscribers

## Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- Redis

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your keys
python -c "from app import create_app; create_app()"  # Init DB
gunicorn wsgi:app -w 4 -b 0.0.0.0:5000
```

### Frontend

```bash
cd frontend
npm install
npm start  # Dev server on :3000
```

### Celery Workers

```bash
cd backend
celery -A celery_worker.celery worker --beat --loglevel=info -Q default,analysis,wearables,insights
```

### Docker

```bash
cp .env.example .env  # Edit with your keys
docker-compose up -d
```

## Environment Variables

### Required
| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask secret key (32+ chars) |
| `MASTER_ENCRYPTION_KEY` | AES-256 master key for file encryption |

### Stripe (Premium Features)
| Variable | Description |
|----------|-------------|
| `STRIPE_SECRET_KEY` | Stripe API secret key |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (frontend) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret |
| `STRIPE_PRICE_BASIC` | Stripe Price ID for basic tier |
| `STRIPE_PRICE_PREMIUM` | Stripe Price ID for premium tier |

### OpenAI (AI Chatbot)
| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o |

### SendGrid (Email)
| Variable | Description |
|----------|-------------|
| `SENDGRID_API_KEY` | SendGrid API key |
| `SENDGRID_FROM_EMAIL` | Sender email address |

### Blockchain (Ethereum)
| Variable | Description |
|----------|-------------|
| `ETH_RPC_URL` | Ethereum RPC endpoint (e.g., Infura, Alchemy) |
| `HEALTH_NFT_CONTRACT_ADDRESS` | Deployed HealthDataNFT contract address |
| `ETH_ACCOUNT_ADDRESS` | Server Ethereum address for signing |
| `ETH_CHAIN_ID` | Chain ID (11155111 for Sepolia testnet) |

### Optional
| Variable | Description |
|----------|-------------|
| `NCBI_API_KEY` | NCBI E-utilities API key |
| `TERRA_API_KEY` | Terra wearable API key |
| `TERRA_DEV_ID` | Terra developer ID |
| `DATABASE_URL` | Database URI (default: SQLite) |
| `CELERY_BROKER_URL` | Redis broker (default: redis://localhost:6379/1) |
| `FRONTEND_URL` | Frontend URL for email links |

## Ethereum Contract ABI

The Health Data NFT contract implements ERC-721 with additional methods:

```json
[
  {"name": "mintHealthRecord", "type": "function", "inputs": [
    {"name": "to", "type": "address"},
    {"name": "dataHash", "type": "bytes32"},
    {"name": "dataType", "type": "string"}
  ]},
  {"name": "storeDataHash", "type": "function", "inputs": [
    {"name": "tokenId", "type": "uint256"},
    {"name": "dataHash", "type": "bytes32"}
  ]},
  {"name": "listForSale", "type": "function", "inputs": [
    {"name": "tokenId", "type": "uint256"},
    {"name": "price", "type": "uint256"}
  ]},
  {"name": "purchaseData", "type": "function", "inputs": [
    {"name": "tokenId", "type": "uint256"}
  ]}
]
```

Deploy to Sepolia testnet using Hardhat/Foundry. Set `HEALTH_NFT_CONTRACT_ADDRESS` to the deployed address.

## Cloud Deployment

### AWS
- **EC2/ECS** for Flask API + Celery workers
- **ElastiCache (Redis)** for Celery broker
- **RDS (PostgreSQL)** for production database
- **S3** for encrypted file storage
- **SageMaker** for ML compute (Prophet, sklearn)
- **SES** as alternative to SendGrid

### GCP
- **Cloud Run** for Flask API
- **Memorystore (Redis)** for Celery broker
- **Cloud SQL (PostgreSQL)** for database
- **GCS** for file storage
- **Vertex AI** for ML workloads
- **Cloud Tasks** as alternative to Celery

### ML Compute Notes
- Prophet and scikit-learn models run in Celery workers
- For heavy WGS analysis, use dedicated ML instances (g5.xlarge / n1-standard-8)
- Consider GPU instances for future deep learning models
- Set `task_soft_time_limit=300` and `task_time_limit=600` in Celery config

## Testing

```bash
cd backend
pytest tests/ -v
```

Test coverage includes:
- Auth (register, login, JWT refresh)
- Genome parsing and analysis
- Blood panel parsing and trends
- Epigenetics analysis
- Microbiome analysis and correlations
- ML analyzer (PhenoAge, zones, predictions)
- Blockchain utilities (simulation mode)
- AI chatbot (mocked OpenAI)
- Subscription and premium gating

## API Endpoints

### Auth
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`

### Genome
- `POST /api/v1/genome/upload`
- `GET /api/v1/genome/uploads`
- `GET /api/v1/genome/analysis/:id/report`

### Blood
- `POST /api/v1/blood/upload`
- `GET /api/v1/blood/trends`
- `POST /api/v1/blood/analyze-changes`

### WGS
- `POST /api/v1/wgs/upload-wgs`
- `GET /api/v1/wgs/ancestry-report/:id`
- `POST /api/v1/wgs/blockchain-store`

### Healthspan (Premium)
- `POST /api/v1/healthspan/calculate-innerage`
- `POST /api/v1/healthspan/optimized-zones`
- `POST /api/v1/healthspan/predict-trends`
- `GET /api/v1/healthspan/reports`

### Chat (Premium)
- `POST /api/v1/chat/message`
- `GET /api/v1/chat/sessions`

### Subscription
- `GET /api/v1/subscription/status`
- `POST /api/v1/subscription/create-checkout`
- `POST /api/v1/subscription/webhook`

## License

Proprietary — all rights reserved.
