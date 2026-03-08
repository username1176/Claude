# GenomeInsight V2 — Design Document
## Elevating to Nebula Genomics + InsideTracker Standards

**Status:** Design Phase — No Code Yet
**Date:** 2026-03-07
**Baseline:** GenomeInsight V1 (Flask + React + Celery, 385 tests, 5 domains, 9 correlation rules)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Nebula-Inspired Features](#3-nebula-inspired-features)
4. [InsideTracker-Inspired Features](#4-insidetracker-inspired-features)
5. [Unified Healthspan Platform](#5-unified-healthspan-platform)
6. [New Data Models](#6-new-data-models)
7. [New API Endpoints](#7-new-api-endpoints)
8. [ML Module Design](#8-ml-module-design)
9. [Blockchain Integration](#9-blockchain-integration)
10. [Subscription Service](#10-subscription-service)
11. [Updated Frontend](#11-updated-frontend)
12. [Security Enhancements](#12-security-enhancements)
13. [Infrastructure Changes](#13-infrastructure-changes)
14. [Migration Strategy](#14-migration-strategy)

---

## 1. Executive Summary

GenomeInsight V2 transforms the platform from a multi-domain health data viewer into a
**predictive healthspan intelligence engine** — combining Nebula Genomics' deep sequencing
capabilities and blockchain privacy with InsideTracker's biological age modeling and
personalized optimization zones.

### What Changes

| Dimension | V1 (Current) | V2 (Proposed) |
|-----------|--------------|---------------|
| Sequencing | VCF only (SNP chips) | WGS: FASTQ/BAM/CRAM + VCF |
| Privacy | AES-256-GCM encryption | + Blockchain data ownership, anonymous mode |
| Genome Access | Variant table | Interactive genome browser + gene/variant search |
| Blood Analysis | Flag H/L/N against lab ranges | Personalized optimized zones + trend prediction |
| Age Modeling | None | Biological age (InnerAge) via ML on biomarkers + methylation |
| AI | Report generation | Conversational AI chatbot (health queries) |
| Predictions | Cross-domain correlations | ML-based healthspan forecasting |
| Wearables | Activity/sleep/HRV display | Healthspan habit reports (weekly) |
| Monetization | None | Subscription tiers (Free/Basic/Premium) |
| Ancestry | None | Deep ancestry (Y-DNA, mtDNA, haplogroups) |
| Microbiome | Gut only | + Oral microbiome (from WGS saliva samples) |

### What Stays the Same

- Flask + SQLAlchemy backend (extended, not replaced)
- React + Wabi Sabi frontend (enhanced)
- Celery async pipeline (new queues added)
- AES-256-GCM encryption (still the foundation — blockchain is additive)
- Existing 9 correlation rules (expanded to 15+)
- JWT auth (extended with subscription-aware middleware)
- 385 existing tests (V2 targets 600+)

---

## 2. Architecture Overview

### V2 System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        GenomeInsight V2                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐                │
│  │ React 18    │  │ Streamlit   │  │ Mobile PWA   │                │
│  │ Wabi Sabi   │  │ Preview     │  │ (future)     │                │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘                │
│         │                │                 │                         │
│         └────────────────┼─────────────────┘                        │
│                          │                                           │
│                   ┌──────▼──────┐                                   │
│                   │  Nginx /    │                                    │
│                   │  API Gateway│                                    │
│                   └──────┬──────┘                                   │
│                          │                                           │
│         ┌────────────────┼────────────────────┐                     │
│         │                │                    │                      │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌─────────▼────────┐           │
│  │ Flask API   │  │ ML Service  │  │ Blockchain Svc   │           │
│  │ (v1 + v2)  │  │ (TF/sklearn)│  │ (Web3.py)        │           │
│  └──────┬──────┘  └──────┬──────┘  └─────────┬────────┘           │
│         │                │                    │                      │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌─────────▼────────┐           │
│  │ Celery      │  │ ML Model    │  │ Ethereum Node    │           │
│  │ Workers     │  │ Store       │  │ (Sepolia testnet)│           │
│  └──────┬──────┘  └─────────────┘  └──────────────────┘           │
│         │                                                           │
│  ┌──────▼──────┐  ┌─────────────┐  ┌──────────────────┐           │
│  │ PostgreSQL  │  │ Redis       │  │ S3/MinIO         │           │
│  │ (primary)   │  │ (cache/     │  │ (FASTQ/BAM      │           │
│  │             │  │  broker)    │  │  object store)   │           │
│  └─────────────┘  └─────────────┘  └──────────────────┘           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### New Services (Docker Compose additions)

| Service | Image | Purpose |
|---------|-------|---------|
| `genomeinsight-ml` | Custom (TF Serving + FastAPI) | Biological age, predictions, biomarker zones |
| `genomeinsight-blockchain` | Custom (Web3.py + Flask) | Data ownership tokens, anonymous storage |
| `genomeinsight-minio` | minio/minio | Object storage for FASTQ/BAM/CRAM files (multi-GB) |
| `genomeinsight-celery-wgs` | Same base image | Dedicated worker for WGS pipeline (high memory) |
| `genomeinsight-chatbot` | Custom (LangChain + Flask) | AI conversational interface |

Total Docker services: 5 (existing) + 5 (new) = **10 services**

---

## 3. Nebula-Inspired Features

### 3.1 Whole Genome Sequencing (WGS) Support

**Inspiration:** Nebula Genomics offers 30x and 100x WGS depth, providing complete genome
coverage rather than just SNP chip genotyping. They accept FASTQ/CRAM files and allow
third-party data import from 23andMe/AncestryDNA.

#### Design

**File Formats Supported:**

| Format | Size Range | Description |
|--------|-----------|-------------|
| FASTQ | 30-200 GB | Raw sequencing reads (paired-end R1/R2) |
| BAM | 30-100 GB | Aligned reads (sorted, indexed) |
| CRAM | 15-50 GB | Compressed aligned reads (reference-based) |
| VCF/gVCF | 50-500 MB | Called variants (existing V1 support) |

**Upload Pipeline:**

```
User uploads FASTQ/BAM/CRAM
        │
        ▼
┌─────────────────┐
│ Chunked Upload  │  ← tus.io resumable upload protocol
│ (5 GB chunks)   │     Handles iPhone/spotty connections
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ S3/MinIO Object │  ← Files too large for disk encryption
│ Store (SSE-C)   │     Server-side encryption with customer key
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Celery WGS      │  ← Dedicated high-memory worker queue
│ Worker           │     Separate from standard analysis queue
└────────┬────────┘
         │
    ┌────┴────────────────────────┐
    │                             │
    ▼                             ▼
┌──────────┐              ┌──────────┐
│ FASTQ:   │              │ BAM/CRAM:│
│ minimap2 │              │ samtools │
│ → BAM    │              │ stats    │
│ → VCF    │              │ → VCF    │
└────┬─────┘              └────┬─────┘
     │                         │
     └────────────┬────────────┘
                  ▼
          ┌──────────────┐
          │ Standard V1  │
          │ VCF Pipeline │  ← Reuse existing genome_analyzer.py
          │ + WGS extras │
          └──────────────┘
```

**WGS-Specific Analysis (beyond V1 VCF pipeline):**

1. **Depth Statistics** — Mean coverage, uniformity, % bases at >=20x/30x
2. **Structural Variants** — CNVs, inversions, translocations (Manta/Delly caller)
3. **Mitochondrial Variants** — Full mtDNA analysis for maternal haplogroup
4. **Y-Chromosome Analysis** — Y-DNA haplogroup assignment (for XY individuals)
5. **HLA Typing** — Immune system gene typing from WGS reads
6. **Pharmacogenomics** — Expanded PGx star allele calling (CYP2D6, CYP2C19, etc.)

**Depth Simulation:**

For users who upload SNP-chip data (23andMe/AncestryDNA VCF), we offer a "simulated depth"
view showing what additional insights WGS at 30x or 100x would reveal — used as an upsell
to encourage full sequencing. This compares:

- SNP chip: ~700K variants (0.02% of genome)
- 30x WGS: ~4-5M variants (full coding + non-coding)
- 100x WGS: ~4-5M variants at higher confidence + rare variant detection

#### New Config Values

```python
# WGS Configuration
MAX_FASTQ_SIZE_GB = 200
MAX_BAM_SIZE_GB = 100
MAX_CRAM_SIZE_GB = 50
WGS_WORKER_MEMORY_GB = 32
WGS_WORKER_CONCURRENCY = 1  # one job at a time (memory-bound)
REFERENCE_GENOME_PATH = "/data/references/GRCh38.fa"
MINIO_ENDPOINT = "minio:9000"
MINIO_BUCKET = "genomeinsight-wgs"
```

---

### 3.2 Blockchain Privacy & Data Ownership

**Inspiration:** Nebula Genomics uses blockchain for transparent consent management,
immutable access logs, and user-controlled data sharing. They partnered with Oasis Labs
for privacy-preserving computation.

#### Design

**Core Concept:** Each user's genomic data gets a **Data Ownership Token (DOT)** — an
ERC-721 NFT on Ethereum that represents ownership and access control. The genomic data
itself never touches the blockchain — only ownership proofs and consent records do.

**Components:**

```
┌─────────────────────────────────────────────────────────┐
│                 Blockchain Layer                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Smart Contracts (Solidity → deployed on Sepolia)       │
│  ┌───────────────────────────────────────────────────┐  │
│  │ DataOwnershipToken.sol (ERC-721)                  │  │
│  │  - mint(user_address, data_hash) → token_id       │  │
│  │  - grantAccess(token_id, researcher_address)      │  │
│  │  - revokeAccess(token_id, researcher_address)     │  │
│  │  - getAccessLog(token_id) → AccessEntry[]         │  │
│  │  - burn(token_id)  ← GDPR right to erasure        │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ConsentRegistry.sol                                │  │
│  │  - recordConsent(user, purpose, expiry)           │  │
│  │  - withdrawConsent(user, purpose)                 │  │
│  │  - verifyConsent(user, purpose) → bool            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ DataMarketplace.sol (future — data monetization)  │  │
│  │  - listDataset(token_id, price_wei, terms)        │  │
│  │  - purchaseAccess(token_id) payable               │  │
│  │  - withdraw(token_id)                             │  │
│  │  - royaltyInfo(token_id) → (receiver, amount)     │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Backend Service (Web3.py + Flask microservice)         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ blockchain_service.py                              │  │
│  │  - mint_ownership_token(user_id, data_sha256)     │  │
│  │  - verify_ownership(user_id, token_id)            │  │
│  │  - record_consent(user_id, purpose, duration)     │  │
│  │  - revoke_consent(user_id, purpose)               │  │
│  │  - get_access_audit_trail(token_id)               │  │
│  │  - anonymous_id(user_id) → deterministic pseudonym│  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Anonymous Mode:**

Users can enable "Anonymous Mode" which:
1. Replaces user_id with a blockchain-derived pseudonym in all API responses
2. Strips PII from stored analysis results
3. Uses zero-knowledge proofs for subscription validation (proving "I have a valid subscription" without revealing identity)
4. All audit logs reference the pseudonym, not the real user_id
5. Data Ownership Token is the only link between pseudonym and real identity

**Data Monetization (Future Phase):**

Users can opt-in to share de-identified genomic data with researchers via the
DataMarketplace smart contract. Revenue split: 80% user / 20% platform.
Researchers purchase time-limited, scope-limited access. All access is logged
immutably on-chain.

#### New Config Values

```python
# Blockchain Configuration
ETHEREUM_RPC_URL = "https://sepolia.infura.io/v3/{PROJECT_ID}"
ETHEREUM_CHAIN_ID = 11155111  # Sepolia testnet
CONTRACT_OWNER_PRIVATE_KEY = env("CONTRACT_OWNER_KEY")  # deployer wallet
DATA_OWNERSHIP_CONTRACT_ADDRESS = env("DOT_CONTRACT_ADDR")
CONSENT_REGISTRY_CONTRACT_ADDRESS = env("CONSENT_CONTRACT_ADDR")
MARKETPLACE_CONTRACT_ADDRESS = env("MARKETPLACE_CONTRACT_ADDR")  # future
GAS_PRICE_STRATEGY = "medium"  # low/medium/fast
```

---

### 3.3 Genome Browser & Search Tools

**Inspiration:** Nebula's Genome Browser lets users visually explore their genome,
search by gene name or rsID, and view variants in genomic context with annotation tracks.

#### Design

**Genome Browser (React component):**

```
┌────────────────────────────────────────────────────────────┐
│ GenomeInsight Genome Browser                               │
├────────────────────────────────────────────────────────────┤
│ Search: [BRCA1____________] [Go]   Chr: [17▾] Pos: [___] │
│                                                            │
│ ═══════════════╦════════════════════════════╦═════════════ │
│ Chromosome 17  ║  43,044,295 - 43,170,245  ║  BRCA1       │
│ ═══════════════╩════════════════════════════╩═════════════ │
│                                                            │
│ Gene Track    ─────[████████████████████]────────          │
│               BRCA1 (NM_007294)                            │
│                                                            │
│ Your Variants ──●──────●────────●──────●──────            │
│               rs1799950  rs80357906  rs1799966             │
│                                                            │
│ ClinVar       ──▲──────▲────────────────────              │
│               Pathogenic  Benign                           │
│                                                            │
│ Conservation  ▓▓▓▓▓▓▓▓░░▓▓▓▓▓▓▓▓▓▓░░░▓▓▓▓               │
│                                                            │
│ Methylation   ▒▒▒░░░░▒▒▒▒▒░░░░░▒▒▒░░░░▒▒▒               │
│ (if epi data)                                              │
└────────────────────────────────────────────────────────────┘
```

**Implementation Approach:**

The browser is a React component using `@jbrowse/react-linear-genome-view` (the JBrowse 2
React component library). This provides:

- Genome coordinate navigation (pan, zoom)
- Multiple annotation tracks (gene models, variants, ClinVar, conservation)
- User's own variants overlaid as a custom track
- Epigenetic data (if available) shown as a methylation heatmap track
- Configurable reference genome (GRCh37/GRCh38)

**Backend Support:**

- `GET /api/v2/genome-browser/tracks` — List available tracks for user
- `GET /api/v2/genome-browser/variants?chr=17&start=43044295&end=43170245` — Fetch user variants in region
- `GET /api/v2/genome-browser/annotations?chr=17&start=...&end=...` — Fetch ClinVar/gene annotations
- Track data served as JBrowse-compatible JSON or tabix-indexed files

**Gene Search:**

- `GET /api/v2/variant-search?q=rs1799950` — Search by rsID across user's data
- `GET /api/v2/variant-search?gene=BRCA1` — Search by gene name
- `GET /api/v2/variant-search?region=chr17:43044295-43170245` — Region query
- Returns: matching variants, annotations, cross-domain correlations (if any)
- Autocomplete powered by Redis-cached gene/variant name index

---

### 3.4 Deep Ancestry & Oral Microbiome

**Inspiration:** Nebula provides Y-DNA and mtDNA haplogroup analysis via WGS, and was
the first to offer oral microbiome reporting from the same saliva sample.

#### Deep Ancestry Design

**Haplogroup Assignment:**

From WGS data, extract:
1. **Mitochondrial DNA (mtDNA)** — Full mitogenome → maternal haplogroup (e.g., H1a1, L3e1)
2. **Y-Chromosome (Y-DNA)** — Full Y-chrom → paternal haplogroup (e.g., R1b1a1a2, E1b1a)
3. **Autosomal Ancestry** — Principal component analysis against reference populations

**Pipeline:**

```
WGS BAM/CRAM
    │
    ├── samtools view -b chrM → mtDNA BAM
    │   └── haplogrep3 classify → maternal haplogroup
    │
    ├── samtools view -b chrY → Y-DNA BAM (if XY)
    │   └── y-lineage-tracker → paternal haplogroup
    │
    └── plink2 --pca → autosomal PCA
        └── sklearn nearest-neighbor vs. 1000 Genomes → ancestry percentages
```

**Ancestry Report Contents:**
- Maternal haplogroup with migration map
- Paternal haplogroup with migration map (if Y-DNA present)
- Ancestry composition percentages (26 reference populations)
- Neanderthal/Denisovan introgression percentage
- Timeline of ancestral migration events

#### Oral Microbiome Design

**Integration with Existing Microbiome Module:**

The existing microbiome module handles gut samples (16S, shotgun, WGS). Oral microbiome
extends this with:

1. **New `sample_source` value:** `oral` (in addition to existing gut/skin/vaginal/environmental)
2. **WGS Oral Extraction:** When a user submits a WGS saliva sample, unmapped reads
   (those not aligning to human reference) are extracted and classified as oral microbiome:
   ```
   samtools view -f 4 wgs.bam | kraken2 --db oral_microbiome_db → oral taxa
   ```
3. **Oral-Specific Analyses:**
   - Periodontal disease risk taxa (Porphyromonas gingivalis, Tannerella forsythia)
   - Caries-associated taxa (Streptococcus mutans)
   - Oral-gut axis correlations (connect oral findings to gut microbiome data)
   - Oral microbiome diversity score + population percentile

4. **Cross-Domain Oral Correlations (new rules):**

   | Rule ID | Domains | Trigger |
   |---------|---------|---------|
   | `oral_gut_axis` | oral_microbiome + gut_microbiome | Shared pathogenic taxa between oral and gut |
   | `oral_inflammation` | oral_microbiome + blood + epigenetics | P. gingivalis high + elevated CRP + TNF hypomethylated |
   | `oral_genome_perio` | oral_microbiome + genome | IL-1 variant + high periodontal pathogens |

---

## 4. InsideTracker-Inspired Features

### 4.1 Biological Age (InnerAge) Calculation

**Inspiration:** InsideTracker's InnerAge 2.0 uses blood biomarkers and DNA data to
calculate biological age, showing users whether they're aging faster or slower than
their chronological age. Based on research from the Horvath clock, PhenoAge (Levine),
and GrimAge epigenetic clocks.

#### Design

**Three-Tier Biological Age Model:**

```
┌─────────────────────────────────────────────────────────┐
│              Biological Age Engine                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Tier 1: BiomarkerAge (blood only)                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Inputs (9 PhenoAge biomarkers):                   │  │
│  │  - Albumin (g/dL)                                 │  │
│  │  - Creatinine (mg/dL)                             │  │
│  │  - Glucose (mg/dL)                                │  │
│  │  - C-reactive protein (mg/L)                      │  │
│  │  - Lymphocyte percent (%)                         │  │
│  │  - Mean cell volume (fL)                          │  │
│  │  - Red cell distribution width (%)                │  │
│  │  - Alkaline phosphatase (U/L)                     │  │
│  │  - White blood cell count (10^3/uL)               │  │
│  │                                                   │  │
│  │ Model: Elastic Net regression (scikit-learn)      │  │
│  │ Training: NHANES dataset (public, 20K+ samples)   │  │
│  │ Output: BiomarkerAge ± confidence interval        │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Tier 2: EpigeneticAge (methylation data required)      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Inputs: 353 CpG site methylation betas            │  │
│  │  (from user's epigenetic upload — 450K or EPIC)   │  │
│  │                                                   │  │
│  │ Models (ensemble):                                │  │
│  │  - Horvath multi-tissue clock (353 CpG sites)     │  │
│  │  - Hannum blood clock (71 CpG sites)              │  │
│  │  - PhenoAge (513 CpG sites)                       │  │
│  │  - GrimAge v2 (1030 CpG sites)                    │  │
│  │                                                   │  │
│  │ Implementation: Pre-trained weights loaded into   │  │
│  │  TensorFlow Serving; CpG → beta vector → predict  │  │
│  │ Output: EpigeneticAge ± CI, pace of aging         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Tier 3: CompositeAge (all data sources)                │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Inputs: BiomarkerAge + EpigeneticAge +            │  │
│  │  - Genome risk scores (polygenic)                 │  │
│  │  - Wearable fitness (VO2max proxy, HRV, sleep)    │  │
│  │  - Microbiome diversity (Shannon index)           │  │
│  │                                                   │  │
│  │ Model: Gradient-boosted ensemble (XGBoost)        │  │
│  │ Output: CompositeAge, domain contributions,       │  │
│  │         actionable factors ranked by impact        │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Age Acceleration Metric:**

```
age_acceleration = biological_age - chronological_age

  Negative = aging slower than average (good)
  Zero     = aging at average pace
  Positive = aging faster than average (actionable)
```

**Tracking Over Time:**

Each time the user uploads new blood data, the InnerAge is recalculated. A time-series
chart shows biological age trajectory vs. chronological age line, making it clear whether
interventions are working.

---

### 4.2 Optimized Biomarker Zones

**Inspiration:** InsideTracker doesn't just flag biomarkers as "in range" or "out of range"
using generic lab reference ranges. They compute personalized "optimized zones" based on
the user's age, sex, ethnicity, activity level, genetics, and health goals.

#### Design

**Current V1:** Blood markers flagged as H/L/N against standard lab ranges.

**V2 Personalized Zones:**

```
Standard Lab Range:     [────────────────────────────────]
                        Low                           High

Optimized Zone:              [════════════]
                             ↑             ↑
                        Optimal Low    Optimal High
                        (personalized) (personalized)

User's Value:                     ●
                              (in optimal zone)
```

**Zone Calculation Algorithm:**

```python
def compute_optimized_zone(marker_name, user_profile):
    """
    Inputs:
      - marker_name: e.g., "vitamin_d"
      - user_profile: {
          age, sex, ethnicity, bmi,
          activity_level,      # from wearable (steps/active minutes)
          genetic_variants,    # relevant SNPs (e.g., VDR for vitamin D)
          health_goals,        # ["longevity", "athletic_performance", "weight_loss"]
        }

    Process:
      1. Start with population reference (NHANES stratified by age/sex)
      2. Adjust for ethnicity (population-specific distributions)
      3. Adjust for genetic variants (e.g., FTO → stricter glucose targets)
      4. Adjust for activity level (athletes need different ranges)
      5. Adjust for health goals (longevity → tighter CRP targets)
      6. Apply research-backed optimal ranges from published literature

    Output:
      - optimal_low, optimal_high (personalized)
      - standard_low, standard_high (lab reference)
      - percentile (where user falls in their demographic)
      - status: "optimal" | "needs_improvement" | "at_risk"
      - recommendations: specific actions to reach optimal zone
    """
```

**Key Biomarkers with Personalized Zones (initial 30):**

| Category | Markers |
|----------|---------|
| Metabolic | Glucose, HbA1c, insulin, HOMA-IR |
| Lipids | Total cholesterol, LDL, HDL, triglycerides, ApoB |
| Inflammation | hs-CRP, IL-6, TNF-alpha, ferritin |
| Liver | ALT, AST, GGT, alkaline phosphatase, bilirubin |
| Kidney | Creatinine, BUN, eGFR, cystatin C |
| Vitamins | Vitamin D, B12, folate, iron, magnesium |
| Hormones | Testosterone, cortisol, DHEA-S, TSH, free T3/T4 |
| Blood Count | WBC, RBC, hemoglobin, hematocrit, platelets, MCV, RDW |

---

### 4.3 AI Health Chatbot

**Inspiration:** InsideTracker's AI assistant answers personalized health questions
using the user's own biomarker data, genetic profile, and wearable trends.

#### Design

**Architecture:**

```
User Question: "Why is my CRP elevated and what can I do?"
        │
        ▼
┌──────────────────┐
│ LangChain Agent  │
│ (GPT-4 / Claude) │
├──────────────────┤
│ System Prompt:   │
│  - You are a     │
│    health science │
│    assistant      │
│  - Use only the  │
│    user's data   │
│  - Always add    │
│    disclaimers   │
│  - Never diagnose│
└───────┬──────────┘
        │
        │  Tool calls (RAG)
        │
   ┌────┴──────────────────────────────┐
   │                                    │
   ▼                                    ▼
┌──────────────┐              ┌──────────────────┐
│ User Context │              │ Knowledge Base   │
│ Retriever    │              │ Retriever         │
│              │              │                   │
│ - Blood data │              │ - PubMed extracts│
│ - Genome     │              │ - Examine.com    │
│   variants   │              │ - NIH guidelines │
│ - Microbiome │              │ - Our correlation│
│ - Wearable   │              │   rule rationale │
│ - InnerAge   │              │                   │
│ - History    │              │ Vector DB         │
│              │              │ (pgvector)        │
└──────────────┘              └──────────────────┘
        │                              │
        └──────────────┬───────────────┘
                       ▼
              ┌────────────────┐
              │ Generated      │
              │ Response with  │
              │ citations +    │
              │ disclaimer     │
              └────────────────┘
```

**Key Design Decisions:**

1. **User-Scoped Context:** The chatbot only has access to the current user's data.
   It cannot see other users' data. Context is assembled per-query from the user's
   latest uploads across all domains.

2. **Citation-Required:** Every factual claim must reference either the user's data
   ("Your CRP is 4.5 mg/L, which is above your optimal zone of <1.0") or a
   published source ("According to a 2023 study in Nature Medicine...").

3. **Guardrails:**
   - Cannot diagnose conditions
   - Cannot recommend specific medications
   - Cannot interpret results as medical advice
   - Must include disclaimer on every response
   - Rate limited: 50 queries/day (Basic), unlimited (Premium)

4. **Conversation Memory:** Redis-backed session memory (last 20 messages per conversation,
   conversations expire after 7 days).

**Sample Interaction:**

```
User: "Why is my vitamin D low and how does it connect to my gut health?"

AI: "Your vitamin D is currently 15 ng/mL — below your personalized optimal
zone of 40-60 ng/mL (adjusted for your VDR gene variant rs2228570 and
northern latitude).

This connects to your gut health in two ways:

1. **Gut-axis methylation correlation** (Priority 88): Your SLC6A4 gene shows
   epigenetic changes, combined with low gut diversity (Shannon 2.2) and this
   low vitamin D. This pattern is associated with impaired serotonin signaling
   and gut barrier function. [Source: Your cross-domain analysis]

2. **Microbiome impact**: Vitamin D supports Lactobacillus and Bifidobacterium
   growth. Your current Bifidobacterium level is 0.8%, well below the 3-5%
   optimal range. [Source: Singh et al., 2020, Gut Microbes]

Suggested actions:
- Vitamin D3 supplementation (discuss dosage with your doctor)
- Fermented foods to support Bifidobacterium
- Retest in 8-12 weeks

⚠️ This is educational information, not medical advice."
```

---

### 4.4 Predictive Health Modeling

**Inspiration:** InsideTracker uses ML to forecast biomarker trajectories, predicting
where your health metrics are heading based on current trends, genetics, and lifestyle.

#### Design

**Prediction Engine:**

```
┌─────────────────────────────────────────────────────────┐
│              Predictive Modeling Pipeline                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Input Features (per user, per timepoint):              │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Blood: 30+ biomarker values + deltas over time    │  │
│  │ Genome: Polygenic risk scores (PRS) per trait     │  │
│  │ Wearable: 30-day rolling avg (steps, sleep, HRV)  │  │
│  │ Microbiome: Diversity + key genus abundances       │  │
│  │ Epigenetics: Methylation age acceleration          │  │
│  │ Demographics: Age, sex, BMI                        │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Model Architecture:                                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 1. Time-Series Forecasting (per biomarker):       │  │
│  │    - LSTM network (TensorFlow)                    │  │
│  │    - Input: last 4+ blood tests (timestamped)     │  │
│  │    - Output: predicted value at +3mo, +6mo, +12mo │  │
│  │    - Confidence intervals via MC dropout           │  │
│  │                                                   │  │
│  │ 2. Risk Trajectory Model:                         │  │
│  │    - XGBoost classifier                           │  │
│  │    - Input: all domain features                   │  │
│  │    - Output: P(biomarker leaves optimal zone)     │  │
│  │      at 3/6/12 month horizons                     │  │
│  │                                                   │  │
│  │ 3. Intervention Impact Model:                     │  │
│  │    - Causal forest (EconML / DoWhy)               │  │
│  │    - Input: proposed intervention + user profile   │  │
│  │    - Output: estimated effect size on each         │  │
│  │      biomarker (e.g., "Vitamin D supplementation  │  │
│  │      predicted to raise your level by 15 ng/mL    │  │
│  │      in 8 weeks based on your genetics")          │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  Training Data:                                         │
│  - NHANES longitudinal cohorts (public, de-identified)  │
│  - UK Biobank summary statistics (public)               │
│  - Platform user data (opt-in, de-identified)           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Minimum Data Requirements:**

| Prediction Type | Minimum Data |
|----------------|--------------|
| Biomarker forecast | 2+ blood uploads (separated by 30+ days) |
| Risk trajectory | 2+ blood uploads + genome OR wearable data |
| Intervention impact | 1+ blood upload + genome data |
| Biological age trend | 3+ blood uploads (separated by 60+ days) |

---

### 4.5 Healthspan Habit Reports

**Inspiration:** InsideTracker generates weekly habit reports from wearable data, scoring
users on sleep quality, activity, stress management, and recovery — all tied back to
their biomarker goals.

#### Design

**Weekly Healthspan Report (auto-generated every Monday):**

```
┌──────────────────────────────────────────────────────┐
│         Weekly Healthspan Report                      │
│         Feb 24 – Mar 2, 2026                         │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Overall Healthspan Score: 62/100  (↑4 from last wk)│
│                                                      │
│  ┌─────────────┬──────┬────────┬──────────────────┐  │
│  │ Habit       │Score │ Trend  │ Biomarker Link   │  │
│  ├─────────────┼──────┼────────┼──────────────────┤  │
│  │ Movement    │ 45   │ ↓      │ HbA1c, CRP      │  │
│  │ Sleep       │ 58   │ ↑      │ Cortisol, HRV   │  │
│  │ Recovery    │ 52   │ →      │ CRP, IL-6        │  │
│  │ Stress Mgmt │ 40   │ ↓      │ Cortisol, DHEA  │  │
│  │ Consistency │ 78   │ ↑      │ All metabolic    │  │
│  └─────────────┴──────┴────────┴──────────────────┘  │
│                                                      │
│  Key Insight: "Your average 3,500 steps/day is      │
│  contributing to your FTO obesity loop correlation.  │
│  Increasing to 7,000 steps could improve your HbA1c │
│  by an estimated 0.3% over 12 weeks."               │
│                                                      │
│  This Week's Focus: Movement                         │
│  Target: 6,000 steps/day (gradual increase)          │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**Habit Scoring Algorithm:**

```python
def compute_habit_scores(wearable_week, user_profile, biomarker_goals):
    """
    Movement Score (0-100):
      - Steps vs. target (age/fitness-adjusted)
      - Active minutes vs. WHO guidelines (150 min/week)
      - Calories burned vs. estimated TDEE

    Sleep Score (0-100):
      - Total sleep vs. optimal (7-9 hours)
      - Deep sleep % vs. target (15-20%)
      - Sleep consistency (bedtime variance)
      - Sleep efficiency (time asleep / time in bed)

    Recovery Score (0-100):
      - Resting HRV vs. personal baseline
      - Resting heart rate trend
      - SpO2 stability

    Stress Management Score (0-100):
      - Stress score from wearable (if available)
      - HRV during waking hours
      - Recovery-to-stress ratio

    Consistency Score (0-100):
      - Days meeting movement target / 7
      - Sleep schedule regularity (stddev of bedtime)
      - Consecutive days with all habits tracked
    """
```

**Celery Task:** `generate_weekly_healthspan_report` — runs Monday 05:00 UTC via Celery Beat.

---

## 5. Unified Healthspan Platform

### 5.1 Healthspan Dashboard

The new dashboard is the centerpiece of V2 — a single view that synthesizes all domains
into an actionable healthspan picture.

```
┌──────────────────────────────────────────────────────────────────┐
│  GenomeInsight — Healthspan Dashboard                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐      │
│  │              Your Biological Age: 34.2                 │      │
│  │              Chronological Age:   41                   │      │
│  │              ─────────────────────────                 │      │
│  │              You're aging 6.8 years slower             │      │
│  │                                                       │      │
│  │  [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░]  34.2 / 41       │      │
│  │                                                       │      │
│  │  Trend: ↓ 0.4 years since last test (improving)       │      │
│  └────────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Healthspan│ │Biomarkers│ │Predictions│ │ Genomic  │           │
│  │Score: 62 │ │Optimal:  │ │Next 6mo: │ │ Risk:    │           │
│  │  /100    │ │ 18/30    │ │ 3 alerts │ │ 2 high   │           │
│  │  ↑4      │ │  ↑2      │ │          │ │ 5 mod    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  ── Top 3 Actions This Week ──────────────────────────────      │
│                                                                  │
│  1. 🏃 Increase daily steps to 6,000 (currently 3,500)          │
│     Impact: HbA1c ↓0.3%, CRP ↓0.5 mg/L predicted               │
│                                                                  │
│  2. 💊 Discuss vitamin D supplementation with your doctor        │
│     Impact: Gut diversity ↑, mood biomarkers ↑ predicted         │
│                                                                  │
│  3. 😴 Improve sleep consistency (±30 min bedtime window)        │
│     Impact: Cortisol ↓, HRV ↑ predicted                         │
│                                                                  │
│  ── Cross-Domain Correlations (12 active) ─────────────────     │
│  [Sorted by priority, with colored severity cards...]            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 New Cross-Domain Correlation Rules (V2 additions)

Expanding from 9 rules in V1 to 15+ in V2:

| Rule ID | Domains | Trigger | New in V2 |
|---------|---------|---------|-----------|
| `oral_gut_axis` | oral + gut microbiome | Shared pathogenic taxa | Yes |
| `oral_inflammation` | oral + blood + epigenetics | P. gingivalis + high CRP + TNF | Yes |
| `oral_genome_perio` | oral + genome | IL-1 variant + periodontal pathogens | Yes |
| `aging_acceleration` | blood + epigenetics + wearable | BioAge accelerating + poor habits | Yes |
| `longevity_genome_habits` | genome + wearable + blood | FOXO3 variant + good habits → quantify benefit | Yes |
| `metabolic_prediction` | blood + genome + wearable | FTO + declining HbA1c trend + low activity | Yes |
| (9 existing V1 rules) | Various | Various | No |

---

## 6. New Data Models

### 6.1 Subscription Model

```python
class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(UUID, primary_key=True, default=uuid4)
    user_id = db.Column(UUID, db.ForeignKey("users.id"), nullable=False, index=True)
    tier = db.Column(db.String(20), nullable=False)
        # "free" | "basic" | "premium"
    status = db.Column(db.String(20), nullable=False, default="active")
        # "active" | "past_due" | "canceled" | "trialing"
    stripe_customer_id = db.Column(db.String(255), unique=True)
    stripe_subscription_id = db.Column(db.String(255), unique=True)
    current_period_start = db.Column(db.DateTime(timezone=True))
    current_period_end = db.Column(db.DateTime(timezone=True))
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    trial_end = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    user = db.relationship("User", backref="subscription", uselist=False)
```

### 6.2 Biological Age Model

```python
class BiologicalAge(db.Model):
    __tablename__ = "biological_ages"

    id = db.Column(UUID, primary_key=True, default=uuid4)
    user_id = db.Column(UUID, db.ForeignKey("users.id"), nullable=False, index=True)
    chronological_age = db.Column(db.Float, nullable=False)
    biomarker_age = db.Column(db.Float)          # Tier 1: blood-only
    epigenetic_age = db.Column(db.Float)          # Tier 2: methylation clock
    composite_age = db.Column(db.Float)           # Tier 3: all-domain ensemble
    age_acceleration = db.Column(db.Float)        # composite - chronological
    confidence_interval = db.Column(db.Float)     # ± years
    model_version = db.Column(db.String(20), nullable=False)
    factors_json = db.Column(db.JSON)
        # { "top_aging_factors": [...], "top_protective_factors": [...],
        #   "domain_contributions": { "blood": 0.35, "epigenetic": 0.40, ... } }
    blood_upload_id = db.Column(UUID, db.ForeignKey("blood_uploads.id"))
    epigenetic_upload_id = db.Column(UUID, db.ForeignKey("epigenetic_uploads.id"))
    calculated_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    user = db.relationship("User", backref="biological_ages")
```

### 6.3 Predictive Model

```python
class HealthPrediction(db.Model):
    __tablename__ = "health_predictions"

    id = db.Column(UUID, primary_key=True, default=uuid4)
    user_id = db.Column(UUID, db.ForeignKey("users.id"), nullable=False, index=True)
    prediction_type = db.Column(db.String(30), nullable=False)
        # "biomarker_forecast" | "risk_trajectory" | "intervention_impact"
    model_version = db.Column(db.String(20), nullable=False)
    input_summary_json = db.Column(db.JSON)
        # { "blood_uploads_used": [...], "wearable_days": 90, ... }
    forecasts_json = db.Column(db.JSON)
        # { "vitamin_d": { "3mo": 22.5, "6mo": 35.1, "12mo": 42.0,
        #                   "ci_low": [...], "ci_high": [...] },
        #   "hba1c": { ... } }
    risk_alerts_json = db.Column(db.JSON)
        # [ { "marker": "hba1c", "horizon": "6mo",
        #     "probability_leaves_optimal": 0.72,
        #     "current_trend": "worsening" } ]
    generated_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    expires_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", backref="health_predictions")
```

### 6.4 Healthspan Habit Report Model

```python
class HealthspanReport(db.Model):
    __tablename__ = "healthspan_reports"

    id = db.Column(UUID, primary_key=True, default=uuid4)
    user_id = db.Column(UUID, db.ForeignKey("users.id"), nullable=False, index=True)
    week_start = db.Column(db.Date, nullable=False)
    week_end = db.Column(db.Date, nullable=False)
    overall_score = db.Column(db.Integer)           # 0-100
    movement_score = db.Column(db.Integer)
    sleep_score = db.Column(db.Integer)
    recovery_score = db.Column(db.Integer)
    stress_score = db.Column(db.Integer)
    consistency_score = db.Column(db.Integer)
    scores_json = db.Column(db.JSON)                # detailed breakdown
    insights_json = db.Column(db.JSON)              # weekly insights
    focus_area = db.Column(db.String(50))           # "movement" | "sleep" | etc.
    biomarker_links_json = db.Column(db.JSON)       # habit → biomarker connections
    generated_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint("user_id", "week_start"),
    )

    user = db.relationship("User", backref="healthspan_reports")
```

### 6.5 WGS Upload Model (extends existing GenomeUpload)

```python
class WGSUpload(db.Model):
    __tablename__ = "wgs_uploads"

    id = db.Column(UUID, primary_key=True, default=uuid4)
    user_id = db.Column(UUID, db.ForeignKey("users.id"), nullable=False, index=True)
    file_format = db.Column(db.String(10), nullable=False)
        # "fastq" | "bam" | "cram"
    file_paths_json = db.Column(db.JSON)
        # { "r1": "s3://bucket/path/R1.fastq.gz",
        #   "r2": "s3://bucket/path/R2.fastq.gz" }  (for FASTQ)
        # or { "bam": "s3://...", "bai": "s3://..." } (for BAM)
    sequencing_depth = db.Column(db.String(10))     # "30x" | "100x"
    genome_build = db.Column(db.String(10), default="GRCh38")
    total_reads = db.Column(db.BigInteger)
    mean_coverage = db.Column(db.Float)
    pct_bases_20x = db.Column(db.Float)
    file_size_bytes = db.Column(db.BigInteger)
    upload_method = db.Column(db.String(20))        # "tus_chunked" | "presigned_url"
    status = db.Column(db.String(20), default="uploading")
        # "uploading" | "uploaded" | "aligning" | "calling" | "analyzing" | "complete" | "error"
    genome_upload_id = db.Column(UUID, db.ForeignKey("genome_uploads.id"))
        # Links to VCF-based GenomeUpload once variants are called
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    completed_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", backref="wgs_uploads")
```

### 6.6 Ancestry Model

```python
class AncestryResult(db.Model):
    __tablename__ = "ancestry_results"

    id = db.Column(UUID, primary_key=True, default=uuid4)
    user_id = db.Column(UUID, db.ForeignKey("users.id"), nullable=False, index=True)
    wgs_upload_id = db.Column(UUID, db.ForeignKey("wgs_uploads.id"))
    maternal_haplogroup = db.Column(db.String(30))      # e.g., "H1a1"
    paternal_haplogroup = db.Column(db.String(30))      # e.g., "R1b1a1a2" (null if XX)
    ancestry_composition_json = db.Column(db.JSON)
        # { "European": 0.62, "East African": 0.25, "South Asian": 0.13, ... }
    neanderthal_pct = db.Column(db.Float)
    denisovan_pct = db.Column(db.Float)
    migration_events_json = db.Column(db.JSON)
        # [ { "period": "45000 years ago", "from": "Africa", "to": "Middle East" }, ... ]
    pca_coordinates_json = db.Column(db.JSON)           # for ancestry plot
    model_version = db.Column(db.String(20))
    calculated_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    user = db.relationship("User", backref="ancestry_results")
```

### 6.7 Blockchain Data Ownership Model

```python
class DataOwnershipToken(db.Model):
    __tablename__ = "data_ownership_tokens"

    id = db.Column(UUID, primary_key=True, default=uuid4)
    user_id = db.Column(UUID, db.ForeignKey("users.id"), nullable=False, index=True)
    token_id = db.Column(db.Integer, unique=True)       # ERC-721 token ID on-chain
    data_hash = db.Column(db.String(66), nullable=False) # SHA-256 of underlying data
    resource_type = db.Column(db.String(30), nullable=False)
        # "genome" | "wgs" | "blood" | "microbiome" | "epigenetics"
    resource_id = db.Column(UUID, nullable=False)
    wallet_address = db.Column(db.String(42))           # user's Ethereum address
    contract_address = db.Column(db.String(42))
    tx_hash = db.Column(db.String(66))                  # minting transaction
    chain_id = db.Column(db.Integer)
    anonymous_id = db.Column(db.String(66))             # pseudonymous identifier
    status = db.Column(db.String(20), default="minted")
        # "minting" | "minted" | "burned"
    minted_at = db.Column(db.DateTime(timezone=True))
    burned_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", backref="data_ownership_tokens")
```

### 6.8 Chat Session Model

```python
class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(UUID, primary_key=True, default=uuid4)
    user_id = db.Column(UUID, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(200))
    messages_json = db.Column(db.JSON, default=list)
        # [ { "role": "user", "content": "...", "timestamp": "..." },
        #   { "role": "assistant", "content": "...", "citations": [...] } ]
    context_snapshot_json = db.Column(db.JSON)
        # snapshot of user data at session start for reproducibility
    message_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    last_message_at = db.Column(db.DateTime(timezone=True))
    expires_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", backref="chat_sessions")
```

### 6.9 User Profile Extension

```python
# Added columns to existing User model:
date_of_birth = db.Column(db.Date)                  # for chronological age
sex = db.Column(db.String(10))                       # "male" | "female" | "other"
ethnicity = db.Column(db.String(50))                 # for population-adjusted zones
health_goals_json = db.Column(db.JSON, default=list)
    # ["longevity", "athletic_performance", "weight_loss", "stress_reduction"]
anonymous_mode = db.Column(db.Boolean, default=False)
wallet_address = db.Column(db.String(42))            # Ethereum address (optional)
```

---

## 7. New API Endpoints

### V2 Endpoints (added to existing V1 API)

#### WGS & Genome Browser

| Method | Path | Description | Tier |
|--------|------|-------------|------|
| POST | `/api/v2/wgs/upload/init` | Initialize chunked WGS upload (tus) | Premium |
| GET | `/api/v2/wgs/uploads` | List WGS uploads | Basic+ |
| GET | `/api/v2/wgs/uploads/<id>` | WGS upload status + pipeline progress | Basic+ |
| GET | `/api/v2/genome-browser/tracks` | Available tracks for user | Basic+ |
| GET | `/api/v2/genome-browser/variants` | Variants in genomic region | Basic+ |
| GET | `/api/v2/genome-browser/annotations` | ClinVar/gene annotations in region | Basic+ |
| GET | `/api/v2/variant-search` | Search by rsID, gene, or region | Basic+ |

#### Biological Age & Predictions

| Method | Path | Description | Tier |
|--------|------|-------------|------|
| GET | `/api/v2/inner-age` | Latest biological age calculation | Basic+ |
| GET | `/api/v2/inner-age/history` | Biological age over time | Basic+ |
| POST | `/api/v2/inner-age/calculate` | Force recalculation | Premium |
| GET | `/api/v2/predictions` | Latest health predictions | Premium |
| POST | `/api/v2/predictions/generate` | Generate new predictions | Premium |
| POST | `/api/v2/predictions/simulate` | Simulate intervention impact | Premium |
| GET | `/api/v2/biomarker-zones` | Personalized optimal zones for all markers | Basic+ |
| GET | `/api/v2/biomarker-zones/<marker>` | Single marker zone + recommendations | Basic+ |

#### AI Chatbot

| Method | Path | Description | Tier |
|--------|------|-------------|------|
| POST | `/api/v2/ai-chat` | Send message, get AI response | Basic (50/day) / Premium (unlimited) |
| GET | `/api/v2/ai-chat/sessions` | List chat sessions | Basic+ |
| GET | `/api/v2/ai-chat/sessions/<id>` | Get chat history | Basic+ |
| DELETE | `/api/v2/ai-chat/sessions/<id>` | Delete chat session | Basic+ |

#### Subscription

| Method | Path | Description | Tier |
|--------|------|-------------|------|
| GET | `/api/v2/subscription` | Current subscription status | Free+ |
| POST | `/api/v2/subscription/checkout` | Create Stripe checkout session | Free+ |
| POST | `/api/v2/subscription/portal` | Create Stripe billing portal session | Basic+ |
| POST | `/api/v2/subscription/webhook` | Stripe webhook handler | System |
| GET | `/api/v2/subscription/usage` | Feature usage (queries, uploads remaining) | Free+ |

#### Healthspan & Habits

| Method | Path | Description | Tier |
|--------|------|-------------|------|
| GET | `/api/v2/healthspan/dashboard` | Unified healthspan dashboard data | Basic+ |
| GET | `/api/v2/healthspan/report` | Latest weekly habit report | Basic+ |
| GET | `/api/v2/healthspan/reports` | Weekly report history | Basic+ |
| GET | `/api/v2/healthspan/score` | Current healthspan score breakdown | Basic+ |

#### Ancestry

| Method | Path | Description | Tier |
|--------|------|-------------|------|
| GET | `/api/v2/ancestry` | Ancestry composition + haplogroups | Basic+ |
| GET | `/api/v2/ancestry/migration` | Ancestral migration timeline | Premium |
| GET | `/api/v2/ancestry/neanderthal` | Archaic introgression details | Premium |

#### Blockchain & Privacy

| Method | Path | Description | Tier |
|--------|------|-------------|------|
| POST | `/api/v2/blockchain/mint` | Mint data ownership token | Premium |
| GET | `/api/v2/blockchain/tokens` | List user's ownership tokens | Premium |
| POST | `/api/v2/blockchain/consent` | Record consent on-chain | Premium |
| DELETE | `/api/v2/blockchain/consent` | Revoke consent | Premium |
| GET | `/api/v2/blockchain/audit-trail` | On-chain access log | Premium |
| POST | `/api/v2/privacy/anonymous-mode` | Enable/disable anonymous mode | Premium |

**Total new endpoints: 32**
**Total platform endpoints: 35 (V1) + 32 (V2) = 67+**

---

## 8. ML Module Design

### Architecture

The ML module runs as a **separate FastAPI microservice** with TensorFlow Serving for
model inference. This keeps heavy ML dependencies out of the Flask API.

```
┌─────────────────────────────────────────────────┐
│            ML Service (FastAPI)                   │
│            Port 8000                              │
├─────────────────────────────────────────────────┤
│                                                  │
│  /predict/biomarker-age                          │
│    Input: 9 PhenoAge biomarker values            │
│    Model: Elastic Net (sklearn, ~50KB)           │
│    Output: age estimate + CI                     │
│                                                  │
│  /predict/epigenetic-age                         │
│    Input: 353+ CpG beta values                   │
│    Model: Horvath/PhenoAge weights (TF Serving)  │
│    Output: 4 clock estimates + ensemble          │
│                                                  │
│  /predict/composite-age                          │
│    Input: bio_age + epi_age + PRS + wearable     │
│    Model: XGBoost ensemble (~2MB)                │
│    Output: composite age + factor contributions  │
│                                                  │
│  /predict/biomarker-forecast                     │
│    Input: time-series of biomarker values        │
│    Model: LSTM (TF Serving, ~15MB)               │
│    Output: 3/6/12 month predictions + CI         │
│                                                  │
│  /predict/risk-trajectory                        │
│    Input: all-domain feature vector              │
│    Model: XGBoost classifier (~5MB)              │
│    Output: P(leaving optimal) per marker         │
│                                                  │
│  /predict/intervention-impact                    │
│    Input: intervention type + user features      │
│    Model: Causal forest (EconML, ~10MB)          │
│    Output: estimated effect sizes                │
│                                                  │
│  /compute/optimized-zones                        │
│    Input: marker_name + user_profile             │
│    Algorithm: NHANES-based + genetic adjustments │
│    Output: optimal_low, optimal_high, percentile │
│                                                  │
│  /health                                         │
│    Readiness check for all models                │
│                                                  │
├─────────────────────────────────────────────────┤
│  Model Store: /models/                           │
│    biomarker_age_v1.pkl     (Elastic Net)        │
│    horvath_clock_v1/        (TF SavedModel)      │
│    phenoage_clock_v1/       (TF SavedModel)      │
│    grimage_clock_v2/        (TF SavedModel)      │
│    composite_age_v1.xgb     (XGBoost)            │
│    biomarker_lstm_v1/       (TF SavedModel)      │
│    risk_trajectory_v1.xgb   (XGBoost)            │
│    intervention_forest_v1/  (EconML)             │
│                                                  │
│  Total model size: ~50 MB                        │
│  Container memory: 4 GB                          │
│  GPU: not required (CPU inference sufficient)    │
└─────────────────────────────────────────────────┘
```

### Model Training Pipeline (offline, not in Docker)

```
Training Data Sources:
  - NHANES (public, ~30K longitudinal samples with blood + demographics)
  - UK Biobank summary statistics (public, population-level)
  - GEO/ArrayExpress (public methylation datasets, 450K/EPIC)
  - Platform opt-in data (future, privacy-preserving federated learning)

Training Schedule:
  - Models retrained quarterly with new data
  - Version-tagged (v1, v2, ...) with A/B rollout
  - Evaluation: MAE for age models, AUROC for risk models
```

### Python Dependencies (ML Service)

```
tensorflow==2.16.*
tensorflow-serving-api==2.16.*
scikit-learn==1.5.*
xgboost==2.1.*
econml==0.15.*
fastapi==0.115.*
uvicorn==0.32.*
numpy==1.26.*
pandas==2.2.*
```

---

## 9. Blockchain Integration

### Smart Contracts (Solidity)

**DataOwnershipToken.sol** — ERC-721 with access control:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract DataOwnershipToken is ERC721, Ownable {
    struct AccessEntry {
        address grantee;
        uint256 grantedAt;
        uint256 expiresAt;
        string purpose;
        bool revoked;
    }

    mapping(uint256 => bytes32) public dataHashes;
    mapping(uint256 => AccessEntry[]) public accessLogs;
    uint256 private _nextTokenId;

    event AccessGranted(uint256 indexed tokenId, address indexed grantee, string purpose);
    event AccessRevoked(uint256 indexed tokenId, address indexed grantee);
    event DataBurned(uint256 indexed tokenId, address indexed owner);

    function mint(address to, bytes32 dataHash) external onlyOwner returns (uint256) {
        uint256 tokenId = _nextTokenId++;
        _safeMint(to, tokenId);
        dataHashes[tokenId] = dataHash;
        return tokenId;
    }

    function grantAccess(uint256 tokenId, address grantee, uint256 duration, string calldata purpose) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        accessLogs[tokenId].push(AccessEntry({
            grantee: grantee,
            grantedAt: block.timestamp,
            expiresAt: block.timestamp + duration,
            purpose: purpose,
            revoked: false
        }));
        emit AccessGranted(tokenId, grantee, purpose);
    }

    function revokeAccess(uint256 tokenId, uint256 entryIndex) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        accessLogs[tokenId][entryIndex].revoked = true;
        emit AccessRevoked(tokenId, accessLogs[tokenId][entryIndex].grantee);
    }

    function burn(uint256 tokenId) external {
        require(ownerOf(tokenId) == msg.sender, "Not token owner");
        _burn(tokenId);
        delete dataHashes[tokenId];
        emit DataBurned(tokenId, msg.sender);
    }
}
```

### Backend Integration (Web3.py)

```python
# blockchain_service.py — runs as Flask microservice on port 8001

from web3 import Web3
from eth_account import Account

class BlockchainService:
    def __init__(self, rpc_url, contract_address, contract_abi, owner_key):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.contract = self.w3.eth.contract(
            address=contract_address, abi=contract_abi
        )
        self.owner_account = Account.from_key(owner_key)

    def mint_token(self, user_wallet: str, data_sha256: str) -> dict:
        """Mint a DataOwnershipToken for user's data."""
        # Build transaction, sign with owner key, send, wait for receipt
        # Return: { token_id, tx_hash, block_number }

    def verify_ownership(self, wallet: str, token_id: int) -> bool:
        """Check if wallet owns the given token."""
        return self.contract.functions.ownerOf(token_id).call() == wallet

    def generate_anonymous_id(self, user_id: str, salt: str) -> str:
        """Deterministic pseudonym from user_id + salt."""
        return Web3.keccak(text=f"{user_id}:{salt}").hex()
```

### Deployment

- Contracts deployed on **Sepolia testnet** (free ETH from faucets)
- Backend uses **Infura** or **Alchemy** as RPC provider (no self-hosted node needed)
- Gas costs: Sepolia testnet ETH is free; mainnet migration requires cost analysis
- Contract addresses stored in environment variables

---

## 10. Subscription Service

### Tier Structure

| Feature | Free | Basic ($19/mo) | Premium ($49/mo) |
|---------|------|----------------|-------------------|
| VCF upload (SNP chip) | 1 | Unlimited | Unlimited |
| WGS upload (FASTQ/BAM) | — | — | Unlimited |
| Blood uploads | 1 | Unlimited | Unlimited |
| Microbiome uploads | — | 2/year | Unlimited |
| Wearable connections | 1 device | 3 devices | Unlimited |
| Biomarker zones | Standard lab ranges | Personalized zones | Personalized + predictions |
| Biological age | — | BiomarkerAge (Tier 1) | CompositeAge (all 3 tiers) |
| Cross-domain correlations | Top 3 only | All | All + new V2 rules |
| AI chatbot | — | 50 queries/day | Unlimited |
| Predictions | — | — | 3/6/12 month forecasts |
| Healthspan reports | — | Monthly | Weekly |
| Genome browser | — | View only | Full search + export |
| Ancestry | — | Basic composition | Deep (Y-DNA, mtDNA, migration) |
| Blockchain privacy | — | — | Data ownership tokens + anonymous mode |
| Data export | VCF only | All formats | All formats + API access |
| Report updates | — | Monthly | Weekly |

### Stripe Integration Architecture

```
User clicks "Upgrade to Premium"
        │
        ▼
POST /api/v2/subscription/checkout
  → Create Stripe Checkout Session
  → Redirect user to Stripe-hosted payment page
        │
        ▼
User completes payment on Stripe
        │
        ▼
Stripe sends webhook → POST /api/v2/subscription/webhook
  → Events handled:
     checkout.session.completed → activate subscription
     invoice.payment_succeeded → renew period
     invoice.payment_failed → set status "past_due"
     customer.subscription.deleted → set status "canceled"
        │
        ▼
Subscription middleware checks tier on every API request
  → @require_tier("premium") decorator on endpoints
  → Returns 403 with upgrade prompt if tier insufficient
```

### Subscription-Aware Middleware

```python
def require_tier(*allowed_tiers):
    """Decorator: restrict endpoint to users with given subscription tier(s)."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            sub = user.subscription
            if not sub or sub.tier not in allowed_tiers:
                return jsonify({
                    "error": "subscription_required",
                    "required_tier": allowed_tiers,
                    "current_tier": sub.tier if sub else "free",
                    "upgrade_url": "/subscribe"
                }), 403
            if sub.status not in ("active", "trialing"):
                return jsonify({"error": "subscription_inactive"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 11. Updated Frontend

### New React Components

| Component | Description | Tier |
|-----------|-------------|------|
| `HealthspanDashboard.js` | Unified dashboard (bio age, scores, actions, predictions) | Basic+ |
| `InnerAge.js` | Biological age display, trend chart, factor breakdown | Basic+ |
| `BiomarkerZones.js` | Visual biomarker ranges with personalized optimal zones | Basic+ |
| `GenomeBrowser.js` | JBrowse 2 React wrapper for genome visualization | Basic+ |
| `VariantSearch.js` | Gene/variant/region search with autocomplete | Basic+ |
| `AIChatbot.js` | Chat interface with streaming responses | Basic+ |
| `PredictionCards.js` | Biomarker forecast cards with trend arrows | Premium |
| `AncestryMap.js` | Interactive map with haplogroups and migration routes | Basic+ |
| `HealthspanReport.js` | Weekly habit report with scores and biomarker links | Basic+ |
| `SubscriptionGate.js` | Paywall component with tier comparison | Free+ |
| `SubscriptionManage.js` | Billing portal, plan change, cancel | Basic+ |
| `BlockchainWallet.js` | Connect wallet, view tokens, manage consent | Premium |
| `AnonymousMode.js` | Toggle anonymous mode, view pseudonym | Premium |
| `OralMicrobiome.js` | Oral microbiome report (extends existing Microbiome) | Basic+ |
| `WGSUpload.js` | Chunked WGS file upload with progress | Premium |

### Wabi Sabi Design Continuity

All new components follow the existing Wabi Sabi design system:
- Earth-tone palette (#F5F5F0 background, #5C4B3F headers, #8B9A7F accents)
- Crimson Text serif for headings, Inter sans-serif for body
- Asymmetric border-radius (12px 4px 12px 4px)
- Frosted glass cards with backdrop-filter
- Ink-wash dividers and organic wave separators
- Imperfect, warm, natural aesthetic throughout

### New wabiSabi.js Theme Additions

```javascript
// New color tokens for V2 features
biologicalAge: {
  younger: '#8B9A7F',      // sage green — aging slower
  neutral: '#C4A882',      // warm gold — aging at pace
  older: '#A0786E',        // terracotta — aging faster
},
subscription: {
  free: '#A8A8A8',         // stone gray
  basic: '#8B9A7F',        // sage green
  premium: '#C4A882',      // warm gold
},
prediction: {
  improving: '#8B9A7F',
  stable: '#C4A882',
  worsening: '#A0786E',
},
```

---

## 12. Security Enhancements

### Blockchain Data Ownership
- ERC-721 tokens provide cryptographic proof of data ownership
- Immutable on-chain audit trail of every access grant/revocation
- GDPR right-to-erasure implemented via token burn + cascade delete

### Anonymous Mode
- Deterministic pseudonym derived from user_id + per-deployment salt
- All API responses strip PII when anonymous mode enabled
- Audit logs reference pseudonym only
- Subscription validation via zero-knowledge proof (future: zk-SNARKs)

### ML Model Security
- Models served read-only (no training data in production)
- Input validation prevents adversarial inputs
- Model versioning with rollback capability
- No user data stored in ML service (stateless inference)

### WGS File Security
- S3 server-side encryption with customer-managed keys (SSE-C)
- Chunked upload with per-chunk SHA-256 integrity verification
- Signed URLs expire after 1 hour for downloads
- WGS files auto-archived to cold storage after 30 days

### Subscription Security
- Stripe handles all payment data (PCI DSS compliant)
- Webhook signature verification (Stripe-Signature header)
- Rate limiting on subscription endpoints
- Grace period for failed payments (3 retry attempts over 7 days)

---

## 13. Infrastructure Changes

### Updated Docker Compose (10 services)

```yaml
services:
  # ── Existing V1 (unchanged) ──
  genomeinsight-api:        # Flask API (port 5000)
  genomeinsight-web:        # React frontend (port 80)
  genomeinsight-redis:      # Redis broker/cache (port 6379)
  genomeinsight-celery:     # Standard Celery worker
  genomeinsight-celery-beat: # Celery Beat scheduler

  # ── New V2 ──
  genomeinsight-ml:
    build: ./ml-service
    ports: ["8000:8000"]
    volumes: ["./models:/models:ro"]
    deploy:
      resources:
        limits: { memory: 4G }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]

  genomeinsight-blockchain:
    build: ./blockchain-service
    ports: ["8001:8001"]
    environment:
      - ETHEREUM_RPC_URL
      - CONTRACT_OWNER_KEY
      - DOT_CONTRACT_ADDR

  genomeinsight-minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    volumes: ["minio-data:/data"]
    environment:
      - MINIO_ROOT_USER
      - MINIO_ROOT_PASSWORD

  genomeinsight-celery-wgs:
    build: ./backend
    command: celery -A celery_worker.celery worker -Q wgs --concurrency=1
    deploy:
      resources:
        limits: { memory: 32G }
    volumes: ["wgs-temp:/tmp/wgs"]

  genomeinsight-chatbot:
    build: ./chatbot-service
    ports: ["8002:8002"]
    environment:
      - ANTHROPIC_API_KEY
      - OPENAI_API_KEY
```

### New Celery Queues

| Queue | Worker | Concurrency | Memory | Purpose |
|-------|--------|-------------|--------|---------|
| `default` | celery | 4 | 2 GB | Standard tasks |
| `analysis` | celery | 4 | 2 GB | Genome/blood/microbiome analysis |
| `wearables` | celery | 4 | 2 GB | Wearable sync |
| `insights` | celery | 4 | 2 GB | Daily insights |
| `wgs` | celery-wgs | 1 | 32 GB | WGS alignment + variant calling |
| `ml` | celery | 2 | 4 GB | ML predictions (calls ML service) |
| `blockchain` | celery | 2 | 1 GB | Token minting, consent recording |

### New Celery Beat Schedule

| Task | Schedule | Queue |
|------|----------|-------|
| `generate_weekly_healthspan_report` | Monday 05:00 UTC | insights |
| `refresh_predictions` | Wednesday 03:00 UTC | ml |
| `recalculate_biological_ages` | After blood upload (event) | ml |
| `update_biomarker_zones` | After blood upload (event) | ml |
| `archive_wgs_to_cold_storage` | Daily 02:00 UTC | wgs |
| `sync_subscription_status` | Every 6 hours | default |

---

## 14. Migration Strategy

### Phase 1: Foundation (Weeks 1-4)
- Add new data models (Subscription, BiologicalAge, HealthPrediction, etc.)
- Implement Stripe subscription with free/basic/premium tiers
- Add subscription middleware to existing endpoints
- Add User profile extensions (DOB, sex, ethnicity, health goals)
- Database migration scripts (Alembic)

### Phase 2: ML & Predictions (Weeks 5-8)
- Build ML microservice (FastAPI + TensorFlow Serving)
- Train BiomarkerAge model on NHANES data
- Implement personalized biomarker zones
- Build InnerAge calculation pipeline
- Add prediction endpoints

### Phase 3: WGS & Genome Browser (Weeks 9-12)
- Set up MinIO object storage
- Implement chunked upload (tus protocol)
- Build WGS alignment pipeline (minimap2 → VCF)
- Integrate JBrowse 2 React genome browser
- Add variant search with autocomplete
- Build ancestry pipeline (haplogroups + PCA)

### Phase 4: AI & Blockchain (Weeks 13-16)
- Build chatbot microservice (LangChain + Claude/GPT-4)
- Implement RAG with user context + knowledge base
- Deploy smart contracts to Sepolia testnet
- Build blockchain service (Web3.py)
- Implement data ownership tokens + anonymous mode

### Phase 5: Healthspan Dashboard (Weeks 17-20)
- Build unified healthspan dashboard
- Implement weekly habit reports
- Add new cross-domain correlation rules (V2 additions)
- Build oral microbiome pipeline (from WGS unmapped reads)
- Comprehensive frontend updates (15 new components)

### Phase 6: Polish & Launch (Weeks 21-24)
- Integration testing across all services
- Performance optimization (caching, query optimization)
- Security audit (penetration testing, smart contract audit)
- Target: 600+ tests
- Documentation and API reference
- Staged rollout (beta users → general availability)

---

## Appendix A: Technology Stack Summary

| Layer | V1 | V2 Additions |
|-------|-----|--------------|
| Frontend | React 18, MUI, Tailwind | + JBrowse 2, Web3.js, LangChain.js |
| API | Flask, SQLAlchemy, JWT | + FastAPI (ML), Stripe SDK, tus |
| ML | — | TensorFlow, scikit-learn, XGBoost, EconML |
| Blockchain | — | Solidity, Web3.py, OpenZeppelin, Infura |
| AI | OpenAI (reports) | + LangChain, pgvector, Claude/GPT-4 (chatbot) |
| Storage | SQLite/PostgreSQL, disk | + MinIO (S3-compatible), cold archive |
| Bioinformatics | VCF parsing | + minimap2, samtools, bcftools, Manta, haplogrep3 |
| Payments | — | Stripe (Checkout, Billing Portal, Webhooks) |
| Infrastructure | Docker Compose (5 svc) | Docker Compose (10 svc), 32 GB WGS worker |

## Appendix B: Test Coverage Targets

| Module | V1 Tests | V2 Target |
|--------|----------|-----------|
| Auth + Users | 45 | 60 |
| Genome + WGS | 65 | 100 |
| Blood + Zones | 50 | 80 |
| Microbiome (gut + oral) | 55 | 75 |
| Epigenetics | 45 | 55 |
| Wearables | 40 | 50 |
| Correlator | 45 | 65 |
| ML Service | — | 40 |
| Blockchain | — | 30 |
| Subscription | — | 25 |
| Chatbot | — | 20 |
| Integration | 20 | 40 |
| **Total** | **385** | **640** |

---

*This document is a design blueprint. No code has been written for V2 features yet.
All V1 functionality (385 tests, 9 correlation rules, 5 domains, 35+ endpoints) remains
intact and is the foundation upon which V2 builds.*