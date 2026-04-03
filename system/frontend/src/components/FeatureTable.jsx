import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'

const WALLET_GROUPS = [
  {
    label: 'Activity & Age',
    icon: '📊',
    keys: [
      'wallet_age_days',
      'tx_count_total',
      'tx_count_in',
      'tx_count_out',
      'unique_counterparties_lifetime',
      'current_eth_balance',
      'avg_out_value_eth',
      'median_inter_tx_minutes',
    ],
  },
  {
    label: 'Token Approvals',
    icon: '🔑',
    keys: [
      'approval_count_total',
      'unlimited_approval_count_lifetime',
      'unlimited_approval_rate',
      'unique_spenders_lifetime',
      'approval_concentration_top_spender',
      'token_transfer_count',
      'cross_token_approval_same_spender_ratio',
    ],
  },
  {
    label: 'Network Behaviour',
    icon: '🕸',
    keys: [
      'fan_in_ratio',
      'pagerank_subgraph',
      'clustering_coefficient',
      'reciprocity_ratio',
      'avg_shortest_path_to_known_scam',
    ],
  },
]

const CONTRACT_GROUPS = [
  {
    label: 'Code & Structure',
    icon: '📋',
    keys: [
      'is_verified',
      'bytecode_size',
      'abi_function_count',
      'external_public_function_count',
      'external_call_sites_count',
      'control_flow_complexity_score',
    ],
  },
  {
    label: 'Dangerous Patterns',
    icon: '⚠️',
    keys: [
      'approval_related_function_flag',
      'permit_related_function_flag',
      'setApprovalForAll_flag',
      'has_create2',
      'proxy_pattern_detected',
      'approval_then_external_call_pattern',
      'approval_then_state_mutation_pattern',
    ],
  },
  {
    label: 'Opcode Signals',
    icon: '⚙️',
    keys: [
      'opcode_freq_CALL',
      'opcode_freq_DELEGATECALL',
      'opcode_freq_SELFDESTRUCT',
      'opcode_freq_SSTORE',
      'opcode_freq_JUMPI',
    ],
  },
  {
    label: 'Static Analysis',
    icon: '🔬',
    keys: [
      'slither_warning_count_total',
      'slither_low_level_call_count',
      'slither_access_control_issues_count',
    ],
  },
]

const FEATURE_INFO = {
  wallet_age_days:                        { label: 'Wallet Age',                  hint: 'Days on-chain. New wallets = higher risk.' },
  tx_count_total:                         { label: 'Total Transactions',          hint: 'All-time tx count. Very low is suspicious.' },
  tx_count_in:                            { label: 'Incoming Txs',                hint: 'Transactions received.' },
  tx_count_out:                           { label: 'Outgoing Txs',                hint: 'Transactions sent.' },
  unique_counterparties_lifetime:         { label: 'Unique Addresses',            hint: 'Distinct addresses ever interacted with.' },
  current_eth_balance:                    { label: 'ETH Balance',                 hint: 'Current ETH held.' },
  avg_out_value_eth:                      { label: 'Avg Sent (ETH)',              hint: 'Average ETH per outgoing tx.' },
  median_inter_tx_minutes:                { label: 'Avg Gap Between Txs',         hint: 'Median minutes between txs. Near-zero = bot.' },
  approval_count_total:                   { label: 'Token Approvals Given',       hint: 'Times this wallet approved others to spend tokens.' },
  unlimited_approval_count_lifetime:      { label: 'Unlimited Approvals',         hint: 'No-cap approvals — allow full token drain.' },
  unlimited_approval_rate:                { label: 'Unlimited Approval Rate',     hint: '% of approvals with no cap. High = red flag.' },
  unique_spenders_lifetime:               { label: 'Approved Spenders',           hint: 'Unique addresses approved to spend tokens.' },
  approval_concentration_top_spender:     { label: 'Approval Concentration',      hint: '% going to one spender. High = concentrated risk.' },
  token_transfer_count:                   { label: 'Token Transfers',             hint: 'Total ERC-20 transfer events.' },
  cross_token_approval_same_spender_ratio:{ label: 'Same Spender Across Tokens',  hint: 'Same address approved for many tokens. Phishing signal.' },
  fan_in_ratio:                           { label: 'Incoming Ratio',              hint: '% of txs that are incoming.' },
  pagerank_subgraph:                      { label: 'Network Centrality',          hint: 'Importance in transaction graph (like PageRank).' },
  clustering_coefficient:                 { label: 'Counterparty Clustering',     hint: 'How connected this wallet\'s contacts are.' },
  reciprocity_ratio:                      { label: 'Two-Way Relationships',       hint: '% of contacts that both sent & received.' },
  avg_shortest_path_to_known_scam:        { label: 'Distance to Known Scam',      hint: 'Hops to nearest scam address. Lower = closer.' },
  is_verified:                            { label: 'Source Code Verified',        hint: 'Verified on Etherscan. Unverified = red flag.' },
  bytecode_size:                          { label: 'Bytecode Size',               hint: 'Deployed contract size in bytes.' },
  abi_function_count:                     { label: 'Function Count',              hint: 'Total functions in the ABI.' },
  external_public_function_count:         { label: 'Public Functions',            hint: 'State-changing functions anyone can call.' },
  external_call_sites_count:              { label: 'External Call Sites',         hint: 'Places that call other contracts.' },
  control_flow_complexity_score:          { label: 'Code Complexity',             hint: 'Logic complexity vs size. High = possibly obfuscated.' },
  approval_related_function_flag:         { label: 'Has Approval Functions',      hint: 'Includes approve/allowance functions.' },
  permit_related_function_flag:           { label: 'Has Gasless Permit',          hint: 'Silent approvals via EIP-2612. Used in drainers.' },
  setApprovalForAll_flag:                 { label: 'Has setApprovalForAll',       hint: 'Blanket NFT/token approval. Common in drainers.' },
  has_create2:                            { label: 'Uses CREATE2',                hint: 'Deploys to predictable addresses. Advanced phishing tool.' },
  proxy_pattern_detected:                 { label: 'Upgradeable Proxy',           hint: 'Logic can be swapped post-deployment.' },
  approval_then_external_call_pattern:    { label: 'Approval → External Call',    hint: 'Classic drainer pattern in bytecode.' },
  approval_then_state_mutation_pattern:   { label: 'Approval → State Write',      hint: 'Approval data recorded — suspicious.' },
  opcode_freq_CALL:                       { label: 'External Call Rate',          hint: 'How often it calls other contracts.' },
  opcode_freq_DELEGATECALL:               { label: 'Delegate Call Rate',          hint: 'Runs another contract\'s code in own context.' },
  opcode_freq_SELFDESTRUCT:               { label: 'Self-Destruct Rate',          hint: 'Destroys contract & sends funds. Rug pull signal.' },
  opcode_freq_SSTORE:                     { label: 'State Write Rate',            hint: 'Frequency of storage writes.' },
  opcode_freq_JUMPI:                      { label: 'Branch Frequency',            hint: 'Conditional jumps — logic complexity.' },
  slither_warning_count_total:            { label: 'Code Warnings',               hint: 'Issues found by static analysis.' },
  slither_low_level_call_count:           { label: 'Low-Level Call Warnings',     hint: 'Risky direct calls flagged.' },
  slither_access_control_issues_count:    { label: 'Access Control Issues',       hint: 'Functions missing permission checks.' },
}

// Determine if a value is "concerning" for coloring
function isConcerning(key, val) {
  const highBad = [
    'unlimited_approval_rate', 'unlimited_approval_count_lifetime', 'approval_concentration_top_spender',
    'cross_token_approval_same_spender_ratio', 'opcode_freq_SELFDESTRUCT', 'slither_warning_count_total',
    'slither_low_level_call_count', 'slither_access_control_issues_count', 'control_flow_complexity_score',
    'approval_then_external_call_pattern', 'approval_then_state_mutation_pattern',
    'setApprovalForAll_flag', 'permit_related_function_flag',
  ]
  const lowBad = ['wallet_age_days', 'tx_count_total', 'avg_shortest_path_to_known_scam', 'is_verified']

  if (highBad.includes(key)) return val > 0
  if (lowBad.includes(key)) {
    if (key === 'is_verified') return val === 0
    if (key === 'wallet_age_days') return val < 30
    if (key === 'tx_count_total') return val < 5
    if (key === 'avg_shortest_path_to_known_scam') return val > 0 && val < 2
  }
  return false
}

function formatValue(key, val) {
  if (typeof val === 'boolean') return val ? 'Yes' : 'No'
  if (val === 1 && ['is_verified', 'approval_related_function_flag', 'permit_related_function_flag',
    'setApprovalForAll_flag', 'has_create2', 'proxy_pattern_detected',
    'approval_then_external_call_pattern', 'approval_then_state_mutation_pattern'].includes(key)) return 'Yes'
  if (val === 0 && ['is_verified', 'approval_related_function_flag', 'permit_related_function_flag',
    'setApprovalForAll_flag', 'has_create2', 'proxy_pattern_detected',
    'approval_then_external_call_pattern', 'approval_then_state_mutation_pattern'].includes(key)) return 'No'
  if (key === 'unlimited_approval_rate') return `${(val * 100).toFixed(0)}%`
  if (key === 'approval_concentration_top_spender') return `${(val * 100).toFixed(0)}%`
  if (key === 'fan_in_ratio') return `${(val * 100).toFixed(0)}%`
  if (key === 'cross_token_approval_same_spender_ratio') return `${(val * 100).toFixed(0)}%`
  if (key === 'current_eth_balance' || key === 'avg_out_value_eth' || key === 'min_in_value_eth') {
    return val === 0 ? '0 ETH' : `${val.toFixed(4)} ETH`
  }
  if (key === 'wallet_age_days') return `${Math.round(val)} days`
  if (Number.isInteger(val)) return val.toLocaleString()
  if (typeof val === 'number') {
    if (val === 0) return '0'
    if (Math.abs(val) < 0.0001) return val.toExponential(2)
    return val.toFixed(4).replace(/\.?0+$/, '')
  }
  return String(val)
}

function FeatureRow({ featureKey, val }) {
  const info = FEATURE_INFO[featureKey] || { label: featureKey, hint: '' }
  const concerning = isConcerning(featureKey, val)
  const formatted = formatValue(featureKey, val)
  const [tipPos, setTipPos] = useState(null)

  return (
    <div
      className="flex items-center justify-between gap-4 py-2.5"
      style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
    >
      <div className="flex items-center gap-1.5 min-w-0">
        <span className="text-white/70 text-sm">{info.label}</span>
        {info.hint && (
          <button
            className="text-white/30 hover:text-white/60 text-xs shrink-0 transition-colors"
            onMouseEnter={e => {
              const r = e.currentTarget.getBoundingClientRect()
              setTipPos({ x: r.left, y: r.bottom + 6 })
            }}
            onMouseLeave={() => setTipPos(null)}
          >
            ⓘ
          </button>
        )}
      </div>

      {tipPos && createPortal(
        <div
          style={{
            position: 'fixed',
            left: Math.min(tipPos.x, window.innerWidth - 260),
            top: tipPos.y,
            zIndex: 9999,
            background: '#0d1117',
            border: '1px solid rgba(0,255,136,0.5)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.85)',
            borderRadius: '10px',
            padding: '10px 14px',
            maxWidth: '240px',
            fontSize: '12px',
            color: 'rgba(255,255,255,0.85)',
            lineHeight: '1.5',
            pointerEvents: 'none',
          }}
        >
          {info.hint}
        </div>,
        document.body
      )}

      <span
        className="text-sm font-mono font-medium shrink-0"
        style={{ color: concerning ? '#ff6b6b' : 'rgba(255,255,255,0.85)' }}
      >
        {formatted}
      </span>
    </div>
  )
}

function FeatureGroup({ group, features, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const entries = group.keys.filter(k => k in features)

  if (entries.length === 0) return null

  return (
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
      <button
        className="w-full flex items-center justify-between px-6 py-3 text-left group"
        onClick={() => setOpen(v => !v)}
      >
        <span className="flex items-center gap-2 text-sm font-medium text-white/60 group-hover:text-white/90 transition-colors">
          <span>{group.icon}</span>
          <span>{group.label}</span>
          <span className="text-white/25 text-xs font-normal">({entries.length})</span>
        </span>
        <span
          className="text-white/30 text-sm transition-transform duration-300"
          style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)', display: 'inline-block' }}
        >
          ▾
        </span>
      </button>
      {open && (
        <div className="px-6 pb-4">
          {entries.map(k => (
            <FeatureRow key={k} featureKey={k} val={features[k]} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function FeatureTable({ features, analysisType }) {
  const [open, setOpen] = useState(false)
  const groups = analysisType === 'wallet' ? WALLET_GROUPS : CONTRACT_GROUPS

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(255,255,255,0.09)',
        border: '1px solid rgba(255,255,255,0.28)',
        backdropFilter: 'blur(20px)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
      }}
    >
      {/* Main toggle */}
      <button
        className="w-full flex items-center justify-between px-6 py-4 text-left group"
        onClick={() => setOpen(v => !v)}
      >
        <div>
          <span className="font-semibold text-sm text-white/80 group-hover:text-white transition-colors">
            Raw Signal Data
          </span>
          <span className="text-white/35 text-xs ml-2">
            {Object.keys(features).length} signals
          </span>
        </div>
        <span
          className="text-white/40 group-hover:text-white/70 text-lg transition-transform duration-300"
          style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)', display: 'inline-block' }}
        >
          ▾
        </span>
      </button>

      {open && (
        <div>
          <div className="px-6 pb-3 text-xs text-white/35 leading-relaxed" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <span className="inline-block mt-3">
              <span style={{ color: '#ff6b6b' }}>Red values</span> indicate elevated risk. Hover <span className="text-white/50">ⓘ</span> for details.
            </span>
          </div>
          {groups.map(group => (
            <FeatureGroup key={group.label} group={group} features={features} />
          ))}
        </div>
      )}
    </div>
  )
}
