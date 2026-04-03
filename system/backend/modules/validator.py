import logging
import os
import re

import requests
from fastapi import HTTPException

from config import ETHERSCAN_BASE, ETHERSCAN_CHAIN_ID

_ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')

logger = logging.getLogger("phishguard.validator")


def validate_and_detect_type(address: str) -> str:
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

        if isinstance(result, str) and result.startswith("0x") and len(result) > 2:
            # Secondary confirmation — only classify as contract if getsourcecode
            # returns a non-empty ContractName AND a real ABI.
            # This guards against EIP-7702 EOAs and other minimal-bytecode addresses.
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
                        return "contract"
            except Exception as exc:
                logger.warning(f"getsourcecode secondary check failed for {address}: {exc}")
            return "wallet"

        return "wallet"
    except Exception:
        return "wallet"
