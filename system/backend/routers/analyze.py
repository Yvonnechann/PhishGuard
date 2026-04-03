import numpy as np
from fastapi import APIRouter, Request
from pydantic import BaseModel

from modules.data_collector import collect_contract_data, collect_wallet_data
from modules.contract_features import compute_contract_features
from modules.wallet_features import compute_wallet_features
from modules.ml_inference import predict
from modules.explainer import explain
from modules.threat_intel import check_threat_intel
from modules.fusion import fuse
from modules.validator import validate_and_detect_type

router = APIRouter()


class AddressRequest(BaseModel):
    address: str


@router.post("/analyze")
async def analyze(body: AddressRequest, request: Request):
    address = body.address

    # Step 1 — validate format + auto-detect type via RPC
    analysis_type = validate_and_detect_type(address)

    # Step 2 — collect raw on-chain data
    if analysis_type == "wallet":
        raw_data = collect_wallet_data(address)
    else:
        raw_data = collect_contract_data(address)

    # Step 3 — feature engineering
    if analysis_type == "wallet":
        feature_dict = compute_wallet_features(raw_data, address)
        model = request.app.state.wallet_model
        feature_names = request.app.state.wallet_feature_names
        explainer_obj = request.app.state.wallet_explainer
    else:
        feature_dict = compute_contract_features(raw_data)
        model = request.app.state.contract_model
        feature_names = request.app.state.contract_feature_names
        explainer_obj = request.app.state.contract_explainer

    # Step 4 — ML inference (raw probability, no threshold applied here)
    ml_score = predict(feature_dict, model, feature_names)

    # Step 5 — SHAP explanation
    feature_array = np.array([[feature_dict[k] for k in feature_names]], dtype=np.float32)
    shap_explanation = explain(feature_array, explainer_obj, feature_names)

    # Step 6 — threat intelligence (live API calls)
    intel = check_threat_intel(address)

    # Step 7 — fusion
    fusion_result = fuse(ml_score, intel["goplus_flagged"], intel["scamdb_match"])

    return {
        "address": address,
        "analysis_type": analysis_type,
        "ml_score": round(ml_score, 4),
        "final_score": fusion_result["final_score"],
        "risk_label": fusion_result["risk_label"],
        "risk_color": fusion_result["risk_color"],
        "goplus_flagged": intel["goplus_flagged"],
        "scamdb_match": intel["scamdb_match"],
        "shap_explanation": shap_explanation,
        "raw_features": feature_dict,
    }
