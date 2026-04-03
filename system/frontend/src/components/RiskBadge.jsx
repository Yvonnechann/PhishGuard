import React, { useEffect, useState } from 'react'
import AnalysisTypeTag from './AnalysisTypeTag'

const RISK_CONFIG = {
  HIGH:   { color: '#ff4444', glow: 'rgba(255,68,68,0.3)',   bg: 'rgba(255,68,68,0.08)',   label: 'HIGH RISK' },
  MEDIUM: { color: '#ff8800', glow: 'rgba(255,136,0,0.3)',   bg: 'rgba(255,136,0,0.08)',   label: 'MEDIUM RISK' },
  LOW:    { color: '#00ff88', glow: 'rgba(0,255,136,0.3)',   bg: 'rgba(0,255,136,0.08)',   label: 'LOW RISK' },
}

const SUMMARIES = {
  HIGH:   '⚠️ Strong indicators of phishing activity detected. Avoid sending funds to this address or approving any token requests from it.',
  MEDIUM: '⚠️ This address has suspicious on-chain characteristics. Exercise caution before interacting.',
  LOW:    '✅ No significant risk indicators found. This address appears safe based on its on-chain activity.',
}

export default function RiskBadge({ result }) {
  const [displayScore, setDisplayScore] = useState(0)
  const cfg = RISK_CONFIG[result.risk_label] || RISK_CONFIG.LOW
  const targetPct = Math.round(result.final_score * 100)

  // Count-up animation
  useEffect(() => {
    const duration = 800
    const start = performance.now()
    function tick(now) {
      const t = Math.min((now - start) / duration, 1)
      // ease-out quad
      const eased = 1 - (1 - t) * (1 - t)
      setDisplayScore(Math.round(eased * targetPct))
      if (t < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [targetPct])

  return (
    <div
      className="rounded-2xl p-8 transition-all duration-200"
      style={{
        background: `${cfg.bg}`,
        border: `1px solid ${cfg.color}66`,
        backdropFilter: 'blur(20px)',
        boxShadow: `0 0 40px ${cfg.glow}`,
        opacity: 0,
        animation: 'fadeUp 0.5s ease-out 0s forwards',
      }}
    >
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">

        {/* Left: score + label */}
        <div className="flex items-center gap-6">
          {/* Big score circle */}
          <div
            className="w-24 h-24 rounded-full flex flex-col items-center justify-center shrink-0"
            style={{
              border: `3px solid ${cfg.color}`,
              boxShadow: `0 0 24px ${cfg.glow}, inset 0 0 16px ${cfg.bg}`,
              background: cfg.bg,
            }}
          >
            <span className="text-2xl font-extrabold" style={{ color: cfg.color }}>
              {displayScore}%
            </span>
          </div>

          <div>
            <div
              className="text-3xl font-extrabold tracking-wide mb-1"
              style={{ color: cfg.color, textShadow: `0 0 20px ${cfg.glow}` }}
            >
              {cfg.label}
            </div>
            <div className="text-[rgba(255,255,255,0.5)] text-sm mb-3">
              Phishing risk probability
            </div>
            <AnalysisTypeTag type={result.analysis_type} />
          </div>
        </div>

        {/* Right: summary */}
        <div
          className="md:max-w-xs text-[rgba(255,255,255,0.7)] text-sm leading-relaxed rounded-xl p-4"
          style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)' }}
        >
          {SUMMARIES[result.risk_label]}
        </div>
      </div>
    </div>
  )
}
