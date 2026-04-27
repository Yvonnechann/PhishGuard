import re

import numpy as np
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from modules.data_collector import collect_wallet_data
from modules.wallet_features import compute_wallet_features
from modules.ml_inference import predict
from modules.explainer import explain
from modules.threat_intel import check_threat_intel
from modules.fusion import fuse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')


class AddressRequest(BaseModel):
    address: str


@router.post("/analyze/address")
@limiter.limit("10/minute")
async def analyze_address(request: Request, body: AddressRequest):
    address = body.address

    # Validate format only — force wallet, no RPC type detection
    if not _ADDRESS_RE.match(address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")

    raw_data = collect_wallet_data(address)
    feature_dict = compute_wallet_features(raw_data, address, scam_set=request.app.state.scam_set)

    model = request.app.state.wallet_model
    feature_names = request.app.state.wallet_feature_names
    explainer_obj = request.app.state.wallet_explainer

    ml_score = predict(feature_dict, model, feature_names)

    feature_array = np.array([[feature_dict[k] for k in feature_names]], dtype=np.float32)
    shap_explanation = explain(feature_array, explainer_obj, feature_names)

    intel = check_threat_intel(address, scam_set=request.app.state.scam_set)
    fusion_result = fuse(ml_score, intel["goplus_flagged"], intel["scamsniffer_flagged"],
                         high_threshold=request.app.state.wallet_threshold)

    return {
        "address": address,
        "analysis_type": "wallet",
        "ml_score": round(ml_score, 4),
        "final_score": fusion_result["final_score"],
        "risk_label": fusion_result["risk_label"],
        "goplus_flagged": intel["goplus_flagged"],
        "scamsniffer_flagged": intel["scamsniffer_flagged"],
        "shap_explanation": shap_explanation,
        "raw_features": feature_dict,
    }
