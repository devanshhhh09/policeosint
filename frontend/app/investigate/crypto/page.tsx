'use client'
import CryptoAtomGraph from '@/components/crypto/CryptoAtomGraph'
import { useState, useEffect } from 'react'
import { investigateAPI } from '@/lib/api'

const SEV: Record<string, string> = {
  CRITICAL:'text-red-400', HIGH:'text-orange-400', MEDIUM:'text-amber-400', LOW:'text-green-400'
}

export default function CryptoPage() {
  const [chain, setChain]     = useState('auto')
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
        investigation_type: 'crypto', query: query.trim(), query_type: chain,
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
    }, 2000)
    return () => clearInterval(t)
  }, [invId])

  const [showGraph, setShowGraph]   = useState(false)
  const [graphCenter, setGraphCenter] = useState('')
  const risk = result?.risk_score ?? 0

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-amber-950 flex items-center justify-center">
          <i className="ti ti-currency-bitcoin text-amber-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Crypto Intelligence</h1>
          <p className="text-gray-500 text-sm">Wallet tracing · Mixer detection · Exchange identification · VASP requests</p>
        </div>
      </div>

      <div className="card p-4 mb-5">
        <div className="flex gap-3 flex-wrap">
          <select value={chain} onChange={e => setChain(e.target.value)} className="select-field w-36">
            <option value="auto">Auto-detect</option>
            <option value="bitcoin">Bitcoin (BTC)</option>
            <option value="ethereum">Ethereum (ETH)</option>
            <option value="tron">Tron (TRX)</option>
            <option value="polygon">Polygon (MATIC)</option>
          </select>
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder="Wallet address or transaction hash"
            className="input-field flex-1 min-w-48" />
          <button onClick={run} disabled={!query.trim() || loading} className="btn-primary px-6">
            {loading ? <><span className="spinner w-4 h-4" />Tracing…</> : <><i className="ti ti-search" />Trace wallet</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
        <p className="text-xs text-gray-600 mt-2 flex items-center gap-1">
          <i className="ti ti-info-circle" />
          Supports BTC (1…/3…/bc1…), ETH (0x…), TRX (T…). Auto-detect identifies chain automatically.
        </p>
      </div>

      {loading && (
        <div className="card p-8 text-center space-y-3">
          <span className="spinner w-8 h-8 block mx-auto" />
          <p className="text-gray-400 text-sm">Tracing blockchain · Checking mixer patterns…</p>
        </div>
      )}

      {result && !loading && (
        <>
          {/* Risk bar */}
          <div className="card p-4 mb-4 flex items-center gap-4">
            <div>
              <div className="text-xs text-gray-500 mb-1">Risk score</div>
              <span className={`text-2xl font-bold ${risk>=70?'text-red-400':risk>=40?'text-amber-400':'text-green-400'}`}>
                {risk}/100
              </span>
            </div>
            <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full rounded-full"
                style={{width:`${risk}%`, background:risk>=70?'#EF4444':risk>=40?'#F59E0B':'#10B981'}} />
            </div>
            <div className="text-xs text-gray-500 text-right">
              <div>{result.summary}</div>
            </div>
          </div>

          {/* 3D Graph toggle */}
          <div className="flex gap-3 mb-4">
            <button onClick={() => { setShowGraph(!showGraph); setGraphCenter(query.trim()) }}
              className={showGraph ? 'btn-primary px-4' : 'btn-secondary px-4'}>
              <i className={`ti ${showGraph ? 'ti-atom-2' : 'ti-atom'} mr-2`} />
              {showGraph ? 'Hide 3D graph' : 'Show 3D atom graph'}
            </button>
          </div>

          {/* 3D Atom Graph */}
          {showGraph && (
            <div className="card overflow-hidden mb-4">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                <i className="ti ti-atom-2 text-blue-400" />
                <span className="text-sm font-semibold text-white">
                  3D Money Flow — {graphCenter.slice(0,16)}…
                </span>
                <span className="text-xs text-gray-500 ml-auto">
                  Drag to rotate · Click any node to inspect
                </span>
              </div>
              <CryptoAtomGraph
                data={result}
                address={graphCenter}
                onRecenter={(addr) => {
                  setQuery(addr)
                  setShowGraph(false)
                  setTimeout(() => run(), 100)
                }}
              />
            </div>
          )}

          {/* Mixer alert */}
          {result.results?.find((r:any)=>r.source_name==='mixer_analysis')?.parsed_data?.mixer_score > 50 && (
            <div className="card p-4 mb-4 border-red-900 bg-red-950/20">
              <div className="flex items-center gap-3">
                <i className="ti ti-alert-triangle text-red-400 text-xl" />
                <div>
                  <div className="text-sm font-semibold text-red-300">
                    Mixer / Tumbler detected — {result.results.find((r:any)=>r.source_name==='mixer_analysis').parsed_data.mixing_confidence} confidence
                  </div>
                  <div className="text-xs text-red-400/70 mt-0.5">
                    Funds may have passed through cryptocurrency mixing service to obscure trail
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Source cards */}
          {result.results?.map((r: any, i: number) => (
            <div key={i} className="card overflow-hidden mb-4">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
                <i className={`ti ${
                  r.source_name==='blockchair'     ?'ti-currency-bitcoin':
                  r.source_name==='etherscan'      ?'ti-currency-ethereum':
                  r.source_name==='mixer_analysis' ?'ti-arrows-shuffle':
                  r.source_name==='cluster_analysis'?'ti-git-branch':'ti-database'
                } text-amber-400 text-lg`} />
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
                  {Object.entries(r.parsed_data||{})
                    .filter(([k])=>!['name','severity','recent_txs','vasp_request_india',
                                     'patterns_detected','known_mixers'].includes(k))
                    .map(([k,v],j)=>(
                      <tr key={j} className="border-b border-gray-800/50 last:border-0">
                        <td className="px-4 py-2.5 text-gray-500 w-44 capitalize align-top">{k.replace(/_/g,' ')}</td>
                        <td className={`px-4 py-2.5 font-medium align-top break-all ${
                          String(v).includes('⚠')||String(v==='true') ? 'text-red-400' :
                          String(v)==='false' ? 'text-green-400' : 'text-white'
                        }`}>
                          {typeof v==='string'&&v.startsWith('http')
                            ? <a href={v} target="_blank" rel="noopener noreferrer"
                                className="text-blue-400 hover:underline">{v.slice(0,50)}</a>
                            : Array.isArray(v)?(v.length?v.join(', '):'—'):String(v||'—')}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>

              {/* Patterns detected */}
              {r.source_name==='mixer_analysis' && r.parsed_data?.patterns_detected?.length>0 && (
                <div className="px-4 pb-3 pt-1 border-t border-gray-800">
                  <div className="text-xs text-gray-500 mb-1">Patterns detected</div>
                  {r.parsed_data.patterns_detected.map((p:string,j:number)=>(
                    <div key={j} className="flex items-center gap-2 text-xs text-amber-300 py-0.5">
                      <i className="ti ti-arrow-right text-amber-400" />{p}
                    </div>
                  ))}
                </div>
              )}

              {/* Recent transactions */}
              {r.source_name!=='mixer_analysis' && r.parsed_data?.recent_txs?.length>0 && (
                <div className="px-4 pb-3 pt-1 border-t border-gray-800">
                  <div className="text-xs text-gray-500 mb-2">Recent transactions</div>
                  {r.parsed_data.recent_txs.slice(0,3).map((tx:any,j:number)=>(
                    <div key={j} className="flex items-center gap-3 text-xs py-1 border-b border-gray-800/30 last:border-0">
                      <span className="font-mono text-gray-500">{String(tx).slice(0,16)}…</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}

          {/* Indian VASP contacts */}
          {result.results?.[0]?.parsed_data && (
            <div className="card p-4">
              <div className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <i className="ti ti-building-bank text-blue-400" />Indian VASP LEA Contacts
              </div>
              <div className="grid grid-cols-2 gap-2">
                {(result.results?.find((_:any)=>true)?.parsed_data?.vasp_request_india ||
                  [{name:'WazirX',leo_contact:'legal@wazirx.com'},
                   {name:'CoinDCX',leo_contact:'legal@coindcx.com'},
                   {name:'ZebPay',leo_contact:'legal@zebpay.com'},
                   {name:'CoinSwitch',leo_contact:'legal@coinswitch.co'}])
                  .map((v:any, i:number) => (
                  <div key={i} className="p-3 bg-gray-800 rounded-lg text-xs">
                    <div className="font-medium text-white">{v.name}</div>
                    <div className="text-gray-500 mt-0.5">{v.leo_contact}</div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-600 mt-3">
                Issue LEA notice u/s 91 CrPC to relevant VASP for transaction records
              </p>
            </div>
          )}

          <div className="flex gap-3 mt-4">
            <button onClick={() => { setResult(null); setQuery('') }} className="btn-secondary">
              <i className="ti ti-refresh" />New trace
            </button>
            <button className="btn-secondary">
              <i className="ti ti-file-report" />Generate report
            </button>
          </div>
        </>
      )}
    </div>
  )
}
