import logging

import requests

logger = logging.getLogger("phishguard.threat_intel")

_GOPLUS_URL = "https://api.gopluslabs.io/api/v1/address_security/{}?chain_id=1"
_CRYPTOSCAMDB_URL = "https://api.cryptoscamdb.org/v1/check/{}"

_GOPLUS_FLAGS = {"is_phishing_activities", "malicious_behavior", "is_honeypot", "blacklist_doubt"}


def check_threat_intel(address: str) -> dict:
    addr = address.lower()

    # ── GoPlus ────────────────────────────────────────────────────────────────
    goplus_flagged = False
    try:
        resp = requests.get(_GOPLUS_URL.format(addr), timeout=5)
        resp.raise_for_status()
        result = resp.json().get("result", {})
        # GoPlus wraps flags under the address key: {"result": {"0xabc...": {...flags...}}}
        if isinstance(result, dict):
            data = result.get(addr, {})
            if isinstance(data, dict):
                goplus_flagged = any(data.get(flag) == "1" for flag in _GOPLUS_FLAGS)
    except Exception as exc:
        logger.warning(f"GoPlus call failed for {addr}: {exc}")

    # ── CryptoScamDB ──────────────────────────────────────────────────────────
    cryptoscamdb_flagged = False
    try:
        resp = requests.get(_CRYPTOSCAMDB_URL.format(addr), timeout=5)
        resp.raise_for_status()
        body = resp.json()
        if body.get("success") is True:
            result = body.get("result")
            cryptoscamdb_flagged = bool(result)
    except Exception as exc:
        logger.warning(f"CryptoScamDB call failed for {addr}: {exc}")

    scamdb_match = goplus_flagged or cryptoscamdb_flagged

    return {
        "goplus_flagged": goplus_flagged,
        "scamdb_match": scamdb_match,
        "cryptoscamdb_flagged": cryptoscamdb_flagged,
    }
