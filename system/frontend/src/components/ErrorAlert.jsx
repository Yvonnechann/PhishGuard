import React from 'react'

export default function ErrorAlert({ message, onRetry }) {
  return (
    <div
      className="rounded-2xl px-6 py-5 mb-6 flex items-start gap-4"
      style={{
        background: 'rgba(255,68,68,0.08)',
        border: '1px solid rgba(255,68,68,0.3)',
        backdropFilter: 'blur(20px)',
        boxShadow: '0 0 24px rgba(255,68,68,0.15)',
        opacity: 0,
        animation: 'fadeIn 0.35s ease-out forwards',
      }}
    >
      <span className="text-[#ff4444] text-xl shrink-0 mt-0.5">⚠</span>
      <div className="flex-1">
        <p className="text-[#ff4444] font-semibold text-sm mb-0.5">Error</p>
        <p className="text-white/60 text-sm">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors"
          style={{
            background: 'rgba(255,68,68,0.15)',
            border: '1px solid rgba(255,68,68,0.4)',
            color: '#ff4444',
            cursor: 'pointer',
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,68,68,0.25)'}
          onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,68,68,0.15)'}
        >
          Retry
        </button>
      )}
    </div>
  )
}
