'use client'
import { useState, useRef } from 'react'
import { api } from '@/lib/api'

const RISK_COLOR = (r: number) =>
  r >= 60 ? 'text-red-400' : r >= 30 ? 'text-amber-400' : 'text-green-400'

const RISK_BADGE = (r: number) =>
  r >= 60 ? 'badge-red' : r >= 30 ? 'badge-amber' : 'badge-green'

const RISK_BORDER = (r: number) =>
  r >= 60 ? 'border-red-900 bg-red-950/10' :
  r >= 30 ? 'border-amber-900 bg-amber-950/10' : 'border-gray-800'

export default function IPDRPage() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile]         = useState<File | null>(null)
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState<any>(null)
  const [error, setError]       = useState('')

  // Filters
  const [filterCountry, setFilterCountry] = useState('all')
  const [filterRisk,    setFilterRisk]    = useState('all')
  const [filterVersion, setFilterVersion] = useState('all')
  const [filterISP,     setFilterISP]     = useState('all')
  const [filterThreat,  setFilterThreat]  = useState('all')
  const [searchIP,      setSearchIP]      = useState('')
  const [sortBy,        setSortBy]        = useState<'risk'|'country'|'isp'|'ip'>('risk')

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) { setFile(f); setResult(null); setError('') }
  }

  const analyze = async () => {
    if (!file) return
    setLoading(true); setResult(null); setError('')
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('include_private', 'false')
      const res = await api.post('/ipdr/analyze', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })
      setResult(res.data)
    } catch (e: any) {
      setError(e.response?.data?.error || e.response?.data?.detail || 'Analysis failed')
    } finally { setLoading(false) }
  }

  // Build filter options from results
  const allResults: any[] = result?.results || []
  const countries = ['all', ...Array.from(new Set(allResults.map((r:any) => r.country).filter(Boolean)))]
  const isps      = ['all', ...Array.from(new Set(allResults.map((r:any) => r.isp).filter(Boolean)))]

  // Apply filters
  const filtered = allResults
    .filter(r => filterCountry === 'all' || r.country === filterCountry)
    .filter(r => filterVersion === 'all' || r.version === filterVersion)
    .filter(r => filterISP     === 'all' || r.isp     === filterISP)
    .filter(r => filterRisk    === 'all' ||
      (filterRisk === 'high'   && r.risk_score >= 60) ||
      (filterRisk === 'medium' && r.risk_score >= 30 && r.risk_score < 60) ||
      (filterRisk === 'low'    && r.risk_score < 30)
    )
    .filter(r => filterThreat === 'all' ||
      (filterThreat === 'tor'     && r.is_tor)   ||
      (filterThreat === 'vpn'     && r.is_vpn)   ||
      (filterThreat === 'proxy'   && r.is_proxy) ||
      (filterThreat === 'foreign' && r.country !== 'IN')
    )
    .filter(r => !searchIP || r.ip.includes(searchIP))
    .sort((a, b) =>
      sortBy === 'risk'    ? b.risk_score - a.risk_score :
      sortBy === 'country' ? (a.country||'').localeCompare(b.country||'') :
      sortBy === 'isp'     ? (a.isp||'').localeCompare(b.isp||'') :
                             a.ip.localeCompare(b.ip)
    )

  const resetFilters = () => {
    setFilterCountry('all'); setFilterRisk('all'); setFilterVersion('all')
    setFilterISP('all'); setFilterThreat('all'); setSearchIP(''); setSortBy('risk')
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-teal-950 flex items-center justify-center">
          <i className="ti ti-file-search text-teal-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">IPDR Analyzer</h1>
          <p className="text-gray-500 text-sm">
            Upload IPDR PDF → Extract all IPv4/IPv6 → GeoIP enrichment → ISP · ASN · Risk scoring
          </p>
        </div>
      </div>

      {/* Upload card */}
      <div className="card p-5 mb-5 border-teal-900">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <div
              onClick={() => fileRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
                          transition-colors ${
                file ? 'border-teal-700 bg-teal-950/20' : 'border-gray-700 hover:border-gray-600'
              }`}>
              <i className={`ti ${file ? 'ti-file-check' : 'ti-upload'} text-3xl block mb-2 ${
                file ? 'text-teal-400' : 'text-gray-500'
              }`} />
              {file ? (
                <>
                  <p className="text-white font-medium">{file.name}</p>
                  <p className="text-gray-500 text-xs mt-1">
                    {(file.size / 1024).toFixed(1)} KB · Click to change
                  </p>
                </>
              ) : (
                <>
                  <p className="text-gray-400 font-medium">Click to upload IPDR PDF</p>
                  <p className="text-gray-600 text-xs mt-1">
                    Supports court-issued IPDR records · Max 50MB
                  </p>
                </>
              )}
            </div>
            <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleFile} />
          </div>
          <div className="flex flex-col gap-2 pt-2">
            <button onClick={analyze} disabled={!file || loading} className="btn-primary px-6 py-3">
              {loading
                ? <><span className="spinner w-4 h-4" />Analyzing…</>
                : <><i className="ti ti-search" />Analyze IPDR</>}
            </button>
            {file && (
              <button onClick={() => { setFile(null); setResult(null); setError('') }}
                className="btn-secondary text-xs">
                <i className="ti ti-x mr-1" />Clear
              </button>
            )}
          </div>
        </div>

        {loading && (
          <div className="mt-4 flex items-center gap-3 text-sm text-teal-400">
            <span className="spinner w-5 h-5" />
            Extracting IPs from PDF… Querying IPinfo for all addresses… This may take 30–60 seconds.
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-red-950/30 border border-red-900 rounded-lg text-red-400 text-sm">
            <i className="ti ti-alert-circle mr-2" />{error}
          </div>
        )}

        <div className="mt-4 grid grid-cols-3 gap-3 text-xs text-gray-600">
          {[
            'Extracts IPv4 and IPv6 addresses automatically',
            'Enriches with GeoIP, ISP, ASN data via IPinfo',
            'Risk scores for foreign, TOR, VPN, proxy IPs',
          ].map((tip, i) => (
            <div key={i} className="flex items-center gap-1">
              <i className="ti ti-check text-teal-400" />{tip}
            </div>
          ))}
        </div>
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Summary stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-5">
            {[
              { label:'Total IPs',    value: result.summary.total_ips_found,       color:'text-white'      },
              { label:'IPv4',         value: result.summary.ipv4_count,            color:'text-blue-400'   },
              { label:'IPv6',         value: result.summary.ipv6_count,            color:'text-purple-400' },
              { label:'High risk',    value: result.summary.high_risk_count,       color:'text-red-400'    },
              { label:'Foreign IPs',  value: result.summary.foreign_ips,           color:'text-amber-400'  },
              { label:'TOR/VPN',      value: result.summary.tor_vpn_proxy,         color:'text-red-400'    },
              { label:'Countries',    value: result.summary.unique_countries,      color:'text-green-400'  },
            ].map(s => (
              <div key={s.label} className="card p-3 text-center">
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Top countries + ISPs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            <div className="card p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Top countries
              </h3>
              {Object.entries(result.summary.top_countries).map(([country, count]: any) => (
                <div key={country} className="flex items-center gap-2 mb-1.5">
                  <span className={`text-xs font-mono w-8 font-bold ${
                    country === 'IN' ? 'text-green-400' : 'text-amber-400'
                  }`}>{country}</span>
                  <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${country==='IN'?'bg-green-600':'bg-amber-600'}`}
                      style={{width:`${Math.round(count/result.summary.total_ips_found*100)}%`}} />
                  </div>
                  <span className="text-xs text-gray-400 w-6 text-right">{count}</span>
                </div>
              ))}
            </div>
            <div className="card p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Top ISPs / ASNs
              </h3>
              {Object.entries(result.summary.top_isps).map(([isp, count]: any) => (
                <div key={isp} className="flex items-center gap-2 mb-1.5">
                  <span className="text-xs text-gray-400 flex-1 truncate">{isp || 'Unknown'}</span>
                  <div className="w-16 h-2 bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-600 rounded-full"
                      style={{width:`${Math.round(count/result.summary.total_ips_found*100)}%`}} />
                  </div>
                  <span className="text-xs text-gray-400 w-4 text-right">{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* High risk IPs alert */}
          {result.high_risk_ips?.length > 0 && (
            <div className="card p-4 mb-5 border-red-900 bg-red-950/20">
              <h3 className="text-sm font-semibold text-red-400 mb-2 flex items-center gap-2">
                <i className="ti ti-alert-triangle text-lg" />
                {result.high_risk_ips.length} High Risk IP{result.high_risk_ips.length > 1 ? 's' : ''} detected
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.high_risk_ips.map((r: any) => (
                  <div key={r.ip} className="flex items-center gap-2 bg-red-950/30 border
                                              border-red-900 rounded-lg px-3 py-1.5 text-xs">
                    <span className="font-mono text-white">{r.ip}</span>
                    <span className="text-red-400 font-bold">{r.risk_score}/100</span>
                    {r.is_tor   && <span className="badge badge-red text-[10px]">TOR</span>}
                    {r.is_vpn   && <span className="badge badge-red text-[10px]">VPN</span>}
                    {r.is_proxy && <span className="badge badge-red text-[10px]">PROXY</span>}
                    <span className="text-gray-400">{r.country}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Filters ── */}
          <div className="card p-4 mb-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <i className="ti ti-filter text-teal-400" />Filter & sort results
              </h3>
              <button onClick={resetFilters}
                className="text-xs text-gray-500 hover:text-white flex items-center gap-1">
                <i className="ti ti-refresh" />Reset
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {/* IP search */}
              <div className="lg:col-span-2">
                <label className="text-xs text-gray-500 mb-1 block">Search IP</label>
                <div className="relative">
                  <i className="ti ti-search absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs" />
                  <input value={searchIP} onChange={e => setSearchIP(e.target.value)}
                    placeholder="Filter by IP address…"
                    className="input-field pl-7 text-xs py-2" />
                </div>
              </div>

              {/* Risk */}
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Risk level</label>
                <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)}
                  className="select-field w-full text-xs">
                  <option value="all">All risks</option>
                  <option value="high">High (≥60)</option>
                  <option value="medium">Medium (30–60)</option>
                  <option value="low">Low (&lt;30)</option>
                </select>
              </div>

              {/* Country */}
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Country</label>
                <select value={filterCountry} onChange={e => setFilterCountry(e.target.value)}
                  className="select-field w-full text-xs">
                  {countries.map(c => (
                    <option key={c} value={c}>{c === 'all' ? 'All countries' : c}</option>
                  ))}
                </select>
              </div>

              {/* IP version */}
              <div>
                <label className="text-xs text-gray-500 mb-1 block">IP version</label>
                <select value={filterVersion} onChange={e => setFilterVersion(e.target.value)}
                  className="select-field w-full text-xs">
                  <option value="all">IPv4 + IPv6</option>
                  <option value="IPv4">IPv4 only</option>
                  <option value="IPv6">IPv6 only</option>
                </select>
              </div>

              {/* Threat type */}
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Threat type</label>
                <select value={filterThreat} onChange={e => setFilterThreat(e.target.value)}
                  className="select-field w-full text-xs">
                  <option value="all">All IPs</option>
                  <option value="foreign">Foreign IPs</option>
                  <option value="tor">TOR exit nodes</option>
                  <option value="vpn">VPN detected</option>
                  <option value="proxy">Proxy detected</option>
                </select>
              </div>
            </div>

            {/* ISP filter + sort */}
            <div className="flex gap-3 mt-3">
              <div className="flex-1">
                <label className="text-xs text-gray-500 mb-1 block">ISP / Organization</label>
                <select value={filterISP} onChange={e => setFilterISP(e.target.value)}
                  className="select-field w-full text-xs">
                  {isps.slice(0, 20).map(i => (
                    <option key={i} value={i}>{i === 'all' ? 'All ISPs' : i}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Sort by</label>
                <select value={sortBy} onChange={e => setSortBy(e.target.value as any)}
                  className="select-field text-xs">
                  <option value="risk">Risk score</option>
                  <option value="country">Country</option>
                  <option value="isp">ISP</option>
                  <option value="ip">IP address</option>
                </select>
              </div>
              <div className="self-end">
                <span className="text-xs text-gray-500">
                  Showing {filtered.length} of {allResults.length} IPs
                </span>
              </div>
            </div>
          </div>

          {/* Results table */}
          <div className="card overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[140px_60px_70px_120px_1fr_100px_100px_80px] gap-2
                            px-4 py-2.5 border-b border-gray-800
                            text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <span>IP Address</span>
              <span>Ver</span>
              <span>Risk</span>
              <span>Country / Region</span>
              <span>ISP / Organization</span>
              <span>ASN</span>
              <span>Flags</span>
              <span>Action</span>
            </div>

            {filtered.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-sm">
                <i className="ti ti-filter-off text-3xl block mb-2 opacity-40" />
                No IPs match current filters
              </div>
            ) : filtered.map((r: any, i: number) => (
              <div key={r.ip}
                className={`grid grid-cols-[140px_60px_70px_120px_1fr_100px_100px_80px] gap-2
                            px-4 py-3 items-center text-sm
                            ${RISK_BORDER(r.risk_score)}
                            ${i < filtered.length-1 ? 'border-b border-gray-800' : ''}
                            hover:bg-gray-800/30 transition-colors`}>

                {/* IP */}
                <span className="font-mono text-xs text-white select-all">{r.ip}</span>

                {/* Version */}
                <span className={`badge text-[10px] ${r.version==='IPv6'?'badge-purple':'badge-blue'}`}>
                  {r.version}
                </span>

                {/* Risk */}
                <div className="flex items-center gap-1">
                  <span className={`text-xs font-bold ${RISK_COLOR(r.risk_score)}`}>
                    {r.risk_score}
                  </span>
                  <span className={`badge text-[10px] ${RISK_BADGE(r.risk_score)}`}>
                    {r.risk_label}
                  </span>
                </div>

                {/* Country */}
                <div>
                  <div className={`text-xs font-medium ${
                    r.country !== 'IN' && r.country ? 'text-amber-400' : 'text-white'
                  }`}>{r.country || '—'}</div>
                  <div className="text-[10px] text-gray-500 truncate">{r.city} {r.region}</div>
                </div>

                {/* ISP */}
                <div className="min-w-0">
                  <div className="text-xs text-white truncate">{r.isp || r.org || '—'}</div>
                  {r.hostname && (
                    <div className="text-[10px] text-gray-600 truncate font-mono">{r.hostname}</div>
                  )}
                </div>

                {/* ASN */}
                <span className="font-mono text-xs text-gray-400">{r.asn || '—'}</span>

                {/* Flags */}
                <div className="flex gap-1 flex-wrap">
                  {r.is_tor   && <span className="badge badge-red text-[10px]">TOR</span>}
                  {r.is_vpn   && <span className="badge badge-red text-[10px]">VPN</span>}
                  {r.is_proxy && <span className="badge badge-red text-[10px]">PROXY</span>}
                  {r.country !== 'IN' && r.country &&
                    <span className="badge badge-amber text-[10px]">FOREIGN</span>}
                </div>

                {/* Action */}
                <div className="flex gap-1">
                  <a href={`/investigate/ip?q=${r.ip}`}
                    className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-0.5"
                    title="Full investigation">
                    <i className="ti ti-search text-sm" />
                  </a>
                  {r.google_maps && (
                    <a href={r.google_maps} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-green-400 hover:text-green-300"
                      title="View on map">
                      <i className="ti ti-map-pin text-sm" />
                    </a>
                  )}
                  {r.abuse_contact && (
                    <a href={`mailto:${r.abuse_contact}`}
                      className="text-xs text-amber-400 hover:text-amber-300"
                      title={`Report abuse: ${r.abuse_contact}`}>
                      <i className="ti ti-mail text-sm" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Export hint */}
          <div className="mt-4 text-xs text-gray-600 flex items-center gap-2">
            <i className="ti ti-info-circle" />
            Click the search icon on any IP to run a full investigation.
            Click the map icon to view location.
            Click the mail icon to contact abuse team.
          </div>
        </>
      )}
    </div>
  )
}
