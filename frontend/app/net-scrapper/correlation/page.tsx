'use client'
import { useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'

export default function CorrelationPage() {
  const [query, setQuery]     = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult]   = useState<any>(null)
  const [error, setError]     = useState('')
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const search = async () => {
    if (!query.trim()) return
    setLoading(true); setResult(null); setError('')
    try {
      const res = await api.get(`/scrapper/correlation/${encodeURIComponent(query.trim())}`)
      setResult(res.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Search failed')
    } finally { setLoading(false) }
  }

  // Draw force graph on canvas
  useEffect(() => {
    if (!result || !canvasRef.current) return
    const canvas = canvasRef.current
    const ctx    = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width  = canvas.offsetWidth
    const H = canvas.height = 350
    ctx.clearRect(0, 0, W, H)

    const nodes = result.nodes || []
    const edges = result.edges || []

    if (nodes.length === 0) return

    // Simple circular layout
    const positions: Record<string, {x:number,y:number}> = {}
    nodes.forEach((n: any, i: number) => {
      if (n.id === 'target') {
        positions[n.id] = { x: W/2, y: H/2 }
      } else {
        const angle = (i / nodes.length) * Math.PI * 2
        const r     = Math.min(W, H) * 0.35
        positions[n.id] = { x: W/2 + Math.cos(angle)*r, y: H/2 + Math.sin(angle)*r }
      }
    })

    // Draw edges
    ctx.strokeStyle = '#374151'
    ctx.lineWidth   = 1
    edges.forEach((e: any) => {
      const s = positions[e.from]
      const t = positions[e.to]
      if (!s || !t) return
      ctx.beginPath()
      ctx.moveTo(s.x, s.y)
      ctx.lineTo(t.x, t.y)
      ctx.stroke()
      // Label
      ctx.fillStyle = '#6B7280'
      ctx.font      = '9px monospace'
      ctx.fillText(e.label || '', (s.x+t.x)/2, (s.y+t.y)/2-4)
    })

    // Draw nodes
    const NODE_COLORS: Record<string,string> = {
      indicator: '#EF4444',
      platform:  '#3B82F6',
      source:    '#10B981',
    }
    nodes.forEach((n: any) => {
      const pos  = positions[n.id]
      if (!pos) return
      const color = n.color || NODE_COLORS[n.type] || '#6B7280'
      const r     = n.id === 'target' ? 20 : 14

      // Circle
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, r, 0, Math.PI*2)
      ctx.fillStyle   = color + '33'
      ctx.fill()
      ctx.strokeStyle = color
      ctx.lineWidth   = 2
      ctx.stroke()

      // Label
      ctx.fillStyle  = '#E5E7EB'
      ctx.font       = n.id === 'target' ? 'bold 11px sans-serif' : '10px sans-serif'
      ctx.textAlign  = 'center'
      ctx.fillText(n.label || n.id, pos.x, pos.y + r + 14)
    })
  }, [result])

  const QUICK = [
    '+919876543210',
    'suspect@paytm',
    'terabox.com',
    '0x742d35Cc6634C',
  ]

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-purple-950 flex items-center justify-center">
          <i className="ti ti-topology-star text-purple-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Cross-Platform Correlation</h1>
          <p className="text-gray-500 text-sm">
            Detect same scammer operating across Telegram · Twitter · Instagram · Dark Web
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {QUICK.map(q => (
          <button key={q} onClick={() => { setQuery(q); }}
            className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border
                       border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors">
            {q}
          </button>
        ))}
      </div>

      <div className="card p-4 mb-5">
        <div className="flex gap-3">
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
            placeholder="Phone number, UPI ID, wallet address, username, URL…"
            className="input-field flex-1" />
          <button onClick={search} disabled={!query.trim() || loading} className="btn-primary px-5">
            {loading ? <><span className="spinner w-4 h-4" />Searching…</> : <><i className="ti ti-search" />Correlate</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      </div>

      {result && !loading && (
        <>
          {/* Summary */}
          <div className="grid grid-cols-3 gap-3 mb-5">
            <div className="card p-4 text-center">
              <div className={`text-2xl font-bold ${result.is_cross_platform ? 'text-red-400' : 'text-green-400'}`}>
                {result.occurrences}
              </div>
              <div className="text-xs text-gray-500 mt-1">Occurrences</div>
            </div>
            <div className="card p-4 text-center">
              <div className={`text-2xl font-bold ${result.platforms?.length > 1 ? 'text-red-400' : 'text-amber-400'}`}>
                {result.platforms?.length || 0}
              </div>
              <div className="text-xs text-gray-500 mt-1">Platforms</div>
            </div>
            <div className="card p-4 text-center">
              {result.is_cross_platform
                ? <div className="text-red-400 font-bold text-sm">⚠ CROSS-PLATFORM</div>
                : <div className="text-green-400 font-bold text-sm">Single platform</div>}
              <div className="text-xs text-gray-500 mt-1">Threat level</div>
            </div>
          </div>

          {result.is_cross_platform && (
            <div className="card p-4 mb-5 border-red-900 bg-red-950/20">
              <div className="flex items-center gap-2 text-red-300 font-semibold text-sm">
                <i className="ti ti-alert-triangle text-red-400 text-xl" />
                Same indicator found across {result.platforms?.join(', ')} — likely same threat actor
              </div>
            </div>
          )}

          {/* Graph */}
          <div className="card overflow-hidden mb-5">
            <div className="px-4 py-3 border-b border-gray-800">
              <span className="text-sm font-semibold text-white">Correlation graph</span>
            </div>
            <div className="bg-gray-950 relative">
              <canvas ref={canvasRef} className="w-full" style={{height:350}} />
            </div>
          </div>

          {/* Indicator list */}
          {result.indicators?.length > 0 && (
            <div className="card overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800">
                <span className="text-sm font-semibold text-white">Found occurrences</span>
              </div>
              {result.indicators.map((ind: any, i: number) => (
                <div key={ind.id} className={`flex items-center gap-3 px-4 py-3 text-sm
                                              ${i < result.indicators.length-1 ? 'border-b border-gray-800' : ''}`}>
                  <span className="badge badge-blue text-xs capitalize">
                    {ind.type?.replace(/_/g,' ')}
                  </span>
                  <span className="text-gray-400 capitalize">{ind.platform}</span>
                  <span className={`text-xs font-bold ml-auto ${
                    ind.risk_score >= 70 ? 'text-red-400' :
                    ind.risk_score >= 40 ? 'text-amber-400' : 'text-green-400'
                  }`}>{ind.risk_score?.toFixed(0)}/100</span>
                  <span className="text-xs text-gray-600">
                    {new Date(ind.first_seen).toLocaleDateString('en-IN')}
                  </span>
                </div>
              ))}
            </div>
          )}

          <button onClick={() => { setResult(null); setQuery('') }} className="btn-secondary mt-4">
            <i className="ti ti-refresh" />New search
          </button>
        </>
      )}
    </div>
  )
}
