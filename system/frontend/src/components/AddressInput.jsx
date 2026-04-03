import React, { useState, useRef } from 'react'
import LoadingSpinner from './LoadingSpinner'

const ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/

export default function AddressInput({ onAnalyze, loading }) {
  const [value, setValue] = useState('')
  const [inlineError, setInlineError] = useState('')
  const [shaking, setShaking] = useState(false)
  const [focused, setFocused] = useState(false)
  const [pressing, setPressing] = useState(false)
  const inputRef = useRef(null)

  function triggerShake() {
    setShaking(true)
    setTimeout(() => setShaking(false), 400)
  }

  function handleSubmit(e) {
    e.preventDefault()
    const trimmed = value.trim()
    if (!ADDRESS_RE.test(trimmed)) {
      setInlineError('Please enter a valid Ethereum address (0x + 40 hex characters)')
      triggerShake()
      return
    }
    setInlineError('')
    onAnalyze(trimmed)
  }

  function handleChange(e) {
    setValue(e.target.value)
    if (inlineError) setInlineError('')
  }

  const borderColor = inlineError
    ? '#ff4444'
    : focused
    ? '#00ff88'
    : 'rgba(255,255,255,0.1)'

  const glowColor = inlineError
    ? 'rgba(255,68,68,0.25)'
    : focused
    ? 'rgba(0,255,136,0.2)'
    : 'transparent'

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div
        className="flex gap-3 items-stretch"
        style={{
          animation: shaking ? 'shake 0.4s ease-in-out' : 'none',
        }}
      >
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={handleChange}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder="0x..."
            disabled={loading}
            className="w-full h-14 px-5 rounded-2xl bg-white/5 text-white placeholder-white/25 font-mono text-sm outline-none transition-all duration-300 disabled:opacity-50"
            style={{
              border: `1px solid ${borderColor}`,
              boxShadow: `0 0 0 4px ${glowColor}`,
              transform: focused ? 'scale(1.01)' : 'scale(1)',
              transition: 'border-color 300ms, box-shadow 300ms, transform 300ms',
              backdropFilter: 'blur(20px)',
            }}
            autoComplete="off"
            spellCheck={false}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          onMouseDown={() => setPressing(true)}
          onMouseUp={() => setPressing(false)}
          onMouseLeave={() => setPressing(false)}
          className="h-14 px-8 rounded-2xl font-semibold text-sm text-black whitespace-nowrap disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
          style={{
            background: loading
              ? 'rgba(0,255,136,0.5)'
              : 'linear-gradient(135deg, #00ff88, #00ccff)',
            transform: pressing ? 'scale(0.97)' : 'scale(1)',
            boxShadow: loading
              ? 'none'
              : '0 0 20px rgba(0,255,136,0.35)',
            transition: 'transform 150ms, box-shadow 200ms, background 200ms',
          }}
          onMouseEnter={e => {
            if (!loading) {
              e.currentTarget.style.boxShadow = '0 0 32px rgba(0,255,136,0.55)'
              e.currentTarget.style.transform = 'scale(1.03)'
            }
          }}
          onMouseLeave={e => {
            e.currentTarget.style.boxShadow = '0 0 20px rgba(0,255,136,0.35)'
            e.currentTarget.style.transform = 'scale(1)'
          }}
        >
          {loading ? (
            <>
              <LoadingSpinner size={16} color="#000" />
              <span>Analyzing…</span>
            </>
          ) : (
            'Analyze'
          )}
        </button>
      </div>

      {/* Inline error */}
      {inlineError && (
        <p
          className="text-[#ff4444] text-sm mt-2 text-left pl-1"
          style={{ animation: 'slideDown 0.25s ease-out forwards' }}
        >
          {inlineError}
        </p>
      )}
    </form>
  )
}
