# GenomeInsight — Microbiome Module Design

## 1. Architecture Overview

```
GenomeInsight/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── microbiome.py          # NEW — Blueprint: upload, list, analysis, correlate-all
│   │   │   ├── auth.py
│   │   │   ├── genome.py
│   │   │   ├── blood.py
│   │   │   ├── epigenetics.py
│   │   │   └── wearables.py
│   │   ├── models/
│   │   │   ├── microbiome.py          # NEW — MicrobiomeUpload, MicrobiomeAnalysis,
│   │   │   │                          #        MicrobiomeTaxon, MicrobiomeDiversityMetric
│   │   │   ├── user.py                # MODIFY — add microbiome_uploads relationship
│   │   │   ├── genome.py
│   │   │   ├── blood.py
│   │   │   ├── epigenetics.py
│   │   │   └── wearable.py
│   │   ├── tasks/
│   │   │   ├── microbiome_tasks.py    # NEW — run_microbiome_analysis, weekly_reanalysis
│   │   │   └── __init__.py            # MODIFY — import microbiome tasks
│   │   └── utils/
│   │       ├── microbiome_analyzer.py # NEW — Parsers, diversity metrics, taxonomy,
│   │       │                          #        cross-domain correlations, API clients
│   │       ├── epigenetics_analyzer.py
│   │       └── wearable_client.py     # MODIFY — add microbiome to generate_cross_domain_insights
│   └── tests/
│       ├── test_microbiome_routes.py  # NEW — API endpoint tests
│       ├── test_microbiome_analyzer.py# NEW — Parser + metric tests
│       └── fixtures/
│           ├── sample_otu_table.csv   # NEW — Test fixture
│           └── sample_biom.biom       # NEW — Test fixture
├── frontend/
│   └── src/components/
│       ├── MicrobiomeDashboard.js     # NEW — Composition charts, diversity scores
│       ├── MicrobiomeUpload.js        # NEW — Upload dropzone for BIOM/OTU/CSV/FASTQ
│       └── DisclaimerModal.js         # MODIFY — add microbiome disclaimer paragraph
├── docker-compose.yml                 # MODIFY — no new services needed
└── README.md                          # MODIFY — add microbiome section
```

---

## 2. Data Models

### 2.1 MicrobiomeUpload

Follows the same pattern as `EpigeneticUpload`: UUID PK, FK to users, encrypted file
storage, status machine, SHA-256 hash for dedup.

```
Table: microbiome_uploads
──────────────────────────────────────────────────────────────────────
Column                  Type            Notes
──────────────────────────────────────────────────────────────────────
id                      String(36) PK   uuid4
user_id                 String(36) FK → users.id
filename_original       String(255)     Original upload filename
file_path_encrypted     String(512)     AES-256-GCM encrypted on disk
file_hash_sha256        String(64)      Deduplication / integrity
file_type               String(10)      biom / csv / tsv / fastq
data_type               String(30)      16s_rrna / shotgun / its / wgs
sample_source           String(50)      gut / oral / skin / vaginal / environmental
collection_date         Date            Nullable — when sample was taken
sequencing_platform     String(50)      Nullable — illumina / nanopore / pacbio
metrics_json            Text            Nullable — quick stats (read count, etc.)
status                  String(20)      uploaded → parsing → analyzing → complete → error
uploaded_at             datetime        UTC default
file_size_bytes         int
──────────────────────────────────────────────────────────────────────
Relationships:
  user        → User.microbiome_uploads  (back_populates)
  analysis    → MicrobiomeAnalysis       (uselist=False, cascade delete)
  taxa        → [MicrobiomeTaxon]        (cascade delete)
```

### 2.2 MicrobiomeAnalysis

Follows `EpigeneticAnalysis` pattern: 1:1 with upload, status tracking, JSON result
storage, AI summary.

```
Table: microbiome_analyses
──────────────────────────────────────────────────────────────────────
Column                      Type          Notes
──────────────────────────────────────────────────────────────────────
id                          String(36) PK uuid4
upload_id                   String(36) FK → microbiome_uploads.id (unique)
status                      String(20)    queued → running → complete → error
total_read_count            int           Nullable
classified_read_count       int           Nullable
taxonomy_level_counts_json  Text          {"phylum": 12, "genus": 85, "species": 210}
composition_json            Text          Top-N taxa at each level with relative abundance
diversity_json              Text          {"shannon": 3.2, "simpson": 0.89, "chao1": 245.0,
                                           "observed_otus": 198, "faith_pd": 12.3}
enterotype                  String(20)    Nullable — Bacteroides / Prevotella / Ruminococcus
health_insights_json        Text          Structured insights array
genome_correlation_json     Text          Host-microbe interaction overlays
epigenetics_correlation_json Text         Gut-gene epigenetic overlays
blood_correlation_json      Text          Inflammation marker correlations
lifestyle_recs_json         Text          Diet/exercise recommendations
ai_summary_text             Text          GPT-generated narrative
started_at                  datetime      Nullable
completed_at                datetime      Nullable
error_message               Text          Nullable
──────────────────────────────────────────────────────────────────────
Relationships:
  upload → MicrobiomeUpload (back_populates)
```

### 2.3 MicrobiomeTaxon

Individual taxon records parsed from the upload. Indexed for fast queries by taxonomy
level and abundance.

```
Table: microbiome_taxa
──────────────────────────────────────────────────────────────────────
Column              Type          Notes
──────────────────────────────────────────────────────────────────────
id                  String(36) PK uuid4
upload_id           String(36) FK → microbiome_uploads.id
taxonomy_level      String(10)    phylum / class / order / family / genus / species
taxonomy_name       String(200)   e.g. "Bacteroides fragilis"
taxonomy_id         String(50)    NCBI taxid (nullable)
relative_abundance  float         0.0 – 1.0
absolute_count      int           Nullable — raw read/OTU count
confidence          float         Nullable — classifier confidence 0.0 – 1.0
parent_taxon        String(200)   Nullable — parent taxonomy name
──────────────────────────────────────────────────────────────────────
Indexes:
  ix_microbiome_taxa_upload_level  (upload_id, taxonomy_level)
  ix_microbiome_taxa_abundance     (upload_id, relative_abundance DESC)
Relationships:
  upload → MicrobiomeUpload (back_populates)
```

### 2.4 MicrobiomeDiversityMetric (optional — can be JSON only)

If per-sample longitudinal tracking is needed later:

```
Table: microbiome_diversity_metrics
──────────────────────────────────────────────────────────────────────
Column          Type          Notes
──────────────────────────────────────────────────────────────────────
id              String(36) PK uuid4
upload_id       String(36) FK → microbiome_uploads.id
metric_name     String(30)    shannon / simpson / chao1 / observed_otus / faith_pd
value           float
computed_at     datetime      UTC
──────────────────────────────────────────────────────────────────────
```

### 2.5 User Model Changes

Add relationship to `app/models/user.py`:

```python
microbiome_uploads = relationship(
    "MicrobiomeUpload", back_populates="user", cascade="all, delete-orphan"
)
```

Add to `app/models/__init__.py`:

```python
from app.models.microbiome import (
    MicrobiomeUpload, MicrobiomeAnalysis, MicrobiomeTaxon,
)
```

---

## 3. API Endpoints

### 3.1 Microbiome Blueprint (`/api/v1/microbiome`)

| Method | Endpoint                                  | Description                                           | Rate Limit    |
|--------|-------------------------------------------|-------------------------------------------------------|---------------|
| POST   | `/upload`                                 | Upload BIOM/OTU CSV/TSV/FASTQ file                    | 5/hour        |
| GET    | `/uploads`                                | List user's microbiome uploads                        | —             |
| GET    | `/uploads/:id`                            | Upload detail + analysis status                       | —             |
| DELETE | `/uploads/:id`                            | Delete upload + analysis + taxa                       | —             |
| GET    | `/analysis/:id`                           | Analysis results (diversity, composition, insights)   | —             |
| GET    | `/analysis/:id/taxa`                      | Paginated taxa list (filter by level, min abundance)  | —             |
| GET    | `/analysis/:id/composition`               | Phylum/genus-level composition breakdown              | —             |
| GET    | `/analysis/:id/genome-correlation`        | Host-microbe gene interaction overlays                | —             |
| POST   | `/uploads/:id/analyze`                    | Re-trigger analysis                                   | 3/hour        |

### 3.2 Correlate-All Endpoint (`/api/v1/insights`)

New unified endpoint added to the existing insights blueprint:

| Method | Endpoint                                  | Description                                           |
|--------|-------------------------------------------|-------------------------------------------------------|
| POST   | `/correlate-all`                          | Unified cross-domain report (genome + epigenetics + microbiome + wearables + blood) |
| GET    | `/correlate-all/latest`                   | Get most recent unified report                        |

#### `/correlate-all` Response Shape

```json
{
  "report_id": "uuid",
  "generated_at": "2026-02-28T12:00:00Z",
  "sections": {
    "genome_summary": { "variant_count": 45, "risk_categories": [...] },
    "epigenetics_summary": { "region_count": 120, "methylation_avg": 0.55 },
    "microbiome_summary": {
      "diversity": { "shannon": 3.2, "simpson": 0.89 },
      "enterotype": "Bacteroides",
      "top_phyla": [...]
    },
    "blood_summary": { "latest_date": "2026-02-20", "flagged_markers": [...] },
    "wearable_summary": { "avg_steps_7d": 8500, "avg_sleep_7d": 420 }
  },
  "cross_domain_insights": [
    {
      "title": "HLA-DQ2 variant + low Bifidobacterium",
      "body": "Your HLA-DQ2 risk variant (rs2187668) combined with low Bifidobacterium abundance (1.2%) suggests monitoring gluten sensitivity...",
      "confidence": "medium",
      "data_sources": ["genome:rs2187668", "microbiome:Bifidobacterium", "blood:iga"],
      "recommendations": ["Increase prebiotic fiber intake", "Consider probiotic supplementation"]
    }
  ],
  "lifestyle_recommendations": [...],
  "disclaimer": "..."
}
```

---

## 4. Utility Module: `microbiome_analyzer.py`

### 4.1 Parsers

```
parse_biom(data: bytes) → list[ParsedTaxon]
    Parse BIOM v1 (JSON) or v2 (HDF5) format OTU tables.
    Extract taxonomy strings and observation counts.

parse_otu_csv(data: bytes) → list[ParsedTaxon]
    Parse CSV/TSV OTU tables with flexible headers:
      Column aliases: {otu_id, #OTU ID, feature_id}
                      {taxonomy, lineage, taxon}
                      {count, reads, abundance}
    Normalize taxonomy strings: "k__Bacteria;p__Firmicutes;..." → structured levels.

parse_fastq_metadata(data: bytes) → dict
    Extract basic stats from FASTQ: read count, avg quality, avg length.
    NOTE: Full FASTQ analysis (assembly, binning) is too heavy for in-app —
    recommend users process via QIIME2/MetaPhlAn first, then upload results.
    Return metadata dict for display; mark upload for "raw" status.
```

### 4.2 Taxonomy Normalization

```
normalize_taxonomy(raw_string: str) → dict[str, str]
    Parse Greengenes ("k__Bacteria;p__Firmicutes;c__Clostridia;...")
    or SILVA ("Bacteria;Firmicutes;Clostridia;...")
    or NCBI ("Bacteria > Firmicutes > Clostridia > ...")
    → {"kingdom": "Bacteria", "phylum": "Firmicutes", "class": "Clostridia", ...}
```

### 4.3 Diversity Metrics

```
compute_alpha_diversity(taxa: list[ParsedTaxon]) → dict
    Shannon index:   H = -Σ(p_i × ln(p_i))
    Simpson index:   D = 1 - Σ(p_i²)
    Chao1 estimator: S_chao1 = S_obs + (f1² / 2f2)  [f1=singletons, f2=doubletons]
    Observed OTUs:   Count of unique taxa

compute_phyla_ratios(taxa: list[ParsedTaxon]) → dict
    Firmicutes/Bacteroidetes ratio (metabolic health indicator)
    Proteobacteria proportion (dysbiosis indicator)
    Actinobacteria proportion (Bifidobacterium presence)
```

### 4.4 Health Insights Engine

```
generate_microbiome_insights(
    diversity: dict,
    composition: dict,
    phyla_ratios: dict,
    enterotype: str | None,
) → list[MicrobiomeInsight]

Rules-based engine (pre-AI):
  - Shannon < 2.5  → alert: "Low diversity associated with metabolic syndrome"
  - F/B ratio > 3  → alert: "Elevated Firmicutes/Bacteroidetes ratio linked to obesity risk"
  - Proteobacteria > 15% → alert: "High Proteobacteria may indicate gut dysbiosis"
  - Bifidobacterium < 2% → rec: "Increase prebiotics for Bifidobacteria growth"
  - Akkermansia < 1% → rec: "Consider polyphenol-rich foods for Akkermansia support"
  - Low Faecalibacterium → rec: "Add fermented foods daily; butyrate production is low"
```

### 4.5 Cross-Domain Correlation Functions

```
correlate_microbiome_genome(
    taxa: list[ParsedTaxon],
    diversity: dict,
    user_variants: list[dict],
) → list[CrossDomainInsight]

Known host-microbe gene interactions:
  Gene      │ Variant      │ Microbiome Link
  ──────────┼──────────────┼──────────────────────────────────────────
  HLA-DQ2   │ rs2187668    │ Gluten sensitivity ↔ Bifidobacterium depletion
  HLA-DQ8   │ rs7454108    │ Celiac risk ↔ altered Lactobacillus
  FUT2      │ rs601338     │ Non-secretor → reduced Bifidobacterium
  NOD2      │ rs2066844    │ Crohn's risk ↔ reduced Faecalibacterium
  IL6       │ rs1800795    │ Inflammation pathway ↔ Proteobacteria bloom
  TCF7L2    │ rs7903146    │ T2D risk ↔ F/B ratio
  APOE      │ rs429358     │ Lipid metabolism ↔ Prevotella vs Bacteroides
  MTHFR     │ rs1801133    │ Folate metabolism ↔ folate-producing bacteria


correlate_microbiome_epigenetics(
    taxa: list[ParsedTaxon],
    epigenetic_overlays: list[dict],
) → list[CrossDomainInsight]

Known epigenetic-microbiome links:
  - Gut-derived SCFAs (butyrate) influence histone acetylation (H3K27ac) in
    intestinal epithelial cells → if user has low Faecalibacterium AND
    H3K27ac signal is reduced at gut-related gene promoters, flag it.
  - NOD2/CARD15 promoter methylation status modulates Crohn's risk differently
    depending on microbiome Firmicutes levels.


correlate_microbiome_blood(
    taxa: list[ParsedTaxon],
    diversity: dict,
    blood_markers: list[dict],
) → list[CrossDomainInsight]

Known blood-microbiome links:
  Marker          │ Microbiome Link
  ────────────────┼──────────────────────────────────────────
  calprotectin    │ > 150 µg/g + low diversity → gut inflammation
  hs_crp          │ > 3 mg/L + high Proteobacteria → systemic inflammation
  hemoglobin_a1c  │ > 5.7% + high F/B ratio → metabolic dysregulation
  vitamin_d       │ < 20 ng/mL + low Lactobacillus → impaired absorption
  ferritin        │ Low + low diversity → malabsorption
  triglycerides   │ Elevated + Prevotella-dominant → dietary pattern flag
  ldl_cholesterol │ Elevated + low Akkermansia → gut barrier permeability


correlate_microbiome_wearables(
    taxa: list[ParsedTaxon],
    diversity: dict,
    wearable_summaries: list[dict],
) → list[CrossDomainInsight]

Known wearable-microbiome links:
  - Low activity (<5000 steps/day avg) → reduced microbial diversity
  - Poor sleep (<6h avg) → elevated F/B ratio, reduced Lactobacillus
  - High resting HR (>80 bpm) + high Proteobacteria → stress-dysbiosis axis
  - Low HRV (<30ms) + low diversity → vagal tone / gut-brain axis concern
```

### 4.6 External API Clients

```
query_nmdc_biosamples(
    ecosystem: str,       # e.g. "Host-associated > Human > Gut"
    taxa_names: list[str],
) → list[dict]
    GET https://api.microbiomedata.org/nmdcschema/biosample_set
    ?filter={"ecosystem_category": "Host-associated", "ecosystem_type": "Human"}
    &max_page_size=25
    Purpose: Find reference biosamples with similar community profiles.

query_ncbi_taxonomy(
    taxon_name: str,
) → dict
    GET https://api.ncbi.nlm.nih.gov/datasets/v2/genome/taxon/{taxon_name}
    Headers: {"api-key": NCBI_API_KEY}
    Purpose: Resolve taxonomy IDs, get genome assembly info.

    Alternative via eUtils:
    GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
    ?db=taxonomy&term={taxon_name}&retmode=json
    Purpose: Get NCBI taxid for downstream queries.

query_ensembl_bacteria(
    species_name: str,
) → dict
    GET https://rest.ensembl.org/info/genomes/taxonomy/{species_name}
    ?content-type=application/json
    Purpose: Get bacterial genome annotations for functional context.
    Note: Ensembl Bacteria covers >30k bacterial genomes; useful for
    annotating dominant taxa with known gene content.

query_hmp_reference(
    body_site: str,  # e.g. "gut", "oral"
) → dict
    Via NCBI eUtils:
    GET https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
    ?db=biosample&term=human+microbiome+project+{body_site}&retmode=json
    Purpose: Retrieve HMP reference abundances for comparison.
```

---

## 5. Celery Tasks

### 5.1 `microbiome_tasks.py`

```
@shared_task
run_microbiome_analysis(analysis_id: str) → dict
    Pipeline:
    1. Decrypt uploaded file using user DEK
    2. Detect format (BIOM vs CSV/TSV vs FASTQ)
    3. Parse → list[ParsedTaxon]
    4. Normalize taxonomy strings
    5. Compute alpha diversity (Shannon, Simpson, Chao1, observed OTUs)
    6. Compute phyla ratios (F/B ratio, Proteobacteria %, etc.)
    7. Determine enterotype (Bacteroides / Prevotella / Ruminococcus)
    8. Query external APIs for reference data (NMDC, NCBI) — with caching
    9. Generate health insights (rules-based)
    10. Cross-reference with user's genome variants
    11. Cross-reference with user's epigenetic overlays
    12. Cross-reference with user's latest blood markers
    13. Generate AI summary (GPT or template fallback)
    14. Persist all results to MicrobiomeAnalysis + MicrobiomeTaxon
    Status: queued → running → complete / error

@shared_task
schedule_weekly_reanalysis() → dict
    For users with active wearable connections + microbiome uploads:
    - Re-run correlations with latest wearable data
    - Update lifestyle recommendations based on activity trends
    - Infer potential microbiome stability from consistent exercise/sleep patterns
    Schedule: Weekly (Celery Beat, Sunday 04:00 UTC)
```

### 5.2 `celery_worker.py` Beat Schedule Addition

```python
"weekly-microbiome-reanalysis": {
    "task": "app.tasks.microbiome_tasks.schedule_weekly_reanalysis",
    "schedule": crontab(minute=0, hour=4, day_of_week=0),  # Sunday 04:00 UTC
    "options": {"queue": "analysis"},
},
```

### 5.3 `tasks/__init__.py` Addition

```python
from app.tasks.microbiome_tasks import (
    run_microbiome_analysis,
    schedule_weekly_reanalysis,
)
```

---

## 6. Cross-Domain Integration Updates

### 6.1 `wearable_client.py` → `generate_cross_domain_insights()`

Add new optional parameter:

```python
def generate_cross_domain_insights(
    wearable_summaries: list[dict],
    user_variants: list[dict] | None = None,
    blood_markers: list[dict] | None = None,
    epigenetic_overlays: list[dict] | None = None,
    microbiome_profile: dict | None = None,         # NEW
) → list[CrossDomainInsight]:
```

Where `microbiome_profile` contains:
```python
{
    "diversity": {"shannon": 3.2, "simpson": 0.89},
    "phyla_ratios": {"firmicutes_bacteroidetes": 2.1, "proteobacteria_pct": 8.0},
    "top_genera": [
        {"name": "Bacteroides", "abundance": 0.25},
        {"name": "Faecalibacterium", "abundance": 0.12},
    ],
    "enterotype": "Bacteroides",
}
```

### 6.2 `wearable_tasks.py` → `_generate_for_user()`

Add microbiome data loading:

```python
microbiome_profile = _load_user_microbiome_profile(user_id)

insights = generate_cross_domain_insights(
    wearable_summaries=wearable_summaries,
    user_variants=user_variants,
    blood_markers=blood_markers,
    epigenetic_overlays=epigenetic_overlays,
    microbiome_profile=microbiome_profile,       # NEW
)
```

New helper:
```python
def _load_user_microbiome_profile(user_id: str) → dict | None:
    """Load latest completed microbiome analysis for the user."""
    latest = (MicrobiomeUpload.query
              .filter_by(user_id=user_id, status="complete")
              .order_by(MicrobiomeUpload.uploaded_at.desc())
              .first())
    if not latest or not latest.analysis:
        return None
    analysis = latest.analysis
    return {
        "diversity": json.loads(analysis.diversity_json or "{}"),
        "phyla_ratios": ...,  # extract from composition_json
        "top_genera": ...,    # extract top 10 from composition_json
        "enterotype": analysis.enterotype,
    }
```

### 6.3 Daily Insight Sources Update

The `data_sources` field in `DailyInsight` already supports arbitrary strings.
Microbiome insights will use the prefix `microbiome:`:

```
"microbiome:diversity"
"microbiome:Bifidobacterium"
"microbiome:firmicutes_bacteroidetes_ratio"
```

---

## 7. Security Considerations

| Concern                        | Mitigation                                                        |
|--------------------------------|-------------------------------------------------------------------|
| PHI in microbiome files        | AES-256-GCM encryption at rest using per-user DEK (existing)     |
| FASTQ files can be very large  | `MAX_MICROBIOME_FILE_SIZE_MB=200` config; streaming decrypt       |
| Taxonomy data is semi-public   | Store parsed taxa unencrypted; only raw files encrypted           |
| External API calls leak data?  | Only send taxonomy names (not user IDs) to NMDC/NCBI/Ensembl     |
| File type validation           | Magic-byte check for BIOM HDF5; header validation for CSV        |
| Path traversal                 | Re-use existing `sanitize_filename()` from genome upload service  |
| Rate-limit uploads             | `@limiter.limit("5 per hour")` on upload endpoint                |

---

## 8. Frontend Updates

### 8.1 `MicrobiomeUpload.js`

- Dropzone accepting `.biom`, `.csv`, `.tsv`, `.fastq`, `.fq`, `.fastq.gz`
- Form fields: `sample_source` (gut/oral/skin dropdown), `collection_date`
- FASTQ warning: "Raw FASTQ files will capture basic stats only. For full
  analysis, pre-process with QIIME2 or MetaPhlAn and upload the OTU table."

### 8.2 `MicrobiomeDashboard.js`

- **Composition donut chart** (Recharts PieChart) — phylum-level
- **Diversity score cards** — Shannon, Simpson, Chao1 with health-range indicators
- **Top genera bar chart** — horizontal bars for top 15 genera
- **F/B ratio gauge** — optimal range indicator (1.0–2.5)
- **Cross-domain insight cards** — filtered by `microbiome:*` sources

### 8.3 `DisclaimerModal.js` Addition

```jsx
<Typography variant="body2" paragraph>
  <strong>Microbiome Analysis:</strong> Gut and other microbiome
  composition analyses are based on sequencing snapshots and may vary
  significantly between samples. Results are compared against public
  reference databases (Human Microbiome Project, NMDC) and do not
  constitute a clinical microbiome test.
</Typography>
```

---

## 9. Docker / Deployment

No new services needed. Microbiome tasks run on the existing `celery` worker
via the `analysis` queue. The weekly reanalysis runs via `celery-beat`.

### Dockerfile change (backend)

Add `biom-format` and `h5py` system dependencies:

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libhts-dev zlib1g-dev libhdf5-dev && \
    rm -rf /var/lib/apt/lists/*
```

### requirements.txt additions

```
biom-format>=2.1.16
h5py>=3.11
scipy>=1.13          # For diversity calculations (already likely a transitive dep)
```

### Celery Beat schedule (docker-compose celery-beat already runs it)

New task auto-discovered; no compose changes needed.

---

## 10. Config Updates

### `app/config.py`

```python
# Microbiome
MAX_MICROBIOME_FILE_SIZE_BYTES = (
    int(os.environ.get("MAX_MICROBIOME_FILE_SIZE_MB", "200")) * 1024 * 1024
)
NMDC_API_BASE = os.environ.get(
    "NMDC_API_BASE", "https://api.microbiomedata.org"
)
```

### `.env.example`

```bash
# Microbiome analysis
MAX_MICROBIOME_FILE_SIZE_MB=200
# NMDC API base (defaults to https://api.microbiomedata.org)
# NMDC_API_BASE=https://api.microbiomedata.org
```

---

## 11. Test Plan

### `test_microbiome_analyzer.py`

| Test Class                  | Cases                                                          |
|-----------------------------|----------------------------------------------------------------|
| TestParseBiom               | Valid BIOM JSON, missing fields, empty table                   |
| TestParseOtuCsv             | Basic CSV, flexible headers, Greengenes taxonomy, SILVA format |
| TestNormalizeTaxonomy       | Greengenes, SILVA, NCBI, partial strings, malformed            |
| TestAlphaDiversity          | Shannon known values, Simpson edge cases, Chao1 with singletons|
| TestPhylaRatios             | Normal F/B, elevated F/B, missing phyla                        |
| TestHealthInsights          | Low diversity alert, high Proteobacteria, recommendations      |
| TestGenomeCorrelation       | HLA-DQ2 + low Bifido, FUT2 non-secretor, no matching variants |
| TestBloodCorrelation        | High CRP + Proteobacteria, low vitamin D + low Lactobacillus  |
| TestWearableCorrelation     | Low activity + low diversity, poor sleep + high F/B ratio      |
| TestNmdcQuery               | Mock HTTP success, HTTP error fallback, empty results          |

### `test_microbiome_routes.py`

| Test                        | Endpoint                                                       |
|-----------------------------|----------------------------------------------------------------|
| test_upload_biom_success    | POST /upload — valid BIOM → 202                                |
| test_upload_csv_success     | POST /upload — valid OTU CSV → 202                             |
| test_upload_fastq_warning   | POST /upload — FASTQ → 202 with "limited_analysis" flag        |
| test_upload_no_file         | POST /upload — missing file → 400                              |
| test_upload_invalid_type    | POST /upload — bad data_type → 400                             |
| test_upload_requires_auth   | POST /upload — no token → 401                                  |
| test_list_uploads           | GET /uploads — returns user's uploads only                     |
| test_get_analysis           | GET /analysis/:id — returns diversity + composition            |
| test_get_taxa_paginated     | GET /analysis/:id/taxa?level=genus&page=1&per_page=20          |
| test_get_composition        | GET /analysis/:id/composition — phylum breakdown               |
| test_genome_correlation     | GET /analysis/:id/genome-correlation                           |
| test_delete_upload          | DELETE /uploads/:id — cascades to analysis + taxa              |
| test_correlate_all          | POST /insights/correlate-all — unified report                  |
| test_cannot_access_other    | GET /uploads/:id — user isolation enforced → 404               |

---

## 12. External API Reference Summary

| API                          | Base URL                                           | Used For                                        |
|------------------------------|----------------------------------------------------|-------------------------------------------------|
| NMDC (Biosamples)            | `https://api.microbiomedata.org`                   | Reference community profiles by ecosystem       |
| NCBI Datasets                | `https://api.ncbi.nlm.nih.gov/datasets/v2`        | Taxonomy resolution, microbial genome metadata  |
| NCBI eUtils                  | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`   | Taxonomy search, HMP reference queries          |
| Ensembl Bacteria             | `https://rest.ensembl.org`                         | Bacterial genome annotations for dominant taxa  |

All external queries send only taxonomy names (never user PII). Results are
cached in Redis with a 24-hour TTL to avoid redundant API calls.

---

## 13. Implementation Order (Suggested)

1. **Models** — `microbiome.py` models + User relationship + migrations
2. **Parsers** — `microbiome_analyzer.py` (parse_biom, parse_otu_csv, normalize_taxonomy)
3. **Metrics** — Diversity calculations + phyla ratios + enterotype classification
4. **Routes** — `microbiome.py` blueprint (upload, list, get, delete, analyze)
5. **Tasks** — `microbiome_tasks.py` (run_microbiome_analysis)
6. **Insights** — Health insight rules engine
7. **Correlations** — genome, epigenetics, blood, wearable cross-references
8. **Correlate-All** — Unified `/correlate-all` endpoint
9. **External APIs** — NMDC, NCBI, Ensembl clients with caching
10. **Frontend** — Upload component, dashboard, disclaimer update
11. **Tests** — Full test suite for all of the above
12. **Weekly task** — `schedule_weekly_reanalysis` + beat schedule update
