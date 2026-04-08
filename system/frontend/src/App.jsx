import React, { useState, useRef } from 'react'
import Grainient from './components/Grainient'
import TextType from './components/TextType'
import ShinyText from './components/ShinyText'
import AddressInput from './components/AddressInput'
import RiskBadge from './components/RiskBadge'
import ExplanationCard from './components/ExplanationCard'
import IntelBadges from './components/IntelBadges'
import FeatureTable from './components/FeatureTable'
import { LoadingSkeleton } from './components/LoadingSpinner'
import ErrorAlert from './components/ErrorAlert'
import { analyzeAddress } from './api/phishguard'

function CopyButton({ text }) {
  const [copied, setCopied] = React.useState(false)
  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {}
  }
  return (
    <button
      onClick={handleCopy}
      title="Copy address"
      className="shrink-0 text-xs px-2 py-0.5 rounded-md transition-all"
      style={{
        background: copied ? 'rgba(0,255,136,0.15)' : 'rgba(255,255,255,0.07)',
        border: `1px solid ${copied ? 'rgba(0,255,136,0.4)' : 'rgba(255,255,255,0.15)'}`,
        color: copied ? '#00ff88' : 'rgba(255,255,255,0.4)',
        cursor: 'pointer',
      }}
    >
      {copied ? '✓ Copied' : '⎘ Copy'}
    </button>
  )
}

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [scannedAddress, setScannedAddress] = useState(null)
  const [lastAddress, setLastAddress] = useState(null)
  const topRef = useRef(null)
  const inputResetRef = useRef(null)

  async function handleAnalyze(address) {
    setLoading(true)
    setError(null)
    setResult(null)
    setScannedAddress(address)
    setLastAddress(address)
    try {
      const data = await analyzeAddress(address)
      setResult(data)
    } catch (err) {
      if (err.response?.status === 400) {
        setError('Invalid address format. Make sure it starts with 0x and is 42 characters long.')
      } else if (err.response?.status === 422) {
        setError('Address could not be processed. It may be unsupported or malformed.')
      } else if (err.code === 'ERR_NETWORK' || !err.response) {
        setError('Cannot reach the server. Make sure the backend is running on port 8000.')
      } else if (err.response?.status >= 500) {
        setError('Server error during analysis. The backend may be overloaded — please try again in a moment.')
      } else {
        setError(`Analysis failed (${err.response?.status ?? 'unknown error'}). Please try again.`)
      }
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setResult(null)
    setError(null)
    setScannedAddress(null)
    if (inputResetRef.current) inputResetRef.current()
    topRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <>
      {/* Grainient — fixed fullscreen, behind content */}
      <div
        className="pointer-events-none"
        style={{ position: 'fixed', inset: 0, zIndex: 0 }}
      >
        <Grainient
          color1="#00aa55"
          color2="#0088bb"
          color3="#080e12"
          timeSpeed={0.35}
          warpStrength={1}
          warpFrequency={4}
          warpSpeed={2.5}
          warpAmplitude={60}
          rotationAmount={300}
          contrast={1.1}
          saturation={0.8}
          grainAmount={0.08}
          zoom={0.95}
        />
      </div>

      {/* Dark veil — ensures text legibility over any shader output */}
      <div
        className="pointer-events-none"
        style={{ position: 'fixed', inset: 0, zIndex: 0, background: 'rgba(4, 6, 8, 0.4)' }}
      />

      <div className="min-h-screen text-white font-sans overflow-x-hidden" style={{ position: 'relative', zIndex: 1 }}>
      <div className="relative max-w-4xl mx-auto px-4 py-16 pb-24">

        {/* Scroll anchor */}
        <div ref={topRef} />

        {/* ── Section 1: Hero ───────────────────────────────────────────── */}
        <div className="text-center mb-14">
          <h1
            className="text-5xl md:text-6xl font-extrabold mb-4 tracking-tight"
            style={{ opacity: 0, animation: 'fadeUp 0.6s ease-out 0s forwards' }}
          >
            <ShinyText
              text="PHISHGUARD"
              color="#00dd77"
              shineColor="#00ffcc"
              spread={90}
              speed={3}
              direction="left"
            />
          </h1>

          <p
            className="text-[rgba(255,255,255,0.55)] text-lg mb-10 max-w-xl mx-auto leading-relaxed"
            style={{ opacity: 0, animation: 'fadeUp 0.6s ease-out 0.2s forwards', minHeight: '2em' }}
          >
            <TextType
              text={[
                'AI-powered phishing detection for Ethereum.',
                'Paste any wallet or contract address.',
                'Get an instant risk assessment.',
              ]}
              typingSpeed={45}
              deletingSpeed={25}
              pauseDuration={2000}
              initialDelay={800}
              showCursor
              cursorCharacter="|"
              cursorBlinkDuration={0.5}
              loop
            />
          </p>

          <div style={{ opacity: 0, animation: 'fadeUp 0.6s ease-out 0.4s forwards' }}>
            <AddressInput onAnalyze={handleAnalyze} loading={loading} resetRef={inputResetRef} />
            <p className="text-[rgba(255,255,255,0.25)] text-sm mt-3">
              Supports wallet addresses and smart contracts
            </p>
          </div>
        </div>

        {/* ── How it works + Try an example (hidden once results load) ─── */}
        {!result && !loading && (
          <div style={{ opacity: 0, animation: 'fadeUp 0.6s ease-out 0.6s forwards' }}>

            {/* How it works */}
            <div className="mb-10">
              <h2 className="text-center text-[rgba(255,255,255,0.4)] text-xs font-semibold uppercase tracking-widest mb-6">
                How it works
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  {
                    step: '01',
                    title: 'Submit Address',
                    desc: 'Paste any Ethereum wallet or contract address.',
                    color: '#00ff88',
                  },
                  {
                    step: '02',
                    title: 'AI Analysis',
                    desc: 'XGBoost model scores 20+ on-chain risk signals.',
                    color: '#00ccff',
                  },
                  {
                    step: '03',
                    title: 'Risk Report',
                    desc: 'Get a risk score, threat intel checks, and explanation.',
                    color: '#00ff88',
                  },
                ].map(({ step, title, desc, color }) => (
                  <div
                    key={step}
                    style={{
                      background: 'rgba(255,255,255,0.09)',
                      border: '1px solid rgba(255,255,255,0.28)',
                      borderRadius: '14px',
                      padding: '20px',
                      backdropFilter: 'blur(20px)',
                      boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
                    }}
                  >
                    <div style={{ color, fontSize: '11px', fontWeight: 700, letterSpacing: '2px', marginBottom: '8px' }}>
                      STEP {step}
                    </div>
                    <div style={{ color: 'white', fontWeight: 600, fontSize: '15px', marginBottom: '6px' }}>
                      {title}
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: '13px', lineHeight: '1.6' }}>
                      {desc}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Try an example */}
            <div className="text-center">
              <p className="text-[rgba(255,255,255,0.4)] text-xs font-semibold uppercase tracking-widest mb-4">
                Try an example
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                <button
                  onClick={() => handleAnalyze('0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045')}
                  style={{
                    background: 'rgba(0,255,136,0.08)',
                    border: '1px solid rgba(0,255,136,0.25)',
                    borderRadius: '10px',
                    padding: '10px 18px',
                    color: '#00ff88',
                    fontSize: '13px',
                    fontFamily: 'JetBrains Mono, monospace',
                    cursor: 'pointer',
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,255,136,0.15)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(0,255,136,0.08)'}
                >
                  ✓ Safe — Vitalik's Wallet
                </button>
                <button
                  onClick={() => handleAnalyze('0x00008a7299aaCab28139C3b7D75Ae886572c0000')}
                  style={{
                    background: 'rgba(255,68,68,0.08)',
                    border: '1px solid rgba(255,68,68,0.25)',
                    borderRadius: '10px',
                    padding: '10px 18px',
                    color: '#ff6b6b',
                    fontSize: '13px',
                    fontFamily: 'JetBrains Mono, monospace',
                    cursor: 'pointer',
                    transition: 'background 0.2s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,68,68,0.15)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,68,68,0.08)'}
                >
                  ⚠ Phishing — Known Scam
                </button>
              </div>
            </div>

          </div>
        )}

        {/* ── Error ──────────────────────────────────────────────────────── */}
        {error && <ErrorAlert message={error} onRetry={() => handleAnalyze(lastAddress)} />}

        {/* ── Loading skeleton ───────────────────────────────────────────── */}
        {loading && <LoadingSkeleton address={scannedAddress} />}

        {/* ── Results ────────────────────────────────────────────────────── */}
        {result && !loading && (
          <div className="space-y-8">

            {/* Scanned address + copy + scan another */}
            <div
              className="flex items-center justify-between gap-3 flex-wrap px-4 py-3 rounded-xl"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}
            >
              <div className="flex items-center gap-2 min-w-0 flex-1 flex-wrap">
                <span className="text-white/35 text-xs shrink-0">Scanned</span>
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full shrink-0"
                  style={{
                    background: result.analysis_type === 'contract' ? 'rgba(0,204,255,0.12)' : 'rgba(0,255,136,0.12)',
                    border: `1px solid ${result.analysis_type === 'contract' ? 'rgba(0,204,255,0.35)' : 'rgba(0,255,136,0.35)'}`,
                    color: result.analysis_type === 'contract' ? '#00ccff' : '#00ff88',
                  }}
                >
                  {result.analysis_type === 'contract' ? '📄 Contract' : '👛 Wallet'}
                </span>
                <span className="text-white/80 text-xs font-mono break-all">
                  {scannedAddress}
                </span>
                <CopyButton text={scannedAddress} />
              </div>
              <button
                onClick={handleReset}
                className="shrink-0 text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
                style={{
                  background: 'rgba(255,255,255,0.07)',
                  border: '1px solid rgba(255,255,255,0.2)',
                  color: 'rgba(255,255,255,0.7)',
                  cursor: 'pointer',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.13)'}
                onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.07)'}
              >
                ← Scan another
              </button>
            </div>

            {/* Section 2: Risk result */}
            <RiskBadge result={result} />

            {/* Section 3: Top factors behind this score */}
            <div>
              <h2 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
                <span style={{ color: '#00ff88' }}>◈</span> Top factors behind this score
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {result.shap_explanation.map((item, i) => (
                  <ExplanationCard key={item.feature} item={item} index={i} features={result.raw_features} />
                ))}
              </div>
            </div>

            {/* Section 4: How the score is computed */}
            <div
              style={{
                background: 'rgba(255,255,255,0.09)',
                border: '1px solid rgba(255,255,255,0.28)',
                borderRadius: '16px',
                backdropFilter: 'blur(20px)',
                boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
                padding: '24px',
                opacity: 0,
                animation: 'fadeUp 0.5s ease-out 0.1s forwards',
              }}
            >
              <h2 className="text-white font-semibold text-base mb-4 flex items-center gap-2">
                <span style={{ color: '#00ccff' }}>◈</span> How this score is computed
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                {[
                  { label: 'Machine Learning', color: '#00ff88', desc: 'XGBoost model scores 20+ on-chain signals — tx patterns, approvals, network graph.' },
                  { label: 'GoPlus Security',  color: '#00ccff', desc: 'Real-time threat feed. A flagged address adds +15 to the score.' },
                  { label: 'Scam Database',    color: '#00ccff', desc: 'Checked against CryptoScamDB. A match adds +10 to the score.' },
                ].map(({ label, color, desc }) => (
                  <div key={label} style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '10px', padding: '14px' }}>
                    <div style={{ color, fontSize: '12px', fontWeight: 700, marginBottom: '6px' }}>{label}</div>
                    <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '12px', lineHeight: '1.6' }}>{desc}</div>
                  </div>
                ))}
              </div>
              <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: '12px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '14px' }}>
                <span style={{ color: '#ff4444', fontWeight: 600 }}>HIGH</span> ≥ 75% &nbsp;·&nbsp;
                <span style={{ color: '#ff8800', fontWeight: 600 }}>MEDIUM</span> 45–74% &nbsp;·&nbsp;
                <span style={{ color: '#00ff88', fontWeight: 600 }}>LOW</span> &lt; 45% &nbsp;·&nbsp;
                Final = ML + intel bonuses, capped at 100%.
              </div>
            </div>

            {/* Section 5: Intel */}
            <div>
              <h2 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
                <span style={{ color: '#00ccff' }}>◈</span> Security Database Checks
              </h2>
              <IntelBadges goplus={result.goplus_flagged} scamdb={result.scamdb_match} />
            </div>

            {/* Section 6: Raw signal data */}
            <FeatureTable features={result.raw_features} analysisType={result.analysis_type} />

            {/* Disclaimer */}
            <div
              style={{
                background: 'rgba(255,180,0,0.05)',
                border: '1px solid rgba(255,180,0,0.2)',
                borderRadius: '12px',
                padding: '14px 18px',
                opacity: 0,
                animation: 'fadeUp 0.5s ease-out 0.4s forwards',
              }}
            >
              <p style={{ color: 'rgba(255,200,80,0.6)', fontSize: '11px', lineHeight: '1.6', margin: 0 }}>
                <span style={{ fontWeight: 700 }}>Disclaimer: </span>
                For informational purposes only. Scores are probabilistic — not a definitive determination of fraud. Always do your own research.
              </p>
            </div>

          </div>
        )}
      </div>
      </div>
    </>
  )
}
