'use client'
import { useState, useEffect } from 'react'
import { investigateAPI } from '@/lib/api'

const SEV: Record<string, string> = {
  CRITICAL: 'text-red-400', HIGH: 'text-orange-400',
  MEDIUM: 'text-amber-400', LOW: 'text-green-400',
}

export default function ThreatPage() {
  const [qtype, setQtype]     = useState('ip')
  const [query, setQuery]     = useState('')
  const [loading, setLoading] = useState(false)
  const [invId, setInvId]     = useState('')
  const [result, setResult]   = useState<any>(null)
  const [error, setError]     = useState('')

  const run = async () => {
    if (!query.trim()) return
    setLoading(true); setResult(null); setError('')
    try {
      const res = await investigateAPI.start({
        investigation_type: 'threat', query: query.trim(), query_type: qtype,
      })
      setInvId(res.data.id)
    } catch (e: any) { setError(e.response?.data?.detail || 'Failed'); setLoading(false) }
  }

  useEffect(() => {
    if (!invId) return
    const t = setInterval(async () => {
      try {
        const res = await investigateAPI.get(invId)
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          setResult(res.data); setLoading(false); clearInterval(t)
        }
      } catch { clearInterval(t); setLoading(false) }
    }, 1500)
    return () => clearInterval(t)
  }, [invId])

  const risk = result?.risk_score ?? 0

  const QUICK_IOCS = [
    { label: 'LockBit (Ransomware)', query: 'LockBit',         type: 'hash' },
    { label: 'SideCopy (APT)',       query: 'SideCopy',        type: 'hash' },
    { label: 'Cobalt Strike',        query: 'Cobalt Strike',    type: 'hash' },
    { label: 'Emotet Loader',        query: 'Emotet',           type: 'hash' },
  ]

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-red-950 flex items-center justify-center">
          <i className="ti ti-bug text-red-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Threat Intelligence</h1>
          <p className="text-gray-500 text-sm">IOC enrichment · MITRE ATT&amp;CK · OTX AlienVault · VirusTotal</p>
        </div>
      </div>

      {/* Quick searches */}
      <div className="flex flex-wrap gap-2 mb-4">
        {QUICK_IOCS.map(q => (
          <button key={q.label}
            onClick={() => { setQuery(q.query); setQtype(q.type) }}
            className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border
                       border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors">
            <i className="ti ti-bug mr-1 text-red-400" />{q.label}
          </button>
        ))}
      </div>

      <div className="card p-4 mb-5">
        <div className="flex gap-3 flex-wrap">
          <select value={qtype} onChange={e => setQtype(e.target.value)} className="select-field w-36">
            <option value="ip">IP Address</option>
            <option value="domain">Domain</option>
            <option value="hash">Hash / Malware</option>
            <option value="url">URL</option>
          </select>
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder={
              qtype === 'ip'     ? '45.33.32.156' :
              qtype === 'domain' ? 'malicious-site.com' :
              qtype === 'hash'   ? 'SHA256 hash or malware name' : 'https://suspicious-url.com'
            }
            className="input-field flex-1 min-w-48" />
          <button onClick={run} disabled={!query.trim() || loading} className="btn-primary px-6">
            {loading ? <><span className="spinner w-4 h-4" />Enriching…</> : <><i className="ti ti-search" />Enrich IOC</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      </div>

      {loading && (
        <div className="card p-8 text-center space-y-3">
          <span className="spinner w-8 h-8 block mx-auto" />
          <p className="text-gray-400 text-sm">Querying OTX · VirusTotal · MITRE ATT&amp;CK…</p>
        </div>
      )}

      {result && !loading && (
        <>
          <div className="card p-4 mb-4 flex items-center gap-4">
            <div>
              <div className="text-xs text-gray-500 mb-1">Threat score</div>
              <span className={`text-2xl font-bold ${risk>=70?'text-red-400':risk>=40?'text-amber-400':'text-green-400'}`}>
                {risk}/100
              </span>
            </div>
            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-700"
                style={{ width:`${risk}%`, background: risk>=70?'#EF4444':risk>=40?'#F59E0B':'#10B981' }} />
            </div>
            <div className="text-xs text-gray-500 max-w-xs text-right truncate">{result.summary}</div>
          </div>

          {/* MITRE ATT&CK section */}
          {result.results?.find((r:any) => r.source_name === 'mitre')?.parsed_data?.techniques?.length > 0 && (
            <div className="card p-4 mb-4">
              <div className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <i className="ti ti-shield-lock text-red-400" />MITRE ATT&amp;CK Techniques
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {result.results.find((r:any) => r.source_name === 'mitre')
                  .parsed_data.techniques.map((t: any, i: number) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-gray-800 rounded-lg">
                    <span className="font-mono text-xs text-red-400 font-bold mt-0.5 flex-shrink-0">{t.id}</span>
                    <div>
                      <div className="text-sm font-medium text-white">{t.name}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{t.tactic}</div>
                    </div>
                    <span className={`text-xs font-bold ml-auto flex-shrink-0 ${SEV[t.severity]||'text-gray-400'}`}>
                      {t.severity}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Source cards */}
          {result.results?.filter((r:any) => r.source_name !== 'mitre').map((r: any, i: number) => (
            <div key={i} className="card overflow-hidden mb-4">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
                <i className={`ti ${
                  r.source_name === 'otx'          ? 'ti-eye' :
                  r.source_name === 'virustotal'   ? 'ti-shield' :
                  r.source_name === 'ioc_analysis' ? 'ti-search' : 'ti-database'
                } text-red-400 text-lg`} />
                <span className="text-sm font-semibold text-white flex-1 capitalize">
                  {r.source_name.replace(/_/g,' ')}
                </span>
                {r.parsed_data?.severity && (
                  <span className={`text-xs font-bold ${SEV[r.parsed_data.severity]||'text-gray-400'}`}>
                    {r.parsed_data.severity}
                  </span>
                )}
                {r.is_suspicious && <span className="badge badge-red text-xs">Suspicious</span>}
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(r.parsed_data || {})
                    .filter(([k]) => !['name','severity','techniques','pulses','demo'].includes(k))
                    .map(([k, v], j) => (
                      <tr key={j} className="border-b border-gray-800/50 last:border-0">
                        <td className="px-4 py-2.5 text-gray-500 w-44 capitalize align-top">{k.replace(/_/g,' ')}</td>
                        <td className={`px-4 py-2.5 font-medium align-top break-all ${
                          String(v).includes('⚠') ? 'text-amber-400' :
                          String(v) === 'true'    ? 'text-red-400'   :
                          String(v) === 'false'   ? 'text-green-400' : 'text-white'
                        }`}>
                          {Array.isArray(v)
                            ? v.length ? v.map((x:any) => typeof x === 'object' ? x.name || JSON.stringify(x) : String(x)).join(', ') : '—'
                            : String(v||'—')}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ))}

          <button onClick={() => { setResult(null); setQuery('') }} className="btn-secondary">
            <i className="ti ti-refresh" />New search
          </button>
        </>
      )}
    </div>
  )
}
