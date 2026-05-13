# PhishGuard

PhishGuard is an Ethereum phishing detection system that analyses wallet addresses and smart contracts using machine learning, on-chain feature engineering, and live threat intelligence. It auto-detects whether a submitted address is a wallet or contract, runs the appropriate XGBoost model, and fuses the ML score with GoPlus and ScamSniffer signals to produce a final risk label (LOW / MEDIUM / HIGH).

---

## Table of Contents

1. [Repository Structure](#repository-structure)
2. [ML Pipeline](#ml-pipeline)
   - [Prerequisites](#prerequisites)
   - [Step 1 — Data Collection](#step-1--data-collection-notebook-01)
   - [Step 2 — Wallet Feature Engineering](#step-2--wallet-feature-engineering-notebook-02)
   - [Step 3 — Contract Feature Engineering](#step-3--contract-feature-engineering-notebook-03)
   - [Step 4 — Wallet Model Training](#step-4--wallet-model-training-notebook-04)
   - [Step 5 — Contract Model Training](#step-5--contract-model-training-notebook-05)
   - [Step 6 — Final Evaluation](#step-6--final-evaluation-notebook-06)
3. [Google Drive Layout](#google-drive-layout)
4. [System Setup](#system-setup)
   - [Backend](#backend)
   - [Frontend](#frontend)
5. [Running the System](#running-the-system)
6. [API Reference](#api-reference)
7. [Security Controls](#security-controls)

---

## Repository Structure

```
PhishGuard/
├── data-collection/
│   ├── PhishGuard_Notebook01_DataCollection.ipynb
│   └── data/                        # gitignored — raw CSVs go here locally
│
├── feature-engineering/
│   ├── PhishGuard_Notebook02_WalletFeatures.ipynb
│   ├── PhishGuard_Notebook03_ContractFeatures.ipynb
│   └── data/                        # gitignored — generated feature CSVs
│
├── model-training/
│   ├── PhishGuard_Notebook04_WalletTraining.ipynb
│   └── PhishGuard_Notebook05_ContractTraining.ipynb
│
├── evaluation/
│   └── PhishGuard_Notebook06_FinalEvaluation.ipynb
│
└── system/
    ├── backend/
    │   ├── main.py
    │   ├── config.py
    │   ├── requirements.txt
    │   ├── .env.example
    │   ├── models/                  # all files tracked in git
    │   │   ├── wallet_feature_schema.json
    │   │   ├── contract_feature_schema.json
    │   │   ├── wallet_threshold.json
    │   │   ├── contract_threshold.json
    │   │   ├── wallet_xgboost_v1.pkl
    │   │   └── contract_xgboost_v1.pkl
    │   ├── modules/
    │   │   ├── data_collector.py
    │   │   ├── wallet_features.py
    │   │   ├── contract_features.py
    │   │   ├── ml_inference.py
    │   │   ├── explainer.py
    │   │   ├── threat_intel.py
    │   │   ├── fusion.py
    │   │   └── validator.py
    │   ├── routers/
    │   │   ├── analyze.py
    │   │   ├── address.py
    │   │   ├── contract.py
    │   │   ├── explain.py
    │   │   └── features.py
    │   └── test_phishguard.py
    └── frontend/
        ├── src/
        │   ├── App.jsx
        │   ├── api/
        │   └── components/
        ├── package.json
        └── vite.config.js
```

---

## ML Pipeline

All six notebooks run on **Google Colab** with Google Drive mounted at `MyDrive/PhishGuard/`. They must be run in order the first time. Later notebooks can be re-run independently as long as their input files already exist on Drive.

### Prerequisites

**Etherscan API key** — required for Notebooks 01 and 03. Sign up at [etherscan.io](https://etherscan.io/register) and create a free API key.

**9 source label files** — place these in `MyDrive/PhishGuard/data/sources/` before running Notebook 01:

| File | Description |
|---|---|
| `eth_labels_phishing.csv` | Ethereum phishing address labels |
| `eth_labels_exchange.csv` | Known exchange addresses (benign) |
| `eth_labels_token_contracts.csv` | Known token contract addresses (benign) |
| `fraud_contracts.csv` | Labelled fraudulent smart contracts |
| `kaggle_fraud.csv` | Kaggle Ethereum fraud dataset |
| `scamsniffer_addresses.json` | ScamSniffer phishing address list |
| `mew_darklist.json` | MyEtherWallet phishing darklist |
| `PTXPHISH.xlsx` | PTXPHISH phishing transaction hashes |
| `defi_seeds.json` | DeFi seed addresses (benign) |

These files are the only things that cannot be regenerated — keep them safe on Drive.

---

### Step 1 — Data Collection (Notebook 01)

**File:** `data-collection/PhishGuard_Notebook01_DataCollection.ipynb`

Loads the 9 source label files, resolves PTXPHISH transaction hashes to contract addresses via `eth_getTransactionByHash`, applies an activity filter (wallets need ≥ 5 transactions, contracts ≥ 2), then collects raw on-chain data for 4,000 wallet addresses (2,000 phishing / 2,000 benign) and up to 1,300 contract addresses via 5 Etherscan API calls each.

Before running, set your API key in Cell 2:
```python
ETHERSCAN_API_KEY = 'YOUR_ETHERSCAN_API_KEY_HERE'
```

Checkpoints are saved every 100 rows so the session can be interrupted and resumed by re-running the same cell.

**Outputs on Drive:**
```
data/raw_wallet_data.csv
data/raw_contract_data.csv
```

---

### Step 2 — Wallet Feature Engineering (Notebook 02)

**File:** `feature-engineering/PhishGuard_Notebook02_WalletFeatures.ipynb`

Reads `raw_wallet_data.csv` and engineers 21 features per wallet across two passes:

- **Pass 1** — transaction-level features: tx counts, counterparty counts, fan-in ratio, inter-transaction timing, ETH value statistics, ERC-20 approval counts, unlimited approval rate, token transfer counts
- **Pass 2** — graph features: builds a transaction graph with NetworkX and computes average shortest path to known scam addresses

The scam address set is loaded from `data/scam_addresses.json`. If that file does not exist, Cell 2b fetches it automatically from CryptoScamDB and ScamSniffer and saves it for future use.

**Inputs on Drive:**
```
data/raw_wallet_data.csv
data/scam_addresses.json   ← auto-fetched if missing
```

**Outputs on Drive:**
```
features/wallet_features.csv        (4,000 rows × 23 columns)
models/wallet_feature_schema.json   (list of 21 feature names)
```

---

### Step 3 — Contract Feature Engineering (Notebook 03)

**File:** `feature-engineering/PhishGuard_Notebook03_ContractFeatures.ipynb`

Reads `raw_contract_data.csv` and engineers 21 features per contract:

- Bytecode-level: bytecode size, EVM opcode counts (`DELEGATECALL`, `SELFDESTRUCT`, `CREATE2`), entropy
- ABI-level: function counts, approval-related functions, upgrade functions, external/public visibility ratio
- Slither static analysis: warning counts by severity (high, medium, low, informational), re-entrancy flags, proxy detection
- Source-level: verification status

Requires `solc` compilers. Cell 1 installs versions 0.4.24, 0.4.25, 0.5.17, 0.6.12, 0.7.6, 0.8.0, and 0.8.19 automatically via `py-solc-x`.

Set your Etherscan API key in Cell 2:
```python
ETHERSCAN_API_KEY = 'YOUR_ETHERSCAN_API_KEY_HERE'
```

Slither runs only on verified contracts (~120 s max each). Checkpoints every 100 rows allow safe resumption.

**Inputs on Drive:**
```
data/raw_contract_data.csv
```

**Outputs on Drive:**
```
features/contract_features.csv        (balanced rows × 23 columns)
models/contract_feature_schema.json   (list of 21 feature names)
```

---

### Step 4 — Wallet Model Training (Notebook 04)

**File:** `model-training/PhishGuard_Notebook04_WalletTraining.ipynb`

Trains an XGBoost classifier on the wallet feature dataset.

- Dataset: 4,000 rows, 2,000 phishing / 2,000 benign, 21 features
- Split: 80% train / 20% test (stratified, `random_seed=42`)
- Hyperparameter tuning via 5-fold cross-validation
- Threshold tuning via precision-recall curve to maximise F1

**Inputs on Drive:**
```
features/wallet_features.csv
models/wallet_feature_schema.json
```

**Outputs on Drive:**
```
models/wallet_xgboost_v1.pkl
models/wallet_threshold.json
```

---

### Step 5 — Contract Model Training (Notebook 05)

**File:** `model-training/PhishGuard_Notebook05_ContractTraining.ipynb`

Trains an XGBoost classifier on the contract feature dataset using the same approach as Notebook 04. Threshold is tuned with the additional constraint that both precision and recall must be ≥ 0.80.

**Inputs on Drive:**
```
features/contract_features.csv
models/contract_feature_schema.json
```

**Outputs on Drive:**
```
models/contract_xgboost_v1.pkl
models/contract_threshold.json
```

---

### Step 6 — Final Evaluation (Notebook 06)

**File:** `evaluation/PhishGuard_Notebook06_FinalEvaluation.ipynb`

Loads both trained models and their held-out test sets, computes accuracy, precision, recall, F1, ROC-AUC, and PR-AUC, and generates plots (ROC curves, precision-recall curves, confusion matrices, SHAP feature importance). All plots are saved to `evaluation/` on Drive.

**Inputs on Drive:**
```
models/wallet_xgboost_v1.pkl
models/wallet_feature_schema.json
models/wallet_test_indices.npy        ← saved by Notebook 04
models/contract_xgboost_v1.pkl
models/contract_feature_schema.json
models/contract_test_indices.npy      ← saved by Notebook 05
features/wallet_features.csv
features/contract_features.csv
```

---

## Google Drive Layout

After running all notebooks, your Drive folder should look like this:

```
MyDrive/PhishGuard/
├── data/
│   ├── sources/
│   │   ├── eth_labels_phishing.csv       ← upload before Notebook 01
│   │   ├── eth_labels_exchange.csv       ← upload before Notebook 01
│   │   ├── eth_labels_token_contracts.csv← upload before Notebook 01
│   │   ├── fraud_contracts.csv           ← upload before Notebook 01
│   │   ├── kaggle_fraud.csv              ← upload before Notebook 01
│   │   ├── scamsniffer_addresses.json    ← upload before Notebook 01
│   │   ├── mew_darklist.json             ← upload before Notebook 01
│   │   ├── PTXPHISH.xlsx                 ← upload before Notebook 01
│   │   └── defi_seeds.json               ← upload before Notebook 01
│   ├── raw_wallet_data.csv               ← generated by Notebook 01
│   ├── raw_contract_data.csv             ← generated by Notebook 01
│   ├── scam_addresses.json               ← auto-fetched by Notebook 02
│   └── checkpoints/                      ← resume state (auto-generated)
├── features/
│   ├── wallet_features.csv               ← generated by Notebook 02
│   └── contract_features.csv             ← generated by Notebook 03
├── models/
│   ├── wallet_feature_schema.json        ← generated by Notebook 02
│   ├── contract_feature_schema.json      ← generated by Notebook 03
│   ├── wallet_xgboost_v1.pkl             ← generated by Notebook 04
│   ├── wallet_threshold.json             ← generated by Notebook 04
│   ├── contract_xgboost_v1.pkl           ← generated by Notebook 05
│   └── contract_threshold.json           ← generated by Notebook 05
└── evaluation/                           ← plots generated by Notebook 06
```

---

## System Setup

### Backend

**Requirements:** Python 3.10+

1. Create and activate a virtual environment:
   ```bash
   cd system/backend
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment file and fill in your API key:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```
   ETHERSCAN_API_KEY=your_etherscan_api_key_here
   GOPLUS_API_KEY=                              # optional
   ```

4. All model files are tracked in git and will be present after cloning:
   ```
   models/
   ├── wallet_xgboost_v1.pkl
   ├── wallet_threshold.json
   ├── contract_xgboost_v1.pkl
   ├── contract_threshold.json
   ├── wallet_feature_schema.json
   └── contract_feature_schema.json
   ```
   No separate download needed.

   > The backend verifies the SHA-256 hash of both `.pkl` files on every startup. If you retrain the models, update `_MODEL_HASHES` in `main.py` with the new digests.

---

### Frontend

**Requirements:** Node.js 18+

1. Install dependencies:
   ```bash
   cd system/frontend
   npm install
   ```

No environment variables are required for the frontend. The API base URL is configured in `src/api/`.

---

## Running the System

Start the backend:
```bash
cd system/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

On startup the backend will:
- Verify model file integrity (SHA-256)
- Load both XGBoost models and SHAP explainers
- Fetch the ScamSniffer blacklist (~2,530 addresses) from GitHub
- Verify the Cloudflare Ethereum RPC

Check that everything loaded correctly:
```
GET http://localhost:8000/health
```

Start the frontend:
```bash
cd system/frontend
npm run dev
```

The UI is available at `http://localhost:5173`.

To run the test suite:
```bash
cd system/backend
pytest test_phishguard.py -v
```

---

## API Reference

All endpoints are under the `/api` prefix. Requests are rate-limited to **10 per minute per IP**.

### `POST /api/analyze`

Auto-detects the address type and runs the full analysis pipeline.

**Request:**
```json
{ "address": "0xabc...123" }
```

**Response:**
```json
{
  "address": "0xabc...123",
  "analysis_type": "wallet",
  "ml_score": 0.8712,
  "final_score": 0.9712,
  "risk_label": "HIGH",
  "goplus_flagged": true,
  "goplus_available": true,
  "scamsniffer_flagged": false,
  "scamsniffer_available": true,
  "shap_explanation": { ... },
  "raw_features": { ... }
}
```

`risk_label` values: `HIGH` (≥ tuned threshold), `MEDIUM` (≥ 0.45), `LOW` (< 0.45).

`final_score` is the ML score boosted by +0.15 if GoPlus flagged and/or +0.10 if ScamSniffer flagged, capped at 1.0. If any threat intel source flags the address, the final score is floored at 0.45 (MEDIUM) regardless of the ML score.

### `POST /api/address`

Wallet-only analysis (skips contract feature path).

### `POST /api/contract`

Contract-only analysis (skips wallet feature path).

### `POST /api/explain`

Returns SHAP feature importance for the address without the full threat intel lookup.

### `POST /api/features`

Returns the raw engineered feature vector for the address.

### `GET /health`

Returns model load status and available threat intel sources.

---

## Security Controls

| Control | Implementation |
|---|---|
| Input validation | Regex check on every address (`^0x[0-9a-fA-F]{40}$`) before any API call |
| Type auto-detection | `eth_getCode` via Etherscan; EIP-7702 EOA disambiguation via `getsourcecode` |
| Model integrity | SHA-256 hash of both `.pkl` files verified on startup; server refuses to start if hashes differ |
| Rate limiting | `slowapi` — 10 analysis requests per minute per IP |
| Threat intel fusion | GoPlus and ScamSniffer checked in parallel; unavailable sources are clearly flagged in the response rather than silently ignored |
| CORS | Restricted to `localhost:5173` and `localhost:3000` |
| Secrets | API keys loaded from `.env` via `python-dotenv`; `.env` is gitignored |
