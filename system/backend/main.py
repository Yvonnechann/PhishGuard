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

BASE_DIR = Path(__file__).parent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("phishguard")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Step 1 — load .env
    load_dotenv(BASE_DIR / ".env")

    # Step 2 — wallet model
    app.state.wallet_model = joblib.load(BASE_DIR / "models" / "wallet_xgboost_v1.pkl")
    logger.info("Wallet model loaded.")

    # Step 3 — contract model
    app.state.contract_model = joblib.load(BASE_DIR / "models" / "contract_xgboost_v1.pkl")
    logger.info("Contract model loaded.")

    # Step 4 — wallet feature schema
    with open(BASE_DIR / "models" / "wallet_feature_schema.json") as f:
        app.state.wallet_feature_names = json.load(f)
    logger.info(f"Wallet schema loaded: {len(app.state.wallet_feature_names)} features.")

    # Step 5 — contract feature schema
    with open(BASE_DIR / "models" / "contract_feature_schema.json") as f:
        app.state.contract_feature_names = json.load(f)
    logger.info(f"Contract schema loaded: {len(app.state.contract_feature_names)} features.")

    # Step 6 — contract threshold
    with open(BASE_DIR / "models" / "contract_threshold.json") as f:
        app.state.contract_threshold = float(json.load(f)["threshold"])
    logger.info(f"Contract threshold loaded: {app.state.contract_threshold}.")

    # Step 8 — wallet SHAP explainer
    app.state.wallet_explainer = shap.TreeExplainer(app.state.wallet_model)
    logger.info("Wallet SHAP explainer initialised.")

    # Step 9 — contract SHAP explainer
    app.state.contract_explainer = shap.TreeExplainer(app.state.contract_model)
    logger.info("Contract SHAP explainer initialised.")

    # Step 10 — verify Cloudflare RPC
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
        logger.warning(f"Cloudflare RPC check failed: {exc}. Alchemy fallback will be used.")

    logger.info("PhishGuard ready.")
    yield


app = FastAPI(title="PhishGuard", version="1.0.0", lifespan=lifespan)

from routers import analyze, address, contract, explain, features  # noqa: E402
app.include_router(analyze.router, prefix="/api")
app.include_router(address.router, prefix="/api")
app.include_router(contract.router, prefix="/api")
app.include_router(explain.router, prefix="/api")
app.include_router(features.router, prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        "intel_sources": ["goplus", "cryptoscamdb"],
    }
