"""Ethereum blockchain integration for health data ownership and privacy.

Provides:
 1. Web3 connection management (mainnet, testnets, L2s).
 2. Health data NFT minting (ERC-721 for data ownership).
 3. Data hash storage on-chain (privacy-preserving audit trail).
 4. Anonymized data marketplace (list/purchase anonymized datasets).
 5. Transaction monitoring and receipt handling.

IMPORTANT: Private keys should NEVER be hardcoded. They are loaded from
environment variables or a secure vault in production.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class TransactionResult:
    """Result of a blockchain transaction."""

    success: bool = False
    tx_hash: str = ""
    block_number: int = 0
    gas_used: int = 0
    token_id: int | None = None
    error: str = ""


@dataclass
class DataListing:
    """An anonymized data listing on the marketplace."""

    token_id: int = 0
    data_type: str = ""
    data_hash: str = ""
    price_wei: str = "0"
    seller: str = ""
    is_active: bool = True


# ── Smart contract ABI (simplified Health Data NFT) ─────────────────────────

# This ABI represents a custom ERC-721 contract for health data ownership.
# In production, deploy this contract and reference its address.
HEALTH_DATA_NFT_ABI = json.loads("""[
    {
        "inputs": [{"name": "to", "type": "address"}, {"name": "dataHash", "type": "bytes32"}, {"name": "metadataURI", "type": "string"}],
        "name": "mintHealthRecord",
        "outputs": [{"name": "tokenId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "dataHash", "type": "bytes32"}],
        "name": "storeDataHash",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "tokenURI",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}, {"name": "priceWei", "type": "uint256"}],
        "name": "listForSale",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "purchaseData",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"name": "tokenId", "type": "uint256"}],
        "name": "delistFromSale",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"name": "dataHash", "type": "bytes32"}],
        "name": "getDataRecord",
        "outputs": [{"name": "owner", "type": "address"}, {"name": "timestamp", "type": "uint256"}, {"name": "metadataURI", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "anonymous": false,
        "inputs": [
            {"indexed": true, "name": "tokenId", "type": "uint256"},
            {"indexed": true, "name": "owner", "type": "address"},
            {"indexed": false, "name": "dataHash", "type": "bytes32"}
        ],
        "name": "HealthRecordMinted",
        "type": "event"
    },
    {
        "anonymous": false,
        "inputs": [
            {"indexed": true, "name": "tokenId", "type": "uint256"},
            {"indexed": false, "name": "priceWei", "type": "uint256"}
        ],
        "name": "DataListedForSale",
        "type": "event"
    },
    {
        "anonymous": false,
        "inputs": [
            {"indexed": true, "name": "tokenId", "type": "uint256"},
            {"indexed": true, "name": "buyer", "type": "address"},
            {"indexed": false, "name": "priceWei", "type": "uint256"}
        ],
        "name": "DataPurchased",
        "type": "event"
    }
]""")

# ── Chain configuration ─────────────────────────────────────────────────────

CHAIN_CONFIG = {
    1: {"name": "Ethereum Mainnet", "explorer": "https://etherscan.io"},
    5: {"name": "Goerli Testnet", "explorer": "https://goerli.etherscan.io"},
    11155111: {"name": "Sepolia Testnet", "explorer": "https://sepolia.etherscan.io"},
    137: {"name": "Polygon Mainnet", "explorer": "https://polygonscan.com"},
    42161: {"name": "Arbitrum One", "explorer": "https://arbiscan.io"},
    8453: {"name": "Base", "explorer": "https://basescan.org"},
}


# ── Web3 connection ─────────────────────────────────────────────────────────


def get_web3_connection(rpc_url: str = ""):
    """Create a Web3 connection to an Ethereum node.

    Args:
        rpc_url: The RPC endpoint URL. Defaults to ETH_RPC_URL env var.

    Returns:
        Connected Web3 instance or None if web3 is not installed.
    """
    try:
        from web3 import Web3
    except ImportError:
        logger.error("web3 package not installed. Run: pip install web3")
        return None

    if not rpc_url:
        rpc_url = os.environ.get("ETH_RPC_URL", "")

    if not rpc_url:
        logger.warning("No Ethereum RPC URL configured")
        return None

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if w3.is_connected():
        logger.info("Connected to Ethereum node: chain_id=%d", w3.eth.chain_id)
        return w3

    logger.error("Failed to connect to Ethereum node at %s", rpc_url)
    return None


def get_contract(w3, contract_address: str = ""):
    """Get a contract instance for the Health Data NFT.

    Args:
        w3: Connected Web3 instance.
        contract_address: Deployed contract address. Defaults to env var.

    Returns:
        Contract instance or None.
    """
    if not contract_address:
        contract_address = os.environ.get("HEALTH_NFT_CONTRACT_ADDRESS", "")

    if not contract_address:
        logger.warning("No Health NFT contract address configured")
        return None

    try:
        from web3 import Web3
        checksum_addr = Web3.to_checksum_address(contract_address)
        return w3.eth.contract(address=checksum_addr, abi=HEALTH_DATA_NFT_ABI)
    except Exception as e:
        logger.error("Failed to load contract: %s", e)
        return None


# ── Transaction helpers ─────────────────────────────────────────────────────


def _build_and_send_tx(w3, contract_fn, account_address: str, private_key: str,
                       value_wei: int = 0) -> TransactionResult:
    """Build, sign, and send a transaction.

    Args:
        w3: Connected Web3 instance.
        contract_fn: Bound contract function call.
        account_address: Sender's address.
        private_key: Sender's private key.
        value_wei: ETH value to send (for payable functions).

    Returns:
        TransactionResult with tx hash and status.
    """
    try:
        from web3 import Web3

        nonce = w3.eth.get_transaction_count(
            Web3.to_checksum_address(account_address)
        )

        tx_params = {
            "from": Web3.to_checksum_address(account_address),
            "nonce": nonce,
            "gas": 300_000,
            "maxFeePerGas": w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": w3.to_wei("2", "gwei"),
            "chainId": w3.eth.chain_id,
        }
        if value_wei > 0:
            tx_params["value"] = value_wei

        tx = contract_fn.build_transaction(tx_params)

        # Estimate gas more accurately
        try:
            estimated_gas = w3.eth.estimate_gas(tx)
            tx["gas"] = int(estimated_gas * 1.2)  # 20% buffer
        except Exception:
            pass  # Use default 300k

        signed = w3.eth.account.sign_transaction(tx, private_key=private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        return TransactionResult(
            success=receipt["status"] == 1,
            tx_hash=receipt["transactionHash"].hex(),
            block_number=receipt["blockNumber"],
            gas_used=receipt["gasUsed"],
        )
    except Exception as e:
        logger.error("Transaction failed: %s", e, exc_info=True)
        return TransactionResult(success=False, error=str(e))


# ── Health data NFT operations ──────────────────────────────────────────────


def mint_health_record(
    data_hash: str,
    metadata_uri: str = "",
    rpc_url: str = "",
    contract_address: str = "",
    account_address: str = "",
    private_key: str = "",
) -> TransactionResult:
    """Mint a health data NFT representing ownership of a dataset.

    Args:
        data_hash: SHA-256 hash of the anonymized health data.
        metadata_uri: IPFS URI pointing to encrypted data metadata.
        rpc_url: Ethereum RPC endpoint.
        contract_address: Deployed NFT contract address.
        account_address: User's Ethereum address.
        private_key: User's private key for signing.

    Returns:
        TransactionResult with minted token ID.
    """
    w3 = get_web3_connection(rpc_url)
    if not w3:
        return TransactionResult(success=False, error="No Web3 connection")

    contract = get_contract(w3, contract_address)
    if not contract:
        return TransactionResult(success=False, error="No contract configured")

    if not account_address:
        account_address = os.environ.get("ETH_ACCOUNT_ADDRESS", "")
    if not private_key:
        private_key = os.environ.get("ETH_PRIVATE_KEY", "")

    if not account_address or not private_key:
        return TransactionResult(
            success=False, error="Ethereum account credentials not configured"
        )

    # Convert hex hash to bytes32
    data_hash_bytes = bytes.fromhex(data_hash.replace("0x", ""))
    if len(data_hash_bytes) != 32:
        return TransactionResult(success=False, error="Invalid data hash length")

    from web3 import Web3
    contract_fn = contract.functions.mintHealthRecord(
        Web3.to_checksum_address(account_address),
        data_hash_bytes,
        metadata_uri or "",
    )

    result = _build_and_send_tx(w3, contract_fn, account_address, private_key)

    # Parse token ID from event logs if successful
    if result.success and result.tx_hash:
        try:
            receipt = w3.eth.get_transaction_receipt(bytes.fromhex(result.tx_hash))
            logs = contract.events.HealthRecordMinted().process_receipt(receipt)
            if logs:
                result.token_id = logs[0]["args"]["tokenId"]
        except Exception:
            logger.debug("Could not parse mint event logs", exc_info=True)

    return result


def store_data_hash(
    data_hash: str,
    rpc_url: str = "",
    contract_address: str = "",
    account_address: str = "",
    private_key: str = "",
) -> TransactionResult:
    """Store a data hash on-chain for auditability without minting an NFT.

    Cheaper than minting (no token created), but creates an immutable
    on-chain record that the data existed at this point in time.
    """
    w3 = get_web3_connection(rpc_url)
    if not w3:
        return TransactionResult(success=False, error="No Web3 connection")

    contract = get_contract(w3, contract_address)
    if not contract:
        return TransactionResult(success=False, error="No contract configured")

    if not account_address:
        account_address = os.environ.get("ETH_ACCOUNT_ADDRESS", "")
    if not private_key:
        private_key = os.environ.get("ETH_PRIVATE_KEY", "")

    if not account_address or not private_key:
        return TransactionResult(
            success=False, error="Ethereum account credentials not configured"
        )

    data_hash_bytes = bytes.fromhex(data_hash.replace("0x", ""))
    if len(data_hash_bytes) != 32:
        return TransactionResult(success=False, error="Invalid data hash length")

    contract_fn = contract.functions.storeDataHash(data_hash_bytes)
    return _build_and_send_tx(w3, contract_fn, account_address, private_key)


# ── Marketplace operations ──────────────────────────────────────────────────


def list_data_for_sale(
    token_id: int,
    price_wei: int,
    rpc_url: str = "",
    contract_address: str = "",
    account_address: str = "",
    private_key: str = "",
) -> TransactionResult:
    """List an anonymized health data NFT for sale on the marketplace.

    The buyer receives access to the encrypted data; decryption key is
    shared via a separate off-chain channel after purchase confirmation.
    """
    w3 = get_web3_connection(rpc_url)
    if not w3:
        return TransactionResult(success=False, error="No Web3 connection")

    contract = get_contract(w3, contract_address)
    if not contract:
        return TransactionResult(success=False, error="No contract configured")

    if not account_address:
        account_address = os.environ.get("ETH_ACCOUNT_ADDRESS", "")
    if not private_key:
        private_key = os.environ.get("ETH_PRIVATE_KEY", "")

    if not account_address or not private_key:
        return TransactionResult(
            success=False, error="Ethereum account credentials not configured"
        )

    contract_fn = contract.functions.listForSale(token_id, price_wei)
    return _build_and_send_tx(w3, contract_fn, account_address, private_key)


def purchase_data(
    token_id: int,
    price_wei: int,
    rpc_url: str = "",
    contract_address: str = "",
    account_address: str = "",
    private_key: str = "",
) -> TransactionResult:
    """Purchase an anonymized health data NFT from the marketplace."""
    w3 = get_web3_connection(rpc_url)
    if not w3:
        return TransactionResult(success=False, error="No Web3 connection")

    contract = get_contract(w3, contract_address)
    if not contract:
        return TransactionResult(success=False, error="No contract configured")

    if not account_address:
        account_address = os.environ.get("ETH_ACCOUNT_ADDRESS", "")
    if not private_key:
        private_key = os.environ.get("ETH_PRIVATE_KEY", "")

    if not account_address or not private_key:
        return TransactionResult(
            success=False, error="Ethereum account credentials not configured"
        )

    contract_fn = contract.functions.purchaseData(token_id)
    return _build_and_send_tx(
        w3, contract_fn, account_address, private_key, value_wei=price_wei
    )


# ── Query functions (read-only, no gas) ─────────────────────────────────────


def get_token_owner(
    token_id: int,
    rpc_url: str = "",
    contract_address: str = "",
) -> str:
    """Query the owner of a health data token."""
    w3 = get_web3_connection(rpc_url)
    if not w3:
        return ""

    contract = get_contract(w3, contract_address)
    if not contract:
        return ""

    try:
        return contract.functions.ownerOf(token_id).call()
    except Exception as e:
        logger.debug("ownerOf query failed: %s", e)
        return ""


def get_data_record(
    data_hash: str,
    rpc_url: str = "",
    contract_address: str = "",
) -> dict:
    """Query an on-chain data record by its hash."""
    w3 = get_web3_connection(rpc_url)
    if not w3:
        return {}

    contract = get_contract(w3, contract_address)
    if not contract:
        return {}

    try:
        data_hash_bytes = bytes.fromhex(data_hash.replace("0x", ""))
        owner, timestamp, uri = contract.functions.getDataRecord(data_hash_bytes).call()
        return {
            "owner": owner,
            "timestamp": timestamp,
            "metadata_uri": uri,
            "data_hash": data_hash,
        }
    except Exception as e:
        logger.debug("getDataRecord query failed: %s", e)
        return {}


def get_explorer_url(tx_hash: str, chain_id: int = 1) -> str:
    """Get the block explorer URL for a transaction."""
    config = CHAIN_CONFIG.get(chain_id, CHAIN_CONFIG[1])
    return f"{config['explorer']}/tx/0x{tx_hash.replace('0x', '')}"


# ── Offline / simulation mode ───────────────────────────────────────────────


def simulate_blockchain_store(data_hash: str, data_type: str) -> dict:
    """Simulate blockchain storage when no Ethereum node is available.

    Returns a mock transaction result for development/testing.
    """
    import hashlib
    import time

    mock_tx_hash = hashlib.sha256(
        f"{data_hash}:{time.time()}".encode()
    ).hexdigest()

    return {
        "success": True,
        "tx_hash": f"0x{mock_tx_hash}",
        "block_number": 0,
        "gas_used": 0,
        "token_id": None,
        "chain_id": 0,
        "mode": "simulation",
        "data_hash": data_hash,
        "data_type": data_type,
        "note": (
            "This is a simulated transaction. Configure ETH_RPC_URL and "
            "HEALTH_NFT_CONTRACT_ADDRESS for real blockchain integration."
        ),
    }
