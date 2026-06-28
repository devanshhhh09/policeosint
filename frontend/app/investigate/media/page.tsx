'use client'
import { useState, useEffect } from 'react'
import { investigateAPI } from '@/lib/api'

export default function MediaPage() {
  const [qtype, setQtype]     = useState('image_url')
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
        investigation_type: 'media', query: query.trim(), query_type: qtype,
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

  const deepfake = result?.results?.find((r:any) => r.source_name === 'deepfake_analysis')?.parsed_data

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-purple-950 flex items-center justify-center">
          <i className="ti ti-photo-scan text-purple-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Media Forensics</h1>
          <p className="text-gray-500 text-sm">EXIF extraction · Reverse image search · Deepfake detection</p>
        </div>
      </div>

      <div className="card p-4 mb-5">
        <div className="flex gap-3 flex-wrap">
          <select value={qtype} onChange={e => setQtype(e.target.value)} className="select-field w-40">
            <option value="image_url">Image URL</option>
            <option value="video_url">Video URL</option>
            <option value="image_hash">File hash</option>
          </select>
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder={
              qtype === 'image_url'  ? 'https://example.com/photo.jpg' :
              qtype === 'video_url'  ? 'https://youtube.com/watch?v=...' :
                                       'SHA256 or MD5 hash of file'
            }
            className="input-field flex-1 min-w-48" />
          <button onClick={run} disabled={!query.trim() || loading} className="btn-primary px-6">
            {loading ? <><span className="spinner w-4 h-4" />Analysing…</> : <><i className="ti ti-search" />Analyse</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
        <p className="text-xs text-gray-600 mt-2 flex items-center gap-1">
          <i className="ti ti-info-circle" />
          For EXIF extraction from uploaded files — use the evidence upload in Case Management
        </p>
      </div>

      {loading && (
        <div className="card p-8 text-center space-y-3">
          <span className="spinner w-8 h-8 block mx-auto" />
          <p className="text-gray-400 text-sm">Analysing media · Checking for manipulation…</p>
        </div>
      )}

      {result && !loading && (
        <>
          {/* Deepfake score */}
          {deepfake && (
            <div className="card p-5 mb-4">
              <div className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                <i className="ti ti-eye text-purple-400" />Deepfake / Manipulation Analysis
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="text-center p-4 bg-gray-800 rounded-xl">
                  <div className="text-xs text-gray-500 mb-1">Authenticity</div>
                  <div className="text-3xl font-bold text-green-400">{deepfake.authenticity_score}%</div>
                </div>
                <div className="text-center p-4 bg-gray-800 rounded-xl">
                  <div className="text-xs text-gray-500 mb-1">Manipulation risk</div>
                  <div className={`text-3xl font-bold ${
                    deepfake.manipulation_score > 30 ? 'text-red-400' :
                    deepfake.manipulation_score > 15 ? 'text-amber-400' : 'text-green-400'
                  }`}>{deepfake.manipulation_score}%</div>
                </div>
              </div>
              {deepfake.flags?.length > 0 && (
                <div>
                  <div className="text-xs text-gray-500 mb-2">Flags detected</div>
                  {deepfake.flags.map((f: string, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-amber-300 py-1">
                      <i className="ti ti-alert-triangle text-amber-400 flex-shrink-0" />{f}
                    </div>
                  ))}
                </div>
              )}
              <p className="text-xs text-gray-600 mt-3">{deepfake.note}</p>
            </div>
          )}

          {/* Reverse search links */}
          {result.results?.find((r:any) => r.source_name === 'reverse_search') && (
            <div className="card p-4 mb-4">
              <div className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <i className="ti ti-photo-search text-purple-400" />Reverse Image Search
              </div>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(
                  result.results.find((r:any) => r.source_name === 'reverse_search')
                    .parsed_data.search_engines || {}
                ).map(([engine, url]: any) => (
                  <a key={engine} href={url} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-2 p-3 bg-gray-800 hover:bg-gray-700
                               rounded-lg text-sm text-gray-300 hover:text-white transition-colors">
                    <i className="ti ti-external-link text-purple-400 flex-shrink-0" />{engine}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Other source cards */}
          {result.results?.filter((r:any) => !['deepfake_analysis','reverse_search'].includes(r.source_name))
            .map((r: any, i: number) => (
            <div key={i} className="card overflow-hidden mb-4">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
                <i className="ti ti-photo text-purple-400 text-lg" />
                <span className="text-sm font-semibold text-white flex-1 capitalize">
                  {r.source_name.replace(/_/g,' ')}
                </span>
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(r.parsed_data || {})
                    .filter(([k]) => !['name','severity','search_engines'].includes(k))
                    .map(([k, v], j) => (
                      <tr key={j} className="border-b border-gray-800/50 last:border-0">
                        <td className="px-4 py-2.5 text-gray-500 w-40 capitalize align-top">{k.replace(/_/g,' ')}</td>
                        <td className="px-4 py-2.5 text-white font-medium align-top break-all">
                          {typeof v === 'string' && v.startsWith('http')
                            ? <a href={v} target="_blank" rel="noopener noreferrer"
                                className="text-blue-400 hover:underline">{v.slice(0,50)}…</a>
                            : Array.isArray(v) ? (v.length ? v.join(', ') : '—') : String(v||'—')}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ))}

          <button onClick={() => { setResult(null); setQuery('') }} className="btn-secondary">
            <i className="ti ti-refresh" />New analysis
          </button>
        </>
      )}
    </div>
  )
}
