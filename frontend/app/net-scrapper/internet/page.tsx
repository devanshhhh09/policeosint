'use client'
import { useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'

const SCAM_TYPES = [
  { id:'investment_scam', label:'Investment Scam',   badge:'badge-red'    },
  { id:'fake_job',        label:'Fake Job',          badge:'badge-amber'  },
  { id:'upi_fraud',       label:'UPI Fraud',         badge:'badge-amber'  },
  { id:'crypto_scam',     label:'Crypto Scam',       badge:'badge-amber'  },
  { id:'loan_scam',       label:'Loan Scam',         badge:'badge-purple' },
  { id:'romance_scam',    label:'Romance Scam',      badge:'badge-purple' },
  { id:'illegal_content', label:'Illegal Content',   badge:'badge-red'    },
]

const RISK_COLOR  = (r: number) => r >= 70 ? 'text-red-400' : r >= 40 ? 'text-amber-400' : 'text-green-400'
const RISK_BORDER = (r: number) => r >= 70 ? 'border-red-900 bg-red-950/10' : r >= 40 ? 'border-amber-900 bg-amber-950/10' : 'border-gray-800'

const SOURCE_ICON: Record<string, string> = {
  reddit:     'ti-brand-reddit',
  twitter:    'ti-brand-x',
  news_rss:   'ti-news',
  govt_alert: 'ti-shield-check',
  web:        'ti-world',
  telegram:   'ti-brand-telegram',
}

export default function InternetScamHub() {
  const [results, setResults]         = useState<any[]>([])
  const [stats, setStats]             = useState<any>(null)
  const [scanning, setScanning]       = useState(false)
  const [progress, setProgress]       = useState('')
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [filterType, setFilterType]   = useState('all')
  const [filterRisk, setFilterRisk]   = useState(0)
  const [sortBy, setSortBy]           = useState<'risk'|'time'>('risk')
  const [urlToScan, setUrlToScan]     = useState('')
  const [urlResult, setUrlResult]     = useState<any>(null)
  const [scanningUrl, setScanningUrl] = useState(false)

  const toggleType = (id: string) =>
    setSelectedTypes(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id])

  const runScan = async () => {
    setScanning(true); setResults([]); setProgress('Searching DuckDuckGo · Google News · Reddit · Twitter…')
    try {
      const res = await api.post('/scrapper/internet/scan', {
        scam_types:      selectedTypes.length > 0 ? selectedTypes : null,
        max_per_query:   5,
        include_reddit:  true,
        include_news:    true,
        include_twitter: true,
      })
      setResults(res.data.results || [])
      setStats({ total: res.data.total, flagged: res.data.flagged, high_risk: res.data.high_risk, by_type: res.data.by_scam_type })
      setProgress('')
    } catch (e: any) {
      setProgress('Scan failed: ' + (e.response?.data?.detail || e.message))
    } finally { setScanning(false) }
  }

  const scanUrl = async () => {
    if (!urlToScan.trim()) return
    setScanningUrl(true); setUrlResult(null)
    try {
      const res = await api.post('/scrapper/internet/scan-url', { url: urlToScan.trim() })
      setUrlResult(res.data)
    } catch (e: any) {
      setUrlResult({ error: e.response?.data?.detail || 'Failed', status: 'failed' })
    } finally { setScanningUrl(false) }
  }

  const filtered = results
    .filter(r => filterType === 'all' || r.scam_type === filterType)
    .filter(r => r.risk_score >= filterRisk)
    .sort((a, b) => sortBy === 'risk'
      ? b.risk_score - a.risk_score
      : new Date(b.scraped_at).getTime() - new Date(a.scraped_at).getTime()
    )

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-blue-950 flex items-center justify-center">
          <i className="ti ti-world-search text-blue-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Internet Scam Intelligence Hub</h1>
          <p className="text-gray-500 text-sm">
            DuckDuckGo · Google News · Reddit · Twitter — live internet scam scraping
          </p>
        </div>
        {stats && (
          <div className="ml-auto flex gap-2">
            <div className="card px-3 py-2 text-center">
              <div className="text-lg font-bold text-white">{stats.total}</div>
              <div className="text-xs text-gray-500">Found</div>
            </div>
            <div className="card px-3 py-2 text-center">
              <div className="text-lg font-bold text-red-400">{stats.flagged}</div>
              <div className="text-xs text-gray-500">Flagged</div>
            </div>
            <div className="card px-3 py-2 text-center">
              <div className="text-lg font-bold text-amber-400">{stats.high_risk}</div>
              <div className="text-xs text-gray-500">High risk</div>
            </div>
          </div>
        )}
      </div>

      {/* Scan config */}
      <div className="card p-5 mb-5 border-blue-900">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <i className="ti ti-radar text-blue-400" />Configure Internet Scan
          </h3>
          <button onClick={runScan} disabled={scanning} className="btn-primary px-6">
            {scanning ? <><span className="spinner w-4 h-4" />Scanning…</> : <><i className="ti ti-radar" />Run Scan</>}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mb-3">
          {SCAM_TYPES.map(t => (
            <button key={t.id} onClick={() => toggleType(t.id)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                selectedTypes.includes(t.id)
                  ? 'border-blue-500 bg-blue-950 text-blue-300'
                  : 'border-gray-700 bg-gray-800 text-gray-400 hover:text-white'
              }`}>
              {t.label}{selectedTypes.includes(t.id) && <i className="ti ti-check ml-1" />}
            </button>
          ))}
        </div>
        {scanning && <p className="text-sm text-blue-400 flex items-center gap-2"><span className="spinner w-4 h-4" />{progress}</p>}

        {/* URL scanner */}
        <div className="mt-4 pt-4 border-t border-gray-800">
          <p className="text-xs text-gray-500 mb-2">Or scan a specific URL:</p>
          <div className="flex gap-2">
            <input value={urlToScan} onChange={e => setUrlToScan(e.target.value)}
              onKeyDown={e => e.key==='Enter' && scanUrl()}
              placeholder="https://suspicious-site.com"
              className="input-field flex-1 text-sm" />
            <button onClick={scanUrl} disabled={!urlToScan.trim() || scanningUrl}
              className="btn-secondary text-sm px-4">
              {scanningUrl ? <><span className="spinner w-4 h-4" />Scanning…</> : <><i className="ti ti-scan" />Scan URL</>}
            </button>
          </div>
          {urlResult && (
            <div className={`mt-3 p-3 rounded-lg border text-sm ${
              urlResult.error ? 'border-red-900 bg-red-950/20' : RISK_BORDER(urlResult.risk_score)
            }`}>
              {urlResult.error ? (
                <p className="text-red-400">{urlResult.error}</p>
              ) : (
                <div className="flex items-center gap-3 flex-wrap">
                  <span className={`text-xl font-bold ${RISK_COLOR(urlResult.risk_score)}`}>
                    {urlResult.risk_score}/100
                  </span>
                  <span className="text-gray-400">{urlResult.category?.replace(/_/g,' ')}</span>
                  {urlResult.is_flagged && <span className="badge badge-red text-xs">⚠ FLAGGED</span>}
                  {urlResult.indicators?.slice(0,3).map((ind: any, i: number) => (
                    <span key={i} className="text-xs bg-gray-800 border border-gray-700
                                              rounded px-2 py-0.5 font-mono text-gray-300">
                      {ind.type?.replace(/_/g,' ')}: {ind.value?.slice(0,25)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Filters */}
      {results.length > 0 && (
        <div className="flex gap-3 mb-4 flex-wrap">
          <select value={filterType} onChange={e => setFilterType(e.target.value)} className="select-field text-xs w-44">
            <option value="all">All scam types</option>
            {SCAM_TYPES.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
          </select>
          <select value={filterRisk} onChange={e => setFilterRisk(Number(e.target.value))} className="select-field text-xs w-40">
            <option value={0}>Any risk</option>
            <option value={40}>Risk ≥ 40</option>
            <option value={70}>Risk ≥ 70</option>
            <option value={90}>Risk ≥ 90</option>
          </select>
          <select value={sortBy} onChange={e => setSortBy(e.target.value as any)} className="select-field text-xs w-36">
            <option value="risk">Sort by risk</option>
            <option value="time">Sort by time</option>
          </select>
          <span className="text-xs text-gray-500 self-center">{filtered.length} results</span>
        </div>
      )}

      {/* Results */}
      {results.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">
          <i className="ti ti-world-search text-5xl block mb-4 opacity-20" />
          <p className="font-medium text-white text-lg mb-2">Ready to scan</p>
          <p className="text-sm max-w-md mx-auto">
            Click <strong className="text-blue-400">Run Scan</strong> to search the internet for active scams.
            Each result shows the exact URL, source, risk score, and IOCs for police investigation.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((r: any) => (
            <div key={r.id} className={`card p-4 border ${RISK_BORDER(r.risk_score)}`}>
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  r.risk_score >= 70 ? 'bg-red-950' : r.risk_score >= 40 ? 'bg-amber-950' : 'bg-gray-800'
                }`}>
                  <i className={`ti ${SOURCE_ICON[r.source_type]||'ti-world'} text-sm text-gray-300`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`text-xs font-bold ${RISK_COLOR(r.risk_score)}`}>
                      Risk: {r.risk_score}/100
                    </span>
                    {r.is_flagged && <span className="badge badge-red text-xs">⚠ FLAGGED</span>}
                    <span className="badge badge-blue text-xs capitalize">{r.scam_type?.replace(/_/g,' ')}</span>
                    <span className="badge badge-gray text-xs capitalize">{r.source_type?.replace(/_/g,' ')}</span>
                    {r.has_upi    && <span className="badge badge-amber text-xs">UPI</span>}
                    {r.has_phone  && <span className="badge badge-amber text-xs">Phone</span>}
                    {r.has_crypto && <span className="badge badge-red text-xs">Crypto</span>}
                    {r.has_terabox&& <span className="badge badge-red text-xs">Terabox</span>}
                    <span className="text-xs text-gray-600 ml-auto">{r.domain}</span>
                  </div>
                  <h3 className="text-sm font-medium text-white mb-1">{r.title}</h3>
                  {r.snippet && <p className="text-xs text-gray-400 mb-2 leading-relaxed">{r.snippet}</p>}
                  <div className="flex items-center gap-2 flex-wrap">
                    <a href={r.url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-blue-400 hover:text-blue-300 font-mono
                                 flex items-center gap-1 underline break-all">
                      <i className="ti ti-external-link flex-shrink-0" />
                      {r.url.slice(0,80)}{r.url.length>80?'…':''}
                    </a>
                  </div>
                  {r.indicators?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {r.indicators.slice(0,4).map((ind: any, i: number) => (
                        <span key={i} className="text-[10px] bg-gray-800 border border-gray-700
                                                  rounded px-2 py-0.5 font-mono text-gray-300">
                          {ind.type?.replace(/_/g,' ')}: {ind.value?.slice(0,25)}
                        </span>
                      ))}
                      {r.indicators.length > 4 && (
                        <span className="text-[10px] text-gray-600">+{r.indicators.length-4} more</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
