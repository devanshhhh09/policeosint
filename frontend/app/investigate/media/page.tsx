'use client'
import { useState, useRef } from 'react'
import { api } from '@/lib/api'

const RISK_COLOR = (r: number) =>
  r >= 60 ? 'text-red-400' : r >= 30 ? 'text-amber-400' : 'text-green-400'
const RISK_BORDER = (r: number) =>
  r >= 60 ? 'border-red-900 bg-red-950/10' :
  r >= 30 ? 'border-amber-900 bg-amber-950/10' : 'border-gray-800'

type Mode = 'upload' | 'url'

export default function MediaForensicsPage() {
  const fileRef = useRef<HTMLInputElement>(null)

  /* upload state */
  const [mode, setMode]         = useState<Mode>('upload')
  const [file, setFile]         = useState<File | null>(null)
  const [preview, setPreview]   = useState<string | null>(null)

  /* url state */
  const [mediaUrl, setMediaUrl] = useState('')

  /* shared */
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState<any>(null)
  const [urlResult, setUrlResult] = useState<any>(null)
  const [error, setError]       = useState('')
  const [activeTab, setActiveTab] = useState<'overview'|'exif'|'gps'|'hashes'|'manipulation'|'headers'|'reverse_search'>('overview')

  /* ── File upload handler ─────────────────────────────────────────────────── */
  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f); setResult(null); setUrlResult(null); setError('')
    const reader = new FileReader()
    reader.onload = ev => setPreview(ev.target?.result as string)
    reader.readAsDataURL(f)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (!f) return
    setFile(f); setResult(null); setError('')
    const reader = new FileReader()
    reader.onload = ev => setPreview(ev.target?.result as string)
    reader.readAsDataURL(f)
  }

  const analyzeFile = async () => {
    if (!file) return
    setLoading(true); setResult(null); setUrlResult(null); setError('')
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await api.post('/media-forensics/analyze', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000,
      })
      setResult(res.data)
      setActiveTab('overview')
    } catch (e: any) {
      setError(e.response?.data?.error || e.response?.data?.detail || 'Analysis failed')
    } finally { setLoading(false) }
  }

  /* ── URL analysis handler ────────────────────────────────────────────────── */
  const analyzeUrl = async () => {
    if (!mediaUrl.trim()) return
    setLoading(true); setResult(null); setUrlResult(null); setError('')
    try {
      const res = await api.post('/media-forensics/analyze-url', { url: mediaUrl.trim() })
      setUrlResult(res.data)
      // If image was downloaded and analyzed, merge into result
      if (res.data.image_analysis && !res.data.image_analysis.error) {
        setResult(res.data.image_analysis)
      }
      setActiveTab('overview')
    } catch (e: any) {
      setError(e.response?.data?.error || e.response?.data?.detail || 'URL analysis failed')
    } finally { setLoading(false) }
  }

  const combined = urlResult || result
  const risk     = combined?.risk_score ?? result?.risk_score ?? 0

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-purple-950 flex items-center justify-center">
          <i className="ti ti-photo-scan text-purple-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Media Forensics</h1>
          <p className="text-gray-500 text-sm">
            Upload image / paste URL → EXIF · GPS location · Device info · Manipulation detection · Reverse search
          </p>
        </div>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1 p-1 bg-gray-900 rounded-xl border border-gray-800 w-fit mb-5">
        {([
          { id:'upload', label:'Upload file',   icon:'ti-upload'   },
          { id:'url',    label:'Paste URL',      icon:'ti-link'     },
        ] as const).map(m => (
          <button key={m.id} onClick={() => { setMode(m.id); setResult(null); setUrlResult(null); setError('') }}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              mode===m.id
                ? 'bg-purple-600 text-white'
                : 'text-gray-400 hover:text-white'
            }`}>
            <i className={`ti ${m.icon}`} />{m.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
        {/* Input panel */}
        <div className="lg:col-span-1 space-y-3">

          {/* Upload mode */}
          {mode === 'upload' && (
            <>
              <div
                onDrop={handleDrop}
                onDragOver={e => e.preventDefault()}
                onClick={() => fileRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer
                            transition-all min-h-48 flex flex-col items-center justify-center ${
                  file ? 'border-purple-700 bg-purple-950/20' : 'border-gray-700 hover:border-gray-600 bg-gray-900'
                }`}>
                {preview ? (
                  <img src={preview} alt="Preview"
                    className="max-h-48 max-w-full rounded-xl object-contain mb-3" />
                ) : (
                  <>
                    <i className="ti ti-cloud-upload text-4xl text-gray-500 mb-3" />
                    <p className="text-gray-400 font-medium">Drop image here</p>
                    <p className="text-gray-600 text-xs mt-1">or click to browse</p>
                    <p className="text-gray-700 text-xs mt-2">JPEG · PNG · WEBP · GIF · BMP</p>
      
              {/* ── Reverse Search ── */}
              {activeTab === ('reverse_search' as typeof activeTab) && (
                <ReverseSearchPanel file={file} mode={mode} mediaUrl={mediaUrl} token="" />
              )}
            </>
                )}
                <input ref={fileRef} type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp,image/bmp"
                  className="hidden" onChange={handleFile} />
              </div>

              {file && (
                <div className="card p-3 text-xs">
                  <div className="text-gray-500 mb-1">Selected file</div>
                  <div className="text-white font-medium truncate">{file.name}</div>
                  <div className="text-gray-500 mt-0.5">{(file.size/1024).toFixed(1)} KB · {file.type}</div>
                </div>
              )}

              <button onClick={analyzeFile} disabled={!file || loading}
                className="btn-primary w-full justify-center py-3">
                {loading ? <><span className="spinner w-4 h-4" />Analyzing…</> : <><i className="ti ti-scan" />Analyze image</>}
              </button>
            </>
          )}

          {/* URL mode */}
          {mode === 'url' && (
            <>
              <div className="card p-4">
                <label className="text-xs text-gray-400 mb-2 block font-medium">
                  Image or video URL
                </label>
                <textarea
                  value={mediaUrl}
                  onChange={e => setMediaUrl(e.target.value)}
                  rows={4}
                  placeholder="https://example.com/photo.jpg&#10;https://t.me/channel/123&#10;https://i.imgur.com/abc.png"
                  className="input-field w-full resize-none text-sm font-mono"
                />
                <p className="text-xs text-gray-600 mt-2">
                  Supports direct image/video URLs from any public source
                </p>
              </div>

              {/* Quick paste examples */}
              <div className="card p-3">
                <div className="text-xs text-gray-500 mb-2">Common sources</div>
                <div className="flex flex-wrap gap-1">
                  {['Telegram','WhatsApp CDN','Instagram CDN','Twitter','Imgur','Terabox'].map(p => (
                    <span key={p} className="text-[10px] px-2 py-1 bg-gray-800 rounded text-gray-400">{p}</span>
                  ))}
                </div>
              </div>

              <button onClick={analyzeUrl} disabled={!mediaUrl.trim() || loading}
                className="btn-primary w-full justify-center py-3">
                {loading ? <><span className="spinner w-4 h-4" />Fetching & analyzing…</> : <><i className="ti ti-link" />Analyze URL</>}
              </button>

              {/* What we extract from URLs */}
              <div className="card p-3 text-xs space-y-1.5">
                <div className="text-gray-500 font-medium mb-2">Extracted from URL:</div>
                {[
                  ['ti-server',     'Hosting platform & CDN'],
                  ['ti-arrows-right','Redirect chain'],
                  ['ti-map-pin',    'GPS (if image with EXIF)'],
                  ['ti-camera',     'Device info (if EXIF)'],
                  ['ti-clock',      'Last modified date'],
                  ['ti-alert-triangle','Terabox/risk flags'],
                ].map(([icon, label]) => (
                  <div key={label} className="flex items-center gap-2 text-gray-500">
                    <i className={`ti ${icon} text-purple-400 text-xs`} />
                    {label}
                  </div>
                ))}
              </div>
            </>
          )}

          {/* Clear button */}
          {(result || urlResult) && (
            <button onClick={() => { setFile(null); setPreview(null); setResult(null); setUrlResult(null); setMediaUrl('') }}
              className="btn-secondary w-full justify-center text-xs">
              <i className="ti ti-x" />Clear results
            </button>
          )}

          {error && (
            <div className="p-3 bg-red-950/30 border border-red-900 rounded-xl text-red-400 text-sm">
              <i className="ti ti-alert-circle mr-2" />{error}
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="lg:col-span-2">
          {!combined && !loading && (
            <div className="card h-full flex flex-col items-center justify-center text-gray-500 min-h-64 p-8">
              <i className="ti ti-photo-scan text-5xl mb-4 opacity-20" />
              <p className="font-medium text-white mb-1">
                {mode === 'upload' ? 'Upload an image to analyze' : 'Paste a URL to analyze'}
              </p>
              <p className="text-sm text-center max-w-xs">
                {mode === 'upload'
                  ? 'Extract GPS coordinates, camera details, timestamps, and detect manipulation'
                  : 'Fetch any public image or video URL and extract all available metadata'}
              </p>
              <div className="grid grid-cols-2 gap-2 mt-4 text-xs w-full max-w-xs">
                {[
                  ['ti-map-pin',      'GPS location'],
                  ['ti-camera',       'Device info'],
                  ['ti-clock',        'Timestamps'],
                  ['ti-shield-check', 'Manipulation'],
                  ['ti-hash',         'File hashes'],
                  ['ti-search',       'Reverse search'],
                ].map(([icon, label]) => (
                  <div key={label} className="flex items-center gap-2 p-2 bg-gray-800 rounded-lg">
                    <i className={`ti ${icon} text-purple-400 text-sm`} />
                    <span className="text-gray-400">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {loading && (
            <div className="card h-full flex flex-col items-center justify-center min-h-64">
              <span className="spinner w-10 h-10 block mb-4" />
              <p className="text-gray-400 text-sm">
                {mode === 'url' ? 'Fetching URL · Extracting headers · Analyzing EXIF…' : 'Extracting EXIF · Parsing GPS · Computing hashes…'}
              </p>
            </div>
          )}

          {combined && !loading && (
            <>
              {/* Risk summary bar */}
              <div className={`card p-4 mb-4 border ${RISK_BORDER(risk)}`}>
                <div className="flex items-center gap-4">
                  <div className="text-center flex-shrink-0">
                    <div className={`text-3xl font-bold ${RISK_COLOR(risk)}`}>{risk}</div>
                    <div className="text-xs text-gray-500">Risk score</div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white font-medium truncate">
                      {combined.summary || result?.summary}
                    </p>
                    <div className="flex gap-2 mt-2 flex-wrap">
                      {(urlResult?.url_metadata?.platform && urlResult.url_metadata.platform !== 'Unknown') && (
                        <span className="badge badge-blue text-xs">
                          🌐 {urlResult.url_metadata.platform}
                        </span>
                      )}
                      {(result?.gps_found || combined?.image_analysis?.gps_found) && (
                        <span className="badge badge-red text-xs">📍 GPS found</span>
                      )}
                      {(result?.manipulation?.is_likely_edited) && (
                        <span className="badge badge-amber text-xs">⚠ Possible edit</span>
                      )}
                      {(result?.device_info?.make) && (
                        <span className="badge badge-blue text-xs">
                          📷 {result.device_info.make}
                        </span>
                      )}
                      {urlResult?.url_metadata?.was_redirected && (
                        <span className="badge badge-amber text-xs">↪ Redirected</span>
                      )}
                      {urlResult?.url_metadata?.risk_flags?.length > 0 && (
                        <span className="badge badge-red text-xs">
                          ⚠ {urlResult.url_metadata.risk_flags.length} risk flag(s)
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 border-b border-gray-800 mb-4 overflow-x-auto">
                {([
                  { id:'overview',     label:'Overview',      show: true },
                  { id:'gps',          label:'📍 GPS',         show: true },
                  { id:'exif',         label:'EXIF',           show: !!result },
                  { id:'manipulation', label:'⚠ Manipulation',  show: !!result },
                  { id:'hashes',       label:'Hashes',         show: !!result },
                  { id:'headers',      label:'HTTP Headers',   show: !!urlResult },
                  { id:'reverse_search', label:'🔍 Reverse Search', show: true },
                  { id:'reverse_search', label:'🔍 Reverse Search', show: true },
                ] as const).filter(t => t.show).map(t => (
                  <button key={t.id} onClick={() => setActiveTab(t.id as typeof activeTab)}
                    className={`px-3 py-2 text-xs font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
                      activeTab===t.id
                        ? 'border-purple-500 text-purple-400'
                        : 'border-transparent text-gray-500 hover:text-gray-300'
                    }`}>{t.label}</button>
                ))}
              </div>

              {/* ── Overview ── */}
              {activeTab === 'overview' && (
                <div className="space-y-3">

                  {/* URL info if URL mode */}
                  {urlResult?.url_metadata && (
                    <div className="card p-4">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                        <i className="ti ti-link mr-1 text-purple-400" />URL analysis
                      </h3>
                      <table className="w-full text-sm">
                        <tbody>
                          {[
                            ['Platform',       urlResult.url_metadata.platform],
                            ['Domain',         urlResult.url_metadata.domain],
                            ['Content type',   urlResult.url_metadata.content_type],
                            ['File size',      urlResult.url_metadata.content_length],
                            ['Server',         urlResult.url_metadata.server],
                            ['Last modified',  urlResult.url_metadata.last_modified],
                            ['Redirected',     urlResult.url_metadata.was_redirected ? `Yes → ${urlResult.url_metadata.final_url?.slice(0,60)}…` : 'No'],
                            ['Media type',     urlResult.media_type],
                          ].filter(([,v]) => v).map(([k,v]) => (
                            <tr key={k as string} className="border-b border-gray-800 last:border-0">
                              <td className="py-2 text-gray-500 w-32 text-xs align-top">{k}</td>
                              <td className={`py-2 font-medium text-xs break-all ${
                                k==='Platform' && urlResult.url_metadata.platform==='Terabox' ? 'text-red-400' : 'text-white'
                              }`}>{String(v)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>

                      {/* Risk flags */}
                      {urlResult.url_metadata.risk_flags?.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-gray-800 space-y-1">
                          {urlResult.url_metadata.risk_flags.map((f: string, i: number) => (
                            <div key={i} className="flex items-start gap-2 text-xs text-amber-300">
                              <i className="ti ti-alert-triangle text-amber-400 flex-shrink-0 mt-0.5" />{f}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Video metadata */}
                  {urlResult?.video_metadata && !urlResult.image_analysis && (
                    <div className="card p-4 border-blue-900 bg-blue-950/10">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                        <i className="ti ti-video mr-1 text-blue-400" />Video metadata
                      </h3>
                      <p className="text-xs text-gray-400">{urlResult.video_metadata.note}</p>
                      <div className="mt-2 space-y-1 text-xs">
                        <div className="flex gap-2">
                          <span className="text-gray-500 w-28">Content type</span>
                          <span className="text-white">{urlResult.video_metadata.content_type}</span>
                        </div>
                        <div className="flex gap-2">
                          <span className="text-gray-500 w-28">File size</span>
                          <span className="text-white">{urlResult.video_metadata.content_length}</span>
                        </div>
                        <div className="flex gap-2">
                          <span className="text-gray-500 w-28">Platform</span>
                          <span className="text-white">{urlResult.video_metadata.platform}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Device info */}
                  {result && (
                    <div className="card p-4">
                      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                        <i className="ti ti-camera mr-1 text-purple-400" />Device information
                      </h3>
                      <table className="w-full text-sm">
                        <tbody>
                          {[
                            ['Make',          result.device_info?.make],
                            ['Model',         result.device_info?.model],
                            ['Software',      result.device_info?.software],
                            ['Lens',          result.device_info?.lens],
                            ['Serial number', result.device_info?.serial],
                            ['Owner name',    result.device_info?.owner],
                            ['Captured at',   result.device_info?.datetime],
                            ['Focal length',  result.device_info?.focal_length ? `${result.device_info.focal_length}mm` : null],
                            ['Format',        result.format?.format],
                            ['Dimensions',    result.format?.width ? `${result.format.width} × ${result.format.height} px` : null],
                            ['File size',     result.format?.file_size_human],
                          ].filter(([,v]) => v).map(([k,v]) => (
                            <tr key={k as string} className="border-b border-gray-800 last:border-0">
                              <td className="py-2 text-gray-500 w-36 text-xs">{k}</td>
                              <td className={`py-2 font-medium text-xs ${
                                k==='Serial number'||k==='Owner name' ? 'text-amber-400' : 'text-white'
                              }`}>{String(v)}</td>
                            </tr>
                          ))}
                          {!result.device_info?.make && (
                            <tr><td colSpan={2} className="py-2 text-gray-600 text-xs">
                              No device information in EXIF — image may have been shared via social media (strips metadata)
                            </td></tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {/* Reverse image search */}
                  <div className="card p-4">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      <i className="ti ti-search mr-1 text-purple-400" />Reverse image search
                    </h3>
                    <p className="text-xs text-gray-500 mb-3">
                      {mode==='url' && mediaUrl
                        ? 'Use the URL directly in these search engines:'
                        : 'Download the image then upload to these search engines:'}
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { name:'Google Images', url:'https://images.google.com/',        icon:'ti-brand-google' },
                        { name:'TinEye',        url:'https://tineye.com/',               icon:'ti-eye'          },
                        { name:'Yandex Images', url:'https://yandex.com/images/',       icon:'ti-search'       },
                        { name:'Bing Visual',   url:'https://www.bing.com/visualsearch', icon:'ti-brand-bing'   },
                      ].map(s => (
                        <a key={s.name} href={s.url} target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-2 p-3 bg-gray-800 rounded-xl border
                                     border-gray-700 hover:border-purple-600 hover:bg-purple-950/20
                                     transition-all text-sm">
                          <i className={`ti ${s.icon} text-purple-400`} />
                          <span className="text-gray-300">{s.name}</span>
                          <i className="ti ti-external-link text-gray-600 ml-auto text-xs" />
                        </a>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* ── GPS ── */}
              {activeTab === 'gps' && (
                <div>
                  {result?.gps ? (
                    <div className="space-y-3">
                      <div className="card p-4 border-red-900 bg-red-950/10">
                        <div className="flex items-center gap-2 mb-3">
                          <i className="ti ti-map-pin text-red-400 text-xl" />
                          <span className="text-red-400 font-semibold text-sm">GPS coordinates found</span>
                        </div>
                        <table className="w-full text-sm">
                          <tbody>
                            {[
                              ['Latitude',      result.gps.latitude],
                              ['Longitude',     result.gps.longitude],
                              ['Altitude',      result.gps.altitude_m ? `${result.gps.altitude_m}m` : '—'],
                              ['Coordinates',   result.gps.dms],
                              ['GPS timestamp', result.gps.gps_timestamp || '—'],
                            ].map(([k,v]) => (
                              <tr key={k as string} className="border-b border-gray-800 last:border-0">
                                <td className="py-2 text-gray-500 w-36 text-xs">{k}</td>
                                <td className="py-2 text-white font-mono text-xs font-medium">{String(v)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="card p-4">
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Open in maps</h3>
                        <div className="space-y-2">
                          {[
                            { name:'Google Maps (Street)',    url:result.gps.google_maps_url, icon:'ti-map'       },
                            { name:'Google Maps (Satellite)', url:result.gps.google_maps_sat, icon:'ti-satellite' },
                            { name:'OpenStreetMap',           url:result.gps.openstreetmap,   icon:'ti-map-2'     },
                          ].map(m => (
                            <a key={m.name} href={m.url} target="_blank" rel="noopener noreferrer"
                              className="flex items-center gap-3 p-3 bg-gray-800 rounded-xl border
                                         border-gray-700 hover:border-green-600 hover:bg-green-950/20 transition-all">
                              <i className={`ti ${m.icon} text-green-400 text-lg`} />
                              <span className="text-sm text-gray-300">{m.name}</span>
                              <span className="ml-auto text-xs text-gray-600 font-mono">
                                {result.gps.latitude}, {result.gps.longitude}
                              </span>
                              <i className="ti ti-external-link text-gray-600 text-xs" />
                            </a>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="card p-10 text-center text-gray-500">
                      <i className="ti ti-map-pin-off text-4xl block mb-3 opacity-30" />
                      <p className="font-medium text-white mb-1">No GPS data found</p>
                      <p className="text-sm">This image does not contain GPS coordinates.</p>
                      <p className="text-xs mt-2 text-gray-600">
                        WhatsApp, Instagram, and Twitter strip GPS metadata before delivery
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* ── EXIF ── */}
              {activeTab === 'exif' && result && (
                <div className="card overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-800">
                    <span className="text-sm font-semibold text-white">
                      EXIF metadata — {Object.keys(result.metadata||{}).length} fields
                    </span>
                  </div>
                  {Object.keys(result.metadata||{}).length === 0 ? (
                    <div className="p-8 text-center text-gray-500 text-sm">No EXIF metadata in this image</div>
                  ) : (
                    <div className="max-h-80 overflow-y-auto">
                      {Object.entries(result.metadata||{}).map(([k,v],i) => (
                        <div key={k} className={`flex items-start gap-3 px-4 py-2 text-xs
                                                  ${i%2===0?'bg-gray-900':'bg-gray-800/50'}`}>
                          <span className="text-gray-500 w-44 flex-shrink-0">{k}</span>
                          <span className="text-white break-all">
                            {Array.isArray(v) ? v.join(', ') : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── Manipulation ── */}
              {activeTab === 'manipulation' && result && (
                <div className="space-y-3">
                  <div className={`card p-4 border ${
                    result.manipulation?.manipulation_risk==='HIGH' ? 'border-red-900 bg-red-950/10' :
                    result.manipulation?.manipulation_risk==='MEDIUM' ? 'border-amber-900 bg-amber-950/10' :
                    'border-green-900 bg-green-950/10'
                  }`}>
                    <div className="flex items-center gap-3 mb-3">
                      <i className={`ti ti-shield text-2xl ${
                        result.manipulation?.manipulation_risk==='HIGH' ? 'text-red-400' :
                        result.manipulation?.manipulation_risk==='MEDIUM' ? 'text-amber-400' : 'text-green-400'
                      }`} />
                      <div>
                        <div className={`font-semibold text-sm ${
                          result.manipulation?.manipulation_risk==='HIGH' ? 'text-red-400' :
                          result.manipulation?.manipulation_risk==='MEDIUM' ? 'text-amber-400' : 'text-green-400'
                        }`}>
                          Manipulation risk: {result.manipulation?.manipulation_risk}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          {result.manipulation?.is_likely_edited ? 'Signs of editing detected' : 'No manipulation indicators'}
                        </div>
                      </div>
                    </div>
                    {result.manipulation?.manipulation_flags?.length > 0
                      ? result.manipulation.manipulation_flags.map((f: string, i: number) => (
                          <div key={i} className="flex items-start gap-2 text-sm">
                            <i className="ti ti-alert-triangle text-amber-400 flex-shrink-0" />
                            <span className="text-amber-200">{f}</span>
                          </div>
                        ))
                      : <p className="text-green-400 text-sm"><i className="ti ti-check mr-2" />No indicators found</p>
                    }
                  </div>
                  <div className="card p-3">
                    <p className="text-xs text-gray-500">
                      <i className="ti ti-info-circle mr-1 text-blue-400" />
                      For court evidence, verify with certified forensic tools (FTK Imager, Autopsy, ExifTool).
                      This analysis is based on metadata — not pixel-level forensics.
                    </p>
                  </div>
                </div>
              )}

              {/* ── Hashes ── */}
              {activeTab === 'hashes' && result && (
                <div className="card p-4">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    <i className="ti ti-hash mr-1 text-purple-400" />File integrity hashes (Section 65B IT Act)
                  </h3>
                  <div className="space-y-3">
                    {Object.entries(result.hashes||{}).map(([algo, hash]) => (
                      <div key={algo} className="bg-gray-800 rounded-xl p-3">
                        <div className="text-xs text-gray-500 uppercase mb-1">{algo.toUpperCase()}</div>
                        <div className="font-mono text-xs text-green-400 break-all select-all">{String(hash)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ── Reverse Search ── */}
              {activeTab === 'reverse_search' && (
                <ReverseSearchPanel
                  file={file}
                  mode={mode}
                  mediaUrl={mediaUrl}
                  token=""
                />
              )}

              {/* ── HTTP Headers ── */}
              {activeTab === 'headers' && urlResult && (
                <div className="card overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-800">
                    <span className="text-sm font-semibold text-white">
                      HTTP response headers — {Object.keys(urlResult.url_metadata?.all_headers||{}).length} fields
                    </span>
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {Object.entries(urlResult.url_metadata?.all_headers||{}).map(([k,v],i) => (
                      <div key={k} className={`flex items-start gap-3 px-4 py-2 text-xs
                                                ${i%2===0?'bg-gray-900':'bg-gray-800/50'}`}>
                        <span className="text-gray-500 w-48 flex-shrink-0 font-mono">{k}</span>
                        <span className="text-white break-all font-mono">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
