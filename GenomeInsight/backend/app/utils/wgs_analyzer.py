"""Whole-Genome Sequencing analysis pipeline.

Handles:
 1. FASTQ parsing via Biopython (read stats, quality metrics).
 2. BAM parsing via pysam (alignment stats, coverage depth).
 3. Simulated variant calling (demonstration; real pipelines use GATK/bcftools).
 4. Ancestry haplogroup inference via NCBI queries.
 5. Oral microbiome cross-referencing with HMP data.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import random
from dataclasses import asdict, dataclass, field

import httpx

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class WGSReadStats:
    """Summary statistics from FASTQ/BAM parsing."""

    total_reads: int = 0
    avg_read_length: float = 0.0
    avg_quality: float = 0.0
    total_bases: int = 0
    gc_content: float = 0.0
    estimated_depth: float = 0.0
    file_format: str = "fastq"


@dataclass
class SimulatedVariant:
    """A variant detected during simulated variant calling."""

    chromosome: str = ""
    position: int = 0
    ref: str = ""
    alt: str = ""
    quality: float = 0.0
    genotype: str = "0/1"
    rsid: str = ""


@dataclass
class AncestryResult:
    """Ancestry analysis result from haplogroup inference."""

    mt_haplogroup: str = ""
    y_haplogroup: str = ""
    population_composition: dict = field(default_factory=dict)
    archaic_ancestry_pct: float = 0.0
    migration_paths: list[dict] = field(default_factory=list)
    historical_context: str = ""


# ── FASTQ parsing (Biopython) ───────────────────────────────────────────────


def parse_fastq_biopython(file_path: str) -> WGSReadStats:
    """Parse a FASTQ file using Biopython SeqIO for detailed stats.

    Falls back to manual parsing if Biopython is unavailable.
    """
    try:
        from Bio import SeqIO
        return _parse_fastq_with_seqio(file_path)
    except ImportError:
        logger.warning("Biopython not available, using manual FASTQ parser")
        return _parse_fastq_manual(file_path)


def _parse_fastq_with_seqio(file_path: str) -> WGSReadStats:
    """Parse FASTQ using Biopython SeqIO."""
    from Bio import SeqIO

    total_reads = 0
    total_length = 0
    total_quality = 0
    quality_count = 0
    gc_count = 0

    for record in SeqIO.parse(file_path, "fastq"):
        total_reads += 1
        seq_len = len(record.seq)
        total_length += seq_len

        # GC content
        seq_str = str(record.seq).upper()
        gc_count += seq_str.count("G") + seq_str.count("C")

        # Quality scores
        quals = record.letter_annotations.get("phred_quality", [])
        total_quality += sum(quals)
        quality_count += len(quals)

    avg_length = total_length / total_reads if total_reads else 0
    avg_quality = total_quality / quality_count if quality_count else 0
    gc_content = gc_count / total_length if total_length else 0

    # Estimate depth: total_bases / human_genome_size (~3.1 billion bp)
    human_genome_size = 3_100_000_000
    estimated_depth = total_length / human_genome_size

    return WGSReadStats(
        total_reads=total_reads,
        avg_read_length=round(avg_length, 1),
        avg_quality=round(avg_quality, 1),
        total_bases=total_length,
        gc_content=round(gc_content, 4),
        estimated_depth=round(estimated_depth, 2),
        file_format="fastq",
    )


def _parse_fastq_manual(file_path: str) -> WGSReadStats:
    """Manual FASTQ parser fallback (no Biopython dependency)."""
    total_reads = 0
    total_length = 0
    total_quality = 0
    quality_count = 0
    gc_count = 0

    with open(file_path, "r") as f:
        while True:
            header = f.readline().strip()
            if not header:
                break
            if not header.startswith("@"):
                continue

            sequence = f.readline().strip()
            f.readline()  # + line
            quality = f.readline().strip()

            total_reads += 1
            seq_len = len(sequence)
            total_length += seq_len

            seq_upper = sequence.upper()
            gc_count += seq_upper.count("G") + seq_upper.count("C")

            for ch in quality:
                total_quality += ord(ch) - 33
                quality_count += 1

    avg_length = total_length / total_reads if total_reads else 0
    avg_quality = total_quality / quality_count if quality_count else 0
    gc_content = gc_count / total_length if total_length else 0
    human_genome_size = 3_100_000_000
    estimated_depth = total_length / human_genome_size

    return WGSReadStats(
        total_reads=total_reads,
        avg_read_length=round(avg_length, 1),
        avg_quality=round(avg_quality, 1),
        total_bases=total_length,
        gc_content=round(gc_content, 4),
        estimated_depth=round(estimated_depth, 2),
        file_format="fastq",
    )


# ── BAM parsing (pysam) ────────────────────────────────────────────────────


def parse_bam(file_path: str) -> WGSReadStats:
    """Parse a BAM file using pysam for alignment statistics.

    Falls back to basic file inspection if pysam is unavailable.
    """
    try:
        import pysam
        return _parse_bam_with_pysam(file_path)
    except ImportError:
        logger.warning("pysam not available, returning basic BAM metadata")
        return _parse_bam_fallback(file_path)


def _parse_bam_with_pysam(file_path: str) -> WGSReadStats:
    """Parse BAM using pysam."""
    import pysam

    samfile = pysam.AlignmentFile(file_path, "rb")

    total_reads = 0
    total_length = 0
    total_quality = 0
    quality_count = 0
    gc_count = 0
    mapped_reads = 0

    for read in samfile.fetch(until_eof=True):
        total_reads += 1
        if read.is_unmapped:
            continue
        mapped_reads += 1

        seq = read.query_sequence or ""
        seq_len = len(seq)
        total_length += seq_len

        gc_count += seq.upper().count("G") + seq.upper().count("C")

        quals = read.query_qualities
        if quals is not None:
            total_quality += sum(quals)
            quality_count += len(quals)

    samfile.close()

    avg_length = total_length / mapped_reads if mapped_reads else 0
    avg_quality = total_quality / quality_count if quality_count else 0
    gc_content = gc_count / total_length if total_length else 0
    human_genome_size = 3_100_000_000
    estimated_depth = total_length / human_genome_size

    return WGSReadStats(
        total_reads=total_reads,
        avg_read_length=round(avg_length, 1),
        avg_quality=round(avg_quality, 1),
        total_bases=total_length,
        gc_content=round(gc_content, 4),
        estimated_depth=round(estimated_depth, 2),
        file_format="bam",
    )


def _parse_bam_fallback(file_path: str) -> WGSReadStats:
    """Basic BAM file inspection without pysam."""
    import os

    file_size = os.path.getsize(file_path)
    # Rough estimate: compressed BAM is ~1/3 of raw data
    estimated_bases = file_size * 3
    human_genome_size = 3_100_000_000
    estimated_depth = estimated_bases / human_genome_size

    return WGSReadStats(
        total_reads=0,
        avg_read_length=0,
        avg_quality=0,
        total_bases=estimated_bases,
        gc_content=0,
        estimated_depth=round(estimated_depth, 2),
        file_format="bam",
    )


# ── Simulated variant calling ───────────────────────────────────────────────

# Clinically relevant SNPs for ancestry and pharmacogenomics
_KNOWN_ANCESTRY_SNPS = [
    {"rsid": "rs3827760", "chr": "2", "pos": 109513601, "gene": "EDAR",
     "desc": "East Asian hair thickness / shovel-shaped incisors"},
    {"rsid": "rs1426654", "chr": "15", "pos": 48426484, "gene": "SLC24A5",
     "desc": "Skin pigmentation (European lightening)"},
    {"rsid": "rs16891982", "chr": "5", "pos": 33951693, "gene": "SLC45A2",
     "desc": "Skin/hair/eye pigmentation"},
    {"rsid": "rs12913832", "chr": "15", "pos": 28365618, "gene": "HERC2/OCA2",
     "desc": "Blue/brown eye color determination"},
    {"rsid": "rs4988235", "chr": "2", "pos": 136608646, "gene": "MCM6/LCT",
     "desc": "Lactase persistence (European)"},
    {"rsid": "rs671", "chr": "12", "pos": 112241766, "gene": "ALDH2",
     "desc": "Alcohol flush reaction (East Asian)"},
    {"rsid": "rs1800497", "chr": "11", "pos": 113270828, "gene": "ANKK1/DRD2",
     "desc": "Dopamine receptor density"},
    {"rsid": "rs7412", "chr": "19", "pos": 44908822, "gene": "APOE",
     "desc": "Alzheimer's risk / lipid metabolism"},
    {"rsid": "rs429358", "chr": "19", "pos": 44908684, "gene": "APOE",
     "desc": "APOE4 allele determination"},
    {"rsid": "rs334", "chr": "11", "pos": 5227002, "gene": "HBB",
     "desc": "Sickle cell trait / malaria resistance"},
]

# Mitochondrial haplogroup markers (simplified)
_MT_HAPLOGROUP_MARKERS = {
    "H": ["263G", "750G", "1438G", "4769G", "8860G", "15326G"],
    "U": ["73G", "7028T", "11467G", "12308G", "12372A"],
    "J": ["295T", "489C", "10398G", "12612G", "13708A"],
    "T": ["709A", "1888A", "4917G", "10463C", "13368A"],
    "K": ["497T", "1189C", "10398G", "10550G", "11299C"],
    "L3": ["769G", "1018A", "16311C"],
    "B": ["8281d", "8289d", "16189C", "16519C"],
    "A": ["663G", "1736G", "4824G", "8794T"],
    "D": ["4883T", "5178A", "8414T"],
    "N": ["8701G", "9540C", "10398A", "10873C"],
}

# Y-chromosome haplogroup markers (simplified)
_Y_HAPLOGROUP_MARKERS = {
    "R1b": "M343",
    "R1a": "M420",
    "I1": "M253",
    "I2": "M438",
    "J2": "M172",
    "J1": "M267",
    "E1b": "M215",
    "G2a": "P15",
    "N": "M231",
    "O": "M175",
    "Q": "M242",
    "C": "M130",
}


def simulate_variant_calling(
    read_stats: WGSReadStats,
    seed: int | None = None,
) -> list[SimulatedVariant]:
    """Simulate variant calling based on read statistics.

    In production, replace with actual GATK HaplotypeCaller or bcftools
    pipeline. This simulation produces deterministic results for a given
    file hash (via seed) for demo/testing purposes.
    """
    if seed is not None:
        random.seed(seed)

    variants = []
    for snp in _KNOWN_ANCESTRY_SNPS:
        # Simulate detection probability based on depth
        depth = read_stats.estimated_depth
        detection_prob = min(0.95, 1 - math.exp(-depth / 5))

        if random.random() < detection_prob:
            genotype = random.choice(["0/0", "0/1", "1/1"])
            quality = min(99, depth * 10 + random.gauss(20, 5))

            variants.append(SimulatedVariant(
                chromosome=snp["chr"],
                position=snp["pos"],
                ref="C",  # Simplified
                alt="T",
                quality=round(max(0, quality), 1),
                genotype=genotype,
                rsid=snp["rsid"],
            ))

    return variants


# ── Ancestry inference ──────────────────────────────────────────────────────

# Reference population allele frequencies for admixture estimation
_POPULATION_ALLELE_FREQS = {
    "rs1426654": {"European": 0.98, "East Asian": 0.02, "African": 0.05, "South Asian": 0.60},
    "rs16891982": {"European": 0.87, "East Asian": 0.01, "African": 0.03, "South Asian": 0.10},
    "rs3827760": {"European": 0.02, "East Asian": 0.90, "African": 0.01, "South Asian": 0.05},
    "rs4988235": {"European": 0.75, "East Asian": 0.05, "African": 0.10, "South Asian": 0.30},
    "rs671": {"European": 0.00, "East Asian": 0.30, "African": 0.00, "South Asian": 0.02},
    "rs334": {"European": 0.01, "East Asian": 0.00, "African": 0.12, "South Asian": 0.03},
    "rs12913832": {"European": 0.75, "East Asian": 0.01, "African": 0.01, "South Asian": 0.05},
}


def infer_ancestry(
    variants: list[SimulatedVariant],
    seed: int | None = None,
) -> AncestryResult:
    """Infer ancestry composition from detected variants.

    Uses a simplified admixture model based on known population allele
    frequencies. Real implementations use ADMIXTURE / RFMix / LASER.
    """
    if seed is not None:
        random.seed(seed)

    # Score each population based on variant matches
    pop_scores = {"European": 0.0, "East Asian": 0.0, "African": 0.0, "South Asian": 0.0}
    scored_count = 0

    variant_map = {v.rsid: v for v in variants}

    for rsid, freqs in _POPULATION_ALLELE_FREQS.items():
        v = variant_map.get(rsid)
        if not v:
            continue

        # Alt allele count: 0/0=0, 0/1=1, 1/1=2
        alt_count = v.genotype.count("1")

        for pop, freq in freqs.items():
            if alt_count > 0:
                pop_scores[pop] += freq * alt_count
            else:
                pop_scores[pop] += (1 - freq) * 2
        scored_count += 1

    # Normalize to percentages
    total = sum(pop_scores.values()) or 1.0
    composition = {pop: round(score / total, 4) for pop, score in pop_scores.items()}

    # Assign haplogroups based on dominant population
    dominant_pop = max(composition, key=composition.get)
    mt_haplogroup = _assign_mt_haplogroup(dominant_pop, seed)
    y_haplogroup = _assign_y_haplogroup(dominant_pop, seed)

    # Estimate archaic ancestry (Neanderthal: ~2% for non-African populations)
    african_pct = composition.get("African", 0)
    archaic_pct = round(max(0, (1 - african_pct) * random.uniform(0.015, 0.025)), 4)

    # Migration paths
    migration_paths = _generate_migration_paths(composition)

    return AncestryResult(
        mt_haplogroup=mt_haplogroup,
        y_haplogroup=y_haplogroup,
        population_composition=composition,
        archaic_ancestry_pct=archaic_pct,
        migration_paths=migration_paths,
        historical_context=_generate_historical_context(
            composition, mt_haplogroup, y_haplogroup
        ),
    )


def _assign_mt_haplogroup(dominant_pop: str, seed: int | None = None) -> str:
    """Assign a mitochondrial haplogroup based on dominant population."""
    pop_haplogroups = {
        "European": ["H", "U", "J", "T", "K"],
        "East Asian": ["B", "A", "D", "N"],
        "African": ["L3"],
        "South Asian": ["U", "H", "T", "N"],
    }
    choices = pop_haplogroups.get(dominant_pop, ["H"])
    return random.choice(choices)


def _assign_y_haplogroup(dominant_pop: str, seed: int | None = None) -> str:
    """Assign a Y-chromosome haplogroup based on dominant population."""
    pop_haplogroups = {
        "European": ["R1b", "R1a", "I1", "I2"],
        "East Asian": ["O", "C", "N", "Q"],
        "African": ["E1b"],
        "South Asian": ["R1a", "J2", "L"],
    }
    choices = pop_haplogroups.get(dominant_pop, ["R1b"])
    return random.choice(choices)


def _generate_migration_paths(composition: dict) -> list[dict]:
    """Generate plausible migration paths based on ancestry composition."""
    paths = []

    if composition.get("European", 0) > 0.20:
        paths.append({
            "origin": "Central Asia / Pontic Steppe",
            "destination": "Europe",
            "period": "~4,500-3,000 BCE",
            "description": "Indo-European migration associated with haplogroup R1b/R1a",
        })
    if composition.get("East Asian", 0) > 0.20:
        paths.append({
            "origin": "Southeast Asia / Yellow River Basin",
            "destination": "East Asia",
            "period": "~10,000-5,000 BCE",
            "description": "Neolithic expansion associated with rice and millet agriculture",
        })
    if composition.get("African", 0) > 0.20:
        paths.append({
            "origin": "East Africa",
            "destination": "Global (Out of Africa)",
            "period": "~70,000-50,000 BCE",
            "description": "Original human migration out of Africa",
        })
    if composition.get("South Asian", 0) > 0.20:
        paths.append({
            "origin": "Central Asia / Indus Valley",
            "destination": "South Asia",
            "period": "~3,000-1,500 BCE",
            "description": "Ancestral South Indian and Steppe pastoralist admixture",
        })

    return paths


def _generate_historical_context(
    composition: dict, mt_haplogroup: str, y_haplogroup: str
) -> str:
    """Generate narrative context for ancestry results."""
    dominant = max(composition, key=composition.get)
    pct = composition[dominant] * 100

    lines = [
        f"Your genetic ancestry is primarily {dominant} ({pct:.1f}%).",
        f"Maternal lineage (mtDNA haplogroup {mt_haplogroup}): ",
    ]

    mt_descriptions = {
        "H": "The most common European haplogroup, dating to ~20,000 years ago. "
             "Associated with post-glacial re-expansion from Iberian refugia.",
        "U": "One of the oldest European haplogroups (~50,000 years). "
             "Common among Mesolithic hunter-gatherers.",
        "J": "Associated with Neolithic farming expansion from the Near East (~10,000 years ago).",
        "T": "Sister clade of J, also linked to Near Eastern Neolithic farmers.",
        "K": "A subclade of U, enriched among Ashkenazi Jewish populations.",
        "L3": "The ancestral haplogroup from which all non-African mtDNA lineages descend.",
        "B": "Common in East/Southeast Asia and among Native Americans. "
             "Associated with coastal migration routes.",
        "A": "Widespread in East Asia and the Americas. One of the founding Native American lineages.",
        "D": "Common in East Asia and Northeast Siberia.",
    }
    lines.append(mt_descriptions.get(mt_haplogroup, "A maternal lineage with deep ancestral roots."))

    lines.append(f"\nPaternal lineage (Y-chromosome haplogroup {y_haplogroup}): ")
    y_descriptions = {
        "R1b": "The most common Y haplogroup in Western Europe. "
               "Strongly associated with the Bell Beaker culture expansion.",
        "R1a": "Common in Eastern Europe, Central Asia, and South Asia. "
               "Associated with Indo-European language dispersal.",
        "I1": "A Scandinavian/Northern European lineage predating the Indo-European migration.",
        "I2": "Common in the Balkans and Sardinia. An ancient European hunter-gatherer lineage.",
        "E1b": "Predominantly African, with subclades found across North Africa "
               "and the Mediterranean.",
        "O": "The most common Y haplogroup in East and Southeast Asia.",
        "J2": "Associated with Neolithic farming and widespread in the Mediterranean and South Asia.",
    }
    lines.append(y_descriptions.get(y_haplogroup, "A paternal lineage tracing deep ancestral routes."))

    return "\n".join(lines)


# ── NCBI haplogroup queries ─────────────────────────────────────────────────


def query_ncbi_haplogroup(
    haplogroup: str,
    haplogroup_type: str = "mt",
    ncbi_api_key: str = "",
    client: httpx.Client | None = None,
) -> dict:
    """Query NCBI for haplogroup information.

    Args:
        haplogroup: The haplogroup name (e.g., "H", "R1b").
        haplogroup_type: "mt" for mitochondrial, "y" for Y-chromosome.
        ncbi_api_key: Optional NCBI API key for higher rate limits.

    Returns:
        Dict with NCBI search results and references.
    """
    if client is None:
        try:
            client = httpx.Client(timeout=15)
        except Exception:
            return {}

    db = "pubmed" if haplogroup_type == "mt" else "pubmed"
    search_term = f"{haplogroup} haplogroup {haplogroup_type}DNA"

    try:
        params = {
            "db": db,
            "term": search_term,
            "retmode": "json",
            "retmax": 5,
            "sort": "relevance",
        }
        if ncbi_api_key:
            params["api_key"] = ncbi_api_key

        resp = client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()

        id_list = data.get("esearchresult", {}).get("idlist", [])

        return {
            "haplogroup": haplogroup,
            "type": haplogroup_type,
            "ncbi_pubmed_ids": id_list,
            "search_term": search_term,
            "result_count": data.get("esearchresult", {}).get("count", "0"),
        }
    except Exception:
        logger.debug("NCBI haplogroup query failed for %s", haplogroup, exc_info=True)
        return {"haplogroup": haplogroup, "type": haplogroup_type, "error": "query_failed"}


def query_ncbi_variant_updates(
    rsids: list[str],
    ncbi_api_key: str = "",
    client: httpx.Client | None = None,
) -> list[dict]:
    """Query NCBI/PubMed for recent research on specific variants.

    Used by the weekly update task to check for new publications.
    """
    if client is None:
        try:
            client = httpx.Client(timeout=15)
        except Exception:
            return []

    results = []
    for rsid in rsids:
        try:
            params = {
                "db": "pubmed",
                "term": f"{rsid} AND (genome OR variant OR SNP)",
                "retmode": "json",
                "retmax": 3,
                "sort": "date",
                "datetype": "pdat",
                "reldate": 30,  # Last 30 days
            }
            if ncbi_api_key:
                params["api_key"] = ncbi_api_key

            resp = client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])

            if id_list:
                results.append({
                    "rsid": rsid,
                    "new_publications": id_list,
                    "count": len(id_list),
                })
        except Exception:
            logger.debug("NCBI variant update query failed for %s", rsid, exc_info=True)

    return results


# ── HMP oral microbiome data query ──────────────────────────────────────────


def query_hmp_oral_data(
    body_site: str = "oral",
    client: httpx.Client | None = None,
) -> dict:
    """Query the Human Microbiome Project for oral-specific reference data.

    Returns summary statistics for comparison with user oral microbiome data.
    """
    if client is None:
        try:
            client = httpx.Client(timeout=15)
        except Exception:
            return {}

    # HMP reference data endpoint (DACC portal)
    try:
        # Query HMP reference genome catalog
        resp = client.get(
            "https://portal.hmpdacc.org/api/files",
            params={
                "filters": json.dumps({
                    "op": "and",
                    "content": [
                        {"op": "=", "content": {"field": "body_site", "value": body_site}},
                    ]
                }),
                "size": 5,
                "format": "json",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "body_site": body_site,
                "total_samples": data.get("pagination", {}).get("total", 0),
                "files": data.get("data", [])[:5],
            }
    except Exception:
        logger.debug("HMP oral data query failed", exc_info=True)

    # Fallback: return curated oral microbiome reference data
    return _get_oral_reference_data()


def _get_oral_reference_data() -> dict:
    """Curated oral microbiome reference data from published HMP studies."""
    return {
        "body_site": "oral",
        "source": "HMP reference (curated)",
        "healthy_oral_composition": {
            "Streptococcus": {"mean_abundance": 0.25, "range": [0.10, 0.45]},
            "Haemophilus": {"mean_abundance": 0.12, "range": [0.05, 0.20]},
            "Neisseria": {"mean_abundance": 0.10, "range": [0.03, 0.18]},
            "Veillonella": {"mean_abundance": 0.09, "range": [0.04, 0.15]},
            "Prevotella": {"mean_abundance": 0.08, "range": [0.02, 0.20]},
            "Rothia": {"mean_abundance": 0.06, "range": [0.02, 0.12]},
            "Fusobacterium": {"mean_abundance": 0.05, "range": [0.01, 0.10]},
            "Actinomyces": {"mean_abundance": 0.04, "range": [0.01, 0.08]},
            "Porphyromonas": {"mean_abundance": 0.03, "range": [0.005, 0.08]},
            "Treponema": {"mean_abundance": 0.02, "range": [0.001, 0.06]},
        },
        "periodontal_pathogens": [
            "Porphyromonas gingivalis",
            "Treponema denticola",
            "Tannerella forsythia",
            "Aggregatibacter actinomycetemcomitans",
            "Fusobacterium nucleatum",
        ],
        "caries_associated": [
            "Streptococcus mutans",
            "Lactobacillus spp.",
            "Scardovia wiggsiae",
            "Bifidobacterium dentium",
        ],
        "healthy_diversity": {
            "shannon_min": 3.0,
            "shannon_max": 5.5,
            "mean_species_count": 200,
        },
    }


def anonymize_data_hash(data: dict) -> str:
    """Create a deterministic hash of data for blockchain storage.

    Strips PII fields before hashing. Returns hex-encoded SHA-256.
    """
    pii_fields = {"email", "name", "phone", "address", "ssn", "date_of_birth", "dob"}
    sanitized = {k: v for k, v in data.items() if k.lower() not in pii_fields}
    canonical = json.dumps(sanitized, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()
