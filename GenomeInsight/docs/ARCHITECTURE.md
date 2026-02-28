# GenomeInsight — Application Architecture

> **Status**: Design Phase
> **Version**: 0.2.0
> **Last Updated**: 2026-02-28

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
9. [Epigenetics Module](#9-epigenetics-module)
10. [Wearables Integration](#10-wearables-integration)
11. [Cross-Domain Correlation Engine](#11-cross-domain-correlation-engine)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Ethical and Legal Considerations](#13-ethical-and-legal-considerations)

---

## 1. Overview

GenomeInsight is a privacy-first web application that enables users to upload
genome data (VCF files from services like 23andMe, AncestryDNA, Nebula Genomics),
routine blood test results, and epigenetic data files, then connect wearable
health devices — all to receive personalized, multi-layered health insights
powered by public genome research databases, epigenomics reference maps,
wearable analytics, and AI-driven natural language reports.

### Core Value Proposition

- **Genome Analysis**: Parse user variants, cross-reference against ClinVar,
  Ensembl, GWAS Catalog, NCBI Entrez, gnomAD, and PharmGKB to surface disease
  risk associations, pharmacogenomic interactions, variant population
  frequencies, and trait predictions.
- **Epigenetics Layer**: Upload BED files (histone marks from ChIP-seq) or
  methylation array data (IDAT/CSV). Cross-reference against ENCODE and
  Roadmap Epigenomics datasets to show how epigenetic modifications at
  regulatory regions interact with the user's genetic variants — e.g.,
  "Methylation at the BRCA1 promoter may reduce expression of this risk gene."
- **Blood Test Tracking**: Upload blood panels over time, visualize trends,
  and correlate improvements or regressions with genome-informed lifestyle
  changes.
- **Wearables Integration**: Connect 400+ devices (Fitbit, Garmin, Apple
  Health, Oura, Whoop, etc.) via unified wearable APIs (Terra / ROOK).
  Pull daily activity, sleep, heart rate, HRV, and SpO2 data. Correlate
  with genome, epigenetic, and blood data — e.g., "Increased daily steps
  correlated with improved glucose control, consistent with your TCF7L2
  diabetes-risk variant."
- **Actionable Tweaks**: Provide small, evidence-backed lifestyle suggestions
  (dietary changes, exercise tips, supplement recommendations) grounded in
  the user's specific genetic profile, epigenetic context, and real-time
  wearable data.

### Non-Goals (v1)

- Clinical-grade diagnostic reporting (this is informational only).
- Direct integration with electronic health record (EHR) systems.
- Real-time genetic sequencing or raw-read processing.
- Direct IDAT binary parsing (users pre-convert to CSV methylation beta
  values using external tools like minfi or sesame).

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              CLIENT TIER                                  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                       React SPA (MUI)                              │  │
│  │                                                                    │  │
│  │  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │  Auth   │ │ Upload  │ │Dashboard │ │ Reports  │ │Wearable  │ │  │
│  │  │  Pages  │ │ Wizard  │ │(Charts)  │ │(AI-gen)  │ │Connect   │ │  │
│  │  └─────────┘ └─────────┘ └──────────┘ └──────────┘ └──────────┘ │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │ Epigenetics  │ │ Daily       │ │ DisclaimerModal +        │  │  │
│  │  │ Upload/View  │ │ Insights    │ │ ErrorBoundary            │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────────────────┘  │  │
│  │                                                                    │  │
│  │  Libraries: Recharts, React-Dropzone, React-Router, Axios        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                              │ HTTPS (TLS 1.3)                           │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        API / APPLICATION TIER                             │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                 Nginx Reverse Proxy                                 │  │
│  │          (TLS termination, rate limiting, CORS)                    │  │
│  └──────────────────────┬─────────────────────────────────────────────┘  │
│                         │                                                │
│  ┌──────────────────────▼─────────────────────────────────────────────┐  │
│  │              Flask Application (Gunicorn)                          │  │
│  │                                                                    │  │
│  │  ┌───────────┐ ┌──────────────┐ ┌──────────────────────────────┐  │  │
│  │  │ Auth      │ │ Upload &     │ │ Analysis &                   │  │  │
│  │  │ Module    │ │ Parse Module │ │ Reporting Module             │  │  │
│  │  │ (JWT +    │ │ (VCF, PDF,   │ │ (Variant lookup, risk       │  │  │
│  │  │  bcrypt)  │ │  CSV, BED)   │ │  scoring, recommendations)  │  │  │
│  │  └───────────┘ └──────────────┘ └──────────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ┌──────────────────┐ ┌───────────────────┐ ┌──────────────────┐  │  │
│  │  │ Epigenetics      │ │ Wearables OAuth   │ │ Cross-Domain     │  │  │
│  │  │ Module           │ │ + Data Sync       │ │ Correlation      │  │  │
│  │  │ (BED/CSV parse,  │ │ (Terra/ROOK,      │ │ Engine           │  │  │
│  │  │  ENCODE queries) │ │  daily pulls)     │ │ (genome+epi+     │  │  │
│  │  └──────────────────┘ └───────────────────┘ │  blood+wearable) │  │  │
│  │                                              └──────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │            Shared Services                                   │  │  │
│  │  │  - File encryption (AES-256-GCM)                             │  │  │
│  │  │  - Input validation & sanitization                           │  │  │
│  │  │  - Rate limiter (Flask-Limiter)                              │  │  │
│  │  │  - OAuth2 token manager (wearables)                          │  │  │
│  │  │  - Logging / audit trail                                     │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                         │                                                │
│  ┌──────────────────────▼─────────────────────────────────────────────┐  │
│  │              Celery Worker Pool (Redis broker)                     │  │
│  │                                                                    │  │
│  │  ┌───────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │genome_analyze │ │ blood_parse  │ │ report_generate          │  │  │
│  │  │(VCF parse,    │ │ (PDF/CSV     │ │ (AI NLG, compile report) │  │  │
│  │  │ API queries)  │ │  extraction) │ │                          │  │  │
│  │  └───────────────┘ └──────────────┘ └──────────────────────────┘  │  │
│  │                                                                    │  │
│  │  ┌───────────────┐ ┌──────────────┐ ┌──────────────────────────┐  │  │
│  │  │epigenetics_   │ │ wearable_    │ │ daily_insight_generate   │  │  │
│  │  │analyze (BED/  │ │ sync (pull   │ │ (cross-domain analysis,  │  │  │
│  │  │ CSV parse,    │ │  daily data  │ │  personalized tweaks)    │  │  │
│  │  │ ENCODE query) │ │  from Terra) │ │                          │  │  │
│  │  └───────────────┘ └──────────────┘ └──────────────────────────┘  │  │
│  │                                                                    │  │
│  │  Celery Beat (scheduler): wearable_sync every 6 hours             │  │
│  │                            daily_insight at 07:00 user-local       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          DATA TIER                                        │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────────┐ │
│  │   SQLite     │  │   Redis      │  │  Encrypted File Store         │ │
│  │  (Primary    │  │  (Celery     │  │  (Local disk or S3-           │ │
│  │   database)  │  │   broker +   │  │   compatible, AES-256         │ │
│  │              │  │   cache)     │  │   at rest)                    │ │
│  └──────────────┘  └──────────────┘  └────────────────────────────────┘ │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                                     │
│                                                                          │
│  ── Genome Databases ──────────────────────────────────────────────────  │
│  ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Ensembl   │ │ ClinVar   │ │  GWAS    │ │  gnomAD  │ │  NCBI     │  │
│  │ VEP API   │ │ E-Utils   │ │ Catalog  │ │  API     │ │ Entrez    │  │
│  └───────────┘ └───────────┘ └──────────┘ └──────────┘ └───────────┘  │
│  ┌───────────┐                                                         │
│  │ PharmGKB  │                                                         │
│  │ API       │                                                         │
│  └───────────┘                                                         │
│                                                                          │
│  ── Epigenetics Databases ─────────────────────────────────────────────  │
│  ┌────────────────────┐  ┌─────────────────────────────────────────┐   │
│  │  ENCODE REST API   │  │  Roadmap Epigenomics                   │   │
│  │  (encodeproject.   │  │  (NIH / WashU EpiGenome Browser)       │   │
│  │   org)             │  │  (egg2.wustl.edu)                      │   │
│  └────────────────────┘  └─────────────────────────────────────────┘   │
│                                                                          │
│  ── Wearables / Health ────────────────────────────────────────────────  │
│  ┌────────────────────┐  ┌─────────────────────────────────────────┐   │
│  │  Terra API         │  │  ROOK API                              │   │
│  │  (tryterra.co)     │  │  (tryrook.io)                          │   │
│  │  400+ devices      │  │  Alternative unified wearable API      │   │
│  └────────────────────┘  └─────────────────────────────────────────┘   │
│                                                                          │
│  ── AI ────────────────────────────────────────────────────────────────  │
│  ┌──────────────────┐                                                   │
│  │  OpenAI API      │                                                   │
│  │  (GPT for NLG)   │                                                   │
│  └──────────────────┘                                                   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Technology | Role |
|-----------|-----------|------|
| **Frontend SPA** | React 18+, MUI, Recharts | User interface, file uploads, wearable connect, dashboard |
| **Reverse Proxy** | Nginx | TLS termination, rate limiting, static asset serving |
| **API Server** | Flask + Gunicorn | REST API, auth, validation, OAuth2 flows, orchestration |
| **Task Queue** | Celery + Redis | Async genome/epigenetics analysis, wearable sync, reports |
| **Scheduler** | Celery Beat | Periodic wearable data pulls, daily insight generation |
| **Database** | SQLite (WAL mode) | User data, analysis results, wearable data, epigenetics |
| **Cache/Broker** | Redis | Celery message broker, API response caching, session store |
| **File Store** | Encrypted disk (or S3) | Raw uploads (VCF, PDF, CSV, BED) encrypted at rest |
| **Genome APIs** | Ensembl, ClinVar, NCBI, GWAS, gnomAD, PharmGKB | Variant annotation, frequencies, pharmacogenomics |
| **Epigenetics APIs** | ENCODE, Roadmap Epigenomics | Methylation/histone reference data for user regions |
| **Wearable APIs** | Terra / ROOK | Unified access to 400+ wearable devices via OAuth2 |
| **AI Engine** | OpenAI API (or self-hosted) | Natural language report generation, daily insights |

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
                                   6. Query gnomAD for population allele frequencies
                                   7. Query NCBI Entrez for gene details
                                   8. Query PharmGKB for drug-gene interactions
                                   9. Score risk categories (cardiovascular,
                                      metabolic, neurological, pharmacogenomic)
                                  10. Cross-reference epigenetics data (if available)
                                  11. Generate lifestyle recommendations
                                  12. Call AI engine for natural language report
                                  13. Store results → GenomeAnalysis record
                                  14. Update status: complete
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

  User
   │
   │              ┌───────────────────────┐       ┌──────────────────────────┐
   ├──── 1:N ────▶│  EpigeneticUpload     │──1:N─▶│  EpigeneticRegion        │
   │              ├───────────────────────┤       ├──────────────────────────┤
   │              │ id (PK)               │       │ id (PK)                  │
   │              │ user_id (FK)          │       │ upload_id (FK)           │
   │              │ filename_original     │       │ chromosome               │
   │              │ file_path_encrypted   │       │ start_pos                │
   │              │ file_type (bed/csv)   │       │ end_pos                  │
   │              │ data_type (histone/   │       │ feature_type (promoter/  │
   │              │   methylation)        │       │   enhancer/insulator/    │
   │              │ assay_type            │       │   gene_body)             │
   │              │ metrics_json          │       │ nearest_gene             │
   │              │ status                │       │ methylation_beta         │
   │              │ uploaded_at           │       │ histone_mark             │
   │              │ file_size_bytes       │       │ signal_value             │
   │              └───────────────────────┘       │ encode_overlap_json      │
   │                                              │ roadmap_overlap_json     │
   │                                              │ interpretation           │
   │                                              └──────────────────────────┘
   │
   │              ┌───────────────────────┐
   ├──── 1:N ────▶│  WearableConnection   │
   │              ├───────────────────────┤
   │              │ id (PK)               │
   │              │ user_id (FK)          │
   │              │ provider (fitbit/     │
   │              │   garmin/apple/oura/  │
   │              │   whoop/...)          │
   │              │ terra_user_id         │
   │              │ access_token_enc      │
   │              │ refresh_token_enc     │
   │              │ token_expires_at      │
   │              │ scopes                │
   │              │ connected_at          │
   │              │ last_sync_at          │
   │              │ status (active/       │
   │              │   expired/revoked)    │
   │              └───────────────────────┘
   │
   │              ┌───────────────────────┐
   ├──── 1:N ────▶│  DailyWearableData    │
   │              ├───────────────────────┤
   │              │ id (PK)               │
   │              │ user_id (FK)          │
   │              │ connection_id (FK)    │
   │              │ date                  │
   │              │ data_type (activity/  │
   │              │   sleep/heart_rate/   │
   │              │   hrv/spo2/stress)    │
   │              │ data_json             │
   │              │ summary_json          │
   │              │ fetched_at            │
   │              └───────────────────────┘
   │
   │              ┌───────────────────────┐
   └──── 1:N ────▶│  DailyInsight         │
                  ├───────────────────────┤
                  │ id (PK)               │
                  │ user_id (FK)          │
                  │ date                  │
                  │ insight_type (daily/  │
                  │   weekly/alert)       │
                  │ title                 │
                  │ body                  │
                  │ data_sources_json     │
                  │ confidence            │
                  │ generated_at          │
                  └───────────────────────┘
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

#### EpigeneticUpload
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → User | |
| filename_original | VARCHAR(255) | NOT NULL | User-facing name |
| file_path_encrypted | VARCHAR(512) | NOT NULL | Path to AES-encrypted file on disk |
| file_type | VARCHAR(10) | NOT NULL | `bed` or `csv` |
| data_type | VARCHAR(20) | NOT NULL | `histone` (BED from ChIP-seq) or `methylation` (CSV beta values) |
| assay_type | VARCHAR(50) | | e.g., "H3K27ac", "H3K4me3", "WGBS", "450K", "EPIC" |
| tissue_type | VARCHAR(100) | | e.g., "blood", "saliva" — for Roadmap matching |
| metrics_json | TEXT | | Aggregated summary: global methylation avg, region counts, etc. |
| status | VARCHAR(20) | NOT NULL | uploaded / parsing / analyzing / complete / error |
| uploaded_at | DATETIME | NOT NULL | UTC |
| file_size_bytes | INTEGER | NOT NULL | For quota enforcement |

#### EpigeneticRegion
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| upload_id | UUID | FK → EpigeneticUpload | |
| chromosome | VARCHAR(5) | NOT NULL | e.g., "chr1", "chrX" |
| start_pos | INTEGER | NOT NULL | Genomic start coordinate |
| end_pos | INTEGER | NOT NULL | Genomic end coordinate |
| feature_type | VARCHAR(20) | | `promoter`, `enhancer`, `insulator`, `gene_body`, `intergenic` |
| nearest_gene | VARCHAR(50) | | Gene symbol for nearest/overlapping gene |
| methylation_beta | FLOAT | | Beta value 0.0-1.0 (methylation data only) |
| histone_mark | VARCHAR(20) | | e.g., "H3K27ac" (histone data only) |
| signal_value | FLOAT | | ChIP-seq signal intensity (histone data only) |
| encode_overlap_json | TEXT | | Overlapping ENCODE experiments metadata |
| roadmap_overlap_json | TEXT | | Overlapping Roadmap Epigenomics annotations |
| interpretation | TEXT | | AI/rule-based interpretation string |

*Index*: (upload_id), (chromosome, start_pos, end_pos), (nearest_gene)

#### WearableConnection
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → User | |
| provider | VARCHAR(50) | NOT NULL | e.g., "fitbit", "garmin", "apple_health", "oura", "whoop" |
| terra_user_id | VARCHAR(100) | UNIQUE | User ID in Terra/ROOK system |
| access_token_enc | BLOB | NOT NULL | OAuth2 access token, AES-encrypted with user DEK |
| refresh_token_enc | BLOB | NOT NULL | OAuth2 refresh token, AES-encrypted with user DEK |
| token_expires_at | DATETIME | | When the current access token expires |
| scopes | TEXT | | Granted OAuth scopes (comma-separated) |
| connected_at | DATETIME | NOT NULL | When user authorized the connection |
| last_sync_at | DATETIME | | Timestamp of most recent data pull |
| status | VARCHAR(20) | NOT NULL | `active`, `expired`, `revoked`, `error` |

*Index*: (user_id, provider) UNIQUE — one connection per provider per user

#### DailyWearableData
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → User | |
| connection_id | UUID | FK → WearableConnection | |
| date | DATE | NOT NULL | Calendar date for this data point |
| data_type | VARCHAR(20) | NOT NULL | `activity`, `sleep`, `heart_rate`, `hrv`, `spo2`, `stress` |
| data_json | TEXT | NOT NULL | Raw data payload from Terra/ROOK (JSON) |
| summary_json | TEXT | | Computed summaries: daily steps, avg HR, sleep score, etc. |
| fetched_at | DATETIME | NOT NULL | When this data was pulled from the provider |

*Index*: (user_id, date, data_type) UNIQUE — one record per user per date per type

Example `summary_json` for activity:
```json
{
  "steps": 8432,
  "active_minutes": 45,
  "calories_burned": 2150,
  "distance_km": 6.2,
  "floors_climbed": 8
}
```

Example `summary_json` for sleep:
```json
{
  "total_sleep_minutes": 420,
  "deep_sleep_minutes": 90,
  "rem_sleep_minutes": 105,
  "light_sleep_minutes": 225,
  "awakenings": 3,
  "sleep_score": 82,
  "bedtime": "23:15",
  "wake_time": "06:15"
}
```

#### DailyInsight
| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| id | UUID | PK | |
| user_id | UUID | FK → User | |
| date | DATE | NOT NULL | Calendar date for this insight |
| insight_type | VARCHAR(20) | NOT NULL | `daily`, `weekly`, `alert` |
| title | VARCHAR(200) | NOT NULL | Short insight title |
| body | TEXT | NOT NULL | Full insight text with evidence references |
| data_sources_json | TEXT | | JSON: which data layers contributed (genome, epigenetics, blood, wearable) |
| confidence | VARCHAR(10) | NOT NULL | low / medium / high |
| generated_at | DATETIME | NOT NULL | When insight was produced |

*Index*: (user_id, date) — for timeline queries

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

### 4.6 Epigenetics Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/epigenetics/upload` | Yes | Upload BED or CSV methylation file |
| GET | `/epigenetics/uploads` | Yes | List user's epigenetic uploads |
| GET | `/epigenetics/uploads/{id}` | Yes | Get upload details and parsed regions |
| DELETE | `/epigenetics/uploads/{id}` | Yes | Delete upload and associated data |
| POST | `/epigenetics/uploads/{id}/analyze` | Yes | Trigger ENCODE/Roadmap cross-referencing |
| GET | `/epigenetics/analysis/{id}` | Yes | Get analysis results |
| GET | `/epigenetics/analysis/{id}/regions` | Yes | Paginated region list with annotations |
| GET | `/epigenetics/analysis/{id}/genome-overlay` | Yes | Epigenetic annotations overlaid on genome variants |

**POST /epigenetics/upload**
```
Request: multipart/form-data
  - file: BED or CSV file (max 100 MB)
  - data_type: "histone" | "methylation"
  - assay_type: "H3K27ac" | "H3K4me3" | "WGBS" | "450K" | "EPIC" (optional)
  - tissue_type: "blood" | "saliva" | "other" (optional, for Roadmap matching)

Response (202):
{
  "upload_id": "uuid",
  "status": "uploaded",
  "message": "Epigenetic data received. Analysis will begin shortly.",
  "analysis_task_id": "celery-task-uuid"
}
```

**GET /epigenetics/analysis/{id}/genome-overlay**
```
Response (200):
{
  "overlays": [
    {
      "variant_rsid": "rs1801133",
      "gene": "MTHFR",
      "variant_risk": "elevated",
      "epigenetic_context": {
        "region": "chr1:11845780-11846780",
        "feature_type": "promoter",
        "methylation_beta": 0.82,
        "interpretation": "High methylation at the MTHFR promoter may reduce
                           expression, compounding the effect of the C677T
                           risk variant on folate metabolism."
      },
      "adjusted_risk_modifier": 1.15
    }
  ]
}
```

### 4.7 Wearables Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/wearables/providers` | Yes | List available wearable providers |
| POST | `/wearables/connect` | Yes | Initiate OAuth2 flow for a provider |
| GET | `/wearables/callback` | No* | OAuth2 callback (state-validated) |
| GET | `/wearables/connections` | Yes | List user's connected devices |
| DELETE | `/wearables/connections/{id}` | Yes | Disconnect a wearable (revoke tokens) |
| POST | `/wearables/connections/{id}/sync` | Yes | Trigger manual data sync |
| GET | `/wearables/data` | Yes | Query wearable data by date range and type |
| GET | `/wearables/data/latest` | Yes | Get most recent day's data |

**POST /wearables/connect**
```
Request:
{
  "provider": "fitbit"
}

Response (200):
{
  "auth_url": "https://api.tryterra.co/v2/auth/...",
  "state": "random-csrf-state-token",
  "provider": "fitbit",
  "message": "Redirect user to auth_url to complete connection."
}
```

**GET /wearables/data**
```
Query params:
  - type: "activity" | "sleep" | "heart_rate" | "hrv" | "spo2" (optional)
  - from_date: "2026-02-01" (optional)
  - to_date: "2026-02-28" (optional)

Response (200):
{
  "data": [
    {
      "date": "2026-02-27",
      "type": "activity",
      "provider": "fitbit",
      "summary": {
        "steps": 8432,
        "active_minutes": 45,
        "calories_burned": 2150,
        "distance_km": 6.2
      }
    },
    {
      "date": "2026-02-27",
      "type": "sleep",
      "provider": "oura",
      "summary": {
        "total_sleep_minutes": 420,
        "deep_sleep_minutes": 90,
        "rem_sleep_minutes": 105,
        "sleep_score": 82
      }
    }
  ]
}
```

### 4.8 Daily Analysis / Insights

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/insights/daily` | Yes | Get today's cross-domain insights |
| GET | `/insights/history` | Yes | Paginated insight history |
| POST | `/insights/generate` | Yes | Force re-generation of daily insight |

**GET /insights/daily**
```
Response (200):
{
  "date": "2026-02-28",
  "insights": [
    {
      "id": "uuid",
      "type": "daily",
      "title": "Great sleep night — your HRV is trending up",
      "body": "Your deep sleep (92 min) was 15% above your 7-day average.
               Combined with your BDNF Val/Met genotype (rs6265 G/A), quality
               deep sleep is especially important for cognitive recovery.
               Keep up the consistent bedtime routine.",
      "data_sources": ["wearable:sleep", "genome:rs6265"],
      "confidence": "medium"
    },
    {
      "id": "uuid",
      "type": "daily",
      "title": "Step count improving glucose risk management",
      "body": "You've averaged 8,200 steps/day this week (up 12% from last
               week). Given your TCF7L2 risk variant (rs7903146 C/T) and your
               last HbA1c reading of 5.8%, sustained activity is your
               strongest lever for glucose control.",
      "data_sources": ["wearable:activity", "genome:rs7903146", "blood:hemoglobin_a1c"],
      "confidence": "high"
    }
  ]
}
```

---

## 5. Security Considerations

### 5.1 Data Classification

| Data Type | Classification | Handling |
|-----------|---------------|----------|
| Genome data (VCF) | **Highly Sensitive PII** | Encrypted at rest (AES-256-GCM), per-user keys |
| Epigenetic data (BED/CSV) | **Highly Sensitive PII** | Encrypted at rest (AES-256-GCM), per-user keys |
| Blood test results | **Sensitive Health Data** | Encrypted at rest, access-controlled |
| Wearable health data | **Sensitive Health Data** | Encrypted at rest, access-controlled |
| Wearable OAuth tokens | **Secret** | AES-encrypted with user DEK, never logged |
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

### 5.7 Wearable OAuth2 Security

```
User clicks "Connect Fitbit"
       │
       ▼
[Frontend] ──POST /wearables/connect──▶ [Flask API]
                                            │
                                   1. Generate CSRF state token (random 32 bytes)
                                   2. Store state in Redis (TTL: 10 min)
                                   3. Build Terra/ROOK auth URL with state + redirect_uri
                                   4. Return auth_url to frontend
                                            │
                                            ▼
[Frontend] ──redirect──▶ [Terra/ROOK OAuth consent page]
                                            │
                              User approves  │
                                            ▼
[Terra/ROOK] ──GET /wearables/callback?code=...&state=...──▶ [Flask API]
                                            │
                                   1. Validate state against Redis (CSRF protection)
                                   2. Exchange authorization code for access + refresh tokens
                                   3. Encrypt tokens with user's DEK (AES-256-GCM)
                                   4. Store WearableConnection record
                                   5. Trigger initial data sync (Celery task)
                                   6. Redirect to frontend success page
```

**OAuth token security measures:**
- Access and refresh tokens are **never stored in plaintext** — encrypted
  with the user's per-user Data Encryption Key (same envelope encryption
  as genome files).
- Tokens are **never logged** or included in error messages.
- Token refresh is handled server-side by the `wearable_sync` Celery task;
  if refresh fails, connection status is set to `expired` and user is
  notified.
- Users can revoke connections at any time via `DELETE /wearables/connections/{id}`,
  which calls the provider's token revocation endpoint and deletes stored tokens.
- **PKCE** (Proof Key for Code Exchange) is used when the provider supports it.

### 5.8 Epigenetic Data Security

- Epigenetic files (BED, CSV) are treated with the same sensitivity as
  genome data: encrypted at rest with per-user DEK.
- Only anonymized region coordinates (chr:start-end) are sent to ENCODE/Roadmap
  APIs — no user identifiers or linked health data.
- Parsed `EpigeneticRegion` records inherit the user's encryption scope.

---

## 6. Genome Database Integration Plan

### 6.1 Integration Overview

```
                    ┌──────────────────┐
                    │   Variant Pool   │
                    │  (from VCF)      │
                    └────────┬─────────┘
                             │
     ┌───────────┬───────────┼───────────┬────────────┐
     │           │           │           │            │
     ▼           ▼           ▼           ▼            ▼
┌─────────┐┌─────────┐┌──────────┐┌──────────┐┌───────────┐
│ Ensembl ││ ClinVar ││  GWAS    ││  gnomAD  ││  NCBI     │
│ VEP API ││ E-Utils ││ Catalog  ││  GraphQL ││  Entrez   │
└────┬────┘└────┬────┘└────┬─────┘└────┬─────┘└─────┬─────┘
     │          │          │           │             │
     ▼          ▼          ▼           ▼             ▼
  Function   Clinical   Trait      Population    Gene func
  conseq.    signif.    assoc.     allele freq   summaries,
  (missense, (patho-   (odds      (global +     dbSNP,
   synon.,    genic,    ratios,    per-ancestry  PubMed
   regul.)    VUS)      p-vals)    breakdown)    literature
     │          │          │           │             │
     └──────────┴──────────┼───────────┴─────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   Annotation     │
                  │   Aggregator     │
                  │   Service        │
                  └────────┬─────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
              ▼            ▼                ▼
      ┌────────────┐ ┌──────────┐  ┌──────────────┐
      │  PharmGKB  │ │ Epigen.  │  │  Wearable    │
      │  (drug-    │ │ Overlay  │  │  Context     │
      │   gene,    │ │ (ENCODE, │  │  (Terra /    │
      │   dosing   │ │  Roadmap │  │   ROOK data) │
      │   guides)  │ │  data)   │  │              │
      └────────────┘ └──────────┘  └──────────────┘
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

#### gnomAD (Genome Aggregation Database)

- **Endpoint**: `https://gnomad.broadinstitute.org/api` (GraphQL)
- **Rate Limit**: No published rate limit; use reasonable batching.
- **Data Retrieved**: Population allele frequencies (global + per-ancestry:
  African, East Asian, European, Latino, South Asian), allele count,
  homozygote count, filtering status (PASS/fail).
- **Example Query**:
  ```python
  import httpx

  query = """
  {
    variant(variantId: "1-55516888-G-A", dataset: gnomad_r4) {
      variant_id
      genome {
        ac
        an
        af
        populations {
          id
          ac
          an
          af
        }
        filters
      }
    }
  }
  """
  response = httpx.post(
      "https://gnomad.broadinstitute.org/api",
      json={"query": query},
  )
  data = response.json()["data"]["variant"]
  ```
- **Integration Strategy**:
  - Query by variant ID (`{chrom}-{pos}-{ref}-{alt}` format).
  - Use population frequencies to contextualize risk: a "pathogenic"
    variant present in 5% of the population is very different from one
    at 0.001%.
  - Store global AF and per-ancestry AF in `VariantAnnotation` (source: `gnomad`).
  - Cache aggressively (TTL: 30 days) — gnomAD releases are infrequent.

#### NCBI Entrez (Gene Details, dbSNP, PubMed)

- **Endpoint**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`
  - Gene: `esearch.fcgi?db=gene&term={gene_symbol}[sym]+AND+human[orgn]`
  - Gene detail: `esummary.fcgi?db=gene&id={gene_id}`
  - dbSNP: `esummary.fcgi?db=snp&id={rsid_number}`
  - PubMed: `esearch.fcgi?db=pubmed&term={rsid}+AND+{condition}`
  - Literature fetch: `efetch.fcgi?db=pubmed&id={pmid}&rettype=abstract`
- **Rate Limit**: 3/second without API key; **10/second with NCBI API key** (free, register at NCBI).
- **Data Retrieved**:
  - **Gene**: Full gene name, summary/function description, genomic location,
    associated pathways, GO terms, expression data.
  - **dbSNP**: Population allele frequencies, functional class, clinical
    significance links, merged rsID mappings.
  - **PubMed**: Literature count for gene-disease pairs, recent publications,
    abstracts for citation.
- **Example Query**:
  ```python
  import httpx

  NCBI_API_KEY = "your_key"

  # Get gene details for MTHFR
  resp = httpx.get(
      "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
      params={
          "db": "gene",
          "term": "MTHFR[sym] AND human[orgn]",
          "retmode": "json",
          "api_key": NCBI_API_KEY,
      },
  )
  gene_ids = resp.json()["esearchresult"]["idlist"]

  # Get gene summary
  summary = httpx.get(
      "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
      params={
          "db": "gene",
          "id": gene_ids[0],
          "retmode": "json",
          "api_key": NCBI_API_KEY,
      },
  )
  gene_data = summary.json()["result"][gene_ids[0]]
  # gene_data["summary"] → "Methylenetetrahydrofolate reductase catalyzes..."
  # gene_data["description"] → "methylenetetrahydrofolate reductase"
  ```
- **Integration Strategy**:
  - **Primary lookups**: For every gene symbol found by Ensembl VEP, fetch
    the gene function summary from NCBI Gene — this powers the "Gene
    Function" section in reports.
  - **Literature enrichment**: For clinically significant variants, query
    PubMed for recent publications to cite in reports.
  - **dbSNP cross-reference**: Resolve merged rsIDs and fetch population
    frequencies as a fallback when gnomAD lacks coverage.
  - Cache gene summaries for 30 days (stable data), PubMed queries for 7 days.

#### PharmGKB (Pharmacogenomics)

- **Endpoint**: `https://api.pharmgkb.org/v1/data/`
  - Variant: `/variant/{rsid}`
  - Clinical annotations: `/clinicalAnnotation?location.rsid={rsid}`
  - Drug labels: `/drugLabel?relatedGenes.symbol={gene}`
  - Guideline annotations: `/guidelineAnnotation?relatedGenes.symbol={gene}`
- **Rate Limit**: Requires API key (free for non-commercial use).
- **Data Retrieved**: Drug-gene interactions, FDA-label pharmacogenomic
  biomarkers, CPIC dosing guidelines, metabolizer phenotype predictions
  (poor/intermediate/normal/rapid/ultra-rapid).
- **Example Query**:
  ```python
  import httpx

  PHARMGKB_KEY = "your_key"
  headers = {"Authorization": f"Bearer {PHARMGKB_KEY}"}

  # Get clinical annotations for CYP2C19 variant
  resp = httpx.get(
      "https://api.pharmgkb.org/v1/data/clinicalAnnotation",
      params={"location.rsid": "rs4244285"},
      headers=headers,
  )
  annotations = resp.json()["data"]
  # Each annotation includes:
  #   - drugs (e.g., clopidogrel, omeprazole)
  #   - phenotype (e.g., "Poor Metabolizer")
  #   - significance level
  #   - CPIC guideline link
  ```
- **Integration Strategy**:
  - Query for all variants in known pharmacogenes: CYP2D6, CYP2C19,
    CYP2C9, CYP1A2, CYP3A5, VKORC1, DPYD, UGT1A1, SLCO1B1, TPMT, NUDT15.
  - Map genotype → metabolizer status using PharmGKB diplotype tables.
  - Pull CPIC dosing guidelines for actionable drug-gene pairs.
  - Integrate into the pharmacogenomic risk category and generate
    drug-specific recommendations (e.g., "Your CYP2C19 poor metabolizer
    status means clopidogrel may be less effective — discuss alternatives
    with your doctor").
  - Cache for 30 days (guideline updates are infrequent).

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
       ├─ GWAS Catalog (individual rsID lookups, parallelized)
       ├─ gnomAD (GraphQL queries, batched by chromosome)
       ├─ NCBI Entrez Gene (for gene function summaries)
       └─ PharmGKB (for variants in known pharmacogenes)
  └─ Write results to cache and database

Step 2.5: Epigenetic Overlay (if user has epigenetic data)
  └─ For each annotated variant, check if it falls within an
     EpigeneticRegion from the user's uploads
  └─ If overlap: annotate with methylation/histone context
  └─ Adjust risk interpretation based on epigenetic state
     (e.g., hypermethylated promoter → reduced expression → risk modifier)

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
| gnomAD | `gnomad:{chrom}:{pos}:{ref}:{alt}` | 30 days | Release-based, very stable |
| NCBI Gene | `ncbi_gene:{gene_symbol}` | 30 days | Gene summaries rarely change |
| NCBI dbSNP | `dbsnp:{rsid}` | 30 days | Stable data |
| NCBI PubMed | `pubmed:{rsid}:{query}` | 7 days | New publications appear frequently |
| PharmGKB | `pharmgkb:{rsid}` | 30 days | Infrequent changes |
| ENCODE | `encode:{chrom}:{start}:{end}:{assay}` | 14 days | New experiments added periodically |
| Roadmap | `roadmap:{chrom}:{start}:{end}:{tissue}` | 30 days | Stable reference dataset |

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
│  - gnomAD population freqs      │
│  - PharmGKB drug interactions   │
│  - Epigenetic context (if any)  │
│  - Blood test trends (if any)   │
│  - Wearable trends (if any)     │
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
│  3. Epigenetic Context          │
│  4. Detailed Variant Findings   │
│  5. Pharmacogenomic Profile     │
│  6. Blood Test Correlations     │
│  7. Wearable Trends & Insights  │
│  8. Lifestyle Recommendations   │
│  9. Suggested Daily Tweaks      │
│ 10. Disclaimers & References    │
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

## 9. Epigenetics Module

### 9.1 Overview

The epigenetics module allows users to upload data reflecting how their genes
are regulated — beyond the DNA sequence itself. Two primary data types are
supported:

| Data Type | File Format | Source | What It Measures |
|-----------|------------|--------|------------------|
| **Histone Marks** | BED (narrowPeak) | ChIP-seq assays | Which genomic regions are active (H3K27ac, H3K4me3) or repressed (H3K27me3) |
| **DNA Methylation** | CSV (beta values) | 450K/EPIC arrays, WGBS | CpG site methylation levels (0.0 = unmethylated, 1.0 = fully methylated) |

### 9.2 File Parsing Pipeline

```
Epigenetic file uploaded
       │
       ▼
  Detect file type
       │
       ├─ BED file ──▶ Validate BED format (chrom, start, end, name, score)
       │                Parse into EpigeneticRegion records
       │                Extract histone mark from column 4 or filename
       │
       ├─ CSV file ──▶ Validate methylation format (probe_id/position, beta_value)
       │                Map probe IDs to genomic coordinates (via manifest)
       │                Parse into EpigeneticRegion records
       │                Calculate global methylation average
       │
       ▼
  Annotate regions
       │
       ├─ Identify feature type (promoter/enhancer/gene_body/intergenic)
       │   using GENCODE gene annotations
       │
       ├─ Map nearest gene symbol for each region
       │
       ▼
  Query external databases
       │
       ├─ ENCODE REST API ──▶ Find overlapping experiments
       │                       (same tissue, same histone mark or WGBS)
       │
       ├─ Roadmap Epigenomics ──▶ ChromHMM state for the region
       │                          (active promoter, enhancer, repressed, etc.)
       │
       ▼
  Generate interpretations
       │
       ├─ Rule-based: "High methylation (β=0.85) at MTHFR promoter →
       │               reduced expression → may compound C677T variant effect"
       │
       ├─ Cross-reference with user's genome variants (if available)
       │
       ▼
  Store results → EpigeneticRegion records
  Update metrics_json on EpigeneticUpload
```

### 9.3 External API Integration

#### ENCODE REST API

- **Base URL**: `https://www.encodeproject.org`
- **Authentication**: None required for public data.
- **Rate Limit**: Respectful usage; no strict published limit.
- **Key Endpoints**:

**Search for experiments by region and assay type:**
```python
import httpx

# Find WGBS (whole-genome bisulfite sequencing) experiments
# overlapping a genomic region in blood tissue
resp = httpx.get(
    "https://www.encodeproject.org/search/",
    params={
        "type": "Experiment",
        "assay_title": "WGBS",
        "biosample_ontology.term_name": "blood",
        "format": "json",
        "limit": 10,
        "field": "accession",
        "field": "biosample_ontology.term_name",
        "field": "target.label",
        "field": "files.href",
    },
    headers={"Accept": "application/json"},
)
experiments = resp.json()["@graph"]
# Returns list of ENCODE experiment accessions with file download URLs
```

**Get specific experiment metadata:**
```python
resp = httpx.get(
    "https://www.encodeproject.org/experiments/ENCSR000AKA/",
    headers={"Accept": "application/json"},
)
experiment = resp.json()
# experiment["assay_title"] → "Histone ChIP-seq"
# experiment["target"]["label"] → "H3K27ac"
# experiment["biosample_ontology"]["term_name"] → "K562"
```

**Search for annotations overlapping user regions:**
```python
# Search for annotations (ChromHMM, peaks) near a specific region
resp = httpx.get(
    "https://www.encodeproject.org/search/",
    params={
        "type": "Annotation",
        "annotation_type": "chromatin state",
        "assembly": "GRCh38",
        "format": "json",
        "limit": 5,
    },
    headers={"Accept": "application/json"},
)
```

#### Roadmap Epigenomics (NIH / WashU)

- **Base URL**: `http://egg2.wustl.edu/roadmap/`
- **Data Portal**: `http://egg2.wustl.edu/roadmap/web_portal/`
- **Data Access**: Bulk data files (BED, bigWig) + REST-like URL patterns.
- **Key Resources**:

**ChromHMM 15-state model (pre-computed chromatin states):**
```python
import httpx

# Download ChromHMM state annotations for a specific epigenome
# E.g., E062 = Primary mononuclear cells from peripheral blood
ROADMAP_BASE = "http://egg2.wustl.edu/roadmap/data/byFileType/chromhmmSegmentations/ChmmModels/coreMarks/jointModel/final"
epigenome_id = "E062"  # Blood mononuclear cells

resp = httpx.get(
    f"{ROADMAP_BASE}/{epigenome_id}_15_coreMarks_hg38lift_mnemonics.bed.gz",
)
# Parse BED: each row = (chrom, start, end, state_label)
# States: TssA (active TSS), TssAFlnk (flanking active TSS),
#         TxFlnk, Tx, TxWk, EnhG, Enh, ZNF/Rpts, Het,
#         TssBiv (bivalent TSS), BivFlnk, EnhBiv, ReprPC,
#         ReprPCWk, Quies
```

**Match user regions to Roadmap chromatin states:**
```python
# For a user's epigenetic region chr1:11845000-11846000:
# 1. Load the relevant Roadmap ChromHMM BED for the user's tissue type
# 2. Intersect with the user's region using coordinate overlap
# 3. Report: "This region is annotated as 'TssA' (Active TSS) in blood
#            cells by the Roadmap Epigenomics reference map, suggesting
#            this is an active promoter region."
```

**Histone mark signal tracks:**
```python
# Download H3K27ac signal for blood cells
SIGNAL_URL = f"http://egg2.wustl.edu/roadmap/data/byFileType/signal/consolidated/macs2signal/pval/{epigenome_id}-H3K27ac.pval.signal.bigwig"
# Use pyBigWig to query signal at specific coordinates
```

- **Integration Strategy**:
  - Pre-download and index ChromHMM state files for the 5 most relevant
    tissue types (blood, saliva, liver, brain, adipose) — these are small
    BED files (~5 MB each).
  - On analysis: intersect user regions with pre-indexed ChromHMM states
    using in-memory interval tree (e.g., `intervaltree` Python library).
  - For histone signal lookups, use remote bigWig queries via `pyBigWig`
    or cache locally.

### 9.4 Genome-Epigenome Cross-Reference Logic

| Scenario | Genome Data | Epigenetic Data | Combined Interpretation |
|----------|-------------|-----------------|------------------------|
| Silenced risk gene | BRCA1 pathogenic variant | High promoter methylation (β>0.7) | "Methylation at the BRCA1 promoter may reduce expression of the risk allele, potentially attenuating the variant's effect — but this is NOT clinically validated." |
| Activated risk enhancer | Risk variant in enhancer region | H3K27ac peak overlapping variant | "Active enhancer mark at your risk variant suggests this regulatory region is active, potentially amplifying the variant's gene-regulatory effect." |
| Bivalent promoter | Risk variant near bivalent TSS | ChromHMM: TssBiv state | "This gene's promoter is in a bivalent state (poised between active and repressed), suggesting context-dependent expression that may be influenced by environmental factors." |
| Pharmacogene silencing | CYP2D6 poor metabolizer | CYP2D6 promoter hypermethylated | "Epigenetic silencing of CYP2D6 may further reduce metabolizer activity beyond what the genotype alone predicts." |

**Risk score adjustment formula:**
```
adjusted_score = base_genetic_score × epigenetic_modifier

where epigenetic_modifier:
  - Promoter hypermethylation of risk gene → 0.85 (attenuating)
  - Active enhancer at risk locus → 1.15 (amplifying)
  - Bivalent state → 1.0 (neutral, flag as uncertain)
  - No epigenetic data → 1.0 (no adjustment)
```

---

## 10. Wearables Integration

### 10.1 Architecture Overview

```
┌───────────────────┐     ┌──────────────────────┐
│   User's Devices  │     │   GenomeInsight       │
│                   │     │   Backend             │
│  ┌─────────────┐  │     │                       │
│  │ Fitbit      │──┼──┐  │  ┌─────────────────┐  │
│  │ Garmin      │  │  │  │  │ Wearable OAuth  │  │
│  │ Apple Watch │  │  │  │  │ Manager         │  │
│  │ Oura Ring   │  │  │  │  │                 │  │
│  │ Whoop       │  │  │  │  │ - /connect      │  │
│  │ Samsung     │  │  ├──┼─▶│ - /callback     │  │
│  │ Polar       │  │  │  │  │ - /disconnect   │  │
│  │ Withings    │  │  │  │  └────────┬────────┘  │
│  │ ...400+     │  │  │  │           │           │
│  └─────────────┘  │  │  │           ▼           │
│                   │  │  │  ┌─────────────────┐  │
└───────────────────┘  │  │  │ Terra / ROOK    │  │
                       │  │  │ Unified API     │  │
                       └──┼─▶│                 │  │
                          │  │ - OAuth2 proxy  │  │
                          │  │ - Data normalizn│  │
                          │  │ - Webhook push  │  │
                          │  └────────┬────────┘  │
                          │           │           │
                          │           ▼           │
                          │  ┌─────────────────┐  │
                          │  │ Celery Tasks    │  │
                          │  │                 │  │
                          │  │ wearable_sync   │  │
                          │  │ (every 6 hours) │  │
                          │  │                 │  │
                          │  │ daily_insight   │  │
                          │  │ (07:00 local)   │  │
                          │  └─────────────────┘  │
                          │                       │
                          └───────────────────────┘
```

### 10.2 Unified Wearable API: Terra

- **Website**: https://tryterra.co/
- **What it does**: Single API to connect 400+ wearable devices. Handles
  OAuth per-provider, normalizes data into a unified schema.
- **Pricing**: Free tier available; paid tiers for production.

**Key API calls:**

```python
import httpx

TERRA_API_KEY = "your_key"
TERRA_DEV_ID = "your_dev_id"
TERRA_BASE = "https://api.tryterra.co/v2"
headers = {
    "x-api-key": TERRA_API_KEY,
    "dev-id": TERRA_DEV_ID,
}

# 1. Generate authentication URL for a provider
resp = httpx.post(
    f"{TERRA_BASE}/auth/generateWidgetSession",
    headers=headers,
    json={
        "reference_id": "user-uuid-in-our-system",
        "providers": "FITBIT,GARMIN,OURA,WITHINGS,WHOOP",
        "auth_success_redirect_url": "https://genomeinsight.app/wearables/success",
        "auth_failure_redirect_url": "https://genomeinsight.app/wearables/error",
    },
)
widget_url = resp.json()["url"]
# Redirect user to widget_url → they select provider and authorize

# 2. Pull daily activity data
resp = httpx.get(
    f"{TERRA_BASE}/daily",
    headers=headers,
    params={
        "user_id": "terra-user-id",
        "start_date": "2026-02-27",
        "end_date": "2026-02-28",
        "to_webhook": False,
    },
)
daily_data = resp.json()["data"]
# daily_data[0]["distance_data"]["steps"] → 8432
# daily_data[0]["calories_data"]["total_burned_calories"] → 2150
# daily_data[0]["heart_rate_data"]["summary"]["avg_hr_bpm"] → 68

# 3. Pull sleep data
resp = httpx.get(
    f"{TERRA_BASE}/sleep",
    headers=headers,
    params={
        "user_id": "terra-user-id",
        "start_date": "2026-02-27",
        "end_date": "2026-02-28",
    },
)
sleep_data = resp.json()["data"]
# sleep_data[0]["sleep_durations_data"]["asleep"]["duration_deep_sleep_state_seconds"]
# sleep_data[0]["sleep_durations_data"]["asleep"]["duration_REM_sleep_state_seconds"]

# 4. Pull body metrics (weight, body fat %)
resp = httpx.get(
    f"{TERRA_BASE}/body",
    headers=headers,
    params={
        "user_id": "terra-user-id",
        "start_date": "2026-02-27",
        "end_date": "2026-02-28",
    },
)
```

### 10.3 Alternative: ROOK API

- **Website**: https://www.tryrook.io/
- **Similar to Terra**: Unified API for 400+ health devices.
- **Key Differences**: Different pricing model, slightly different data
  normalization schema.

```python
import httpx

ROOK_API_KEY = "your_key"
ROOK_BASE = "https://api.rook.io/api/v1"
headers = {"Authorization": f"Bearer {ROOK_API_KEY}"}

# Pull daily summary
resp = httpx.get(
    f"{ROOK_BASE}/users/{user_id}/summaries/daily",
    headers=headers,
    params={"date": "2026-02-27"},
)
# Returns normalized daily: steps, calories, HR, sleep, etc.
```

### 10.4 Data Sync Architecture

**Celery Beat scheduled tasks:**

```python
# In celery_worker.py / celery config:
CELERYBEAT_SCHEDULE = {
    "wearable-sync-all-users": {
        "task": "app.tasks.wearable_tasks.sync_all_active_connections",
        "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
    },
    "daily-insight-generation": {
        "task": "app.tasks.insight_tasks.generate_daily_insights",
        "schedule": crontab(minute=0, hour=7),  # 07:00 UTC (adjust per user timezone)
    },
}
```

**Sync flow:**

```
Celery Beat triggers wearable_sync_all
       │
       ▼
  Query all WearableConnection WHERE status = 'active'
       │
       ▼
  For each connection:
       │
       ├─ Check token_expires_at → refresh if needed
       │   (encrypt new tokens with user DEK)
       │
       ├─ Call Terra/ROOK API for data since last_sync_at
       │   - /daily (activity)
       │   - /sleep
       │   - /body
       │   - /nutrition (if available)
       │
       ├─ Normalize response → DailyWearableData records
       │   - Compute summary_json (steps, avg HR, sleep score, etc.)
       │
       ├─ Update WearableConnection.last_sync_at
       │
       └─ On error: set status = 'error', log, retry next cycle
```

### 10.5 Webhook Support (Optional)

Terra supports push-based data delivery via webhooks. Instead of polling:

```python
# Terra sends POST to our webhook endpoint when new data arrives
@wearable_bp.route("/webhook/terra", methods=["POST"])
def terra_webhook():
    payload = request.get_json()
    # Verify webhook signature
    signature = request.headers.get("terra-signature")
    if not verify_terra_signature(signature, request.data):
        return jsonify({"error": "Invalid signature"}), 401

    user_id = payload["user"]["reference_id"]  # Our user UUID
    data_type = payload["type"]  # "activity", "sleep", "body", etc.
    data = payload["data"]

    # Store as DailyWearableData
    store_wearable_data(user_id, data_type, data)

    return jsonify({"status": "ok"}), 200
```

---

## 11. Cross-Domain Correlation Engine

### 11.1 Overview

The correlation engine is the heart of GenomeInsight's differentiation. It
connects all four data layers — genome, epigenetics, blood, and wearables —
to produce insights that no single data source could provide alone.

### 11.2 Correlation Matrix

| Genome Variant | Epigenetic Context | Blood Marker | Wearable Signal | Combined Insight |
|---------------|-------------------|--------------|-----------------|------------------|
| TCF7L2 rs7903146 (T/T, high diabetes risk) | — | HbA1c trending up (5.4→5.8%) | Steps declining (8k→5k/day) | "Your diabetes-risk genotype + rising HbA1c + declining activity is a concerning trend. Even 30 min/day of walking can significantly improve insulin sensitivity." |
| APOE ε4 carrier | — | LDL 145 mg/dL (elevated) | Low activity, poor sleep | "Your APOE ε4 status predisposes to elevated LDL. Combined with low activity and poor sleep (both linked to lipid metabolism), prioritize a Mediterranean diet and consistent exercise." |
| MTHFR C677T (T/T) | MTHFR promoter methylated (β=0.8) | Homocysteine 18 μmol/L (high) | — | "Your MTHFR variant reduces enzyme activity, and high promoter methylation may further suppress expression. Your elevated homocysteine confirms impaired folate metabolism. Consider methylfolate supplementation (consult your doctor)." |
| BDNF Val66Met (G/A) | — | — | Deep sleep 45 min (low), HRV declining | "Your BDNF variant affects neuroplasticity. Low deep sleep and declining HRV suggest suboptimal neural recovery. Prioritize sleep hygiene: consistent bedtime, cool room, no screens 1hr before bed." |
| CYP1A2 slow (A/C) | — | — | Resting HR elevated after afternoon coffee (wearable timestamp) | "Your slow caffeine metabolism genotype + elevated afternoon HR pattern suggests caffeine is significantly impacting your cardiovascular system. Consider limiting caffeine to mornings only." |
| HFE C282Y carrier | HFE promoter active (low methylation) | Ferritin 450 ng/mL (very high) | — | "Your hemochromatosis variant + active gene expression + very high ferritin is a clear signal. Discuss phlebotomy schedule with your doctor." |
| FTO rs9939609 (A/A, obesity risk) | — | — | Steps avg 3k/day, BMI 29 (from body data) | "Your FTO risk variant + low activity + near-obese BMI: the FTO gene affects satiety signaling. Structured exercise (aim for 7k+ steps) has been shown to significantly attenuate FTO-related weight gain." |

### 11.3 Insight Generation Pipeline

```
Celery Beat: daily_insight_generate (07:00)
       │
       ▼
  For each user with active data:
       │
       ├─ Load user's latest data from each layer:
       │   ├─ Genome: risk_summary_json, key variants, pharmacogenomics
       │   ├─ Epigenetics: EpigeneticRegion records (if any)
       │   ├─ Blood: most recent BloodResult records, trend direction
       │   └─ Wearable: last 7 days of DailyWearableData summaries
       │
       ├─ Run correlation rules engine:
       │   ├─ Match variant-blood pairs (e.g., APOE + LDL)
       │   ├─ Match variant-wearable pairs (e.g., FTO + steps)
       │   ├─ Match epigenetic-variant pairs (e.g., methylation + MTHFR)
       │   ├─ Match blood-wearable pairs (e.g., glucose + activity)
       │   └─ Detect trend changes (improving/worsening/new threshold)
       │
       ├─ Rank by priority:
       │   ├─ Alert-level: Dangerous trend (e.g., HbA1c rising + declining activity)
       │   ├─ Daily: Notable observation (e.g., great sleep night)
       │   └─ Weekly: Summary of trends
       │
       ├─ Generate natural language insight (GPT or template):
       │   ├─ Include specific data points from all contributing sources
       │   ├─ Reference relevant rsIDs and gene names
       │   ├─ Provide actionable suggestion
       │   └─ Include disclaimer
       │
       └─ Store → DailyInsight records
```

### 11.4 Alert Thresholds

| Condition | Trigger | Alert Level |
|-----------|---------|-------------|
| Blood marker exits normal range | Flag changes H→L or L→H | Alert |
| Wearable metric declines >20% week-over-week | Steps, sleep, HRV | Daily |
| Blood + genome convergence | Risk variant + abnormal blood value | Alert |
| Positive trend | Blood marker improving toward normal | Daily (positive) |
| Wearable + genome opportunity | Exercise correlated with risk gene amelioration | Weekly |

---

## 12. Deployment Architecture

### 12.1 Docker Compose Topology

```
┌───────────────────────────────────────────────────────────┐
│                 docker-compose.yml                          │
│                                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌──────────┐  │
│  │  nginx   │  │  flask   │  │  worker  │ │  beat    │  │
│  │  :80/443 │─▶│  :5000   │  │ (celery) │ │ (sched.) │  │
│  └──────────┘  └──────────┘  └──────────┘ └──────────┘  │
│                      │              │            │         │
│                      ▼              ▼            ▼         │
│               ┌──────────┐  ┌──────────┐                  │
│               │  redis   │  │  flower  │                  │
│               │  :6379   │  │  :5555   │                  │
│               └──────────┘  └──────────┘                  │
│                                                            │
│  Volumes:                                                  │
│    - sqlite_data:/data/db                                  │
│    - encrypted_files:/data/files                           │
│    - redis_data:/data/redis                                │
│    - roadmap_cache:/data/roadmap (pre-downloaded BEDs)     │
│                                                            │
└───────────────────────────────────────────────────────────┘
```

### 12.2 Container Specifications

| Service | Base Image | Resources | Notes |
|---------|-----------|-----------|-------|
| nginx | nginx:alpine | 256MB RAM | Static assets, TLS, proxy |
| flask | python:3.12-slim | 512MB RAM | Gunicorn with 4 workers |
| worker | python:3.12-slim | 1GB RAM | Celery with 2 concurrent workers |
| beat | python:3.12-slim | 256MB RAM | Celery Beat scheduler (wearable sync, daily insights) |
| redis | redis:7-alpine | 256MB RAM | Persistence: RDB + AOF |
| flower | mher/flower | 128MB RAM | Celery monitoring (admin only) |

### 12.3 Environment Variables

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

# External APIs — Genome
NCBI_API_KEY=<ncbi-api-key>
PHARMGKB_API_KEY=<pharmgkb-api-key>
OPENAI_API_KEY=<openai-api-key>

# External APIs — Wearables
TERRA_API_KEY=<terra-api-key>
TERRA_DEV_ID=<terra-dev-id>
TERRA_WEBHOOK_SECRET=<terra-webhook-secret>
# OR: ROOK_API_KEY=<rook-api-key>

# File Storage
UPLOAD_DIR=/data/files
MAX_VCF_SIZE_MB=500
MAX_BLOOD_FILE_SIZE_MB=20
MAX_EPIGENETICS_FILE_SIZE_MB=100
```

---

## 13. Ethical and Legal Considerations

### 13.1 Medical Disclaimer Policy

- Disclaimers displayed on **every** page containing health information.
- Forced acknowledgment during onboarding before first upload.
- Reports always include a non-removable disclaimer section.
- Language reviewed by legal counsel before launch.

### 13.2 Genetic Non-Discrimination

- Inform users about GINA (Genetic Information Nondiscrimination Act) in
  the US and equivalent laws in other jurisdictions.
- Advise users about potential implications of genetic data sharing.

### 13.3 Data Sovereignty

- Allow users to choose data residency region (future, multi-region
  deployment).
- All processing happens server-side; no genome data sent to third parties
  except anonymized variant IDs to public databases (rsIDs only, no
  identifying information).

### 13.4 Transparency

- Show users exactly which databases were queried for each finding.
- Link to original research papers (PubMed).
- Show confidence levels for all recommendations.
- Display last-updated dates for all external data sources.

### 13.5 Wearable Data Ethics

- Users can **disconnect any wearable** at any time, which revokes the
  OAuth token and stops data collection.
- Wearable data is **never shared** with wearable providers or third parties.
- Users are clearly informed that wearable correlations are **observational,
  not causal** — e.g., correlation between steps and glucose does not prove
  causation.
- All wearable insights include: "This observation is based on your personal
  data trends and genetic profile. It is not medical advice."

### 13.6 Epigenetic Data Caveats

- Users are informed that epigenetic marks are **tissue-specific** and
  **dynamic** — data from saliva may not reflect liver or brain epigenetics.
- Epigenetic-genome risk adjustments are presented as **experimental and
  informational** with appropriate uncertainty language.
- No clinical claims are made about epigenetic modifications.

### 13.7 Informed Consent

Users must acknowledge before uploading:
1. This is not a medical diagnostic tool.
2. Their data will be encrypted and stored securely.
3. They can delete all their data at any time.
4. Variant IDs (not personal data) are sent to public research databases
   for annotation.
5. Region coordinates (not personal data) are sent to ENCODE/Roadmap for
   epigenetic annotation.
6. Wearable data is pulled via third-party APIs (Terra/ROOK) and stored
   encrypted on GenomeInsight servers.
7. AI-generated reports and cross-domain insights may contain errors.
8. Correlations between data layers are observational, not diagnostic.

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
| BED/BigWig | pybedtools, pyBigWig | 0.9+ / 0.3+ | Epigenetic file parsing |
| Interval Tree | intervaltree | 3.1+ | Fast genomic region overlap queries |
| Scheduler | Celery Beat | 5+ | Periodic wearable sync, daily insights |
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
| Iron Metabolism | HFE, TFR2, HAMP | rs1800562, rs1799945 | Hemochromatosis, iron overload |
| Vitamin D | GC (DBP), CYP2R1 | rs2282679, rs10741657 | Vitamin D metabolism |
| Longevity | FOXO3, CETP, APOE | rs2802292, rs5882 | Aging-related pathways |

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
│   │   │   ├── epigenetics.py    # EpigeneticUpload, EpigeneticRegion
│   │   │   ├── wearable.py       # WearableConnection, DailyWearableData
│   │   │   ├── insight.py        # DailyInsight
│   │   │   ├── annotation.py     # VariantAnnotation
│   │   │   ├── recommendation.py # HealthRecommendation
│   │   │   └── audit.py          # AuditLog
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py           # /auth/* endpoints
│   │   │   ├── genome.py         # /genome/* endpoints
│   │   │   ├── blood.py          # /blood/* endpoints
│   │   │   ├── epigenetics.py    # /epigenetics/* endpoints
│   │   │   ├── wearables.py      # /wearables/* endpoints (OAuth, data)
│   │   │   ├── insights.py       # /insights/* endpoints (daily analysis)
│   │   │   ├── dashboard.py      # /dashboard/* endpoints
│   │   │   └── tasks.py          # /tasks/* endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── vcf_parser.py     # VCF file parsing
│   │   │   ├── blood_parser.py   # PDF/CSV blood test parsing
│   │   │   ├── epigenetics_parser.py  # BED/CSV epigenetic file parsing
│   │   │   ├── encryption.py     # File encryption/decryption
│   │   │   ├── annotation/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ensembl.py    # Ensembl VEP client
│   │   │   │   ├── clinvar.py    # ClinVar E-Utils client
│   │   │   │   ├── gwas.py       # GWAS Catalog client
│   │   │   │   ├── gnomad.py     # gnomAD GraphQL client
│   │   │   │   ├── ncbi.py       # NCBI Entrez (Gene, dbSNP, PubMed)
│   │   │   │   ├── pharmgkb.py   # PharmGKB client
│   │   │   │   ├── encode.py     # ENCODE REST API client
│   │   │   │   ├── roadmap.py    # Roadmap Epigenomics client
│   │   │   │   └── aggregator.py # Combine all annotations
│   │   │   ├── wearable_client.py # Terra/ROOK API wrapper
│   │   │   ├── risk_scorer.py    # Risk category scoring (incl. epigenetic modifier)
│   │   │   ├── correlation_engine.py # Cross-domain correlation logic
│   │   │   ├── recommender.py    # Recommendation engine
│   │   │   └── report_generator.py # AI report generation
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   ├── genome_tasks.py   # Celery: genome_analyze
│   │   │   ├── blood_tasks.py    # Celery: blood_parse
│   │   │   ├── epigenetics_tasks.py  # Celery: epigenetics_analyze
│   │   │   ├── wearable_tasks.py # Celery: wearable_sync
│   │   │   ├── insight_tasks.py  # Celery: daily_insight_generate
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
│   │   │   ├── epigenetics/      # Upload, region viewer, genome overlay
│   │   │   ├── wearables/        # Connect device, data dashboard, trends
│   │   │   ├── insights/         # Daily insight cards, timeline
│   │   │   ├── dashboard/        # Summary cards, charts
│   │   │   ├── reports/          # AI report viewer (expanded sections)
│   │   │   └── common/           # Shared UI (DisclaimerModal, ErrorBoundary)
│   │   ├── hooks/                # Custom React hooks
│   │   ├── pages/                # Route-level components
│   │   ├── store/                # State management (Zustand or Context)
│   │   └── types/                # TypeScript interfaces
│   └── tests/
└── docs/
    └── ARCHITECTURE.md           # This document
```
