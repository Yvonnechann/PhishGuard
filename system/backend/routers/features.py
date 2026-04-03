from fastapi import APIRouter, Request

from modules.data_collector import collect_contract_data, collect_wallet_data
from modules.contract_features import compute_contract_features
from modules.wallet_features import compute_wallet_features
from modules.validator import validate_and_detect_type

router = APIRouter()


@router.get("/features/{address}")
async def get_features(address: str, request: Request):
    analysis_type = validate_and_detect_type(address)

    if analysis_type == "wallet":
        raw_data = collect_wallet_data(address)
        feature_dict = compute_wallet_features(raw_data, address)
    else:
        raw_data = collect_contract_data(address)
        feature_dict = compute_contract_features(raw_data)

    return {
        "analysis_type": analysis_type,
        "raw_features": feature_dict,
    }
