import logging

import requests

logger = logging.getLogger("phishguard.threat_intel")

_GOPLUS_URL = "https://api.gopluslabs.io/api/v1/address_security/{}?chain_id=1"

_GOPLUS_FLAGS = {
    "phishing_activities", "stealing_attack", "blacklist_doubt",
    "fake_token", "fake_kyc", "fake_standard_interface",
    "honeypot_related_address", "sanctioned", "cybercrime",
    "financial_crime", "money_laundering", "blackmail_activities",
    "malicious_mining_activities", "mixer", "darkweb_transactions",
    "number_of_malicious_contracts_created", "reinit",
}


def check_threat_intel(address: str, scam_set=None) -> dict:
    addr = address.lower()

    # ── GoPlus ────────────────────────────────────────────────────────────────
    goplus_flagged = False
    goplus_available = True
    try:
        resp = requests.get(_GOPLUS_URL.format(addr), timeout=5)
        resp.raise_for_status()
        result = resp.json().get("result", {})
        if isinstance(result, dict):
            goplus_flagged = any(result.get(flag) == "1" for flag in _GOPLUS_FLAGS)
    except Exception as exc:
        logger.warning(f"GoPlus call failed for {addr}: {exc}")
        goplus_available = False

    # ── ScamSniffer (pre-loaded set at startup) ───────────────────────────────
    # scam_set is None when the startup fetch failed — treat as unavailable
    scamsniffer_available = scam_set is not None
    scamsniffer_flagged = addr in scam_set if scamsniffer_available else False

    scamdb_match = goplus_flagged or scamsniffer_flagged

    return {
        "goplus_flagged": goplus_flagged,
        "goplus_available": goplus_available,
        "scamsniffer_flagged": scamsniffer_flagged,
        "scamsniffer_available": scamsniffer_available,
        "scamdb_match": scamdb_match,
    }
