import React, { useEffect, useRef, useState } from 'react'

const TOOLTIPS = {
  wallet_age_days: 'How long this wallet has existed on-chain.',
  tx_count_in: 'How many transactions this address received.',
  tx_count_out: 'How many transactions this address sent.',
  tx_count_total: 'Total number of on-chain transactions.',
  unique_counterparties_lifetime: 'Number of distinct addresses ever interacted with.',
  fan_in_ratio: 'What fraction of transactions were incoming.',
  median_inter_tx_minutes: 'Typical gap between transactions in minutes.',
  std_inter_tx_minutes: 'How irregular the transaction timing is.',
  avg_out_value_eth: 'Average ETH sent per outbound transaction.',
  std_out_value_eth: 'How varied the outbound ETH amounts are.',
  min_in_value_eth: 'Smallest ETH amount ever received.',
  current_eth_balance: 'Current ETH balance of this address.',
  approval_count_total: 'Total ERC-20 token approvals granted.',
  unlimited_approval_count_lifetime: 'Number of unlimited token spend approvals.',
  unique_spenders_lifetime: 'How many different addresses were approved to spend tokens.',
  approval_concentration_top_spender: 'How concentrated approvals are to one spender.',
  unlimited_approval_rate: 'Fraction of approvals that were unlimited.',
  token_transfer_count: 'Total ERC-20 token transfer events.',
  cross_token_approval_same_spender_ratio: 'How often the same spender was approved across multiple tokens.',
  pagerank_subgraph: 'Centrality of this address in its transaction network.',
  clustering_coefficient: 'How interconnected its counterparties are.',
  reciprocity_ratio: 'Fraction of two-way transaction relationships.',
  avg_shortest_path_to_known_scam: 'Network distance to nearest known scam address.',
  is_verified: 'Whether the contract source code is verified.',
  bytecode_size: 'Size of the contract bytecode in bytes.',
  abi_function_count: 'Number of functions in the contract ABI.',
  external_public_function_count: 'Number of state-changing public functions.',
  approval_related_function_flag: 'Contract has token approval functions.',
  permit_related_function_flag: 'Contract has gasless permit functionality.',
  setApprovalForAll_flag: 'Contract has setApprovalForAll — common in NFT drainers.',
  opcode_freq_CALL: 'How often external calls occur in the bytecode.',
  opcode_freq_DELEGATECALL: 'How often delegate calls occur.',
  opcode_freq_SELFDESTRUCT: 'How often self-destruct occurs.',
  opcode_freq_SSTORE: 'How often state is written.',
  opcode_freq_JUMPI: 'Frequency of conditional jumps (control flow complexity).',
  external_call_sites_count: 'Number of distinct external call sites.',
  has_create2: 'Uses CREATE2 for deterministic contract deployment.',
  proxy_pattern_detected: 'Matches EIP-1967 upgradeable proxy pattern.',
  approval_then_external_call_pattern: 'Approval opcode followed by external call.',
  approval_then_state_mutation_pattern: 'Approval opcode followed by state write.',
  control_flow_complexity_score: 'Control flow complexity relative to bytecode size.',
  slither_warning_count_total: 'Total static analysis warnings.',
  slither_low_level_call_count: 'Low-level call warnings.',
  slither_access_control_issues_count: 'Access control issues found.',
}

export default function ExplanationCard({ item, index }) {
  const increases = item.direction === 'increases_risk'
  const accentColor = increases ? '#ff4444' : '#00ff88'
  const barRef = useRef(null)
  const [showTip, setShowTip] = useState(false)

  // Bar width: normalize abs(shap_value) against ~3.5 max, cap at 100%
  const barPct = Math.min(Math.abs(item.shap_value) / 3.5 * 100, 100).toFixed(1)

  // Animate bar after card fades in
  useEffect(() => {
    if (!barRef.current) return
    const delay = 300 + index * 100 + 400 // after card appears
    const timer = setTimeout(() => {
      if (barRef.current) {
        barRef.current.style.width = `${barPct}%`
      }
    }, delay)
    return () => clearTimeout(timer)
  }, [barPct, index])

  return (
    <div
      className="rounded-2xl p-5 relative cursor-default group flex flex-col"
      style={{
        background: 'rgba(255,255,255,0.09)',
        border: '1px solid rgba(255,255,255,0.28)',
        backdropFilter: 'blur(20px)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
        opacity: 0,
        animation: `fadeUp 0.5s ease-out ${0.1 + index * 0.1}s forwards`,
        transition: 'border-color 200ms, transform 200ms, box-shadow 200ms',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.30)'
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = `0 8px 32px rgba(0,0,0,0.4)`
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.28)'
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      {/* Direction indicator */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl font-bold" style={{ color: accentColor }}>
          {increases ? '↑' : '↓'}
        </span>
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: accentColor }}>
          {increases ? 'Raises risk score' : 'Lowers risk score'}
        </span>
      </div>

      {/* Feature description */}
      <div
        className="text-white text-sm font-medium leading-snug mb-4 flex items-start gap-1"
        onMouseEnter={() => setShowTip(true)}
        onMouseLeave={() => setShowTip(false)}
      >
        <span>{item.description}</span>
        <span className="text-white/30 text-xs mt-0.5 cursor-help shrink-0">ⓘ</span>
      </div>

      {/* Tooltip */}
      {showTip && TOOLTIPS[item.feature] && (
        <div
          className="absolute left-0 right-0 -top-1 -translate-y-full rounded-xl p-3 text-xs text-white/80 leading-relaxed z-50"
          style={{ background: 'rgba(10,10,20,0.95)', border: '1px solid rgba(255,255,255,0.12)', backdropFilter: 'blur(20px)' }}
        >
          {TOOLTIPS[item.feature]}
        </div>
      )}

      {/* Magnitude bar */}
      <div className="mt-auto h-1.5 rounded-full bg-white/10 overflow-hidden">
        <div
          ref={barRef}
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: '0%', background: `linear-gradient(90deg, ${accentColor}99, ${accentColor})` }}
        />
      </div>

      {/* Impact */}
      <div className="text-[rgba(255,255,255,0.35)] text-xs mt-2 text-right">
        Impact: {Math.abs(item.shap_value) > 2 ? 'Very High' : Math.abs(item.shap_value) > 1 ? 'High' : Math.abs(item.shap_value) > 0.5 ? 'Medium' : 'Low'}
      </div>
    </div>
  )
}
