import React, { useState } from 'react'
import AddressInput from './components/AddressInput'
import RiskBadge from './components/RiskBadge'
import ExplanationCard from './components/ExplanationCard'
import IntelBadges from './components/IntelBadges'
import FeatureTable from './components/FeatureTable'
import { LoadingSkeleton } from './components/LoadingSpinner'
import ErrorAlert from './components/ErrorAlert'
import { analyzeAddress } from './api/phishguard'

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleAnalyze(address) {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await analyzeAddress(address)
      setResult(data)
    } catch (err) {
      if (err.response?.status === 400) {
        setError('Invalid Ethereum address format.')
      } else {
        setError('Analysis failed — server error. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white font-sans overflow-x-hidden">
      {/* Ambient glow */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-[radial-gradient(ellipse,rgba(0,255,136,0.06)_0%,transparent_70%)]" />
      </div>

      <div className="relative max-w-4xl mx-auto px-4 py-16 pb-24">

        {/* ── Section 1: Hero ───────────────────────────────────────────── */}
        <div className="text-center mb-14">
          <h1
            className="text-5xl md:text-6xl font-extrabold mb-4 tracking-tight"
            style={{ opacity: 0, animation: 'fadeUp 0.6s ease-out 0s forwards' }}
          >
            <span style={{
              background: 'linear-gradient(90deg, #00ff88, #00ccff)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              PhishGuard
            </span>
          </h1>

          <p
            className="text-[rgba(255,255,255,0.55)] text-lg mb-10 max-w-xl mx-auto leading-relaxed"
            style={{ opacity: 0, animation: 'fadeUp 0.6s ease-out 0.2s forwards' }}
          >
            Detect Ethereum phishing addresses using AI — paste any wallet or contract address below
          </p>

          <div style={{ opacity: 0, animation: 'fadeUp 0.6s ease-out 0.4s forwards' }}>
            <AddressInput onAnalyze={handleAnalyze} loading={loading} />
            <p className="text-[rgba(255,255,255,0.25)] text-sm mt-3">
              Supports wallet addresses and smart contracts
            </p>
          </div>
        </div>

        {/* ── Error ──────────────────────────────────────────────────────── */}
        {error && <ErrorAlert message={error} />}

        {/* ── Loading skeleton ───────────────────────────────────────────── */}
        {loading && <LoadingSkeleton />}

        {/* ── Results ────────────────────────────────────────────────────── */}
        {result && !loading && (
          <div className="space-y-8">

            {/* Section 2: Risk result */}
            <RiskBadge result={result} />

            {/* Section 3: Why this score */}
            <div>
              <h2 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
                <span style={{ color: '#00ff88' }}>◈</span> Why did it get this score?
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {result.shap_explanation.map((item, i) => (
                  <ExplanationCard key={item.feature} item={item} index={i} />
                ))}
              </div>
            </div>

            {/* Section 4: Intel */}
            <div>
              <h2 className="text-white font-semibold text-lg mb-4 flex items-center gap-2">
                <span style={{ color: '#00ccff' }}>◈</span> External Intelligence Checks
              </h2>
              <IntelBadges goplus={result.goplus_flagged} scamdb={result.scamdb_match} />
            </div>

            {/* Section 5: Advanced details */}
            <FeatureTable features={result.raw_features} analysisType={result.analysis_type} />
          </div>
        )}
      </div>
    </div>
  )
}
