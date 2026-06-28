'use client'
import { useState, useEffect } from 'react'
import { investigateAPI } from '@/lib/api'

const SEV: Record<string, string> = {
  CRITICAL:'text-red-400', HIGH:'text-orange-400', MEDIUM:'text-amber-400', LOW:'text-green-400'
}

export default function DarkWebPage() {
  const [qtype, setQtype]     = useState('email')
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
        investigation_type: 'dark_web', query: query.trim(), query_type: qtype,
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

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-indigo-950 flex items-center justify-center">
          <i className="ti ti-moon text-indigo-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Dark Web Monitoring</h1>
          <p className="text-gray-500 text-sm">Credential leaks · Ahmia Tor search · Breach intelligence</p>
        </div>
      </div>

      <div className="card p-4 mb-5 border-indigo-900">
        <div className="flex gap-3 flex-wrap">
          <select value={qtype} onChange={e => setQtype(e.target.value)} className="select-field w-36">
            <option value="email">Email address</option>
            <option value="domain">Organisation domain</option>
            <option value="keyword">Keyword / name</option>
          </select>
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder={
              qtype === 'email'   ? 'officer@police.gov.in' :
              qtype === 'domain'  ? 'haryana.gov.in' : 'keyword to monitor'
            }
            className="input-field flex-1 min-w-48" />
          <button onClick={run} disabled={!query.trim() || loading} className="btn-primary px-6">
            {loading ? <><span className="spinner w-4 h-4" />Scanning…</> : <><i className="ti ti-search" />Scan Dark Web</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
        <p className="text-xs text-gray-600 mt-2 flex items-center gap-1">
          <i className="ti ti-info-circle" />All scans are passive and read-only. No Tor connection required.
        </p>
      </div>

      {loading && (
        <div className="card p-8 text-center space-y-3">
          <span className="spinner w-8 h-8 block mx-auto" />
          <p className="text-gray-400 text-sm">Scanning Ahmia · Checking credential databases…</p>
          <p className="text-gray-600 text-xs">This may take 10–15 seconds</p>
        </div>
      )}

      {result && !loading && (
        <>
          <div className="card p-4 mb-4 flex items-center gap-4">
            <div>
              <div className="text-xs text-gray-500 mb-1">Exposure score</div>
              <span className={`text-2xl font-bold ${risk>=70?'text-red-400':risk>=40?'text-amber-400':'text-green-400'}`}>
                {risk}/100
              </span>
            </div>
            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full rounded-full"
                style={{ width:`${risk}%`, background: risk>=70?'#EF4444':risk>=40?'#F59E0B':'#10B981' }} />
            </div>
            <div className="text-xs text-gray-500">{result.summary}</div>
          </div>

          {result.results?.map((r: any, i: number) => (
            <div key={i} className="card overflow-hidden mb-4">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
                <i className={`ti ${
                  r.source_name === 'ahmia'              ? 'ti-search' :
                  r.source_name === 'credential_check'   ? 'ti-database-leak' :
                  r.source_name === 'breach_intelligence'? 'ti-alert-triangle' : 'ti-moon'
                } text-indigo-400 text-lg`} />
                <span className="text-sm font-semibold text-white flex-1 capitalize">
                  {r.source_name.replace(/_/g,' ')}
                </span>
                {r.parsed_data?.severity && (
                  <span className={`text-xs font-bold ${SEV[r.parsed_data.severity]||'text-gray-400'}`}>
                    {r.parsed_data.severity}
                  </span>
                )}
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(r.parsed_data || {})
                    .filter(([k]) => !['name','severity','recommendations','relevant_breaches'].includes(k))
                    .map(([k, v], j) => (
                      <tr key={j} className="border-b border-gray-800/50 last:border-0">
                        <td className="px-4 py-2.5 text-gray-500 w-44 capitalize align-top">{k.replace(/_/g,' ')}</td>
                        <td className={`px-4 py-2.5 font-medium align-top ${
                          String(v).includes('⚠') ? 'text-amber-400' :
                          String(v) === 'true'    ? 'text-red-400'   :
                          String(v) === 'false'   ? 'text-green-400' : 'text-white'
                        }`}>
                          {Array.isArray(v) ? (v.length ? v.join(', ') : '—') : String(v||'—')}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>

              {/* Breach list */}
              {r.source_name === 'breach_intelligence' && r.parsed_data?.relevant_breaches?.length > 0 && (
                <div className="px-4 pb-4">
                  <div className="text-xs text-gray-500 mb-2 mt-1">Recent relevant breaches</div>
                  <div className="space-y-2">
                    {r.parsed_data.relevant_breaches.map((b: any, j: number) => (
                      <div key={j} className="flex items-center gap-3 p-2 bg-gray-800 rounded-lg text-xs">
                        <i className="ti ti-database-leak text-red-400" />
                        <span className="text-white font-medium">{b.name}</span>
                        <span className="text-gray-500">{b.date}</span>
                        <span className="text-amber-400 ml-auto">{b.records} records</span>
                        <span className="badge badge-red">{b.type.replace(/_/g,' ')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {r.source_name === 'breach_intelligence' && r.parsed_data?.recommendations?.length > 0 && (
                <div className="px-4 pb-4 border-t border-gray-800 pt-3">
                  <div className="text-xs text-gray-500 mb-2">Recommended actions</div>
                  {r.parsed_data.recommendations.map((rec: string, j: number) => (
                    <div key={j} className="flex items-center gap-2 text-xs text-gray-300 py-1">
                      <i className="ti ti-arrow-right text-indigo-400 flex-shrink-0" />{rec}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}

          <button onClick={() => { setResult(null); setQuery('') }} className="btn-secondary">
            <i className="ti ti-refresh" />New scan
          </button>
        </>
      )}
    </div>
  )
}
