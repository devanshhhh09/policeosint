'use client'
import { useState, useRef } from 'react'
import { api } from '@/lib/api'

const SEVERITY_CLS: Record<string, string> = {
  CRITICAL: 'text-red-400 font-bold',
  HIGH:     'text-orange-400 font-semibold',
  MEDIUM:   'text-amber-400',
  LOW:      'text-green-400',
}
const SEVERITY_BADGE: Record<string, string> = {
  CRITICAL: 'badge-red',
  HIGH:     'badge-red',
  MEDIUM:   'badge-amber',
  LOW:      'badge-green',
}

type SortKey = 'risk_score' | 'country' | 'isp' | 'ip'
type FilterSeverity = 'all' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
type FilterVersion  = 'all' | 'IPv4' | 'IPv6'

export default function IPDRPage() {
  const fileRef  = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult]       = useState<any>(null)
  const [error, setError]         = useState('')
  const [tab, setTab]             = useState<'upload'|'paste'>('upload')
  const [pasteText, setPasteText] = useState('')

  // Filters
  const [searchIP,      setSearchIP]      = useState('')
  const [filterCountry, setFilterCountry] = useState('all')
  const [filterISP,     setFilterISP]     = useState('all')
  const [filterSeverity,setFilterSeverity]= useState<FilterSeverity>('all')
  const [filterVersion, setFilterVersion] = useState<FilterVersion>('all')
  const [filterFlags,   setFilterFlags]   = useState(false)
  const [sortKey,       setSortKey]       = useState<SortKey>('risk_score')
  const [sortDir,       setSortDir]       = useState<'asc'|'desc'>('desc')
  const [page,          setPage]          = useState(1)
  const PER_PAGE = 25

  const uploadPDF = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true); setResult(null); setError('')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('include_private', 'false')
      form.append('max_ips', '500')
      const res = await api.post('/ipdr/analyze-pdf', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })
      setResult(res.data)
      setPage(1)
    } catch (e: any) {
      setError(e.response?.data?.detail || e.response?.data?.error || 'Upload failed')
    } finally { setUploading(false) }
  }

  const analyzeText = async () => {
    if (!pasteText.trim()) return
    setUploading(true); setResult(null); setError('')
    try {
      const res = await api.post('/ipdr/analyze-text', {
        text: pasteText, max_ips: 200
      })
      setResult(res.data)
      setPage(1)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Analysis failed')
    } finally { setUploading(false) }
  }

  // Get unique values for filter dropdowns
  const allIPs: any[]    = result?.ip_details || []
  const countries        = ['all', ...Array.from(new Set(allIPs.map((ip: any) => ip.country).filter(Boolean))).sort()]
  const isps             = ['all', ...Array.from(new Set(allIPs.map((ip: any) => ip.isp).filter(Boolean))).sort()]

  // Apply filters + sort
  const filtered = allIPs
    .filter((ip: any) => !searchIP      || ip.ip.includes(searchIP) || ip.isp?.toLowerCase().includes(searchIP.toLowerCase()) || ip.city?.toLowerCase().includes(searchIP.toLowerCase()))
    .filter((ip: any) => filterCountry === 'all' || ip.country === filterCountry)
    .filter((ip: any) => filterISP      === 'all' || ip.isp      === filterISP)
    .filter((ip: any) => filterSeverity === 'all' || ip.severity === filterSeverity)
    .filter((ip: any) => filterVersion  === 'all' || ip.version  === filterVersion)
    .filter((ip: any) => !filterFlags   || ip.flags?.length > 0)
    .sort((a: any, b: any) => {
      const av = a[sortKey] ?? ''
      const bv = b[sortKey] ?? ''
      const cmp = typeof av === 'number'
        ? av - bv
        : String(av).localeCompare(String(bv))
      return sortDir === 'desc' ? -cmp : cmp
    })

  const totalPages = Math.ceil(filtered.length / PER_PAGE)
  const paginated  = filtered.slice((page-1)*PER_PAGE, page*PER_PAGE)

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortDir('desc') }
    setPage(1)
  }

  const SortIcon = ({ k }: { k: SortKey }) => sortKey === k
    ? <i className={`ti ti-chevron-${sortDir==='desc'?'down':'up'} text-blue-400 text-xs`} />
    : <i className="ti ti-selector text-gray-600 text-xs" />

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-teal-950 flex items-center justify-center">
          <i className="ti ti-file-search text-teal-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">IPDR Analysis Tool</h1>
          <p className="text-gray-500 text-sm">
            Upload IPDR PDF · Extract IPv4 & IPv6 · GeoIP enrichment · Risk filtering
          </p>
        </div>
      </div>

      {/* Input tabs */}
      {!result && (
        <>
          <div className="flex gap-1 border-b border-gray-800 mb-5">
            {(['upload','paste'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px capitalize transition-colors ${
                  tab===t ? 'border-teal-500 text-teal-400' : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}>{t === 'upload' ? 'Upload PDF' : 'Paste text'}</button>
            ))}
          </div>

          {tab === 'upload' && (
            <div className="card p-8 text-center border-dashed border-2 border-gray-700
                            hover:border-teal-700 transition-colors cursor-pointer mb-5"
              onClick={() => fileRef.current?.click()}>
              <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={uploadPDF} />
              {uploading ? (
                <>
                  <span className="spinner w-10 h-10 block mx-auto mb-4" />
                  <p className="text-gray-400">Extracting IPs and enriching with GeoIP data…</p>
                  <p className="text-gray-600 text-sm mt-1">This may take 30–60 seconds for large files</p>
                </>
              ) : (
                <>
                  <i className="ti ti-file-type-pdf text-5xl text-teal-400 block mb-3" />
                  <p className="text-white font-medium mb-1">Click to upload IPDR PDF</p>
                  <p className="text-gray-500 text-sm">
                    Supports single or multi-page PDFs · Max 50MB · All IPs extracted automatically
                  </p>
                  <div className="flex justify-center gap-4 mt-4 text-xs text-gray-600">
                    <span><i className="ti ti-check text-teal-400 mr-1" />IPv4 extraction</span>
                    <span><i className="ti ti-check text-teal-400 mr-1" />IPv6 extraction</span>
                    <span><i className="ti ti-check text-teal-400 mr-1" />GeoIP enrichment</span>
                    <span><i className="ti ti-check text-teal-400 mr-1" />Risk scoring</span>
                  </div>
                </>
              )}
            </div>
          )}

          {tab === 'paste' && (
            <div className="card p-4 mb-5">
              <label className="text-xs text-gray-400 mb-2 block">
                Paste IPDR data or any text containing IP addresses
              </label>
              <textarea value={pasteText} onChange={e => setPasteText(e.target.value)}
                rows={8} placeholder="Paste IPDR text here — IPv4 and IPv6 will be extracted automatically…"
                className="input-field w-full resize-none font-mono text-xs mb-3" />
              <button onClick={analyzeText} disabled={!pasteText.trim() || uploading}
                className="btn-primary">
                {uploading ? <><span className="spinner w-4 h-4" />Analyzing…</> : <><i className="ti ti-search" />Extract & Analyze IPs</>}
              </button>
            </div>
          )}

          {error && (
            <div className="card p-4 border-red-900 bg-red-950/20">
              <p className="text-red-400 text-sm flex items-center gap-2">
                <i className="ti ti-alert-circle" />{error}
              </p>
            </div>
          )}
        </>
      )}

      {/* Results */}
      {result && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-5">
            {[
              { label:'Total IPs',      value: result.summary?.total_ipv4_found || result.summary?.public_ipv4 || 0,  color:'text-white'      },
              { label:'Public IPv4',    value: result.summary?.public_ipv4  || 0,  color:'text-blue-400'   },
              { label:'Private IPv4',   value: result.summary?.private_ipv4 || 0,  color:'text-gray-400'   },
              { label:'IPv6',           value: result.summary?.ipv6_found   || 0,  color:'text-purple-400' },
              { label:'Countries',      value: result.summary?.unique_countries || 0, color:'text-teal-400' },
              { label:'ISPs',           value: result.summary?.unique_isps  || 0,  color:'text-green-400'  },
              { label:'High risk',      value: result.summary?.high_risk_ips || 0, color:'text-red-400'    },
            ].map(s => (
              <div key={s.label} className="card p-3 text-center">
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                <div className="text-[10px] text-gray-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Top countries + ISPs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            {result.top_countries && Object.keys(result.top_countries).length > 0 && (
              <div className="card p-4">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  Top countries
                </h3>
                <div className="space-y-2">
                  {Object.entries(result.top_countries).slice(0,6).map(([country, count]: any) => (
                    <div key={country} className="flex items-center gap-3">
                      <span className="text-xs text-white w-8">{country}</span>
                      <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                        <div className="h-full bg-teal-600 rounded-full"
                          style={{width:`${Math.round(count/allIPs.length*100)}%`}} />
                      </div>
                      <span className="text-xs text-gray-400 w-6 text-right">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {result.top_isps && Object.keys(result.top_isps).length > 0 && (
              <div className="card p-4">
                <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                  Top ISPs / Organizations
                </h3>
                <div className="space-y-2">
                  {Object.entries(result.top_isps).slice(0,6).map(([isp, count]: any) => (
                    <div key={isp} className="flex items-center gap-3">
                      <span className="text-xs text-white flex-1 truncate">{isp}</span>
                      <span className="text-xs text-gray-400">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* High risk IPs */}
          {result.high_risk_ips?.length > 0 && (
            <div className="card p-4 mb-5 border-red-900 bg-red-950/10">
              <h3 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2">
                <i className="ti ti-alert-triangle" />High risk IPs detected ({result.high_risk_ips.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.high_risk_ips.slice(0,20).map((ip: string) => (
                  <span key={ip} className="font-mono text-xs bg-red-950 border border-red-900
                                            text-red-300 px-2 py-1 rounded">{ip}</span>
                ))}
              </div>
            </div>
          )}

          {/* ── FILTERS ─────────────────────────────────────────────────────── */}
          <div className="card p-4 mb-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              <i className="ti ti-filter mr-1" />Filter & Search
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {/* Search */}
              <div className="col-span-2 md:col-span-1 lg:col-span-2 relative">
                <i className="ti ti-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-xs" />
                <input value={searchIP} onChange={e => { setSearchIP(e.target.value); setPage(1) }}
                  placeholder="Search IP, ISP, city…"
                  className="input-field pl-8 text-xs h-9" />
              </div>

              {/* Country */}
              <select value={filterCountry} onChange={e => { setFilterCountry(e.target.value); setPage(1) }}
                className="select-field text-xs h-9">
                {countries.map(c => <option key={c} value={c}>{c === 'all' ? 'All countries' : c}</option>)}
              </select>

              {/* ISP */}
              <select value={filterISP} onChange={e => { setFilterISP(e.target.value); setPage(1) }}
                className="select-field text-xs h-9">
                <option value="all">All ISPs</option>
                {isps.filter(i => i !== 'all').slice(0,30).map(i => (
                  <option key={i} value={i}>{i.slice(0,30)}</option>
                ))}
              </select>

              {/* Severity */}
              <select value={filterSeverity} onChange={e => { setFilterSeverity(e.target.value as any); setPage(1) }}
                className="select-field text-xs h-9">
                <option value="all">All risk levels</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              {/* IP version + flags */}
              <div className="flex gap-2">
                <select value={filterVersion} onChange={e => { setFilterVersion(e.target.value as any); setPage(1) }}
                  className="select-field text-xs h-9 flex-1">
                  <option value="all">IPv4 + IPv6</option>
                  <option value="IPv4">IPv4 only</option>
                  <option value="IPv6">IPv6 only</option>
                </select>
                <button onClick={() => { setFilterFlags(!filterFlags); setPage(1) }}
                  className={`h-9 px-3 rounded-lg border text-xs transition-colors flex-shrink-0 ${
                    filterFlags
                      ? 'border-red-700 bg-red-950 text-red-400'
                      : 'border-gray-700 bg-gray-800 text-gray-400 hover:text-white'
                  }`} title="Flagged only (TOR/VPN/Proxy)">
                  <i className="ti ti-flag" />
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between mt-3">
              <span className="text-xs text-gray-500">
                Showing {filtered.length} of {allIPs.length} IPs
                {filterSeverity !== 'all' || filterCountry !== 'all' || filterISP !== 'all' || searchIP || filterFlags
                  ? ' (filtered)' : ''}
              </span>
              <button onClick={() => {
                setSearchIP(''); setFilterCountry('all'); setFilterISP('all')
                setFilterSeverity('all'); setFilterVersion('all'); setFilterFlags(false); setPage(1)
              }} className="text-xs text-gray-500 hover:text-white">
                <i className="ti ti-x mr-1" />Clear filters
              </button>
            </div>
          </div>

          {/* ── IP TABLE ─────────────────────────────────────────────────────── */}
          <div className="card overflow-hidden mb-4">
            {/* Table header */}
            <div className="grid grid-cols-[110px_60px_80px_120px_130px_120px_80px_100px] gap-2
                            px-4 py-2.5 border-b border-gray-800 text-xs font-semibold
                            text-gray-500 uppercase tracking-wider">
              <button onClick={() => toggleSort('ip')} className="flex items-center gap-1 hover:text-white text-left">
                IP Address <SortIcon k="ip" />
              </button>
              <span>Ver.</span>
              <button onClick={() => toggleSort('risk_score')} className="flex items-center gap-1 hover:text-white">
                Risk <SortIcon k="risk_score" />
              </button>
              <button onClick={() => toggleSort('country')} className="flex items-center gap-1 hover:text-white">
                Country <SortIcon k="country" />
              </button>
              <button onClick={() => toggleSort('isp')} className="flex items-center gap-1 hover:text-white text-left">
                ISP / Org <SortIcon k="isp" />
              </button>
              <span>City / Region</span>
              <span>ASN</span>
              <span>Flags</span>
            </div>

            {paginated.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-sm">
                No IPs match current filters
              </div>
            ) : paginated.map((ip: any, i: number) => (
              <div key={ip.ip}
                className={`grid grid-cols-[110px_60px_80px_120px_130px_120px_80px_100px] gap-2
                            px-4 py-2.5 items-center text-xs
                            hover:bg-gray-800/30 transition-colors
                            ${i < paginated.length-1 ? 'border-b border-gray-800/50' : ''}
                            ${ip.risk_score >= 40 ? 'bg-red-950/5' : ''}`}>
                {/* IP */}
                <div>
                  <span className="font-mono text-white">{ip.ip}</span>
                  {ip.hostname && (
                    <div className="text-[10px] text-gray-600 truncate">{ip.hostname}</div>
                  )}
                </div>

                {/* Version */}
                <span className={`badge text-[10px] ${ip.version==='IPv6'?'badge-purple':'badge-blue'}`}>
                  {ip.version}
                </span>

                {/* Risk */}
                <div>
                  <span className={`font-bold ${SEVERITY_CLS[ip.severity] || 'text-gray-400'}`}>
                    {ip.risk_score}
                  </span>
                  <div className={`text-[10px] ${SEVERITY_CLS[ip.severity] || 'text-gray-400'}`}>
                    {ip.severity}
                  </div>
                </div>

                {/* Country */}
                <span className="text-gray-300">{ip.country || '—'}</span>

                {/* ISP */}
                <span className="text-gray-300 truncate">{ip.isp || '—'}</span>

                {/* City */}
                <span className="text-gray-400 truncate">
                  {[ip.city, ip.region].filter(Boolean).join(', ') || '—'}
                </span>

                {/* ASN */}
                <span className="font-mono text-gray-500 text-[10px]">{ip.asn || '—'}</span>

                {/* Flags */}
                <div className="flex flex-wrap gap-0.5">
                  {ip.flags?.length > 0
                    ? ip.flags.map((f: string) => (
                        <span key={f} className="badge badge-red text-[9px] px-1">{f}</span>
                      ))
                    : <span className="text-gray-700 text-[10px]">clean</span>}
                  {ip.google_maps && (
                    <a href={ip.google_maps} target="_blank" rel="noopener noreferrer"
                      className="text-teal-400 hover:text-teal-300 ml-1" title="View on map">
                      <i className="ti ti-map-pin text-xs" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">
                Page {page} of {totalPages} · {filtered.length} results
              </span>
              <div className="flex gap-2">
                <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1}
                  className="btn-secondary text-xs px-3 py-1.5 disabled:opacity-40">
                  <i className="ti ti-chevron-left" />Prev
                </button>
                {Array.from({length: Math.min(5, totalPages)}, (_, i) => {
                  const pg = page <= 3 ? i+1 : page+i-2
                  if (pg < 1 || pg > totalPages) return null
                  return (
                    <button key={pg} onClick={() => setPage(pg)}
                      className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                        pg===page ? 'border-blue-500 bg-blue-950 text-blue-400' : 'border-gray-700 bg-gray-800 text-gray-400'
                      }`}>{pg}</button>
                  )
                })}
                <button onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page===totalPages}
                  className="btn-secondary text-xs px-3 py-1.5 disabled:opacity-40">
                  Next<i className="ti ti-chevron-right" />
                </button>
              </div>
            </div>
          )}

          {/* Reset button */}
          <div className="mt-5">
            <button onClick={() => { setResult(null); setError(''); setPasteText('') }}
              className="btn-secondary">
              <i className="ti ti-upload" />Analyze another file
            </button>
          </div>
        </>
      )}
    </div>
  )
}
