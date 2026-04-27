import logging
import os
import re

import requests
from fastapi import HTTPException

from config import ETHERSCAN_BASE, ETHERSCAN_CHAIN_ID

_ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')

logger = logging.getLogger("phishguard.validator")


def validate_and_detect_type(address: str) -> tuple[str, str]:
    """Return (analysis_type, bytecode_hex) so callers can reuse the bytecode."""
    if not _ADDRESS_RE.match(address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")
    try:
        r = requests.get(ETHERSCAN_BASE, params={
            "chainid": ETHERSCAN_CHAIN_ID,
            "module": "proxy",
            "action": "eth_getCode",
            "address": address,
            "tag": "latest",
            "apikey": os.getenv("ETHERSCAN_API_KEY", ""),
        }, timeout=10)
        result = r.json().get("result", "0x")
        bytecode_hex = result if isinstance(result, str) and result.startswith("0x") else "0x"

        # Bytecode length in bytes: subtract "0x" prefix and divide by 2
        bytecode_bytes = (len(bytecode_hex) - 2) // 2

        if bytecode_bytes > 100:
            # Substantial bytecode → real contract (verified or not).
            # EIP-7702 EOAs have only ~23 bytes, so this threshold safely excludes them.
            return "contract", bytecode_hex

        if bytecode_bytes > 0:
            # Short bytecode (1–100 bytes): could be EIP-7702 EOA.
            # Use getsourcecode as a tiebreaker.
            try:
                src_r = requests.get(ETHERSCAN_BASE, params={
                    "chainid": ETHERSCAN_CHAIN_ID,
                    "module": "contract",
                    "action": "getsourcecode",
                    "address": address,
                    "apikey": os.getenv("ETHERSCAN_API_KEY", ""),
                }, timeout=10)
                src_data = src_r.json().get("result", [])
                if isinstance(src_data, list) and len(src_data) > 0:
                    entry = src_data[0]
                    contract_name = entry.get("ContractName", "").strip()
                    abi = entry.get("ABI", "").strip()
                    if (contract_name
                            and abi
                            and abi != "Contract source code not verified"):
                        return "contract", bytecode_hex
            except Exception as exc:
                logger.warning(f"getsourcecode secondary check failed for {address}: {exc}")
            return "wallet", "0x"

        return "wallet", "0x"
    except Exception:
        return "wallet", "0x"
