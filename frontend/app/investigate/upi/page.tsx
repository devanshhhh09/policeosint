'use client'
import { useState, useEffect } from 'react'
import { investigateAPI } from '@/lib/api'

export default function UPIPage() {
  const [qtype, setQtype]     = useState('upi_id')
  const [query, setQuery]     = useState('')
  const [loading, setLoading] = useState(false)
  const [invId, setInvId]     = useState('')
  const [result, setResult]   = useState<any>(null)
  const [error, setError]     = useState('')

  const run = async () => {
    if (!query.trim()) return
    setLoading(true); setResult(null); setError('')
    try {
      const res = await investigateAPI.start({ investigation_type: 'upi_fraud', query: query.trim(), query_type: qtype })
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
    <div className="p-6 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-red-950 flex items-center justify-center">
          <i className="ti ti-qrcode text-red-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">UPI Fraud Investigation</h1>
          <p className="text-gray-500 text-sm">Risk scoring · Fraud patterns · Mule detection</p>
        </div>
      </div>

      <div className="card p-4 mb-5">
        <div className="flex gap-3 flex-wrap">
          <select value={qtype} onChange={e => setQtype(e.target.value)} className="select-field w-40">
            <option value="upi_id">UPI ID</option>
            <option value="phone">Phone number</option>
            <option value="qr_data">QR code data</option>
            <option value="merchant_id">Merchant ID</option>
          </select>
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder={qtype === 'upi_id' ? 'suspect@paytm' : qtype === 'phone' ? '+919876543210' : 'upi://pay?pa=...'}
            className="input-field flex-1 min-w-48" />
          <button onClick={run} disabled={!query.trim() || loading} className="btn-primary px-6">
            {loading ? <><span className="spinner w-4 h-4" />Investigating…</> : <><i className="ti ti-search" />Investigate</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      </div>

      {loading && (
        <div className="card p-8 text-center space-y-3">
          <span className="spinner w-8 h-8 block mx-auto" />
          <p className="text-gray-400 text-sm">Analysing UPI ID · Fraud patterns · Mule detection…</p>
        </div>
      )}

      {result && !loading && (
        <>
          {/* Risk */}
          <div className="card p-4 mb-4">
            <div className="flex items-center gap-4 mb-3">
              <div>
                <div className="text-xs text-gray-500 mb-1">Fraud risk score</div>
                <span className={`text-3xl font-bold ${risk>=70?'text-red-400':risk>=40?'text-amber-400':'text-green-400'}`}>
                  {risk}/100
                </span>
              </div>
              <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-700"
                  style={{ width:`${risk}%`, background: risk>=70?'#EF4444':risk>=40?'#F59E0B':'#10B981' }} />
              </div>
            </div>

            {/* IPC sections */}
            {result.results?.find((r:any) => r.source_name === 'fraud_patterns')?.parsed_data?.matches?.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-800">
                <div className="text-xs text-gray-500 mb-2">Fraud patterns detected</div>
                <div className="flex flex-wrap gap-2">
                  {result.results.find((r:any) => r.source_name === 'fraud_patterns')
                    .parsed_data.matches.map((m: any) => (
                    <span key={m.pattern_id} className="badge badge-red">{m.label}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Source cards */}
          {result.results?.map((r: any, i: number) => (
            <div key={i} className="card overflow-hidden mb-4">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
                <i className={`ti ${
                  r.source_name === 'upi_analysis'   ? 'ti-qrcode' :
                  r.source_name === 'fraud_patterns' ? 'ti-alert-triangle' :
                  r.source_name === 'mule_detection' ? 'ti-users' : 'ti-database'
                } text-red-400 text-lg`} />
                <span className="text-sm font-semibold text-white flex-1 capitalize">
                  {r.source_name.replace(/_/g,' ')}
                </span>
                {r.is_suspicious && <span className="badge badge-red text-xs">Suspicious</span>}
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(r.parsed_data || {})
                    .filter(([k]) => !['name','severity','matches','status'].includes(k))
                    .map(([k, v], j) => (
                      <tr key={j} className="border-b border-gray-800/50 last:border-0">
                        <td className="px-4 py-2.5 text-gray-500 w-44 capitalize align-top">{k.replace(/_/g,' ')}</td>
                        <td className={`px-4 py-2.5 font-medium align-top ${
                          String(v) === 'true' || String(v).includes('⚠') || String(v).includes('CRIT') ? 'text-red-400' :
                          String(v) === 'false' ? 'text-green-400' : 'text-white'
                        }`}>
                          {Array.isArray(v) ? (v.length ? v.join(' · ') : '—') : String(v||'—')}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ))}

          {/* Recommended actions */}
          {result.results?.find((r:any) => r.source_name === 'mule_detection') && (
            <div className="card p-4 mb-4 border-amber-900">
              <div className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                <i className="ti ti-list-check" />Recommended actions
              </div>
              <ul className="space-y-1.5">
                {['Flag UPI ID with PSP','Request transaction logs from bank','File on Cybercrime.gov.in',
                  'Issue notice u/s 91 CrPC to bank','Collect CDR from telecom provider'].map((a,i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                    <i className="ti ti-arrow-right text-amber-400 mt-0.5 flex-shrink-0" />{a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-3">
            <button onClick={() => { setResult(null); setQuery('') }} className="btn-secondary">
              <i className="ti ti-refresh" />New investigation
            </button>
            <button className="btn-secondary"><i className="ti ti-file-report" />Generate report</button>
          </div>
        </>
      )}
    </div>
  )
}
