import React from 'react'

/** Inline spinner — used inside the Analyze button */
export default function LoadingSpinner({ size = 18, color = '#000' }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: size,
        height: size,
        border: `2px solid ${color}33`,
        borderTopColor: color,
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
        flexShrink: 0,
      }}
    />
  )
}

/** Full-page skeleton shown while analysis is running */
function SkeletonCard({ height = 120, delay = 0 }) {
  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        height,
        background: 'rgba(255,255,255,0.04)',
        border: '1px solid rgba(255,255,255,0.07)',
        backdropFilter: 'blur(20px)',
        opacity: 0,
        animation: `fadeIn 0.4s ease-out ${delay}s forwards`,
      }}
    >
      <div
        style={{
          height: '100%',
          background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.06) 50%, transparent 100%)',
          backgroundSize: '600px 100%',
          animation: 'shimmer 1.5s linear infinite',
        }}
      />
    </div>
  )
}

export function LoadingSkeleton({ address }) {
  return (
    <div className="space-y-8">
      {/* Loading message */}
      <div
        className="text-center py-4"
        style={{ opacity: 0, animation: 'fadeIn 0.4s ease-out 0.1s forwards' }}
      >
        <p className="text-white/50 text-sm">
          Analysing <span className="font-mono text-white/70">{address ? `${address.slice(0,8)}...${address.slice(-6)}` : 'address'}</span>
        </p>
        <p className="text-white/30 text-xs mt-1">Fetching on-chain data and running ML model — this may take 10–20s</p>
      </div>

      {/* Risk badge skeleton */}
      <SkeletonCard height={128} delay={0} />

      {/* SHAP cards skeleton */}
      <div>
        <div
          className="h-5 w-48 rounded-lg mb-4"
          style={{
            background: 'rgba(255,255,255,0.07)',
            animation: 'shimmer 1.5s linear infinite',
            backgroundSize: '400px 100%',
          }}
        />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SkeletonCard height={140} delay={0.05} />
          <SkeletonCard height={140} delay={0.1} />
          <SkeletonCard height={140} delay={0.15} />
        </div>
      </div>

      {/* How the score is computed skeleton */}
      <SkeletonCard height={140} delay={0.1} />

      {/* Intel skeleton */}
      <div>
        <div
          className="h-5 w-56 rounded-lg mb-4"
          style={{
            background: 'rgba(255,255,255,0.07)',
            animation: 'shimmer 1.5s linear infinite',
            backgroundSize: '400px 100%',
          }}
        />
        <div className="flex gap-4">
          <SkeletonCard height={88} delay={0.2} />
          <SkeletonCard height={88} delay={0.25} />
        </div>
      </div>
    </div>
  )
}
