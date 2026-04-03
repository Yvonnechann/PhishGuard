import React from 'react'

function Badge({ flagged, flaggedLabel, clearLabel, flaggedSub, clearSub, delay }) {
  const color  = flagged ? '#ff4444' : '#00ff88'
  const bgCol  = flagged ? 'rgba(255,68,68,0.14)'  : 'rgba(0,255,136,0.10)'
  const border = flagged ? 'rgba(255,68,68,0.6)'  : 'rgba(0,255,136,0.5)'
  const glow   = flagged ? 'rgba(255,68,68,0.25)' : 'rgba(0,255,136,0.2)'

  return (
    <div
      className="flex-1 min-w-[240px] rounded-2xl p-5 transition-all duration-200"
      style={{
        background: bgCol,
        border: `1px solid ${border}`,
        backdropFilter: 'blur(20px)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
        opacity: 0,
        animation: `popIn 0.4s ease-out ${delay}s forwards`,
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = `0 0 24px ${glow}`
        e.currentTarget.style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      <div className="flex items-center gap-3 mb-2">
        <span
          className="text-xl w-8 h-8 rounded-full flex items-center justify-center shrink-0 font-bold"
          style={{ background: flagged ? 'rgba(255,68,68,0.2)' : 'rgba(0,255,136,0.15)', color }}
        >
          {flagged ? '⚠' : '✓'}
        </span>
        <span className="font-semibold text-sm" style={{ color }}>
          {flagged ? flaggedLabel : clearLabel}
        </span>
      </div>
      <p className="text-[rgba(255,255,255,0.45)] text-xs leading-relaxed pl-11">
        {flagged ? flaggedSub : clearSub}
      </p>
    </div>
  )
}

export default function IntelBadges({ goplus, scamdb }) {
  return (
    <div className="flex flex-wrap gap-4">
      <Badge
        flagged={goplus}
        flaggedLabel="Flagged by GoPlus Security"
        clearLabel="GoPlus Security: Clear"
        flaggedSub="GoPlus, a blockchain threat intelligence service, has identified this address as malicious — linked to phishing, scams, or fund-trapping."
        clearSub="GoPlus Security has not flagged this address. No known malicious activity on record."
        delay={0.05}
      />
      <Badge
        flagged={scamdb}
        flaggedLabel="Found in Scam Database"
        clearLabel="Not in Scam Database"
        flaggedSub="This address appears in a community-maintained fraud registry. It has been publicly reported as a scam address."
        clearSub="This address is not present in any known scam database. No community reports found."
        delay={0.15}
      />
    </div>
  )
}
