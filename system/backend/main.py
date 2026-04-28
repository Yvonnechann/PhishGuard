import hashlib
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import shap
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from config import SCORE_HIGH

BASE_DIR = Path(__file__).parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phishguard")

# A08 — model file integrity hashes (sha256 of files as trained)
_MODEL_HASHES = {
    "wallet_xgboost_v1.pkl":   "b3c77f991369be3ce98fb7f1b624e72661f8da3b68d7bfaadfff85097cd6e501",
    "contract_xgboost_v1.pkl": "5777034f12b0066dbc40092738125c089cf045b985d8388e56ce3ace8419e338",
}


def _verify_model_integrity(filename: str) -> None:
    path = BASE_DIR / "models" / filename
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    expected = _MODEL_HASHES[filename]
    if digest != expected:
        raise RuntimeError(
            f"Model integrity check FAILED for {filename}: "
            f"expected {expected}, got {digest}"
        )
    logger.info(f"Integrity OK: {filename}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Step 1 — load .env
    load_dotenv(BASE_DIR / ".env")

    # Step 2 — verify model file integrity before loading (A08)
    _verify_model_integrity("wallet_xgboost_v1.pkl")
    _verify_model_integrity("contract_xgboost_v1.pkl")

    # Step 3 — wallet model
    app.state.wallet_model = joblib.load(BASE_DIR / "models" / "wallet_xgboost_v1.pkl")
    logger.info("Wallet model loaded.")

    # Step 4 — contract model
    app.state.contract_model = joblib.load(BASE_DIR / "models" / "contract_xgboost_v1.pkl")
    logger.info("Contract model loaded.")

    # Step 5 — wallet feature schema
    with open(BASE_DIR / "models" / "wallet_feature_schema.json") as f:
        app.state.wallet_feature_names = json.load(f)
    logger.info(f"Wallet schema loaded: {len(app.state.wallet_feature_names)} features.")

    # Step 6 — contract feature schema
    with open(BASE_DIR / "models" / "contract_feature_schema.json") as f:
        app.state.contract_feature_names = json.load(f)
    logger.info(f"Contract schema loaded: {len(app.state.contract_feature_names)} features.")

    # Step 7 — contract threshold
    with open(BASE_DIR / "models" / "contract_threshold.json") as f:
        app.state.contract_threshold = float(json.load(f)["threshold"])
    logger.info(f"Contract threshold loaded: {app.state.contract_threshold}.")

    # Step 8 — wallet threshold
    wallet_threshold_path = BASE_DIR / "models" / "wallet_threshold.json"
    if wallet_threshold_path.exists():
        with open(wallet_threshold_path) as f:
            app.state.wallet_threshold = float(json.load(f)["threshold"])
        logger.info(f"Wallet threshold loaded: {app.state.wallet_threshold}.")
    else:
        app.state.wallet_threshold = SCORE_HIGH
        logger.info(f"Wallet threshold file not found — using default {SCORE_HIGH}.")

    # Step 9 — wallet SHAP explainer
    app.state.wallet_explainer = shap.TreeExplainer(app.state.wallet_model)
    logger.info("Wallet SHAP explainer initialised.")

    # Step 10 — contract SHAP explainer
    app.state.contract_explainer = shap.TreeExplainer(app.state.contract_model)
    logger.info("Contract SHAP explainer initialised.")

    # Step 11 — verify Cloudflare RPC
    try:
        import requests as _requests
        from config import CLOUDFLARE_RPC
        resp = _requests.post(
            CLOUDFLARE_RPC,
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            timeout=5,
        )
        resp.raise_for_status()
        logger.info("Cloudflare RPC connection verified.")
    except Exception as exc:
        logger.warning(f"Cloudflare RPC check failed: {exc}.")

    # Step 12 — load ScamSniffer scam address blacklist at startup
    _SCAMSNIFFER_URL = (
        "https://raw.githubusercontent.com/scamsniffer/scam-database/main/blacklist/address.json"
    )
    try:
        import requests as _requests
        r = _requests.get(_SCAMSNIFFER_URL, timeout=10)
        r.raise_for_status()
        app.state.scam_set = set(addr.lower() for addr in r.json() if isinstance(addr, str))
        logger.info(f"ScamSniffer blacklist loaded: {len(app.state.scam_set)} addresses.")
    except Exception as exc:
        app.state.scam_set = None
        logger.warning(f"ScamSniffer blacklist fetch failed: {exc}. ScamSniffer checks will show as unavailable.")

    logger.info("PhishGuard ready.")
    yield


# A04 — rate limiter: 10 analysis requests per minute per IP
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])

app = FastAPI(title="PhishGuard", version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import analyze, address, contract, explain, features  # noqa: E402
app.include_router(analyze.router, prefix="/api")
app.include_router(address.router, prefix="/api")
app.include_router(contract.router, prefix="/api")
app.include_router(explain.router, prefix="/api")
app.include_router(features.router, prefix="/api")


# Global 500 handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
async def health(request: Request):
    return {
        "status": "ok",
        "wallet_model_loaded": hasattr(request.app.state, "wallet_model") and request.app.state.wallet_model is not None,
        "contract_model_loaded": hasattr(request.app.state, "contract_model") and request.app.state.contract_model is not None,
        "intel_sources": ["goplus", "scamsniffer"],
    }
