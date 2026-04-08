import React, { useEffect, useRef } from 'react'

// Formats raw value into a human-readable string
function formatValue(key, val) {
  if (val === null || val === undefined) return '—'
  if (key === 'wallet_age_days') return `${Math.round(val)} days`
  if (key === 'unlimited_approval_rate') return `${(val * 100).toFixed(0)}%`
  if (key === 'fan_in_ratio') return `${(val * 100).toFixed(0)}%`
  if (key === 'approval_concentration_top_spender') return `${(val * 100).toFixed(0)}%`
  if (key === 'cross_token_approval_same_spender_ratio') return `${(val * 100).toFixed(0)}%`
  if (key === 'current_eth_balance' || key === 'avg_out_value_eth' || key === 'min_in_value_eth') {
    return val === 0 ? '0 ETH' : `${parseFloat(val).toFixed(4)} ETH`
  }
  if (key === 'median_inter_tx_minutes') return `${Math.round(val)} min`
  if (['is_verified', 'approval_related_function_flag', 'permit_related_function_flag',
    'setApprovalForAll_flag', 'has_create2', 'proxy_pattern_detected',
    'approval_then_external_call_pattern', 'approval_then_state_mutation_pattern'].includes(key)) {
    return val === 1 ? 'Yes' : 'No'
  }
  if (Number.isInteger(val)) return val.toLocaleString()
  if (typeof val === 'number') return val === 0 ? '0' : val.toFixed(3).replace(/\.?0+$/, '')
  return String(val)
}

// Plain English context sentence for each feature + direction
function getContext(key, val, increases, capped = false) {
  if (key === 'wallet_age_days') {
    const days = Math.round(val)
    if (increases) {
      if (days < 30)  return `Only ${days} day${days === 1 ? '' : 's'} old — brand new wallets are a strong phishing signal.`
      if (days < 90)  return `${days} days old — less than 3 months old, a strong risk signal.`
      if (days < 180) return `${days} days old — less than 6 months old, a moderate risk signal.`
      if (days < 365) return `${days} days old — under a year old; the model found this younger than most legitimate wallets in training data.`
      return `${days} days old — younger than the majority of established wallets, contributing a small risk signal.`
    }
    return `${days} days old — established wallet age, consistent with legitimate activity.`
  }
  if (key === 'tx_count_total') {
    const display = capped ? '500+' : (val === 1 ? '1' : val.toLocaleString())
    if (increases) return `Only ${display} transaction${val === 1 ? '' : 's'} — very low activity is a common trait of scam addresses.`
    return `${display} transactions — high activity suggests a legitimate, active address.`
  }
  if (key === 'unlimited_approval_rate') {
    const pct = (val * 100).toFixed(0)
    if (increases) return `${pct}% of approvals were unlimited — this allows full token drainage.`
    return `${pct}% unlimited approvals — mostly capped approvals indicate safer behaviour.`
  }
  if (key === 'unlimited_approval_count_lifetime') {
    if (increases) return `${val} unlimited approvals given — each one is a potential drain risk.`
    return `Only ${val} unlimited approval${val === 1 ? '' : 's'} — low risk from approvals.`
  }
  if (key === 'approval_count_total') {
    if (increases) return `${val} token approvals given — unusually high approval counts are a phishing signal.`
    return `${val} token approvals — within normal range.`
  }
  if (key === 'avg_shortest_path_to_known_scam') {
    if (increases) return `Only ${val?.toFixed(1)} hop${val <= 1 ? '' : 's'} from a known scam address in the transaction graph.`
    return `${val?.toFixed(1)} hops from known scams — well-separated from bad actors.`
  }
  if (key === 'unique_counterparties_lifetime') {
    if (increases) return `Only ${val} unique address${val === 1 ? '' : 'es'} — very limited interaction history.`
    return `${val.toLocaleString()} unique addresses interacted with — broad legitimate activity.`
  }
  if (key === 'fan_in_ratio') {
    const pct = (val * 100).toFixed(0)
    if (increases) return `${pct}% of transactions are incoming — address mainly receives, rarely sends.`
    return `${pct}% incoming — balanced send/receive activity.`
  }
  if (key === 'approval_concentration_top_spender') {
    const pct = (val * 100).toFixed(0)
    if (increases) return `${pct}% of approvals go to one address — highly concentrated, risky pattern.`
    return `Approvals spread across multiple addresses — less concentrated risk.`
  }
  if (key === 'token_transfer_count') {
    if (increases) return `${val} token transfers — unusually high for a new or low-activity address.`
    return `${val} token transfers — normal transfer activity.`
  }
  if (key === 'median_inter_tx_minutes') {
    if (increases) return `Avg ${Math.round(val)} min between transactions — bot-like timing pattern.`
    return `Avg ${Math.round(val)} min between transactions — natural human timing.`
  }
  if (key === 'pagerank_subgraph') {
    if (increases) return `High network centrality — this address sits at the centre of many transactions.`
    return `Low network centrality — not a hub in the transaction graph.`
  }
  if (key === 'is_verified') {
    if (increases) return `Source code is not verified on Etherscan — unverified contracts are a red flag.`
    return `Source code is verified on Etherscan — transparent and auditable.`
  }
  if (key === 'setApprovalForAll_flag') {
    if (increases) return `Contract has setApprovalForAll — commonly used in NFT drainer contracts.`
    return `No setApprovalForAll — lower blanket approval risk.`
  }
  if (key === 'permit_related_function_flag') {
    if (increases) return `Contract supports gasless approvals (permit) — used to silently drain wallets.`
    return `No gasless permit function detected.`
  }
  if (key === 'approval_then_external_call_pattern') {
    if (increases) return `Approval followed by external call detected in bytecode — classic drainer pattern.`
    return `No approval-then-call pattern found.`
  }
  if (key === 'proxy_pattern_detected') {
    if (increases) return `Upgradeable proxy — contract logic can be replaced after deployment.`
    return `No proxy pattern — contract logic is fixed.`
  }
  if (key === 'abi_function_count') {
    if (increases) return val === 0
      ? `No ABI available — unverified contract. Absence of a public ABI is itself a red flag.`
      : `${val} function${val === 1 ? '' : 's'} in the ABI — unusually high for a simple contract.`
    return `${val} function${val === 1 ? '' : 's'} in the ABI — within normal range.`
  }
  if (key === 'external_public_function_count') {
    if (increases) return val === 0
      ? `No verified public functions — contract source is unverified, functions cannot be inspected.`
      : `${val} state-changing public function${val === 1 ? '' : 's'} — high number increases attack surface.`
    return `${val} state-changing public function${val === 1 ? '' : 's'} — within normal range.`
  }
  if (key === 'control_flow_complexity_score') {
    if (increases) return `High code complexity — may indicate obfuscated or deliberately confusing logic.`
    return `Low code complexity — straightforward contract logic.`
  }
  if (key === 'cross_token_approval_same_spender_ratio') {
    const pct = (val * 100).toFixed(0)
    if (increases) return `${pct}% of approvals use the same spender across multiple tokens — a drainer pattern.`
    return `Approvals are spread across different spenders.`
  }
  if (key === 'tx_count_in') {
    if (increases) return `${val} incoming transaction${val === 1 ? '' : 's'} — unusually high inbound count can indicate a drainer collecting from victims.`
    return `${val} incoming transactions — normal inbound activity.`
  }
  if (key === 'tx_count_out') {
    if (increases) return `Only ${val} outgoing transaction${val === 1 ? '' : 's'} — very few sends is typical of dormant or newly deployed scam addresses.`
    return `${val} outgoing transactions — active sending history consistent with legitimate use.`
  }
  if (key === 'std_inter_tx_minutes') {
    if (increases) return `Low variance in transaction timing — robotic, clock-like intervals suggest automated or bot-driven activity.`
    return `High variance in transaction timing — irregular intervals suggest human-driven activity.`
  }
  if (key === 'avg_out_value_eth') {
    if (increases) return val === 0
      ? `No outbound ETH transfers — address only receives, never sends ETH.`
      : `Avg outbound value ${parseFloat(val).toFixed(4)} ETH — elevated average can indicate large fund movements.`
    return val === 0
      ? `No outbound ETH transfers recorded.`
      : `Avg outbound value ${parseFloat(val).toFixed(4)} ETH — within normal range.`
  }
  if (key === 'std_out_value_eth') {
    if (increases) return `High variance in outbound ETH amounts — erratic transfer sizes are common in draining operations.`
    return `Consistent outbound ETH amounts — stable transfer sizes suggest routine activity.`
  }
  if (key === 'min_in_value_eth') {
    if (increases) return val === 0
      ? `Minimum inbound value is 0 ETH — dust transactions or zero-value calls, often used in phishing lures.`
      : `Minimum inbound value ${parseFloat(val).toFixed(4)} ETH — very small deposits can indicate test or lure transactions.`
    return `Minimum inbound value ${parseFloat(val).toFixed(4)} ETH — no anomalous dust activity detected.`
  }
  if (key === 'current_eth_balance') {
    if (increases) return val === 0
      ? `Current ETH balance is 0 — funds have been fully drained or never held; consistent with a swept wallet.`
      : `Current balance ${parseFloat(val).toFixed(4)} ETH — elevated balance on a suspicious address warrants caution.`
    return val === 0
      ? `Zero ETH balance — no funds currently held.`
      : `Current balance ${parseFloat(val).toFixed(4)} ETH — within expected range.`
  }
  if (key === 'unique_spenders_lifetime') {
    if (increases) return `${val} unique spender${val === 1 ? '' : 's'} approved lifetime — many distinct spenders amplify the drain attack surface.`
    return `Only ${val} unique spender${val === 1 ? '' : 's'} approved — limited approval exposure.`
  }
  if (key === 'reciprocity_ratio') {
    const pct = (val * 100).toFixed(0)
    if (increases) return `${pct}% of counterparties are one-way — address sends to or receives from most parties without any reciprocal interaction, typical of scam flows.`
    return `${pct}% reciprocal interactions — two-way activity with counterparties suggests genuine relationships.`
  }
  if (key === 'clustering_coefficient') {
    if (increases) return `High clustering in transaction graph — address sits inside a tightly connected cluster, common in coordinated scam networks.`
    return `Low clustering coefficient — address interacts with diverse, unconnected parties.`
  }
  if (key === 'bytecode_size') {
    if (increases) return val === 0
      ? `No bytecode — address has no deployed code, which is unexpected for an address classified as a contract.`
      : `${val} bytes of bytecode — large contracts can hide complex or obfuscated logic.`
    return val === 0
      ? `No bytecode detected.`
      : `${val} bytes of bytecode — within normal contract size range.`
  }
  if (key === 'approval_related_function_flag') {
    if (increases) return `Contract contains approval-related functions — capable of requesting token spending permissions from users.`
    return `No approval-related functions detected — contract does not request token permissions.`
  }
  if (key === 'has_create2') {
    if (increases) return `Contract uses CREATE2 — allows deploying child contracts to predictable addresses, a common technique in factory-based drainer toolkits.`
    return `No CREATE2 usage — contract does not dynamically deploy sub-contracts.`
  }
  if (key === 'opcode_freq_CALL') {
    if (increases) return `High CALL opcode frequency — contract makes many external calls, increasing the risk of reentrancy or fund forwarding.`
    return `Low CALL frequency — few external calls, reducing reentrancy exposure.`
  }
  if (key === 'opcode_freq_DELEGATECALL') {
    if (increases) return `DELEGATECALL present in bytecode — executes external code in the contract's own storage context; a known attack vector.`
    return `No DELEGATECALL detected — contract does not delegate execution to external code.`
  }
  if (key === 'opcode_freq_SELFDESTRUCT') {
    if (increases) return `SELFDESTRUCT opcode present — contract can destroy itself and sweep all ETH to an arbitrary address.`
    return `No SELFDESTRUCT — contract cannot self-destruct or drain its ETH balance.`
  }
  if (key === 'opcode_freq_SSTORE') {
    if (increases) return `High SSTORE frequency — many state writes; complex state manipulation can obscure fund movements.`
    return `Low SSTORE frequency — minimal state writes, straightforward contract behaviour.`
  }
  if (key === 'opcode_freq_JUMPI') {
    if (increases) return `High conditional branch count — complex control flow can hide malicious execution paths in obfuscated contracts.`
    return `Low conditional branch count — simple, transparent control flow.`
  }
  if (key === 'slither_warning_count_total') {
    if (increases) return `${val} Slither warning${val === 1 ? '' : 's'} detected — static analysis found potential vulnerabilities or dangerous patterns.`
    return `No Slither warnings — static analysis found no flagged patterns.`
  }
  if (key === 'slither_low_level_call_count') {
    if (increases) return `${val} low-level call${val === 1 ? '' : 's'} (assembly/call) — bypasses Solidity safety checks, often used in drainer contracts.`
    return `No low-level calls — contract uses safe, high-level Solidity calls only.`
  }
  if (key === 'slither_access_control_issues_count') {
    if (increases) return `${val} access control issue${val === 1 ? '' : 's'} — functions lack proper permission checks, allowing unauthorised actions.`
    return `No access control issues — functions are properly permissioned.`
  }
  if (key === 'external_call_sites_count') {
    if (increases) return `${val} external call site${val === 1 ? '' : 's'} — contract calls out to other addresses in many places, increasing attack surface.`
    return `${val} external call site${val === 1 ? '' : 's'} — limited external interactions.`
  }
  if (key === 'approval_then_state_mutation_pattern') {
    if (increases) return `Approval followed by state mutation detected — contract modifies storage after token approvals, a pattern seen in drainer logic.`
    return `No approval-then-state-mutation pattern found.`
  }
  // Fallback
  if (increases) return `This signal is elevated, contributing to a higher risk score.`
  return `This signal is within a safe range, reducing the risk score.`
}

export default function ExplanationCard({ item, index, features = {} }) {
  const increases = item.direction === 'increases_risk'
  const accentColor = increases ? '#ff4444' : '#00ff88'
  const barRef = useRef(null)

  // For wallet_age_days use the display value (real days) not the log-transformed model value
  const rawVal = item.feature === 'wallet_age_days' && features.wallet_age_days_display !== undefined
    ? features.wallet_age_days_display
    : features[item.feature]
  const isCapped = item.feature === 'tx_count_total' && !!features.tx_count_capped
  const formattedVal = rawVal !== undefined
    ? (isCapped ? '500+' : formatValue(item.feature, rawVal))
    : null
  const context = getContext(item.feature, rawVal, increases, isCapped)
  const impactLabel = Math.abs(item.shap_value) > 2 ? 'Very High' : Math.abs(item.shap_value) > 1 ? 'High' : Math.abs(item.shap_value) > 0.5 ? 'Medium' : 'Low'
  const barPct = Math.min(Math.abs(item.shap_value) / 3.5 * 100, 100).toFixed(1)

  useEffect(() => {
    if (!barRef.current) return
    const timer = setTimeout(() => {
      if (barRef.current) barRef.current.style.width = `${barPct}%`
    }, 300 + index * 100 + 400)
    return () => clearTimeout(timer)
  }, [barPct, index])

  return (
    <div
      className="rounded-2xl p-5 relative cursor-default flex flex-col"
      style={{
        background: 'rgba(255,255,255,0.09)',
        border: `1px solid ${increases ? 'rgba(255,68,68,0.25)' : 'rgba(0,255,136,0.2)'}`,
        backdropFilter: 'blur(20px)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
        opacity: 0,
        animation: `fadeUp 0.5s ease-out ${0.1 + index * 0.1}s forwards`,
        transition: 'border-color 200ms, transform 200ms, box-shadow 200ms',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.4)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,0.3)'
      }}
    >
      {/* Direction badge */}
      <div className="flex items-center gap-1.5 mb-3">
        <span className="text-base font-bold leading-none" style={{ color: accentColor }}>
          {increases ? '↑' : '↓'}
        </span>
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: accentColor }}>
          {increases ? 'Raises risk' : 'Lowers risk'}
        </span>
        <span
          className="ml-auto text-xs font-medium px-2 py-0.5 rounded-full"
          style={{
            background: increases ? 'rgba(255,68,68,0.12)' : 'rgba(0,255,136,0.1)',
            color: increases ? '#ff8080' : '#00cc77',
          }}
        >
          {impactLabel}
        </span>
      </div>

      {/* Feature name */}
      <div className="text-white/60 text-xs mb-1">{item.description}</div>

      {/* Value — hero number */}
      {formattedVal !== null && (
        <div
          className="text-2xl font-bold mb-2 leading-tight"
          style={{ color: increases ? '#ff6b6b' : '#00ff88' }}
        >
          {formattedVal}
        </div>
      )}

      {/* Plain English context */}
      <div className="text-white/50 text-xs leading-relaxed mb-4">
        {context}
      </div>

      {/* Impact bar */}
      <div className="mt-auto h-1 rounded-full bg-white/10 overflow-hidden">
        <div
          ref={barRef}
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: '0%', background: `linear-gradient(90deg, ${accentColor}88, ${accentColor})` }}
        />
      </div>
    </div>
  )
}
