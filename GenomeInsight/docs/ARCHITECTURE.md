# GenomeInsight — Application Architecture

> **Status**: Design Phase
> **Version**: 0.1.0
> **Last Updated**: 2026-02-27

---

## Table of Contents

1. [Overview](#1-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Data Models](#3-data-models)
4. [API Endpoints](#4-api-endpoints)
5. [Security Considerations](#5-security-considerations)
6. [Genome Database Integration Plan](#6-genome-database-integration-plan)
7. [Blood Test Processing Pipeline](#7-blood-test-processing-pipeline)
8. [AI-Driven Insights Engine](#8-ai-driven-insights-engine)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Ethical and Legal Considerations](#10-ethical-and-legal-considerations)

---

## 1. Overview

GenomeInsight is a privacy-first web application that enables users to upload
genome data (VCF files from services like 23andMe, AncestryDNA, Nebula Genomics)
and routine blood test results, then receive personalized health insights
powered by public genome research databases and AI-driven natural language
reports.

### Core Value Proposition

- **Genome Analysis**: Parse user variants, cross-reference against ClinVar,
  Ensembl, GWAS Catalog, and NCBI to surface disease risk associations,
  pharmacogenomic interactions, and trait predictions.
- **Blood Test Tracking**: Upload blood panels over time, visualize trends,
  and correlate improvements or regressions with genome-informed lifestyle
  changes.
- **Actionable Tweaks**: Provide small, evidence-backed lifestyle suggestions
  (dietary changes, exercise tips, supplement recommendations) grounded in
  the user's specific genetic profile.

### Non-Goals (v1)

- Clinical-grade diagnostic reporting (this is informational only).
- Direct integration with electronic health record (EHR) systems.
- Real-time genetic sequencing or raw-read processing.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT TIER                                │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   React SPA (Vite)                            │  │
│  │                                                               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────────┐  │  │
│  │  │  Auth    │ │ Upload   │ │ Dashboard │ │   Reports     │  │  │
│  │  │  Pages   │ │ Wizard   │ │ (Charts)  │ │  (AI-gen)     │  │  │
│  │  └──────────┘ └──────────┘ └───────────┘ └───────────────┘  │  │
│  │                                                               │  │
│  │  UI Libraries: Recharts, React-Dropzone, React-Router        │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │ HTTPS (TLS 1.3)                      │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        API / APPLICATION TIER                        │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                 Nginx Reverse Proxy                            │  │
│  │          (TLS termination, rate limiting, CORS)                │  │
│  └──────────────────────┬─────────────────────────────────────────┘  │
│                         │                                            │
│  ┌──────────────────────▼─────────────────────────────────────────┐  │
│  │              Flask Application (Gunicorn)                      │  │
│  │                                                                │  │
│  │  ┌───────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │ Auth      │ │ Upload &     │ │ Analysis &               │  │  │
│  │  │ Module    │ │ Parse Module │ │ Reporting Module         │  │  │
│  │  │ (JWT +    │ │ (VCF, PDF,   │ │ (Variant lookup,        │  │  │
│  │  │  bcrypt)  │ │  CSV parse)  │ │  risk scoring,          │  │  │
│  │  └───────────┘ └──────────────┘ │  recommendations)       │  │  │
│  │                                  └──────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────────────┐  │  │
│  │  │            Shared Services                               │  │  │
│  │  │  - File encryption (AES-256-GCM)                         │  │  │
│  │  │  - Input validation & sanitization                       │  │  │
│  │  │  - Rate limiter (Flask-Limiter)                          │  │  │
│  │  │  - Logging / audit trail                                 │  │  │
│  │  └──────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                         │                                            │
│  ┌──────────────────────▼─────────────────────────────────────────┐  │
│  │              Celery Worker Pool (Redis broker)                 │  │
│  │                                                                │  │
│  │  ┌────────────────┐ ┌────────────────┐ ┌───────────────────┐  │  │
│  │  │ genome_analyze │ │ blood_parse    │ │ report_generate   │  │  │
│  │  │ (VCF parse,    │ │ (PDF/CSV       │ │ (AI NLG,         │  │  │
│  │  │  API queries)  │ │  extraction)   │ │  compile report)  │  │  │
│  │  └────────────────┘ └────────────────┘ └───────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          DATA TIER                                    │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │
│  │   SQLite     │  │   Redis      │  │  Encrypted File Store     │ │
│  │  (Primary    │  │  (Celery     │  │  (Local disk or S3-       │ │
│  │   database)  │  │   broker +   │  │   compatible, AES-256     │ │
│  │              │  │   cache)     │  │   at rest)                │ │
│  └──────────────┘  └──────────────┘  └────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                                 │
│                                                                      │
│  ┌────────────┐ ┌────────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │  Ensembl   │ │  ClinVar   │ │  GWAS    │ │  NCBI (dbSNP,    │ │
│  │  REST API  │ │  E-Utils   │ │  Catalog │ │  PubMed, Gene)   │ │
│  └────────────┘ └────────────┘ └──────────┘ └────────────────────┘ │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────────────────────────────┐ │
│  │  OpenAI API      │  │  PharmGKB (pharmacogenomics, optional)  │ │
│  │  (GPT for NLG)   │  │                                         │ │
│  └──────────────────┘  └──────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Technology | Role |
|-----------|-----------|------|
| **Frontend SPA** | React 18+, Vite, Recharts | User interface, file uploads, dashboard visualizations |
| **Reverse Proxy** | Nginx | TLS termination, rate limiting, static asset serving |
| **API Server** | Flask + Gunicorn | REST API, authentication, request validation, orchestration |
| **Task Queue** | Celery + Redis | Async genome analysis, blood test parsing, report generation |
| **Database** | SQLite (WAL mode) | User data, analysis results, blood test history |
| **Cache/Broker** | Redis | Celery message broker, API response caching, session store |
| **File Store** | Encrypted disk (or S3) | Raw uploads (VCF, PDF, CSV) encrypted at rest |
| **External APIs** | Ensembl, ClinVar, NCBI, GWAS | Variant annotation, disease associations, research data |
| **AI Engine** | OpenAI API (or self-hosted) | Natural language report generation |

### Request Flow Example: Genome Upload & Analysis

```
User uploads VCF file
        │
        ▼
[React] ──POST /api/v1/genome/upload──▶ [Flask API]
                                            │
                                   1. Validate file (size, type, format header)
                                   2. Encrypt file → write to file store
                                   3. Create GenomeUpload record (status: uploaded)
                                   4. Dispatch Celery task: genome_analyze
                                            │
                                            ▼
                                    [Celery Worker]
                                            │
                                   1. Decrypt & parse VCF (cyvcf2 / PyVCF3)
                                   2. Extract variants (rsIDs, CHROM, POS, REF, ALT)
                                   3. Batch query Ensembl VEP for consequences
                                   4. Query ClinVar for clinical significance
                                   5. Query GWAS Catalog for trait associations
                                   6. Score risk categories (cardiovascular,
                                      metabolic, neurological, pharmacogenomic)
                                   7. Generate lifestyle recommendations
                                   8. Call AI engine for natural language report
                                   9. Store results → GenomeAnalysis record
                                  10. Update status: complete
                                            │
                                            ▼
[React] ◀──GET /api/v1/genome/analysis/{id}── [Flask API]
        (polls or receives WebSocket notification)
```

---

## 3. Data Models

### Entity Relationship Diagram

```
┌──────────────┐       ┌───────────────────┐       ┌──────────────────┐
│     User     │       │   GenomeUpload    │       │ GenomeAnalysis   │
├──────────────┤       ├───────────────────┤       ├──────────────────┤
│ id (PK)      │──1:N─▶│ id (PK)           │──1:1─▶│ id (PK)          │
│ email        │       │ user_id (FK)      │       │ upload_id (FK)   │
│ password_hash│       │ filename_orig     │       │ status           │
│ created_at   │       │ file_path_enc     │       │ variant_count    │
│ updated_at   │       │ file_hash_sha256  │       │ risk_summary_json│
│ tos_accepted │       │ source_service    │       │ recommendations  │
│ data_enc_key │       │ status            │       │ ai_report_text   │
│ (encrypted)  │       │ uploaded_at       │       │ started_at       │
└──────────────┘       │ file_size_bytes   │       │ completed_at     │
       │               └───────────────────┘       │ error_message    │
       │                                           └──────────────────┘
       │
       │               ┌───────────────────┐       ┌──────────────────┐
       │               │   BloodUpload     │       │  BloodResult     │
       └──────1:N─────▶├───────────────────┤       ├──────────────────┤
                       │ id (PK)           │──1:N─▶│ id (PK)          │
                       │ user_id (FK)      │       │ upload_id (FK)   │
                       │ filename_orig     │       │ marker_name      │
                       │ file_path_enc     │       │ value            │
                       │ file_type         │       │ unit             │
                       │ test_date         │       │ reference_low    │
                       │ lab_name          │       │ reference_high   │
                       │ uploaded_at       │       │ flag (H/L/N)     │
                       │ status            │       └──────────────────┘
                       └───────────────────┘

       ┌───────────────────┐       ┌──────────────────────────┐
       │   Variant         │       │  VariantAnnotation       │
       ├───────────────────┤       ├──────────────────────────┤
       │ id (PK)           │──1:N─▶│ id (PK)                  │
       │ analysis_id (FK)  │       │ variant_id (FK)          │
       │ rsid              │       │ source (ensembl/clinvar/ │
       │ chromosome        │       │         gwas/ncbi)       │
       │ position          │       │ gene_symbol              │
       │ ref_allele        │       │ consequence              │
       │ alt_allele        │       │ clinical_significance    │
       │ genotype          │       │ trait_association         │
       │ quality           │       │ risk_allele              │
       └───────────────────┘       │ odds_ratio               │
                                   │ p_value                  │
                                   │ pubmed_ids               │
                                   │ retrieved_at             │
                                   └──────────────────────────┘

       ┌──────────────────────────┐
       │  HealthRecommendation    │
       ├──────────────────────────┤
       │ id (PK)                  │
       │ analysis_id (FK)         │
       │ category (diet/exercise/ │
       │   supplement/lifestyle)  │
       │ title                    │
       │ body                     │
       │ evidence_rsids           │
       │ evidence_sources         │
       │ confidence (low/med/hi)  │
       │ priority (1-10)          │
       └──────────────────────────┘

       ┌──────────────────────────┐
       │  AuditLog                │
       ├──────────────────────────┤
       │ id (PK)                  │
       │ user_id (FK, nullable)   │
       │ action                   │
       │ resource_type            │
       │ resource_id              │
       │ ip_address               │
       │ timestamp                │
       └──────────────────────────┘
```

### Model Details

#### User
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | Avoid sequential IDs for security |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Validated format |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt, cost factor 12 |
| created_at | DATETIME | NOT NULL | UTC |
| updated_at | DATETIME | NOT NULL | UTC |
| tos_accepted_at | DATETIME | NOT NULL | Terms of service acceptance timestamp |
| data_encryption_key_enc | BLOB | NOT NULL | Per-user AES key, encrypted with master key |

#### GenomeUpload
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → User | |
| filename_original | VARCHAR(255) | NOT NULL | User-facing name |
| file_path_encrypted | VARCHAR(512) | NOT NULL | Path to AES-encrypted file on disk |
| file_hash_sha256 | CHAR(64) | NOT NULL | Integrity verification |
| source_service | VARCHAR(50) | | e.g., "23andme", "ancestry", "nebula", "unknown" |
| genome_build | VARCHAR(10) | | e.g., "GRCh37", "GRCh38" |
| status | VARCHAR(20) | NOT NULL | uploaded / parsing / analyzing / complete / error |
| uploaded_at | DATETIME | NOT NULL | UTC |
| file_size_bytes | INTEGER | NOT NULL | For quota enforcement |

#### GenomeAnalysis
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| upload_id | UUID | FK → GenomeUpload, UNIQUE | One analysis per upload |
| status | VARCHAR(20) | NOT NULL | queued / running / complete / error |
| variant_count | INTEGER | | Total variants parsed |
| annotated_variant_count | INTEGER | | Variants with at least one annotation |
| risk_summary_json | TEXT | | JSON blob: category → score mapping |
| ai_report_text | TEXT | | Full natural language report |
| ai_report_generated_at | DATETIME | | When AI report was produced |
| started_at | DATETIME | | Task start |
| completed_at | DATETIME | | Task end |
| error_message | TEXT | | Populated on failure |

#### Variant
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| analysis_id | UUID | FK → GenomeAnalysis | |
| rsid | VARCHAR(20) | | e.g., "rs1801133" (may be null for novel variants) |
| chromosome | VARCHAR(5) | NOT NULL | e.g., "chr1", "chrX" |
| position | INTEGER | NOT NULL | Genomic coordinate |
| ref_allele | VARCHAR(500) | NOT NULL | Reference allele |
| alt_allele | VARCHAR(500) | NOT NULL | Alternate allele |
| genotype | VARCHAR(10) | NOT NULL | e.g., "0/1", "1/1" |
| quality | FLOAT | | VCF QUAL field |

*Index*: (analysis_id, rsid), (analysis_id, chromosome, position)

#### VariantAnnotation
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| variant_id | UUID | FK → Variant | |
| source | VARCHAR(20) | NOT NULL | ensembl / clinvar / gwas_catalog / ncbi / pharmgkb |
| gene_symbol | VARCHAR(50) | | e.g., "MTHFR", "CYP1A2" |
| consequence | VARCHAR(100) | | e.g., "missense_variant" |
| clinical_significance | VARCHAR(100) | | e.g., "Pathogenic", "Benign", "Risk factor" |
| condition_name | VARCHAR(500) | | Associated disease/trait name |
| trait_association | TEXT | | Free-text description |
| risk_allele | VARCHAR(20) | | Which allele carries risk |
| odds_ratio | FLOAT | | From GWAS if available |
| p_value | FLOAT | | Statistical significance |
| pubmed_ids | TEXT | | Comma-separated PubMed IDs |
| source_record_id | VARCHAR(100) | | External DB accession |
| retrieved_at | DATETIME | NOT NULL | When annotation was fetched |

#### BloodUpload
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → User | |
| filename_original | VARCHAR(255) | NOT NULL | |
| file_path_encrypted | VARCHAR(512) | NOT NULL | |
| file_type | VARCHAR(10) | NOT NULL | pdf / csv |
| test_date | DATE | NOT NULL | When the blood test was taken |
| lab_name | VARCHAR(255) | | Optional |
| status | VARCHAR(20) | NOT NULL | uploaded / parsing / complete / error |
| uploaded_at | DATETIME | NOT NULL | UTC |

#### BloodResult
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| upload_id | UUID | FK → BloodUpload | |
| marker_name | VARCHAR(100) | NOT NULL | Normalized name, e.g., "total_cholesterol" |
| marker_display_name | VARCHAR(100) | NOT NULL | e.g., "Total Cholesterol" |
| value | FLOAT | NOT NULL | Numeric value |
| unit | VARCHAR(30) | NOT NULL | e.g., "mg/dL", "mmol/L" |
| reference_low | FLOAT | | Normal range lower bound |
| reference_high | FLOAT | | Normal range upper bound |
| flag | VARCHAR(5) | | "H" (high), "L" (low), "N" (normal) |

*Index*: (upload_id), composite index on (user_id via upload, marker_name, test_date) for trend queries

#### HealthRecommendation
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| analysis_id | UUID | FK → GenomeAnalysis | |
| category | VARCHAR(20) | NOT NULL | diet / exercise / supplement / lifestyle / pharmacogenomic |
| title | VARCHAR(200) | NOT NULL | Short recommendation title |
| body | TEXT | NOT NULL | Detailed explanation |
| evidence_rsids | TEXT | | Comma-separated rsIDs supporting this |
| evidence_sources | TEXT | | JSON array of {source, id, url} |
| confidence | VARCHAR(10) | NOT NULL | low / medium / high |
| priority | INTEGER | NOT NULL | 1 (highest) to 10 (lowest) |

#### AuditLog
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → User, nullable | Null for unauthenticated actions |
| action | VARCHAR(50) | NOT NULL | e.g., "login", "upload_genome", "view_report" |
| resource_type | VARCHAR(50) | | e.g., "GenomeUpload", "BloodUpload" |
| resource_id | UUID | | |
| ip_address | VARCHAR(45) | | IPv4/IPv6 |
| timestamp | DATETIME | NOT NULL | UTC |

---

## 4. API Endpoints

### Base URL: `/api/v1`

All endpoints return JSON. Authenticated endpoints require `Authorization: Bearer <jwt>`.

### 4.1 Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Create account |
| POST | `/auth/login` | No | Get JWT token pair |
| POST | `/auth/refresh` | Yes (refresh token) | Refresh access token |
| POST | `/auth/logout` | Yes | Invalidate refresh token |
| DELETE | `/auth/account` | Yes | Delete account and all data (GDPR) |

**POST /auth/register**
```
Request:
{
  "email": "user@example.com",
  "password": "...",           // min 12 chars, complexity rules
  "tos_accepted": true
}

Response (201):
{
  "user_id": "uuid",
  "email": "user@example.com",
  "created_at": "2026-02-27T..."
}
```

**POST /auth/login**
```
Request:
{
  "email": "user@example.com",
  "password": "..."
}

Response (200):
{
  "access_token": "jwt...",     // 15-minute expiry
  "refresh_token": "jwt...",    // 7-day expiry, httponly cookie
  "token_type": "Bearer"
}
```

### 4.2 Genome Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/genome/upload` | Yes | Upload VCF file |
| GET | `/genome/uploads` | Yes | List user's genome uploads |
| GET | `/genome/uploads/{id}` | Yes | Get upload status/metadata |
| DELETE | `/genome/uploads/{id}` | Yes | Delete upload and associated data |
| POST | `/genome/uploads/{id}/analyze` | Yes | Trigger analysis (if not auto) |
| GET | `/genome/analysis/{id}` | Yes | Get analysis results |
| GET | `/genome/analysis/{id}/variants` | Yes | Paginated variant list |
| GET | `/genome/analysis/{id}/risks` | Yes | Risk category summary |
| GET | `/genome/analysis/{id}/recommendations` | Yes | Lifestyle recommendations |
| GET | `/genome/analysis/{id}/report` | Yes | Full AI-generated report |

**POST /genome/upload**
```
Request: multipart/form-data
  - file: VCF file (max 500 MB)
  - source_service: "23andme" | "ancestry" | "nebula" | "other" (optional)

Response (202):
{
  "upload_id": "uuid",
  "status": "uploaded",
  "message": "File received. Analysis will begin shortly.",
  "analysis_task_id": "celery-task-uuid"
}
```

**GET /genome/analysis/{id}/risks**
```
Response (200):
{
  "analysis_id": "uuid",
  "risk_categories": [
    {
      "category": "cardiovascular",
      "overall_risk": "elevated",         // low / average / elevated / high
      "score": 6.8,                       // 1-10 scale
      "key_variants": [
        {
          "rsid": "rs10757274",
          "gene": "9p21.3",
          "genotype": "G/G",
          "contribution": "Associated with increased coronary artery disease risk",
          "odds_ratio": 1.28,
          "source": "gwas_catalog"
        }
      ],
      "summary": "Your genetic profile shows elevated cardiovascular risk..."
    },
    {
      "category": "pharmacogenomic",
      "findings": [
        {
          "rsid": "rs762551",
          "gene": "CYP1A2",
          "genotype": "A/C",
          "metabolizer_status": "slow",
          "implication": "Slow caffeine metabolism — consider limiting intake",
          "source": "pharmgkb"
        }
      ]
    }
  ]
}
```

**GET /genome/analysis/{id}/recommendations**
```
Response (200):
{
  "recommendations": [
    {
      "id": "uuid",
      "category": "diet",
      "title": "Reduce caffeine intake",
      "body": "Your CYP1A2 variant (rs762551 A/C) indicates slow caffeine metabolism...",
      "confidence": "high",
      "priority": 2,
      "evidence": [
        {"rsid": "rs762551", "source": "pharmgkb", "pubmed": "17522597"}
      ]
    },
    {
      "id": "uuid",
      "category": "supplement",
      "title": "Consider omega-3 supplementation",
      "body": "Variants in FADS1/FADS2 suggest reduced ability to convert ALA to EPA/DHA...",
      "confidence": "medium",
      "priority": 4,
      "evidence": [
        {"rsid": "rs174546", "source": "gwas_catalog", "pubmed": "21829377"}
      ]
    }
  ]
}
```

### 4.3 Blood Test Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/blood/upload` | Yes | Upload blood test file (PDF/CSV) |
| GET | `/blood/uploads` | Yes | List user's blood uploads |
| GET | `/blood/uploads/{id}` | Yes | Get upload details and parsed results |
| DELETE | `/blood/uploads/{id}` | Yes | Delete upload and results |
| PUT | `/blood/uploads/{id}/results` | Yes | Manually correct parsed values |
| GET | `/blood/trends` | Yes | Get time-series data for markers |
| GET | `/blood/correlations` | Yes | Genome-blood correlations |

**POST /blood/upload**
```
Request: multipart/form-data
  - file: PDF or CSV (max 20 MB)
  - test_date: "2026-02-15" (ISO 8601)
  - lab_name: "Quest Diagnostics" (optional)

Response (202):
{
  "upload_id": "uuid",
  "status": "uploaded",
  "message": "File received. Parsing will begin shortly.",
  "parse_task_id": "celery-task-uuid"
}
```

**GET /blood/trends**
```
Query params:
  - markers: "total_cholesterol,ldl,hdl,triglycerides" (comma-separated)
  - from_date: "2025-01-01" (optional)
  - to_date: "2026-02-27" (optional)

Response (200):
{
  "trends": {
    "total_cholesterol": {
      "display_name": "Total Cholesterol",
      "unit": "mg/dL",
      "data_points": [
        {"date": "2025-03-10", "value": 220, "flag": "H"},
        {"date": "2025-09-15", "value": 198, "flag": "N"},
        {"date": "2026-02-15", "value": 185, "flag": "N"}
      ],
      "reference_range": {"low": 125, "high": 200},
      "trend_direction": "improving"
    }
  }
}
```

**GET /blood/correlations**
```
Response (200):
{
  "correlations": [
    {
      "blood_marker": "ldl_cholesterol",
      "genome_variants": ["rs429358 (APOE ε4)"],
      "observation": "Your APOE ε4 carrier status may contribute to elevated LDL...",
      "recommendation": "A Mediterranean-style diet may be particularly beneficial...",
      "blood_trend": "improving"
    }
  ]
}
```

### 4.4 Dashboard / Insights

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/dashboard/summary` | Yes | Aggregated overview for dashboard |
| GET | `/dashboard/timeline` | Yes | Combined genome + blood timeline |

### 4.5 Task Status

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/tasks/{task_id}/status` | Yes | Poll Celery task status |

```
Response (200):
{
  "task_id": "celery-uuid",
  "status": "running",          // queued / running / complete / error
  "progress": 45,               // percentage (0-100)
  "current_step": "Querying ClinVar for variant annotations...",
  "result_url": null             // populated on completion
}
```

---

## 5. Security Considerations

### 5.1 Data Classification

| Data Type | Classification | Handling |
|-----------|---------------|----------|
| Genome data (VCF) | **Highly Sensitive PII** | Encrypted at rest (AES-256-GCM), per-user keys |
| Blood test results | **Sensitive Health Data** | Encrypted at rest, access-controlled |
| Analysis results | **Sensitive** | Encrypted at rest, tied to user |
| User credentials | **Secret** | bcrypt-hashed, never stored in plaintext |
| AI-generated reports | **Sensitive** | Stored encrypted, user-owned |

### 5.2 Encryption Architecture

```
┌─────────────────────────────────────────────┐
│              Master Key (MK)                │
│  Stored in environment variable or          │
│  hardware security module (HSM) / KMS       │
│  NEVER in database or code                  │
├─────────────────────────────────────────────┤
│                    │                        │
│         encrypts   ▼                        │
│  ┌──────────────────────────────────┐       │
│  │  Per-User Data Encryption Key   │       │
│  │  (DEK) — stored encrypted in    │       │
│  │  User.data_encryption_key_enc   │       │
│  └──────────────────────────────────┘       │
│                    │                        │
│         encrypts   ▼                        │
│  ┌──────────────────────────────────┐       │
│  │  User's files on disk           │       │
│  │  (VCF, PDF, CSV)               │       │
│  └──────────────────────────────────┘       │
└─────────────────────────────────────────────┘
```

- **Envelope encryption**: Master key encrypts per-user DEKs; DEKs encrypt
  user files. Rotating the master key requires only re-encrypting DEKs, not
  all files.
- **AES-256-GCM** for file encryption (authenticated encryption).
- **bcrypt** (cost factor 12+) for password hashing.
- **JWT tokens** signed with RS256 (asymmetric) — access tokens expire in
  15 minutes, refresh tokens in 7 days.

### 5.3 Transport Security

- All traffic over **TLS 1.3** (minimum TLS 1.2).
- **HSTS** headers with `max-age=31536000; includeSubDomains`.
- Certificate pinning recommended for mobile clients (future).

### 5.4 Application Security

| Threat | Mitigation |
|--------|-----------|
| **SQL Injection** | SQLAlchemy ORM with parameterized queries; no raw SQL |
| **XSS** | React's built-in escaping; Content-Security-Policy headers |
| **CSRF** | SameSite cookies; CSRF tokens for state-changing requests |
| **File Upload Attacks** | Validate file headers (magic bytes), not just extensions; size limits; scan with ClamAV; store outside web root |
| **Path Traversal** | Generate UUIDs for stored filenames; never use user-supplied paths |
| **Broken Authentication** | Rate limit login (5 attempts/minute); account lockout after 10 failures; JWT rotation |
| **Data Exposure** | Encrypt at rest; minimize data in API responses; no genome data in logs |
| **Insecure Deserialization** | Validate all JSON input with marshmallow/pydantic schemas |
| **IDOR** | All resource access checks user ownership at the query level |
| **Dependency Vulnerabilities** | Automated dependency scanning (Dependabot/Snyk); pin versions |

### 5.5 File Upload Security

1. **Size limits**: VCF ≤ 500 MB, PDF/CSV ≤ 20 MB.
2. **Type validation**: Check magic bytes (`##fileformat=VCF` for VCF;
   `%PDF` for PDF; UTF-8 text for CSV).
3. **Virus scanning**: Pipe uploads through ClamAV before processing.
4. **Storage**: Write to a non-web-accessible directory with randomized UUID
   filenames. Encrypt immediately.
5. **Streaming**: Use chunked uploads for large VCF files to avoid memory
   exhaustion.

### 5.6 Privacy and GDPR Compliance

- **Right to deletion**: `DELETE /auth/account` purges all user data,
  uploaded files, analysis results, and audit logs (anonymized).
- **Data portability**: `GET /api/v1/export` returns all user data as a
  downloadable archive (future endpoint).
- **Consent tracking**: `tos_accepted_at` timestamp on user record.
- **Data minimization**: Only store variants with known annotations; discard
  raw VCF after parsing if user opts in.
- **Audit logging**: All data access events logged for compliance review.

---

## 6. Genome Database Integration Plan

### 6.1 Integration Overview

```
                    ┌──────────────────┐
                    │   Variant Pool   │
                    │  (from VCF)      │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌───────────┐
     │  Ensembl   │  │  ClinVar   │  │   GWAS    │
     │  VEP API   │  │  E-Utils   │  │  Catalog  │
     └─────┬──────┘  └─────┬──────┘  └─────┬─────┘
           │               │               │
           ▼               ▼               ▼
     Functional       Clinical          Trait
     consequences     significance      associations
     (missense,       (pathogenic,      (odds ratios,
      synonymous,      benign, VUS)      p-values)
      regulatory)
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   Annotation     │
                    │   Aggregator     │
                    │   Service        │
                    └────────┬─────────┘
                             │
                    ┌────────┴─────────┐
                    │                  │
                    ▼                  ▼
            ┌────────────┐    ┌──────────────┐
            │  NCBI      │    │  PharmGKB    │
            │  (dbSNP,   │    │  (drug-gene  │
            │   PubMed,  │    │   inter-     │
            │   Gene)    │    │   actions)   │
            └────────────┘    └──────────────┘
```

### 6.2 External API Details

#### Ensembl Variant Effect Predictor (VEP)

- **Endpoint**: `https://rest.ensembl.org/vep/human/region`
- **Method**: POST (batch of up to 200 variants per request)
- **Rate Limit**: 15 requests/second (55,000/hour) without API key;
  higher with registered email.
- **Data Retrieved**: Gene symbol, consequence type (missense, synonymous,
  etc.), SIFT/PolyPhen predictions, regulatory annotations.
- **Integration Strategy**:
  - Batch variants in groups of 200.
  - Use exponential backoff on 429 responses.
  - Cache responses in Redis (TTL: 30 days) keyed by `variant:{build}:{chrom}:{pos}:{ref}:{alt}`.
  - Fall back to local VEP cache file (downloadable from Ensembl) for
    offline/high-volume processing.

#### ClinVar (via NCBI E-Utilities)

- **Endpoint**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
  - `esearch.fcgi?db=clinvar&term={rsid}`
  - `esummary.fcgi?db=clinvar&id={uid}`
- **Rate Limit**: 3 requests/second without API key; 10/second with
  registered NCBI API key (free).
- **Data Retrieved**: Clinical significance (pathogenic, likely pathogenic,
  benign, VUS), associated conditions, review status (star rating),
  submitter information.
- **Integration Strategy**:
  - Query by rsID or (chrom, pos, ref, alt).
  - Parse XML responses (ClinVar returns XML by default; use
    `requests` + `xml.etree`).
  - Store clinical significance and condition associations.
  - Cache aggressively (ClinVar updates monthly).

#### GWAS Catalog

- **Endpoint**: `https://www.ebi.ac.uk/gwas/rest/api/singleNucleotidePolymorphisms/{rsid}/associations`
- **Rate Limit**: Generous; no strict published limit but respect
  reasonable usage.
- **Data Retrieved**: Trait associations, odds ratios, p-values, study
  accessions, PubMed references.
- **Integration Strategy**:
  - Query per rsID.
  - Filter associations by p-value threshold (≤ 5×10⁻⁸ for
    genome-wide significance).
  - Map EFO trait ontology terms to human-readable category labels.

#### NCBI dbSNP / Gene / PubMed

- **Endpoint**: E-Utilities (`esearch`, `esummary`, `efetch`)
- **Use Case**: Supplement missing data — gene function summaries, variant
  population frequencies (from dbSNP), literature references (PubMed).
- **Integration Strategy**: Secondary lookups for variants flagged as
  clinically significant by ClinVar or GWAS Catalog.

#### PharmGKB (Optional / Future)

- **Endpoint**: `https://api.pharmgkb.org/v1/data/variant/{rsid}`
- **Rate Limit**: Requires API key (free for non-commercial).
- **Data Retrieved**: Drug-gene interactions, dosing guidelines,
  metabolizer phenotype predictions.
- **Integration Strategy**: Query for variants in known pharmacogenes
  (CYP2D6, CYP2C19, CYP1A2, VKORC1, etc.).

### 6.3 Annotation Pipeline Architecture

```
Step 1: VCF Parse
  └─ Extract variants → (chrom, pos, ref, alt, genotype, rsid)
  └─ Normalize alleles (left-align, trim)
  └─ Detect genome build (GRCh37 vs GRCh38) from VCF header
  └─ Liftover if needed (use pyliftover for coordinate conversion)

Step 2: Batch Annotation
  └─ Check Redis cache for each variant
  └─ Split uncached variants into batches
  └─ Fan out parallel requests:
       ├─ Ensembl VEP (batches of 200)
       ├─ ClinVar (batches of 50 rsIDs)
       └─ GWAS Catalog (individual rsID lookups, parallelized)
  └─ Write results to cache and database

Step 3: Risk Scoring
  └─ Aggregate variant annotations by category:
       ├─ Cardiovascular (APOE, 9p21, LPA, PCSK9, etc.)
       ├─ Metabolic (FTO, TCF7L2, PPARG, etc.)
       ├─ Neurological (APOE ε4, BDNF, COMT, etc.)
       ├─ Pharmacogenomic (CYP family, VKORC1, DPYD, etc.)
       ├─ Nutritional (MTHFR, FADS1/2, LCT, FUT2, etc.)
       └─ Inflammatory (TNF, IL6, CRP-related, etc.)
  └─ Calculate weighted risk scores per category
       (weights based on odds ratios, clinical significance,
        evidence level)

Step 4: Recommendation Generation
  └─ Map risk profiles to recommendation templates
  └─ Pharmacogenomic: direct gene → drug/substance mappings
  └─ Nutritional: gene → nutrient metabolism mappings
  └─ Rank by confidence and priority

Step 5: AI Report Generation
  └─ Compile structured data into prompt
  └─ Call OpenAI API (or self-hosted model) for natural language report
  └─ Include disclaimers and citations
  └─ Store report text in GenomeAnalysis record
```

### 6.4 Caching Strategy

| Data Source | Cache Key Pattern | TTL | Rationale |
|-------------|-------------------|-----|-----------|
| Ensembl VEP | `vep:{build}:{chrom}:{pos}:{ref}:{alt}` | 30 days | Annotations stable between Ensembl releases |
| ClinVar | `clinvar:{rsid}` | 14 days | Monthly updates |
| GWAS Catalog | `gwas:{rsid}` | 14 days | Periodic new studies |
| NCBI dbSNP | `dbsnp:{rsid}` | 30 days | Stable data |
| PharmGKB | `pharmgkb:{rsid}` | 30 days | Infrequent changes |

### 6.5 Rate Limiting and Resilience

- **Circuit breaker**: If an external API returns 5 consecutive errors,
  stop querying for 60 seconds and log an alert.
- **Retry with backoff**: 3 retries with exponential backoff (1s, 2s, 4s)
  on 429/5xx responses.
- **Graceful degradation**: If one API is unavailable, proceed with
  remaining sources and mark affected annotations as "incomplete".
- **Fallback**: Maintain a local SQLite mirror of commonly queried rsIDs
  (~50,000 most impactful variants) for offline analysis.

---

## 7. Blood Test Processing Pipeline

### 7.1 Supported Input Formats

| Format | Parser | Strategy |
|--------|--------|----------|
| **CSV** | pandas | Column header matching against known marker aliases |
| **PDF (structured)** | PyPDF2 + regex | Extract text, pattern-match lab result tables |
| **PDF (scanned)** | Tesseract OCR (optional, v2) | OCR then pattern-match |

### 7.2 Marker Normalization

Blood tests use varying names across labs. A normalization table maps
aliases to canonical names:

```
"Total Cholesterol"   → total_cholesterol
"CHOL"                → total_cholesterol
"Cholesterol, Total"  → total_cholesterol
"LDL-C"              → ldl_cholesterol
"LDL Cholesterol"    → ldl_cholesterol
"Low Density Lipo"   → ldl_cholesterol
"HbA1c"              → hemoglobin_a1c
"Hemoglobin A1C"     → hemoglobin_a1c
"A1C"                → hemoglobin_a1c
...
```

Store this as a configurable JSON/YAML mapping file, extensible by admins.

### 7.3 Parsing Pipeline

```
Upload received
      │
      ▼
  Detect file type (magic bytes)
      │
      ├─ CSV ──▶ pandas.read_csv() ──▶ Column header matching
      │                                  │
      ├─ PDF ──▶ PyPDF2 text extraction ▶ Regex pattern matching
      │           │                       for lab result tables
      │           └─ If extraction poor ─▶ Flag for manual review
      │
      ▼
  Normalize marker names (alias → canonical)
      │
      ▼
  Validate values (type check, range check for obvious errors)
      │
      ▼
  Store BloodResult records
      │
      ▼
  Flag out-of-range values
      │
      ▼
  Return parsed results to user for confirmation/correction
```

### 7.4 Trend Analysis

- Query all BloodResult records for a user, grouped by `marker_name`,
  ordered by `test_date`.
- Calculate:
  - **Direction**: improving / worsening / stable (based on movement
    toward/away from reference range).
  - **Rate of change**: percentage change between consecutive tests.
  - **Projection**: Simple linear regression for future trajectory
    (display with heavy caveats).

### 7.5 Genome-Blood Correlation

Cross-reference blood markers with genome analysis results:

| Blood Marker | Relevant Genes | Correlation Logic |
|-------------|---------------|-------------------|
| LDL Cholesterol | APOE, PCSK9, LDLR | APOE ε4 carriers may show elevated LDL despite diet |
| HbA1c / Glucose | TCF7L2, SLC30A8 | Diabetes risk variants correlated with glucose trends |
| Vitamin D | GC (DBP), CYP2R1 | Variants affecting vitamin D metabolism |
| Folate | MTHFR | C677T variant reduces folate metabolism |
| CRP / Inflammation | IL6, TNF, CRP | Inflammation-related variants vs. CRP levels |
| Iron / Ferritin | HFE | Hemochromatosis variants vs. iron levels |

---

## 8. AI-Driven Insights Engine

### 8.1 Report Generation Architecture

```
┌─────────────────────────────────┐
│    Structured Analysis Data     │
│  (risks, variants, blood data)  │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Prompt Builder             │
│                                 │
│  - System prompt with medical   │
│    writing guidelines           │
│  - User's risk profile (JSON)   │
│  - Key variant summaries        │
│  - Blood test trends (if any)   │
│  - Recommendation templates     │
│  - Disclaimer requirements      │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      OpenAI API (GPT-4o)        │
│  or self-hosted LLM             │
│                                 │
│  Temperature: 0.3 (factual)     │
│  Max tokens: 4000               │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Post-Processing            │
│                                 │
│  - Validate no hallucinated     │
│    rsIDs or gene names          │
│  - Ensure disclaimers present   │
│  - Format into sections         │
│  - Add citation links           │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│      Final Report               │
│                                 │
│  Sections:                      │
│  1. Executive Summary           │
│  2. Genetic Risk Overview       │
│  3. Detailed Findings           │
│  4. Lifestyle Recommendations   │
│  5. Blood Test Correlations     │
│  6. Suggested Tweaks            │
│  7. Disclaimers & References    │
└─────────────────────────────────┘
```

### 8.2 Prompt Engineering Guidelines

- **System prompt** establishes the model as a genetics-literate health
  communicator that ALWAYS includes disclaimers.
- **Grounding**: Every claim must reference a specific rsID and source
  database. The prompt includes structured data — the model summarizes,
  it does not invent associations.
- **Temperature 0.3**: Favors factual, deterministic output.
- **Post-processing validation**: Cross-check that every rsID mentioned in
  the report exists in the user's actual variant data.

### 8.3 Disclaimer Injection

Every report MUST include (enforced at the application level, not reliant
on the AI model):

```
⚠️ IMPORTANT DISCLAIMER
This report is for informational and educational purposes only. It is NOT
medical advice and should NOT be used to diagnose, treat, or prevent any
disease. Genetic associations represent statistical probabilities, not
certainties. Always consult a qualified healthcare provider before making
health decisions based on genetic information.
```

---

## 9. Deployment Architecture

### 9.1 Docker Compose Topology

```
┌────────────────────────────────────────────────────────┐
│                 docker-compose.yml                      │
│                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  nginx   │  │  flask   │  │  worker  │            │
│  │  :80/443 │─▶│  :5000   │  │ (celery) │            │
│  └──────────┘  └──────────┘  └──────────┘            │
│                      │              │                  │
│                      ▼              ▼                  │
│               ┌──────────┐  ┌──────────┐              │
│               │  redis   │  │  flower  │              │
│               │  :6379   │  │  :5555   │              │
│               └──────────┘  └──────────┘              │
│                                                        │
│  Volumes:                                              │
│    - sqlite_data:/data/db                              │
│    - encrypted_files:/data/files                       │
│    - redis_data:/data/redis                            │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 9.2 Container Specifications

| Service | Base Image | Resources | Notes |
|---------|-----------|-----------|-------|
| nginx | nginx:alpine | 256MB RAM | Static assets, TLS, proxy |
| flask | python:3.12-slim | 512MB RAM | Gunicorn with 4 workers |
| worker | python:3.12-slim | 1GB RAM | Celery with 2 concurrent workers |
| redis | redis:7-alpine | 256MB RAM | Persistence: RDB + AOF |
| flower | mher/flower | 128MB RAM | Celery monitoring (admin only) |

### 9.3 Environment Variables

```
# Flask
FLASK_SECRET_KEY=<random-256-bit>
MASTER_ENCRYPTION_KEY=<random-256-bit>        # For envelope encryption
JWT_PRIVATE_KEY_PATH=/secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/secrets/jwt_public.pem
DATABASE_URL=sqlite:///data/db/genomeinsight.db

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# External APIs
NCBI_API_KEY=<ncbi-api-key>
OPENAI_API_KEY=<openai-api-key>

# File Storage
UPLOAD_DIR=/data/files
MAX_VCF_SIZE_MB=500
MAX_BLOOD_FILE_SIZE_MB=20
```

---

## 10. Ethical and Legal Considerations

### 10.1 Medical Disclaimer Policy

- Disclaimers displayed on **every** page containing health information.
- Forced acknowledgment during onboarding before first upload.
- Reports always include a non-removable disclaimer section.
- Language reviewed by legal counsel before launch.

### 10.2 Genetic Non-Discrimination

- Inform users about GINA (Genetic Information Nondiscrimination Act) in
  the US and equivalent laws in other jurisdictions.
- Advise users about potential implications of genetic data sharing.

### 10.3 Data Sovereignty

- Allow users to choose data residency region (future, multi-region
  deployment).
- All processing happens server-side; no genome data sent to third parties
  except anonymized variant IDs to public databases (rsIDs only, no
  identifying information).

### 10.4 Transparency

- Show users exactly which databases were queried for each finding.
- Link to original research papers (PubMed).
- Show confidence levels for all recommendations.
- Display last-updated dates for all external data sources.

### 10.5 Informed Consent

Users must acknowledge before uploading:
1. This is not a medical diagnostic tool.
2. Their data will be encrypted and stored securely.
3. They can delete all their data at any time.
4. Variant IDs (not personal data) are sent to public research databases
   for annotation.
5. AI-generated reports may contain errors.

---

## Appendix A: Technology Stack Summary

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Frontend | React | 18+ | SPA UI |
| Frontend Build | Vite | 5+ | Dev server, bundling |
| Charts | Recharts | 2+ | Dashboard visualizations |
| File Upload UI | react-dropzone | 14+ | Drag-and-drop uploads |
| Backend | Flask | 3.0+ | REST API |
| WSGI Server | Gunicorn | 22+ | Production server |
| ORM | SQLAlchemy | 2.0+ | Database access |
| Migrations | Alembic | 1.13+ | Schema migrations |
| Validation | marshmallow | 3+ | Request/response schemas |
| Auth | PyJWT + bcrypt | | JWT tokens, password hashing |
| Task Queue | Celery | 5+ | Async processing |
| Message Broker | Redis | 7+ | Celery broker + cache |
| Database | SQLite | 3.40+ | Primary data store (WAL mode) |
| VCF Parsing | cyvcf2 | 0.31+ | Fast VCF parsing (C backend) |
| PDF Parsing | PyPDF2 | 3+ | Blood test PDF extraction |
| Data Processing | pandas | 2+ | CSV parsing, data manipulation |
| Encryption | cryptography | 42+ | AES-256-GCM file encryption |
| HTTP Client | httpx | 0.27+ | Async external API calls |
| Containerization | Docker + Compose | 25+ / 2+ | Deployment |
| Reverse Proxy | Nginx | 1.25+ | TLS, rate limiting |
| Monitoring | Flower | 2+ | Celery task monitoring |

## Appendix B: Known Variant Categories for Risk Scoring

| Category | Example Genes/Loci | Example rsIDs | Traits |
|----------|-------------------|---------------|--------|
| Cardiovascular | 9p21.3, APOE, LPA, PCSK9 | rs10757274, rs429358, rs4420638 | CAD, stroke risk |
| Type 2 Diabetes | TCF7L2, SLC30A8, FTO | rs7903146, rs13266634 | Diabetes susceptibility |
| Pharmacogenomics | CYP1A2, CYP2D6, CYP2C19, VKORC1 | rs762551, rs1065852, rs4244285 | Drug metabolism |
| Nutrition | MTHFR, FADS1/2, LCT, FUT2 | rs1801133, rs174546, rs4988235 | Nutrient metabolism |
| Inflammation | IL6, TNF, CRP-related | rs1800795, rs1800629 | Chronic inflammation |
| Neurological | APOE (ε4), BDNF, COMT | rs429358, rs6265, rs4680 | Cognitive traits |
| Obesity | FTO, MC4R | rs9939609, rs17782313 | BMI, appetite |
| Sleep | CLOCK, PER2, ADA | rs1801260, rs2304672, rs73598374 | Circadian rhythm |
| Caffeine | CYP1A2, ADORA2A | rs762551, rs5751876 | Caffeine sensitivity |
| Lactose | LCT (MCM6) | rs4988235 | Lactose tolerance |

## Appendix C: Project Directory Structure (Proposed)

```
genomeinsight/
├── docker-compose.yml
├── .env.example
├── nginx/
│   └── nginx.conf
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py           # Flask app factory
│   │   ├── config.py             # Configuration classes
│   │   ├── extensions.py         # SQLAlchemy, Celery, Redis init
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── genome.py         # GenomeUpload, GenomeAnalysis, Variant
│   │   │   ├── blood.py          # BloodUpload, BloodResult
│   │   │   ├── annotation.py     # VariantAnnotation
│   │   │   ├── recommendation.py # HealthRecommendation
│   │   │   └── audit.py          # AuditLog
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           # /auth/* endpoints
│   │   │   ├── genome.py         # /genome/* endpoints
│   │   │   ├── blood.py          # /blood/* endpoints
│   │   │   ├── dashboard.py      # /dashboard/* endpoints
│   │   │   └── tasks.py          # /tasks/* endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── vcf_parser.py     # VCF file parsing
│   │   │   ├── blood_parser.py   # PDF/CSV blood test parsing
│   │   │   ├── encryption.py     # File encryption/decryption
│   │   │   ├── annotation/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ensembl.py    # Ensembl VEP client
│   │   │   │   ├── clinvar.py    # ClinVar E-Utils client
│   │   │   │   ├── gwas.py       # GWAS Catalog client
│   │   │   │   ├── ncbi.py       # NCBI dbSNP/PubMed client
│   │   │   │   └── aggregator.py # Combine annotations
│   │   │   ├── risk_scorer.py    # Risk category scoring
│   │   │   ├── recommender.py    # Recommendation engine
│   │   │   └── report_generator.py # AI report generation
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── genome_tasks.py   # Celery: genome_analyze
│   │   │   ├── blood_tasks.py    # Celery: blood_parse
│   │   │   └── report_tasks.py   # Celery: report_generate
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           # Marshmallow schemas for auth
│   │   │   ├── genome.py
│   │   │   └── blood.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── marker_aliases.yaml
│   │       └── variant_categories.yaml
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_genome.py
│       ├── test_blood.py
│       └── fixtures/
│           ├── sample.vcf
│           ├── sample_blood.csv
│           └── sample_blood.pdf
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                  # API client (axios/fetch wrappers)
│   │   ├── components/
│   │   │   ├── auth/             # Login, Register forms
│   │   │   ├── genome/           # Upload wizard, analysis views
│   │   │   ├── blood/            # Upload, results table, trend charts
│   │   │   ├── dashboard/        # Summary cards, charts
│   │   │   ├── reports/          # AI report viewer
│   │   │   └── common/           # Shared UI components
│   │   ├── hooks/                # Custom React hooks
│   │   ├── pages/                # Route-level components
│   │   ├── store/                # State management (Zustand or Context)
│   │   └── types/                # TypeScript interfaces
│   └── tests/
└── docs/
    └── ARCHITECTURE.md           # This document
```
