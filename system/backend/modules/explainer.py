import logging

import numpy as np

logger = logging.getLogger("phishguard.explainer")

FEATURE_DESCRIPTIONS = {
    "wallet_age_days": "Wallet age in days",
    "tx_count_in": "Number of inbound transactions",
    "tx_count_out": "Number of outbound transactions",
    "tx_count_total": "Total transaction count lifetime",
    "unique_counterparties_lifetime": "Unique addresses interacted with lifetime",
    "fan_in_ratio": "Proportion of inbound vs total transactions",
    "median_inter_tx_minutes": "Median time between transactions in minutes",
    "std_inter_tx_minutes": "Variability in transaction timing",
    "avg_out_value_eth": "Average ETH value sent outbound",
    "std_out_value_eth": "Variability in outbound ETH values",
    "min_in_value_eth": "Minimum inbound transaction value in ETH",
    "current_eth_balance": "Current ETH balance",
    "approval_count_total": "Total token approvals granted lifetime",
    "unlimited_approval_count_lifetime": "Lifetime count of unlimited token approvals",
    "unique_spenders_lifetime": "Distinct spender addresses approved lifetime",
    "approval_concentration_top_spender": "Fraction of approvals to single top spender",
    "unlimited_approval_rate": "Rate of unlimited approvals to total approvals",
    "token_transfer_count": "Total ERC-20 token transfer events",
    "cross_token_approval_same_spender_ratio": "Cross-token approvals to same spender address",
    "pagerank_subgraph": "Network centrality score in transaction graph",
    "clustering_coefficient": "How interconnected counterparties are",
    "reciprocity_ratio": "Proportion of two-way transaction relationships",
    "avg_shortest_path_to_known_scam": "Graph distance to nearest confirmed scam address",
    "is_verified": "Source code verified on Etherscan",
    "bytecode_size": "Size of contract bytecode in bytes",
    "abi_function_count": "Number of functions in contract ABI",
    "external_public_function_count": "Number of state-changing public functions",
    "approval_related_function_flag": "Contains token approval functions",
    "permit_related_function_flag": "Contains EIP-2612 gasless permit function",
    "setApprovalForAll_flag": "Contains setApprovalForAll — NFT drainer risk",
    "opcode_freq_CALL": "Frequency of external call operations",
    "opcode_freq_DELEGATECALL": "Frequency of delegate call operations",
    "opcode_freq_SELFDESTRUCT": "Frequency of self-destruct operations",
    "opcode_freq_SSTORE": "Frequency of state write operations",
    "opcode_freq_JUMPI": "Frequency of conditional jump operations",
    "external_call_sites_count": "Number of distinct external call sites",
    "has_create2": "Uses CREATE2 deterministic deployment",
    "proxy_pattern_detected": "Matches known upgradeable proxy pattern",
    "approval_then_external_call_pattern": "Approval followed by external call pattern",
    "approval_then_state_mutation_pattern": "Approval followed by state mutation pattern",
    "control_flow_complexity_score": "Control flow complexity per byte of bytecode",
    "slither_warning_count_total": "Total static analysis warnings",
    "slither_low_level_call_count": "Low-level call warnings from static analysis",
    "slither_access_control_issues_count": "Access control issues from static analysis",
}


def explain(feature_array, explainer, feature_names: list) -> list:
    try:
        raw = explainer.shap_values(feature_array)

        # shap_values may return a list (one array per class) or a single array
        if isinstance(raw, list):
            shap_vals = np.array(raw[1]).flatten()
        else:
            shap_vals = np.array(raw).flatten()

        pairs = sorted(
            zip(feature_names, shap_vals),
            key=lambda x: abs(x[1]),
            reverse=True,
        )

        result = []
        for feature, sv in pairs[:3]:
            sv_float = float(sv)
            result.append({
                "feature": feature,
                "shap_value": round(sv_float, 4),
                "direction": "increases_risk" if sv_float > 0 else "decreases_risk",
                "description": FEATURE_DESCRIPTIONS.get(feature, feature),
            })

        return result
    except Exception as exc:
        logger.error(f"explainer failed: {exc}")
        return []
