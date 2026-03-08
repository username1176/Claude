"""Tests for blockchain utility functions (testnet/simulation mode)."""

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    flask_app = create_app("testing")
    with flask_app.app_context():
        _db.create_all()
    yield flask_app
    with flask_app.app_context():
        _db.session.remove()
        _db.drop_all()


class TestBlockchainSimulation:
    """Test blockchain utilities in simulation mode (no Ethereum node)."""

    def test_simulate_blockchain_store(self, app):
        from app.utils.blockchain_utils import simulate_blockchain_store

        with app.app_context():
            result = simulate_blockchain_store(
                data_hash="0x" + "ab" * 32,
                data_type="genome",
                user_id="test-user-123",
            )
            assert isinstance(result, dict)
            assert "tx_hash" in result
            assert "token_id" in result
            assert result["tx_hash"].startswith("0x")

    def test_get_web3_connection_no_rpc(self, app):
        from app.utils.blockchain_utils import get_web3_connection

        with app.app_context():
            w3 = get_web3_connection()
            # Without ETH_RPC_URL set, should return None or a disconnected instance
            assert w3 is None or not w3.is_connected()

    def test_store_data_hash_simulation(self, app):
        """When no Ethereum node is configured, store_data_hash should fall back to simulation."""
        from app.utils.blockchain_utils import store_data_hash

        with app.app_context():
            result = store_data_hash(
                data_hash="0x" + "cd" * 32,
                data_type="blood_panel",
                user_id="test-user-456",
            )
            assert isinstance(result, dict)
            assert "tx_hash" in result or "simulated" in result


class TestDataHashing:
    """Test PII-stripping data hashing."""

    def test_anonymize_data_hash(self, app):
        from app.utils.wgs_analyzer import anonymize_data_hash

        with app.app_context():
            data = {"name": "John Doe", "ssn": "123-45-6789", "genotype": "AA"}
            hash1 = anonymize_data_hash(data)
            hash2 = anonymize_data_hash(data)
            assert isinstance(hash1, str)
            assert len(hash1) == 64  # SHA-256 hex
            assert hash1 == hash2  # Deterministic
