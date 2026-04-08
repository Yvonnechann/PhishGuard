import logging

import requests

logger = logging.getLogger("phishguard.threat_intel")

_GOPLUS_URL = "https://api.gopluslabs.io/api/v1/address_security/{}?chain_id=1"
_CRYPTOSCAMDB_URL = "https://api.cryptoscamdb.org/v1/check/{}"

_GOPLUS_FLAGS = {
    "phishing_activities", "stealing_attack", "blacklist_doubt",
    "fake_token", "fake_kyc", "fake_standard_interface",
    "honeypot_related_address", "sanctioned", "cybercrime",
    "financial_crime", "money_laundering", "blackmail_activities",
    "malicious_mining_activities", "mixer", "darkweb_transactions",
}


def check_threat_intel(address: str) -> dict:
    addr = address.lower()

    # ── GoPlus ────────────────────────────────────────────────────────────────
    goplus_flagged = False
    try:
        resp = requests.get(_GOPLUS_URL.format(addr), timeout=5)
        resp.raise_for_status()
        result = resp.json().get("result", {})
        # GoPlus returns flags directly under result: {"result": {"cybercrime":"0", ...}}
        if isinstance(result, dict):
            goplus_flagged = any(result.get(flag) == "1" for flag in _GOPLUS_FLAGS)
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
