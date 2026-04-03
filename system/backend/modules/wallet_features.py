import logging
import time
from collections import defaultdict
from statistics import median, stdev

import networkx as nx
import requests

logger = logging.getLogger("phishguard.wallet_features")

_CRYPTOSCAMDB_ADDRESSES_URL = "https://api.cryptoscamdb.org/v1/addresses"


def _fetch_live_scam_set() -> set:
    try:
        resp = requests.get(_CRYPTOSCAMDB_ADDRESSES_URL, timeout=5)
        resp.raise_for_status()
        body = resp.json()
        result = body.get("result", {})
        # result may be a dict keyed by address, or a list of addresses
        if isinstance(result, dict):
            return set(addr.lower() for addr in result.keys())
        if isinstance(result, list):
            return set(addr.lower() for addr in result if isinstance(addr, str))
        return set()
    except Exception as exc:
        logger.warning(f"CryptoScamDB addresses fetch failed: {exc}")
        return set()


def compute_wallet_features(raw_data: dict, address: str) -> dict:
    addr = address.lower()
    txs = raw_data.get("txs", []) or []

    if not txs:
        logger.warning(
            f"No transactions found for {addr} — all tx-derived features will be 0. "
            "This is expected for self-destructed contracts detected as wallets."
        )
    tokentxs = raw_data.get("tokentxs", []) or []
    approval_logs = raw_data.get("approval_logs", []) or []
    balance_wei = raw_data.get("balance_wei", "0") or "0"

    now = int(time.time())

    # ── Basic counts ──────────────────────────────────────────────────────────
    tx_count_in = sum(1 for tx in txs if tx.get("to", "").lower() == addr)
    tx_count_out = sum(1 for tx in txs if tx.get("from", "").lower() == addr)
    tx_count_total = tx_count_in + tx_count_out

    # ── Wallet age ────────────────────────────────────────────────────────────
    if txs:
        min_ts = min(int(tx.get("timeStamp", now)) for tx in txs)
        wallet_age_days = (now - min_ts) / 86400.0
    else:
        wallet_age_days = 0.0

    # ── Counterparties ────────────────────────────────────────────────────────
    all_addrs = set()
    for tx in txs:
        f = tx.get("from", "").lower()
        t = tx.get("to", "").lower()
        if f and f != addr:
            all_addrs.add(f)
        if t and t != addr:
            all_addrs.add(t)
    unique_counterparties_lifetime = len(all_addrs)

    # ── fan_in_ratio ──────────────────────────────────────────────────────────
    fan_in_ratio = (tx_count_in / tx_count_total) if tx_count_total > 0 else 0.0

    # ── Inter-tx timing ───────────────────────────────────────────────────────
    if len(txs) >= 2:
        timestamps = sorted(int(tx.get("timeStamp", 0)) for tx in txs)
        diffs_minutes = [(timestamps[i+1] - timestamps[i]) / 60.0 for i in range(len(timestamps)-1)]
        median_inter_tx_minutes = float(median(diffs_minutes))
        std_inter_tx_minutes = float(stdev(diffs_minutes)) if len(diffs_minutes) >= 2 else 0.0
    else:
        median_inter_tx_minutes = 0.0
        std_inter_tx_minutes = 0.0

    # ── Outbound value stats ──────────────────────────────────────────────────
    out_values = [int(tx.get("value", 0)) / 1e18 for tx in txs if tx.get("from", "").lower() == addr]
    avg_out_value_eth = float(sum(out_values) / len(out_values)) if out_values else 0.0
    std_out_value_eth = float(stdev(out_values)) if len(out_values) >= 2 else 0.0

    # ── Inbound min value ─────────────────────────────────────────────────────
    in_values = [int(tx.get("value", 0)) / 1e18 for tx in txs if tx.get("to", "").lower() == addr]
    min_in_value_eth = float(min(in_values)) if in_values else 0.0

    # ── Balance ───────────────────────────────────────────────────────────────
    try:
        current_eth_balance = int(balance_wei) / 1e18
    except (ValueError, TypeError):
        current_eth_balance = 0.0

    # ── Approvals ─────────────────────────────────────────────────────────────
    approval_count_total = len(approval_logs)
    UNLIMITED = 2**256 - 1

    unlimited_approval_count_lifetime = sum(
        1 for log in approval_logs if log.get("amount") == UNLIMITED
    )

    spender_counts: dict = defaultdict(int)
    spender_tokens: dict = defaultdict(set)
    for log in approval_logs:
        sp = log.get("spender", "").lower()
        tc = log.get("token_contract", "").lower()
        spender_counts[sp] += 1
        spender_tokens[sp].add(tc)

    unique_spenders_lifetime = len(spender_counts)

    approval_concentration_top_spender = (
        max(spender_counts.values()) / approval_count_total
        if approval_count_total > 0 else 0.0
    )

    unlimited_approval_rate = (
        unlimited_approval_count_lifetime / approval_count_total
        if approval_count_total > 0 else 0.0
    )

    # cross_token_approval_same_spender_ratio
    if unique_spenders_lifetime > 0:
        multi_token_spenders = sum(1 for tokens in spender_tokens.values() if len(tokens) > 1)
        cross_token_approval_same_spender_ratio = multi_token_spenders / unique_spenders_lifetime
    else:
        cross_token_approval_same_spender_ratio = 0.0

    # ── Token transfers ───────────────────────────────────────────────────────
    token_transfer_count = len(tokentxs)

    # ── NetworkX graph ────────────────────────────────────────────────────────
    G = nx.DiGraph()
    G.add_node(addr)

    edge_weights: dict = defaultdict(int)
    for tx in txs:
        f = tx.get("from", "").lower()
        t = tx.get("to", "").lower()
        w = int(tx.get("value", 0))
        if f and t:
            edge_weights[(f, t)] += w

    for (f, t), w in edge_weights.items():
        G.add_edge(f, t, weight=w)

    pagerank_subgraph = float(nx.pagerank(G).get(addr, 0.0)) if G.number_of_nodes() > 1 else 0.0
    clustering_coefficient = float(nx.clustering(G.to_undirected()).get(addr, 0.0))

    # ── Reciprocity ───────────────────────────────────────────────────────────
    if unique_counterparties_lifetime > 0:
        reciprocal = sum(
            1 for cp in all_addrs
            if G.has_edge(addr, cp) and G.has_edge(cp, addr)
        )
        reciprocity_ratio = reciprocal / unique_counterparties_lifetime
    else:
        reciprocity_ratio = 0.0

    # ── Avg shortest path to known scam ───────────────────────────────────────
    scam_set = _fetch_live_scam_set()
    try:
        if G.number_of_nodes() > 1 and addr in G and scam_set:
            lengths = nx.shortest_path_length(G, source=addr)
            scam_distances = [d for node, d in lengths.items() if node in scam_set]
            avg_shortest_path_to_known_scam = float(sum(scam_distances) / len(scam_distances)) if scam_distances else 99.0
        else:
            avg_shortest_path_to_known_scam = 99.0
    except Exception:
        avg_shortest_path_to_known_scam = 99.0

    return {
        "wallet_age_days": float(wallet_age_days),
        "tx_count_in": int(tx_count_in),
        "tx_count_out": int(tx_count_out),
        "tx_count_total": int(tx_count_total),
        "unique_counterparties_lifetime": int(unique_counterparties_lifetime),
        "fan_in_ratio": float(fan_in_ratio),
        "median_inter_tx_minutes": float(median_inter_tx_minutes),
        "std_inter_tx_minutes": float(std_inter_tx_minutes),
        "avg_out_value_eth": float(avg_out_value_eth),
        "std_out_value_eth": float(std_out_value_eth),
        "min_in_value_eth": float(min_in_value_eth),
        "current_eth_balance": float(current_eth_balance),
        "approval_count_total": int(approval_count_total),
        "unlimited_approval_count_lifetime": int(unlimited_approval_count_lifetime),
        "unique_spenders_lifetime": int(unique_spenders_lifetime),
        "approval_concentration_top_spender": float(approval_concentration_top_spender),
        "unlimited_approval_rate": float(unlimited_approval_rate),
        "token_transfer_count": int(token_transfer_count),
        "cross_token_approval_same_spender_ratio": float(cross_token_approval_same_spender_ratio),
        "pagerank_subgraph": float(pagerank_subgraph),
        "clustering_coefficient": float(clustering_coefficient),
        "reciprocity_ratio": float(reciprocity_ratio),
        "avg_shortest_path_to_known_scam": float(avg_shortest_path_to_known_scam),
    }
