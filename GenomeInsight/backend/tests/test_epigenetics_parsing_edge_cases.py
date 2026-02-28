"""Additional edge-case tests for epigenetics parsing and wearable OAuth flow."""

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.utils.epigenetics_analyzer import (
    ParsedRegion,
    annotate_feature_type,
    cross_reference_genome,
    parse_bed,
    parse_methylation_csv,
)
from app.utils.wearable_client import (
    TerraAuthResult,
    TerraTokens,
    encrypt_token,
    decrypt_token,
    exchange_terra_token,
    generate_terra_auth_url,
    pull_terra_data,
    refresh_terra_token,
    SUPPORTED_PROVIDERS,
)


# ══════════════════════════════════════════════════════════════════════════════
# Epigenetics BED parsing edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestBedParsingEdgeCases:
    def test_unicode_characters_in_bed(self):
        data = "chr1\t100\t200\tgene_ñ\t10\n".encode("utf-8")
        regions = parse_bed(data)
        assert len(regions) == 1
        assert regions[0].name == "gene_ñ"

    def test_windows_line_endings(self):
        data = b"chr1\t100\t200\r\nchr2\t300\t400\r\n"
        regions = parse_bed(data)
        assert len(regions) == 2

    def test_mixed_headers_and_data(self):
        data = (
            b"track name=test description='my test'\n"
            b"browser position chr1:100-200\n"
            b"#chrom\tstart\tend\n"
            b"chr1\t100\t200\n"
            b"chr1\t300\t400\n"
        )
        regions = parse_bed(data)
        assert len(regions) == 2

    def test_tab_and_space_separated(self):
        # Only tab-separated should work for BED
        data = b"chr1\t100\t200\n"
        regions = parse_bed(data)
        assert len(regions) == 1

    def test_large_coordinates(self):
        data = b"chr1\t248956422\t248956423\n"  # End of chr1
        regions = parse_bed(data)
        assert len(regions) == 1
        assert regions[0].start_pos == 248956422

    def test_zero_length_region_skipped(self):
        data = b"chr1\t100\t100\n"  # start == end
        regions = parse_bed(data)
        assert len(regions) == 0

    def test_non_h3_assay_type_ignored(self):
        data = b"chr1\t100\t200\tpeak1\t10\n"
        regions = parse_bed(data, assay_type="ATAC-seq")
        assert regions[0].histone_mark is None

    def test_all_lines_malformed(self):
        data = b"bad\nworse\nterrible\n"
        regions = parse_bed(data)
        assert len(regions) == 0


# ══════════════════════════════════════════════════════════════════════════════
# Methylation CSV parsing edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestMethylationCsvEdgeCases:
    def test_hash_chr_header(self):
        data = b"#chr,start,end,beta_value\nchr1,1000,1001,0.75\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 1
        assert regions[0].chromosome == "chr1"

    def test_uppercase_headers(self):
        data = b"CHROM,POSITION,BETA\nchr5,5000,0.45\n"
        # Our aliases are lowercase; headers should be matched case-insensitively
        regions = parse_methylation_csv(data)
        assert len(regions) == 1

    def test_chromstart_chromend_headers(self):
        data = b"chr,chromStart,chromEnd,avg_beta,gene_name\nchr1,1000,1500,0.3,TP53\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 1
        assert regions[0].start_pos == 1000
        assert regions[0].end_pos == 1500
        assert regions[0].name == "TP53"

    def test_empty_rows_skipped(self):
        data = b"chr,start,beta\n\nchr1,1000,0.5\n\n\nchr2,2000,0.8\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 2

    def test_empty_chromosome_skipped(self):
        data = b"chr,start,beta\n,1000,0.5\nchr1,2000,0.8\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 1
        assert regions[0].chromosome == "chr1"

    def test_beta_boundary_values(self):
        data = b"chr,start,beta\nchr1,100,0.0\nchr1,200,1.0\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 2
        assert regions[0].methylation_beta == 0.0
        assert regions[1].methylation_beta == 1.0

    def test_extra_columns_ignored(self):
        data = b"chr,start,beta,extra1,extra2\nchr1,100,0.5,foo,bar\n"
        regions = parse_methylation_csv(data)
        assert len(regions) == 1


# ══════════════════════════════════════════════════════════════════════════════
# Feature annotation edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestAnnotationEdgeCases:
    def test_brca1_promoter(self):
        # BRCA1 at chr17:43044295-43170245
        region = ParsedRegion("chr17", 43044000, 43045000)
        feature, gene = annotate_feature_type(region)
        assert feature == "promoter"
        assert gene == "BRCA1"

    def test_apoe_gene_body(self):
        # APOE at chr19:44905754-44909393; promoter window is ±2000 from start
        # Use a coordinate well past the promoter window
        region = ParsedRegion("chr19", 44908500, 44909000)
        feature, gene = annotate_feature_type(region)
        assert feature == "gene_body"
        assert gene == "APOE"

    def test_cross_reference_multiple_variants_same_gene(self):
        """Multiple variants in the same gene should produce multiple overlays."""
        regions = [ParsedRegion("chr1", 11785000, 11786000, methylation_beta=0.85)]
        annotations = {
            "chr1:11785000-11786000": {
                "feature_type": "promoter",
                "nearest_gene": "MTHFR",
                "state": "ReprPC",
            }
        }
        variants = [
            {"rsid": "rs1801133", "gene": "MTHFR", "genotype": "T/T", "risk_level": "elevated"},
            {"rsid": "rs1801131", "gene": "MTHFR", "genotype": "A/C", "risk_level": "average"},
        ]
        overlays = cross_reference_genome(regions, annotations, variants)
        assert len(overlays) == 2
        rsids = {o.variant_rsid for o in overlays}
        assert rsids == {"rs1801133", "rs1801131"}


# ══════════════════════════════════════════════════════════════════════════════
# Wearable OAuth mock tests
# ══════════════════════════════════════════════════════════════════════════════


class TestWearableOAuthMock:
    def test_all_providers_generate_auth_url(self):
        """Every supported provider should return a valid auth result."""
        for provider in SUPPORTED_PROVIDERS:
            result = generate_terra_auth_url(
                provider=provider,
                terra_api_key="",
                redirect_uri="http://localhost/callback",
            )
            assert isinstance(result, TerraAuthResult)
            assert result.provider == provider
            assert "http" in result.auth_url

    def test_exchange_token_with_mock_http(self):
        """Mock Terra API token exchange."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "user": {
                "user_id": "terra-user-abc",
                "access_token": "access-123",
                "refresh_token": "refresh-456",
            }
        }
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp

        tokens = exchange_terra_token(
            code="auth-code-xyz",
            terra_api_key="test-key",
            terra_dev_id="dev-id",
            client=mock_client,
        )
        assert tokens.terra_user_id == "terra-user-abc"
        assert tokens.access_token == "access-123"
        assert tokens.refresh_token == "refresh-456"

    def test_dev_fallback_creates_mock_tokens(self):
        """Without API key, exchange returns mock tokens."""
        tokens = exchange_terra_token(
            code="test",
            terra_api_key="",
            terra_dev_id="",
        )
        assert tokens.terra_user_id.startswith("terra_mock_")
        assert tokens.access_token.startswith("mock_access_")

    def test_token_encryption_with_varied_lengths(self):
        """Encrypt/decrypt tokens of various lengths."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        dek = AESGCM.generate_key(bit_length=256)
        for token in ["a", "x" * 100, "special-chars-!@#$%^&*()", ""]:
            encrypted = encrypt_token(token, dek)
            decrypted = decrypt_token(encrypted, dek)
            assert decrypted == token

    def test_wrong_key_fails_decrypt(self):
        """Decrypting with wrong key should raise."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        dek1 = AESGCM.generate_key(bit_length=256)
        dek2 = AESGCM.generate_key(bit_length=256)
        encrypted = encrypt_token("secret-token", dek1)
        with pytest.raises(Exception):
            decrypt_token(encrypted, dek2)

    def test_pull_terra_data_dev_fallback(self):
        """Without API credentials, pull_terra_data returns mock data."""
        result = pull_terra_data(
            terra_user_id="test-user",
            data_type="activity",
            start_date=date(2026, 2, 27),
            end_date=date(2026, 2, 28),
            terra_api_key="",
            terra_dev_id="",
        )
        # Should return mock data without raising
        assert isinstance(result, (dict, list))
