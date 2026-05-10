"""
test_phishguard.py — PhishGuard unit test suite (FYP01–FYP24)

Run from system/backend/:
    pytest test_phishguard.py -v
"""

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from modules.explainer import explain
from modules.fusion import fuse
from modules.ml_inference import predict
from modules.threat_intel import check_threat_intel
from modules.validator import validate_and_detect_type
from main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WALLET_FEATURES = [
    "tx_count_in", "tx_count_out", "tx_count_total",
    "unique_counterparties_lifetime", "fan_in_ratio",
    "median_inter_tx_minutes", "std_inter_tx_minutes",
    "avg_out_value_eth", "std_out_value_eth", "min_in_value_eth",
    "current_eth_balance", "approval_count_total",
    "unlimited_approval_count_lifetime", "unique_spenders_lifetime",
    "approval_concentration_top_spender", "unlimited_approval_rate",
    "token_transfer_count", "cross_token_approval_same_spender_ratio",
    "pagerank_subgraph", "reciprocity_ratio",
    "avg_shortest_path_to_known_scam",
]

CONTRACT_FEATURES = [
    "is_verified", "bytecode_size", "abi_function_count",
    "external_public_function_count", "approval_related_function_flag",
    "permit_related_function_flag", "setApprovalForAll_flag",
    "opcode_freq_CALL", "opcode_freq_DELEGATECALL",
    "opcode_freq_SELFDESTRUCT", "opcode_freq_SSTORE",
    "opcode_freq_JUMPI", "external_call_sites_count",
    "has_create2", "proxy_pattern_detected",
    "approval_then_external_call_pattern",
    "approval_then_state_mutation_pattern",
    "control_flow_complexity_score", "slither_warning_count_total",
    "slither_low_level_call_count", "slither_access_control_issues_count",
]

VALID_ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
CONTRACT_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

# 101 bytes of bytecode (202 hex chars) — exceeds the 100-byte contract threshold
LARGE_BYTECODE = "0x" + "ab" * 101

WALLET_FEATURE_DICT = {k: 0.0 for k in WALLET_FEATURES}
CONTRACT_FEATURE_DICT = {k: 0.0 for k in CONTRACT_FEATURES}

EXPECTED_RESPONSE_FIELDS = {
    "address", "analysis_type", "ml_score", "final_score", "risk_label",
    "goplus_flagged", "goplus_available", "scamsniffer_flagged",
    "scamsniffer_available", "shap_explanation", "raw_features",
}

MOCK_SHAP_EXPLANATION = [
    {
        "feature": "tx_count_in",
        "shap_value": 0.5,
        "direction": "increases_risk",
        "description": "Number of inbound transactions",
    },
    {
        "feature": "fan_in_ratio",
        "shap_value": -0.3,
        "direction": "decreases_risk",
        "description": "Proportion of inbound vs total transactions",
    },
    {
        "feature": "approval_count_total",
        "shap_value": 0.2,
        "direction": "increases_risk",
        "description": "Total token approvals granted lifetime",
    },
]

MOCK_INTEL_CLEAN = {
    "goplus_flagged": False,
    "goplus_available": True,
    "scamsniffer_flagged": False,
    "scamsniffer_available": True,
    "scamdb_match": False,
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _test_lifespan(app):
    """No-op lifespan that sets mock app.state for integration tests."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])

    mock_explainer = MagicMock()
    mock_explainer.shap_values.return_value = np.zeros((1, 21))

    app.state.wallet_model = mock_model
    app.state.contract_model = mock_model
    app.state.wallet_feature_names = WALLET_FEATURES
    app.state.contract_feature_names = CONTRACT_FEATURES
    app.state.wallet_explainer = mock_explainer
    app.state.contract_explainer = mock_explainer
    app.state.wallet_threshold = 0.5486
    app.state.contract_threshold = 0.7413
    app.state.scam_set = set()
    yield


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear in-memory rate limiter storage before every test."""
    from routers.analyze import limiter as _lim
    storage = getattr(_lim, "_storage", None)
    if storage is not None:
        for attr in ("storage", "expirations", "events", "_events", "_entries"):
            obj = getattr(storage, attr, None)
            if isinstance(obj, dict):
                obj.clear()
    yield


@pytest.fixture
def client():
    """TestClient with the real lifespan replaced by a lightweight test setup."""
    _orig = app.router.lifespan_context
    app.router.lifespan_context = _test_lifespan
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.router.lifespan_context = _orig


# ---------------------------------------------------------------------------
# FYP01–FYP05: validate_and_detect_type()
# ---------------------------------------------------------------------------

# FYP01: Address containing a non-hex character raises HTTP 400
def test_FYP01():
    with pytest.raises(HTTPException) as exc_info:
        validate_and_detect_type("0x5b19a172b4ce95310d14f49c3575ed84f9b55bZZ")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid Ethereum address format"


# FYP02: Address shorter than 42 characters raises HTTP 400
def test_FYP02():
    with pytest.raises(HTTPException) as exc_info:
        validate_and_detect_type("0xABCDEF")
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Invalid Ethereum address format"


# FYP03: eth_getCode returns "0x" (no bytecode) → ("wallet", "0x")
def test_FYP03():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": "0x"}
    with patch("modules.validator.requests.get", return_value=mock_resp):
        result = validate_and_detect_type(VALID_ADDRESS)
    assert result == ("wallet", "0x")


# FYP04: eth_getCode returns bytecode > 100 bytes → ("contract", bytecode_hex)
def test_FYP04():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": LARGE_BYTECODE}
    with patch("modules.validator.requests.get", return_value=mock_resp):
        result = validate_and_detect_type(VALID_ADDRESS)
    assert result == ("contract", LARGE_BYTECODE)


# FYP05: eth_getCode raises unexpected exception → ("wallet", "0x") safe default
def test_FYP05():
    with patch("modules.validator.requests.get", side_effect=Exception("connection error")):
        result = validate_and_detect_type(VALID_ADDRESS)
    assert result == ("wallet", "0x")


# ---------------------------------------------------------------------------
# FYP06–FYP07: predict()
# ---------------------------------------------------------------------------

# FYP06: Valid 21-feature dict returns a float in [0.0, 1.0]
def test_FYP06():
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])

    result = predict(WALLET_FEATURE_DICT, mock_model, WALLET_FEATURES)

    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


# FYP07: Feature dict with one key removed returns 0.5 neutral fallback
def test_FYP07():
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.3, 0.7]])
    incomplete = {k: 0.0 for k in WALLET_FEATURES[:-1]}  # last feature missing

    result = predict(incomplete, mock_model, WALLET_FEATURES)

    assert result == 0.5


# ---------------------------------------------------------------------------
# FYP08–FYP10: explain()
# ---------------------------------------------------------------------------

# FYP08: TreeExplainer returns single SHAP array → list of exactly 3 dicts
def test_FYP08():
    # Distinct magnitudes so sorting is unambiguous
    shap_array = np.array([[
        0.50, 0.80, 0.30, 0.10, 0.05, 0.15, 0.25, 0.02,
        0.40, 0.12, 0.07, 0.18, 0.35, 0.22, 0.09,
        0.06, 0.11, 0.14, 0.03, 0.08, 0.16,
    ]])
    mock_explainer = MagicMock()
    mock_explainer.shap_values.return_value = shap_array
    feature_array = np.zeros((1, 21), dtype=np.float32)

    result = explain(feature_array, mock_explainer, WALLET_FEATURES)

    assert len(result) == 3
    for item in result:
        assert set(item.keys()) == {"feature", "shap_value", "direction", "description"}


# FYP09: TreeExplainer returns list of two arrays → selects index [1] (phishing class)
def test_FYP09():
    benign_vals = np.zeros((1, 21))
    phishing_vals = np.array([[
        0.50, 0.80, 0.30, 0.10, 0.05, 0.15, 0.25, 0.02,
        0.40, 0.12, 0.07, 0.18, 0.35, 0.22, 0.09,
        0.06, 0.11, 0.14, 0.03, 0.08, 0.16,
    ]])
    mock_explainer = MagicMock()
    mock_explainer.shap_values.return_value = [benign_vals, phishing_vals]
    feature_array = np.zeros((1, 21), dtype=np.float32)

    result = explain(feature_array, mock_explainer, WALLET_FEATURES)

    # Highest |shap_val| in phishing_vals is 0.80 at index 1 ("tx_count_out")
    assert len(result) == 3
    assert result[0]["feature"] == WALLET_FEATURES[1]
    assert result[0]["shap_value"] == pytest.approx(0.80, abs=1e-4)


# FYP10: TreeExplainer raises exception → empty list, no exception propagated
def test_FYP10():
    mock_explainer = MagicMock()
    mock_explainer.shap_values.side_effect = RuntimeError("SHAP internal error")
    feature_array = np.zeros((1, 21), dtype=np.float32)

    result = explain(feature_array, mock_explainer, WALLET_FEATURES)

    assert result == []


# ---------------------------------------------------------------------------
# FYP11–FYP14: check_threat_intel()
# ---------------------------------------------------------------------------

# FYP11: GoPlus returns phishing_activities="1" → goplus_flagged=True, available=True
def test_FYP11():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": {"phishing_activities": "1"}}
    with patch("modules.threat_intel.requests.get", return_value=mock_resp):
        result = check_threat_intel(VALID_ADDRESS, scam_set=set())
    assert result["goplus_flagged"] is True
    assert result["goplus_available"] is True


# FYP12: GoPlus raises connection exception → goplus_flagged=False, available=False
def test_FYP12():
    with patch("modules.threat_intel.requests.get", side_effect=ConnectionError("timeout")):
        result = check_threat_intel(VALID_ADDRESS, scam_set=set())
    assert result["goplus_flagged"] is False
    assert result["goplus_available"] is False


# FYP13: Lowercase target address present in scam_set → scamsniffer_flagged=True
def test_FYP13():
    addr_lower = VALID_ADDRESS.lower()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": {}}
    with patch("modules.threat_intel.requests.get", return_value=mock_resp):
        result = check_threat_intel(VALID_ADDRESS, scam_set={addr_lower})
    assert result["scamsniffer_flagged"] is True
    assert result["scamsniffer_available"] is True


# FYP14: scam_set is None (startup fetch failed) → scamsniffer unavailable, not flagged
def test_FYP14():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"result": {}}
    with patch("modules.threat_intel.requests.get", return_value=mock_resp):
        result = check_threat_intel(VALID_ADDRESS, scam_set=None)
    assert result["scamsniffer_flagged"] is False
    assert result["scamsniffer_available"] is False


# ---------------------------------------------------------------------------
# FYP15–FYP21: fuse()
# ---------------------------------------------------------------------------

# FYP15: GoPlus +0.15 raises 0.3 to 0.45 which exactly triggers MEDIUM floor
def test_FYP15():
    result = fuse(0.3, goplus_flagged=True, scamsniffer_flagged=False)
    assert result["final_score"] == pytest.approx(0.45)
    assert result["risk_label"] == "MEDIUM"


# FYP16: ScamSniffer +0.10 raises 0.3 to 0.40 which is lifted to MEDIUM floor
def test_FYP16():
    result = fuse(0.3, goplus_flagged=False, scamsniffer_flagged=True)
    assert result["final_score"] == pytest.approx(0.45)
    assert result["risk_label"] == "MEDIUM"


# FYP17: Both bonuses raise 0.1 to 0.35 which is still lifted to MEDIUM floor
def test_FYP17():
    result = fuse(0.1, goplus_flagged=True, scamsniffer_flagged=True)
    assert result["final_score"] == pytest.approx(0.45)
    assert result["risk_label"] == "MEDIUM"


# FYP18: Both bonuses raise 0.9 to 1.15 which is capped at 1.0
def test_FYP18():
    result = fuse(0.9, goplus_flagged=True, scamsniffer_flagged=True)
    assert result["final_score"] == pytest.approx(1.0)


# FYP19: ml_score=0.55 >= high_threshold=0.5486 with no intel → HIGH
def test_FYP19():
    result = fuse(0.55, goplus_flagged=False, scamsniffer_flagged=False,
                  high_threshold=0.5486)
    assert result["final_score"] == pytest.approx(0.55)
    assert result["risk_label"] == "HIGH"


# FYP20: ml_score=0.30 < 0.45 with no intel → LOW
def test_FYP20():
    result = fuse(0.30, goplus_flagged=False, scamsniffer_flagged=False,
                  high_threshold=0.5486)
    assert result["final_score"] == pytest.approx(0.30)
    assert result["risk_label"] == "LOW"


# FYP21: ml_score=0.50 in [0.45, 0.5486) with no intel → MEDIUM
def test_FYP21():
    result = fuse(0.50, goplus_flagged=False, scamsniffer_flagged=False,
                  high_threshold=0.5486)
    assert result["final_score"] == pytest.approx(0.50)
    assert result["risk_label"] == "MEDIUM"


# ---------------------------------------------------------------------------
# FYP22–FYP24: POST /api/analyze integration tests
# ---------------------------------------------------------------------------

# FYP22: Valid wallet address → HTTP 200, analysis_type="wallet", all 11 fields present
def test_FYP22(client):
    with patch("routers.analyze.validate_and_detect_type", return_value=("wallet", "0x")), \
         patch("routers.analyze.collect_wallet_data", return_value={}), \
         patch("routers.analyze.compute_wallet_features", return_value=WALLET_FEATURE_DICT), \
         patch("routers.analyze.predict", return_value=0.3), \
         patch("routers.analyze.explain", return_value=MOCK_SHAP_EXPLANATION), \
         patch("routers.analyze.check_threat_intel", return_value=MOCK_INTEL_CLEAN):

        response = client.post("/api/analyze", json={"address": VALID_ADDRESS})

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_type"] == "wallet"
    assert EXPECTED_RESPONSE_FIELDS.issubset(set(data.keys()))


# FYP23: Valid contract address → HTTP 200, analysis_type="contract", all 11 fields present
def test_FYP23(client):
    with patch("routers.analyze.validate_and_detect_type", return_value=("contract", LARGE_BYTECODE)), \
         patch("routers.analyze.collect_contract_data", return_value={}), \
         patch("routers.analyze.compute_contract_features", return_value=CONTRACT_FEATURE_DICT), \
         patch("routers.analyze.predict", return_value=0.2), \
         patch("routers.analyze.explain", return_value=MOCK_SHAP_EXPLANATION), \
         patch("routers.analyze.check_threat_intel", return_value=MOCK_INTEL_CLEAN):

        response = client.post("/api/analyze", json={"address": CONTRACT_ADDRESS})

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_type"] == "contract"
    assert EXPECTED_RESPONSE_FIELDS.issubset(set(data.keys()))


# FYP24: 11 requests from same IP within 1 minute → first 10 succeed, 11th returns HTTP 429
def test_FYP24(client):
    with patch("routers.analyze.validate_and_detect_type", return_value=("wallet", "0x")), \
         patch("routers.analyze.collect_wallet_data", return_value={}), \
         patch("routers.analyze.compute_wallet_features", return_value=WALLET_FEATURE_DICT), \
         patch("routers.analyze.predict", return_value=0.3), \
         patch("routers.analyze.explain", return_value=[]), \
         patch("routers.analyze.check_threat_intel", return_value=MOCK_INTEL_CLEAN):

        responses = [
            client.post("/api/analyze", json={"address": VALID_ADDRESS})
            for _ in range(11)
        ]

    assert all(r.status_code == 200 for r in responses[:10])
    assert responses[10].status_code == 429
