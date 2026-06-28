'use client'
import { useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'

const CATEGORY_COLORS: Record<string, string> = {
  fake_job:        'badge-amber',
  investment_scam: 'badge-red',
  crypto_scam:     'badge-red',
  illegal_content: 'badge-red',
  leaked_data:     'badge-purple',
  normal:          'badge-green',
  unclassified:    'badge-gray',
}

const RISK_COLOR = (r: number) =>
  r >= 70 ? 'text-red-400' : r >= 40 ? 'text-amber-400' : 'text-green-400'

export default function InstagramPage() {
  const [sources, setSources]       = useState<any[]>([])
  const [content, setContent]       = useState<any[]>([])
  const [indicators, setIndicators] = useState<any[]>([])
  const [stats, setStats]           = useState<any>(null)
  const [identifier, setIdentifier] = useState('')
  const [loading, setLoading]       = useState(false)
  const [scraping, setScraping]     = useState<string | null>(null)
  const [tab, setTab]               = useState<'feed'|'indicators'|'sources'>('feed')
  const pollRef = useRef<any>(null)

  const load = async () => {
    try {
      const [s, c, i, st] = await Promise.all([
        api.get('/scrapper/sources?platform=instagram'),
        api.get('/scrapper/content?platform=instagram&per_page=30'),
        api.get('/scrapper/indicators?platform=instagram&per_page=20'),
        api.get('/scrapper/stats'),
      ])
      setSources(s.data)
      setContent(c.data.content || [])
      setIndicators(i.data.indicators || [])
      setStats(st.data)
    } catch {}
  }

  useEffect(() => {
    load()
    pollRef.current = setInterval(load, 15000)
    return () => clearInterval(pollRef.current)
  }, [])

  const addSource = async () => {
    if (!identifier.trim()) return
    setLoading(true)
    try {
      await api.post('/scrapper/sources', {
        platform:   'instagram',
        identifier: identifier.trim(),
      })
      setIdentifier('')
      await load()
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Failed to add source')
    } finally { setLoading(false) }
  }

  const scrape = async (sourceId: string) => {
    setScraping(sourceId)
    try {
      const res = await api.post(`/scrapper/sources/${sourceId}/scrape?limit=50`)
      await load()
      alert(`Scraped ${res.data.messages_scraped} posts. ${res.data.flagged} flagged.`)
    } catch {} finally { setScraping(null) }
  }

  const analyzeText = async (text: string) => {
    const res = await api.post('/scrapper/analyze', { text, platform: 'instagram' })
    const d   = res.data
    alert(`Category: ${d.category}\nRisk: ${d.risk_score}/100\nIOCs found: ${d.indicator_count}`)
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-pink-950 flex items-center justify-center">
          <i className="ti ti-brand-instagram text-pink-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Instagram Intelligence Dashboard</h1>
          <p className="text-gray-500 text-sm">
            Profile scraping · Bio scam keywords · Story monitoring · Comment analysis
          </p>
        </div>
        <div className="ml-auto flex gap-2">
          {stats && (
            <>
              <div className="card px-3 py-2 text-center">
                <div className="text-lg font-bold text-red-400">{stats.flagged_content || 0}</div>
                <div className="text-xs text-gray-500">Flagged</div>
              </div>
              <div className="card px-3 py-2 text-center">
                <div className="text-lg font-bold text-amber-400">{stats.high_risk_indicators || 0}</div>
                <div className="text-xs text-gray-500">High risk IOCs</div>
              </div>
              <div className="card px-3 py-2 text-center">
                <div className="text-lg font-bold text-pink-400">{stats.total_sources || 0}</div>
                <div className="text-xs text-gray-500">Profiles</div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Add source */}
      <div className="card p-4 mb-5 border-pink-900">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <i className="ti ti-brand-instagram absolute left-3 top-1/2 -translate-y-1/2 text-pink-400" />
            <input value={identifier} onChange={e => setIdentifier(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addSource()}
              placeholder="@username  or  https://instagram.com/username  or  profile URL"
              className="input-field pl-10" />
          </div>
          <button onClick={addSource} disabled={!identifier.trim() || loading}
            className="btn-primary px-5">
            {loading
              ? <><span className="spinner w-4 h-4" />Adding…</>
              : <><i className="ti ti-plus" />Monitor</>}
          </button>
        </div>
        <div className="grid grid-cols-3 gap-2 mt-3">
          {[
            'Scrape bio for scam keywords',
            'Extract phone/UPI from captions',
            'Detect fake job posts in stories',
          ].map((tip, i) => (
            <div key={i} className="text-xs text-gray-600 flex items-center gap-1">
              <i className="ti ti-check text-pink-400 flex-shrink-0" />{tip}
            </div>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800 mb-5">
        {(['feed','indicators','sources'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px capitalize transition-colors ${
              tab===t ? 'border-pink-500 text-pink-400' : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}>{t}</button>
        ))}
      </div>

      {/* Feed */}
      {tab === 'feed' && (
        <div className="space-y-3">
          {content.length === 0 ? (
            <div className="card p-10 text-center text-gray-500">
              <i className="ti ti-brand-instagram text-4xl block mb-3 opacity-30" />
              <p className="font-medium text-white mb-1">No posts yet</p>
              <p className="text-sm">Add a profile above and click Scrape to fetch content</p>
            </div>
          ) : content.map((c: any) => (
            <div key={c.id} className={`card p-4 border ${
              c.risk_score >= 70 ? 'border-red-900 bg-red-950/10' :
              c.risk_score >= 40 ? 'border-amber-900 bg-amber-950/10' : 'border-gray-800'
            }`}>
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  c.risk_score >= 70 ? 'bg-red-950' :
                  c.risk_score >= 40 ? 'bg-amber-950' : 'bg-gray-800'
                }`}>
                  <i className="ti ti-brand-instagram text-sm text-pink-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`badge ${CATEGORY_COLORS[c.category] || 'badge-gray'} text-xs`}>
                      {c.category?.replace(/_/g,' ')}
                    </span>
                    <span className={`text-xs font-bold ${RISK_COLOR(c.risk_score)}`}>
                      Risk: {c.risk_score}/100
                    </span>
                    {c.is_flagged && <span className="badge badge-red text-xs">⚠ FLAGGED</span>}
                    {c.author && (
                      <span className="text-xs text-pink-400 font-mono">@{c.author}</span>
                    )}
                    <span className="text-xs text-gray-600 ml-auto">
                      {new Date(c.scraped_at).toLocaleTimeString('en-IN')}
                    </span>
                  </div>
                  <p className="text-sm text-gray-300 leading-relaxed break-words">
                    {c.content_text}
                  </p>
                  <button onClick={() => analyzeText(c.content_text || '')}
                    className="mt-2 text-xs text-pink-400 hover:text-pink-300">
                    <i className="ti ti-analyze mr-1" />Re-analyze
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Indicators */}
      {tab === 'indicators' && (
        <div className="card overflow-hidden">
          <div className="grid grid-cols-[120px_1fr_80px_60px_100px] gap-3 px-4 py-2.5
                          border-b border-gray-800 text-xs font-semibold text-gray-500
                          uppercase tracking-wider">
            <span>Type</span><span>Value</span><span>Platform</span><span>Risk</span><span>First seen</span>
          </div>
          {indicators.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">No indicators extracted yet</div>
          ) : indicators.map((ind: any, i: number) => (
            <div key={ind.id}
              className={`grid grid-cols-[120px_1fr_80px_60px_100px] gap-3 px-4 py-3
                          items-center text-sm
                          ${i < indicators.length-1 ? 'border-b border-gray-800' : ''}`}>
              <span className="badge badge-blue text-xs capitalize">
                {ind.indicator_type?.replace(/_/g,' ')}
              </span>
              <span className="font-mono text-xs text-white truncate">{ind.value}</span>
              <span className="text-xs text-gray-400 capitalize">{ind.platform}</span>
              <span className={`text-xs font-bold ${RISK_COLOR(ind.risk_score)}`}>
                {ind.risk_score?.toFixed(0)}
              </span>
              <span className="text-xs text-gray-600">
                {new Date(ind.first_seen).toLocaleDateString('en-IN')}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Sources */}
      {tab === 'sources' && (
        <div className="card overflow-hidden">
          {sources.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">
              No profiles monitored yet. Add one above.
            </div>
          ) : sources.map((s: any, i: number) => (
            <div key={s.id}
              className={`flex items-center gap-3 px-4 py-3
                          ${i < sources.length-1 ? 'border-b border-gray-800' : ''}`}>
              <div className="w-8 h-8 rounded-full bg-pink-950 flex items-center justify-center flex-shrink-0">
                <i className="ti ti-brand-instagram text-pink-400 text-sm" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-white">{s.display_name}</div>
                <div className="text-xs text-gray-500 font-mono">{s.identifier}</div>
              </div>
              <span className="text-xs text-gray-500">{s.message_count} posts</span>
              <span className={`badge text-xs ${
                s.status === 'active' ? 'badge-green' : 'badge-gray'
              }`}>{s.status}</span>
              <button onClick={() => scrape(s.id)} disabled={scraping === s.id}
                className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1">
                {scraping === s.id
                  ? <><span className="spinner w-3 h-3" />Scraping…</>
                  : <><i className="ti ti-download" />Scrape</>}
              </button>
              <button onClick={() => api.delete(`/scrapper/sources/${s.id}`).then(load)}
                className="text-red-400 hover:text-red-300 text-xs px-2">
                <i className="ti ti-trash" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
