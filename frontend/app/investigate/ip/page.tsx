'use client'
import { useState, useEffect } from 'react'
import { investigateAPI } from '@/lib/api'

const SEVERITY_CLS: Record<string, string> = {
  CRITICAL: 'text-red-400', HIGH: 'text-orange-400',
  MEDIUM: 'text-amber-400', LOW: 'text-green-400',
}

export default function IPPage() {
  const [query, setQuery]     = useState('')
  const [loading, setLoading] = useState(false)
  const [invId, setInvId]     = useState('')
  const [result, setResult]   = useState<any>(null)
  const [error, setError]     = useState('')

  const run = async () => {
    if (!query.trim()) return
    setLoading(true); setResult(null); setError('')
    try {
      const res = await investigateAPI.start({ investigation_type: 'ip', query: query.trim(), query_type: 'ipv4' })
      setInvId(res.data.id)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed'); setLoading(false)
    }
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
    <div className="p-6 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-green-950 flex items-center justify-center">
          <i className="ti ti-server text-green-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">IP Intelligence</h1>
          <p className="text-gray-500 text-sm">GeoIP · Shodan · VirusTotal · ASN lookup</p>
        </div>
      </div>

      <div className="card p-4 mb-5">
        <div className="flex gap-3">
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder="IP address e.g. 45.33.32.156"
            className="input-field flex-1" />
          <button onClick={run} disabled={!query.trim() || loading} className="btn-primary px-6">
            {loading ? <><span className="spinner w-4 h-4" />Investigating…</> : <><i className="ti ti-search" />Investigate</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      </div>

      {loading && (
        <div className="card p-8 text-center space-y-3">
          <span className="spinner w-8 h-8 block mx-auto" />
          <p className="text-gray-400 text-sm">Querying IPinfo · Shodan · VirusTotal…</p>
        </div>
      )}

      {result && !loading && (
        <>
          <div className="card p-4 mb-4 flex items-center gap-4">
            <div>
              <div className="text-xs text-gray-500 mb-1">Risk score</div>
              <span className={`text-2xl font-bold ${risk>=70?'text-red-400':risk>=40?'text-amber-400':'text-green-400'}`}>
                {risk}/100
              </span>
            </div>
            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full rounded-full"
                style={{ width:`${risk}%`, background: risk>=70?'#EF4444':risk>=40?'#F59E0B':'#10B981' }} />
            </div>
            <div className="text-xs text-gray-500 text-right">
              <div>{result.sources_queried?.length || 0} sources queried</div>
              <div className="text-gray-600 mt-0.5 max-w-48 truncate">{result.summary}</div>
            </div>
          </div>

          {result.results?.map((r: any, i: number) => (
            <div key={i} className="card overflow-hidden mb-4">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
                <i className={`ti ti-${r.source_name === 'shodan' ? 'server' : r.source_name === 'virustotal' ? 'shield' : 'map-pin'} text-blue-400 text-lg`} />
                <span className="text-sm font-semibold text-white flex-1 capitalize">
                  {r.source_name.replace(/_/g,' ')}
                </span>
                {r.parsed_data?.severity && (
                  <span className={`text-xs font-bold ${SEVERITY_CLS[r.parsed_data.severity]||'text-gray-400'}`}>
                    {r.parsed_data.severity}
                  </span>
                )}
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(r.parsed_data || {})
                    .filter(([k]) => !['name','severity','status'].includes(k))
                    .map(([k, v], j) => (
                      <tr key={j} className="border-b border-gray-800/50 last:border-0">
                        <td className="px-4 py-2.5 text-gray-500 w-40 capitalize align-top">{k.replace(/_/g,' ')}</td>
                        <td className={`px-4 py-2.5 font-medium align-top ${
                          String(v).includes('⚠')||String(v).includes('CRIT')||String(v).includes('HIGH') ? 'text-red-400' :
                          String(v) === 'true' ? 'text-red-400' :
                          String(v) === 'false' ? 'text-green-400' : 'text-white'
                        }`}>
                          {Array.isArray(v) ? (v.length ? v.join(', ') : '—') : String(v||'—')}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ))}

          <div className="flex gap-3">
            <button onClick={() => { setResult(null); setQuery('') }} className="btn-secondary">
              <i className="ti ti-refresh" />New investigation
            </button>
            <button className="btn-secondary"><i className="ti ti-folder-plus" />Save to case</button>
          </div>
        </>
      )}
    </div>
  )
}
