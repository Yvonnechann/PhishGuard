import React from 'react'

export default function AnalysisTypeTag({ type }) {
  const isWallet = type === 'wallet'
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold"
      style={{
        background: isWallet ? 'rgba(0,204,255,0.12)' : 'rgba(0,255,136,0.12)',
        border: `1px solid ${isWallet ? 'rgba(0,204,255,0.3)' : 'rgba(0,255,136,0.3)'}`,
        color: isWallet ? '#00ccff' : '#00ff88',
      }}
    >
      <span>{isWallet ? '◎' : '⬡'}</span>
      {isWallet ? 'Wallet Analysis' : 'Smart Contract Analysis'}
    </span>
  )
}
