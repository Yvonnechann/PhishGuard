from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from modules.data_collector import collect_contract_data, collect_wallet_data
from modules.contract_features import compute_contract_features
from modules.wallet_features import compute_wallet_features
from modules.validator import validate_and_detect_type

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/features/{address}")
@limiter.limit("10/minute")
async def get_features(address: str, request: Request):
    analysis_type, bytecode_hex = validate_and_detect_type(address)

    if analysis_type == "wallet":
        raw_data = collect_wallet_data(address)
        feature_dict = compute_wallet_features(raw_data, address, scam_set=request.app.state.scam_set)
    else:
        raw_data = collect_contract_data(address, bytecode_hex=bytecode_hex)
        feature_dict = compute_contract_features(raw_data)

    return {
        "analysis_type": analysis_type,
        "raw_features": feature_dict,
    }
