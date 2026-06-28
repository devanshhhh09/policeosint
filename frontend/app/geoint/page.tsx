'use client'
import { useState, useEffect } from 'react'
import { investigateAPI } from '@/lib/api'

export default function GeointPage() {
  const [qtype, setQtype]     = useState('coordinates')
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
        investigation_type: 'geoint', query: query.trim(), query_type: qtype,
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

  const QUICK = [
    { label: 'New Delhi',   query: '28.6139, 77.2090', type: 'coordinates' },
    { label: 'Gurugram',    query: '28.4595, 77.0266', type: 'coordinates' },
    { label: 'Mumbai',      query: '19.0760, 72.8777', type: 'coordinates' },
    { label: 'Bengaluru',   query: '12.9716, 77.5946', type: 'coordinates' },
  ]

  const geocodeData  = result?.results?.find((r:any) => r.source_name === 'reverse_geocode')?.parsed_data
  const intelData    = result?.results?.find((r:any) => r.source_name === 'location_intel')?.parsed_data
  const lat = geocodeData?.latitude || intelData?.latitude
  const lon = geocodeData?.longitude || intelData?.longitude

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-emerald-950 flex items-center justify-center">
          <i className="ti ti-map-pin text-emerald-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">GEOINT — Location Intelligence</h1>
          <p className="text-gray-500 text-sm">Reverse geocoding · IP location · Satellite · Sun angle</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {QUICK.map(q => (
          <button key={q.label} onClick={() => { setQuery(q.query); setQtype(q.type) }}
            className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border
                       border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors">
            <i className="ti ti-map-pin mr-1 text-emerald-400" />{q.label}
          </button>
        ))}
      </div>

      <div className="card p-4 mb-5">
        <div className="flex gap-3 flex-wrap">
          <select value={qtype} onChange={e => setQtype(e.target.value)} className="select-field w-40">
            <option value="coordinates">GPS coordinates</option>
            <option value="ip_location">IP address</option>
            <option value="address">Street address</option>
            <option value="image_url">Image URL</option>
          </select>
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && run()}
            placeholder={
              qtype === 'coordinates' ? '28.6139, 77.2090' :
              qtype === 'ip_location' ? '103.21.244.0' :
              qtype === 'address'     ? 'Sector 14, Gurugram, Haryana' : 'https://image-url.com/photo.jpg'
            }
            className="input-field flex-1 min-w-48" />
          <button onClick={run} disabled={!query.trim() || loading} className="btn-primary px-6">
            {loading ? <><span className="spinner w-4 h-4" />Locating…</> : <><i className="ti ti-map-pin" />Geolocate</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      </div>

      {loading && (
        <div className="card p-8 text-center space-y-3">
          <span className="spinner w-8 h-8 block mx-auto" />
          <p className="text-gray-400 text-sm">Querying OpenStreetMap Nominatim · IPinfo…</p>
        </div>
      )}

      {result && !loading && (
        <>
          {/* Map links */}
          {lat && lon && (
            <div className="card p-4 mb-4">
              <div className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                <i className="ti ti-map text-emerald-400" />Location found — open in map
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {[
                  { label: 'Google Maps',      url: `https://maps.google.com/maps?q=${lat},${lon}`, icon: 'ti-map' },
                  { label: 'Satellite view',   url: `https://maps.google.com/maps?q=${lat},${lon}&t=k`, icon: 'ti-satellite' },
                  { label: 'Street view',      url: `https://www.google.com/maps/@${lat},${lon},3a,75y,90t/data=!3m1!1e3`, icon: 'ti-street-view' },
                  { label: 'OpenStreetMap',    url: `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}&zoom=15`, icon: 'ti-world' },
                ].map(m => (
                  <a key={m.label} href={m.url} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-2 p-3 bg-gray-800 hover:bg-gray-700
                               rounded-lg text-xs text-gray-300 hover:text-white transition-colors">
                    <i className={`ti ${m.icon} text-emerald-400`} />{m.label}
                  </a>
                ))}
              </div>

              {/* Embedded map preview */}
              <div className="mt-3 rounded-lg overflow-hidden border border-gray-700" style={{height:200}}>
                <iframe
                  src={`https://www.openstreetmap.org/export/embed.html?bbox=${lon-0.02},${lat-0.02},${lon+0.02},${lat+0.02}&layer=mapnik&marker=${lat},${lon}`}
                  width="100%" height="200" style={{border:0}}
                  title="Location map"
                />
              </div>
            </div>
          )}

          {/* Result cards */}
          {result.results?.map((r: any, i: number) => (
            <div key={i} className="card overflow-hidden mb-4">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
                <i className="ti ti-map-pin text-emerald-400 text-lg" />
                <span className="text-sm font-semibold text-white flex-1 capitalize">
                  {r.source_name.replace(/_/g,' ')}
                </span>
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(r.parsed_data || {})
                    .filter(([k]) => !['name','severity','search_links'].includes(k))
                    .map(([k, v], j) => (
                      <tr key={j} className="border-b border-gray-800/50 last:border-0">
                        <td className="px-4 py-2.5 text-gray-500 w-44 capitalize align-top">{k.replace(/_/g,' ')}</td>
                        <td className="px-4 py-2.5 font-medium align-top text-white break-all">
                          {typeof v === 'string' && v.startsWith('http')
                            ? <a href={v} target="_blank" rel="noopener noreferrer"
                                className="text-blue-400 hover:text-blue-300 underline">{v.slice(0,60)}…</a>
                            : Array.isArray(v) ? (v.length ? v.join(', ') : '—') : String(v||'—')}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          ))}

          <button onClick={() => { setResult(null); setQuery('') }} className="btn-secondary">
            <i className="ti ti-refresh" />New location
          </button>
        </>
      )}
    </div>
  )
}
