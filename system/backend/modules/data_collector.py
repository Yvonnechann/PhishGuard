import json
import logging
import os

import requests

from config import APPROVAL_TOPIC, ETHERSCAN_BASE, ETHERSCAN_CHAIN_ID, TX_LIMIT

logger = logging.getLogger("phishguard.data_collector")


def _etherscan_get(params: dict) -> dict:
    params["chainid"] = ETHERSCAN_CHAIN_ID
    params["apikey"] = os.environ.get("ETHERSCAN_API_KEY", "")
    try:
        resp = requests.get(ETHERSCAN_BASE, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning(f"Etherscan request failed: {exc}")
        return {"status": "0", "result": []}


def _safe_txlist(raw: dict) -> list:
    """Return filtered tx list regardless of status field.

    Etherscan V2 returns status='0' with message='No transactions found'
    and an empty list — that is valid, not an error.
    """
    result = raw.get("result", [])
    if not isinstance(result, list):
        return []
    return [
        {**tx, "from": tx.get("from", "").lower(), "to": tx.get("to", "").lower()}
        for tx in result
        if tx.get("isError") == "0"
    ]


def collect_wallet_data(address: str) -> dict:
    addr = address.lower()

    # Transactions
    txs_raw = _etherscan_get({
        "module": "account",
        "action": "txlist",
        "address": addr,
        "startblock": 0,
        "endblock": 99999999,
        "offset": TX_LIMIT,
        "sort": "desc",
        "page": 1,
    })
    txs = _safe_txlist(txs_raw)

    # Token transfers
    tokentxs_raw = _etherscan_get({
        "module": "account",
        "action": "tokentx",
        "address": addr,
        "offset": 200,
        "sort": "desc",
        "page": 1,
    })
    tokentxs_result = tokentxs_raw.get("result", [])
    if not isinstance(tokentxs_result, list):
        tokentxs_result = []
    tokentxs = tokentxs_result

    # Balance
    balance_raw = _etherscan_get({
        "module": "account",
        "action": "balance",
        "address": addr,
        "tag": "latest",
    })
    balance_result = balance_raw.get("result", "0")
    if not isinstance(balance_result, str) or not balance_result.isdigit():
        balance_result = "0"
    balance_wei = balance_result

    # Approval logs (getLogs)
    logs_raw = _etherscan_get({
        "module": "logs",
        "action": "getLogs",
        "topic0": APPROVAL_TOPIC,
        "topic1": "0x000000000000000000000000" + addr[2:],  # owner = address
        "fromBlock": 0,
        "toBlock": "latest",
    })
    logs_result = logs_raw.get("result", [])
    if not isinstance(logs_result, list):
        logs_result = []

    approval_logs = []
    for log in logs_result:
        try:
            topics = log.get("topics", [])
            if len(topics) < 3:
                continue
            owner = "0x" + topics[1][-40:]
            spender = "0x" + topics[2][-40:]
            data = log.get("data", "0x0")
            amount = int(data, 16) if data and data != "0x" else 0
            raw_ts = log.get("timeStamp", "0x0")
            # timeStamp from getLogs is HEX
            timestamp = int(raw_ts, 16)
            token_contract = log.get("address", "").lower()
            approval_logs.append({
                "owner": owner.lower(),
                "spender": spender.lower(),
                "amount": amount,
                "timestamp": timestamp,
                "token_contract": token_contract,
            })
        except Exception as exc:
            logger.warning(f"Failed to decode approval log: {exc}")
            continue

    return {
        "txs": txs,
        "tokentxs": tokentxs,
        "balance_wei": balance_wei,
        "approval_logs": approval_logs,
    }


def collect_contract_data(address: str) -> dict:
    addr = address.lower()

    # Bytecode via Etherscan V2 proxy (no RPC needed)
    bytecode_hex = "0x"
    try:
        code_raw = _etherscan_get({
            "module": "proxy",
            "action": "eth_getCode",
            "address": addr,
            "tag": "latest",
        })
        result = code_raw.get("result", "0x")
        if isinstance(result, str) and result.startswith("0x"):
            bytecode_hex = result
    except Exception as exc:
        logger.warning(f"Etherscan eth_getCode failed: {exc}")

    # ABI
    abi_raw = _etherscan_get({
        "module": "contract",
        "action": "getabi",
        "address": addr,
    })
    abi_result = abi_raw.get("result", "")
    abi_list: list = []
    if isinstance(abi_result, str) and abi_result.startswith("["):
        try:
            abi_list = json.loads(abi_result)
        except Exception:
            abi_list = []

    # Source / verified
    src_raw = _etherscan_get({
        "module": "contract",
        "action": "getsourcecode",
        "address": addr,
    })
    src_result = src_raw.get("result", [])
    is_verified = 0
    if isinstance(src_result, list) and len(src_result) > 0:
        source_code = src_result[0].get("SourceCode", "")
        is_verified = 1 if isinstance(source_code, str) and source_code.strip() else 0

    # Transactions
    txs_raw = _etherscan_get({
        "module": "account",
        "action": "txlist",
        "address": addr,
        "startblock": 0,
        "endblock": 99999999,
        "offset": TX_LIMIT,
        "sort": "desc",
        "page": 1,
    })
    txs = _safe_txlist(txs_raw)

    return {
        "bytecode_hex": bytecode_hex,
        "abi_list": abi_list,
        "is_verified": is_verified,
        "txs": txs,
    }
