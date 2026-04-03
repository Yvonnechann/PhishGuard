import numpy as np
from fastapi import APIRouter, Request

from modules.data_collector import collect_contract_data, collect_wallet_data
from modules.contract_features import compute_contract_features
from modules.wallet_features import compute_wallet_features
from modules.explainer import explain
from modules.validator import validate_and_detect_type

router = APIRouter()


@router.get("/explain/{address}")
async def explain_address(address: str, request: Request):
    analysis_type = validate_and_detect_type(address)

    if analysis_type == "wallet":
        raw_data = collect_wallet_data(address)
        feature_dict = compute_wallet_features(raw_data, address)
        feature_names = request.app.state.wallet_feature_names
        explainer_obj = request.app.state.wallet_explainer
    else:
        raw_data = collect_contract_data(address)
        feature_dict = compute_contract_features(raw_data)
        feature_names = request.app.state.contract_feature_names
        explainer_obj = request.app.state.contract_explainer

    feature_array = np.array([[feature_dict[k] for k in feature_names]], dtype=np.float32)
    shap_explanation = explain(feature_array, explainer_obj, feature_names)

    return {"shap_explanation": shap_explanation}
