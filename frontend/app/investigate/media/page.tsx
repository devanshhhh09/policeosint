'use client'
import { useState, useRef } from 'react'
import { api } from '@/lib/api'

const RISK_COLOR = (r: number) =>
  r >= 60 ? 'text-red-400' : r >= 30 ? 'text-amber-400' : 'text-green-400'

export default function MediaForensicsPage() {
  const fileRef   = useRef<HTMLInputElement>(null)
  const [file, setFile]         = useState<File | null>(null)
  const [preview, setPreview]   = useState<string | null>(null)
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState<any>(null)
  const [error, setError]       = useState('')
  const [activeTab, setActiveTab] = useState<'overview'|'exif'|'gps'|'hashes'|'manipulation'>('overview')

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setResult(null)
    setError('')
    const reader = new FileReader()
    reader.onload = (ev) => setPreview(ev.target?.result as string)
    reader.readAsDataURL(f)
  }

  const analyze = async () => {
    if (!file) return
    setLoading(true); setResult(null); setError('')
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

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) {
      setFile(f)
      setResult(null)
      setError('')
      const reader = new FileReader()
      reader.onload = (ev) => setPreview(ev.target?.result as string)
      reader.readAsDataURL(f)
    }
  }

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
            EXIF extraction · GPS location · Device identification · Manipulation detection · Reverse image search
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-5">
        {/* Upload panel */}
        <div className="lg:col-span-1">
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
              </>
            )}
            <input ref={fileRef} type="file"
              accept="image/jpeg,image/png,image/gif,image/webp,image/bmp"
              className="hidden" onChange={handleFile} />
          </div>

          {file && (
            <div className="mt-3 space-y-2">
              <div className="card p-3 text-xs">
                <div className="text-gray-500 mb-1">Selected file</div>
                <div className="text-white font-medium truncate">{file.name}</div>
                <div className="text-gray-500 mt-0.5">{(file.size/1024).toFixed(1)} KB · {file.type}</div>
              </div>
              <button onClick={analyze} disabled={loading}
                className="btn-primary w-full justify-center py-3">
                {loading
                  ? <><span className="spinner w-4 h-4" />Analyzing…</>
                  : <><i className="ti ti-scan" />Analyze image</>}
              </button>
              <button onClick={() => { setFile(null); setPreview(null); setResult(null) }}
                className="btn-secondary w-full justify-center text-xs">
                <i className="ti ti-x" />Clear
              </button>
            </div>
          )}

          {error && (
            <div className="mt-3 p-3 bg-red-950/30 border border-red-900 rounded-xl text-red-400 text-sm">
              <i className="ti ti-alert-circle mr-2" />{error}
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="lg:col-span-2">
          {!result && !loading && (
            <div className="card h-full flex flex-col items-center justify-center text-gray-500 min-h-64">
              <i className="ti ti-photo-scan text-5xl mb-4 opacity-20" />
              <p className="font-medium text-white mb-1">Upload an image to analyze</p>
              <p className="text-sm text-center max-w-xs">
                Extract GPS coordinates, camera details, timestamps, and detect manipulation
              </p>
              <div className="grid grid-cols-2 gap-2 mt-4 text-xs w-full max-w-xs">
                {[
                  ['ti-map-pin',       'GPS location'],
                  ['ti-camera',        'Device info'],
                  ['ti-clock',         'Timestamps'],
                  ['ti-shield-check',  'Manipulation check'],
                  ['ti-hash',          'File hashes'],
                  ['ti-search',        'Reverse image search'],
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
              <p className="text-gray-400">Extracting EXIF data · Parsing GPS · Computing hashes…</p>
            </div>
          )}

          {result && !loading && (
            <>
              {/* Risk + summary */}
              <div className={`card p-4 mb-4 border ${
                result.risk_score >= 60 ? 'border-red-900 bg-red-950/10' :
                result.risk_score >= 30 ? 'border-amber-900 bg-amber-950/10' : 'border-gray-800'
              }`}>
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <div className={`text-3xl font-bold ${RISK_COLOR(result.risk_score)}`}>
                      {result.risk_score}
                    </div>
                    <div className="text-xs text-gray-500">Risk score</div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-white font-medium">{result.summary}</p>
                    <div className="flex gap-2 mt-2 flex-wrap">
                      {result.gps_found && (
                        <span className="badge badge-red text-xs">📍 GPS data found</span>
                      )}
                      {result.manipulation?.is_likely_edited && (
                        <span className="badge badge-amber text-xs">⚠ Possible edit</span>
                      )}
                      {result.device_info?.make && (
                        <span className="badge badge-blue text-xs">
                          📷 {result.device_info.make} {result.device_info.model}
                        </span>
                      )}
                      {result.format?.width && (
                        <span className="badge badge-gray text-xs">
                          {result.format.width}×{result.format.height}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex gap-1 border-b border-gray-800 mb-4 overflow-x-auto">
                {([
                  { id:'overview',     label:'Overview'    },
                  { id:'gps',          label:'📍 GPS Location' },
                  { id:'exif',         label:'EXIF Metadata' },
                  { id:'manipulation', label:'⚠ Manipulation' },
                  { id:'hashes',       label:'File Hashes'  },
                ] as const).map(t => (
                  <button key={t.id} onClick={() => setActiveTab(t.id)}
                    className={`px-3 py-2 text-xs font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
                      activeTab===t.id
                        ? 'border-purple-500 text-purple-400'
                        : 'border-transparent text-gray-500 hover:text-gray-300'
                    }`}>{t.label}</button>
                ))}
              </div>

              {/* Overview */}
              {activeTab === 'overview' && (
                <div className="space-y-3">
                  {/* Device info */}
                  <div className="card p-4">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      <i className="ti ti-camera mr-1 text-purple-400" />Device information
                    </h3>
                    <table className="w-full text-sm">
                      <tbody>
                        {[
                          ['Make',         result.device_info?.make],
                          ['Model',        result.device_info?.model],
                          ['Software',     result.device_info?.software],
                          ['Lens',         result.device_info?.lens],
                          ['Serial number',result.device_info?.serial],
                          ['Owner name',   result.device_info?.owner],
                          ['Captured at',  result.device_info?.datetime],
                          ['Focal length', result.device_info?.focal_length ? `${result.device_info.focal_length}mm` : null],
                        ].filter(([,v]) => v).map(([k,v]) => (
                          <tr key={k as string} className="border-b border-gray-800 last:border-0">
                            <td className="py-2 text-gray-500 w-36">{k}</td>
                            <td className={`py-2 font-medium ${
                              k==='Serial number'||k==='Owner name' ? 'text-amber-400' : 'text-white'
                            }`}>{String(v)}</td>
                          </tr>
                        ))}
                        {!result.device_info?.make && (
                          <tr><td colSpan={2} className="py-2 text-gray-600 text-xs">No device information found in this image</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* File info */}
                  <div className="card p-4">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      <i className="ti ti-file-info mr-1 text-purple-400" />File information
                    </h3>
                    <table className="w-full text-sm">
                      <tbody>
                        {[
                          ['Format',      result.format?.format],
                          ['Dimensions',  result.format?.width ? `${result.format.width} × ${result.format.height} pixels` : null],
                          ['File size',   result.format?.file_size_human],
                          ['Filename',    result.filename],
                        ].filter(([,v]) => v).map(([k,v]) => (
                          <tr key={k as string} className="border-b border-gray-800 last:border-0">
                            <td className="py-2 text-gray-500 w-36">{k}</td>
                            <td className="py-2 text-white font-medium">{String(v)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Reverse image search */}
                  <div className="card p-4">
                    <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                      <i className="ti ti-search mr-1 text-purple-400" />Reverse image search
                    </h3>
                    <p className="text-xs text-gray-500 mb-3">
                      Download the image then upload it to find where it appears online
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { name:'Google Images', url:'https://images.google.com/',           icon:'ti-brand-google' },
                        { name:'TinEye',        url:'https://tineye.com/',                   icon:'ti-eye'          },
                        { name:'Yandex Images', url:'https://yandex.com/images/',           icon:'ti-search'       },
                        { name:'Bing Visual',   url:'https://www.bing.com/visualsearch',    icon:'ti-brand-bing'   },
                      ].map(s => (
                        <a key={s.name} href={s.url} target="_blank" rel="noopener noreferrer"
                          className="flex items-center gap-2 p-3 bg-gray-800 rounded-xl
                                     border border-gray-700 hover:border-purple-600
                                     hover:bg-purple-950/20 transition-all text-sm">
                          <i className={`ti ${s.icon} text-purple-400`} />
                          <span className="text-gray-300">{s.name}</span>
                          <i className="ti ti-external-link text-gray-600 ml-auto text-xs" />
                        </a>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* GPS */}
              {activeTab === 'gps' && (
                <div>
                  {result.gps ? (
                    <div className="space-y-3">
                      <div className="card p-4 border-red-900 bg-red-950/10">
                        <div className="flex items-center gap-2 mb-3">
                          <i className="ti ti-map-pin text-red-400 text-xl" />
                          <span className="text-red-400 font-semibold text-sm">
                            GPS coordinates found — location identified
                          </span>
                        </div>
                        <table className="w-full text-sm">
                          <tbody>
                            {[
                              ['Latitude',     result.gps.latitude],
                              ['Longitude',    result.gps.longitude],
                              ['Altitude',     result.gps.altitude_m ? `${result.gps.altitude_m}m` : '—'],
                              ['Coordinates',  result.gps.dms],
                              ['GPS timestamp',result.gps.gps_timestamp || '—'],
                            ].map(([k,v]) => (
                              <tr key={k as string} className="border-b border-gray-800 last:border-0">
                                <td className="py-2 text-gray-500 w-36">{k}</td>
                                <td className="py-2 text-white font-mono font-medium">{String(v)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="card p-4">
                        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                          Open location in maps
                        </h3>
                        <div className="grid grid-cols-1 gap-2">
                          {[
                            { name:'Google Maps (Street)',   url:result.gps.google_maps_url, icon:'ti-map'         },
                            { name:'Google Maps (Satellite)',url:result.gps.google_maps_sat, icon:'ti-satellite'   },
                            { name:'OpenStreetMap',          url:result.gps.openstreetmap,   icon:'ti-map-2'       },
                          ].map(m => (
                            <a key={m.name} href={m.url} target="_blank" rel="noopener noreferrer"
                              className="flex items-center gap-3 p-3 bg-gray-800 rounded-xl
                                         border border-gray-700 hover:border-green-600
                                         hover:bg-green-950/20 transition-all">
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
                      <p className="text-sm">This image does not contain GPS coordinates in its metadata.</p>
                      <p className="text-xs mt-2 text-gray-600">
                        GPS is often stripped by social media platforms (WhatsApp, Instagram, Twitter)
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* EXIF */}
              {activeTab === 'exif' && (
                <div className="card overflow-hidden">
                  <div className="px-4 py-3 border-b border-gray-800">
                    <span className="text-sm font-semibold text-white">
                      EXIF metadata — {Object.keys(result.metadata||{}).length} fields
                    </span>
                  </div>
                  {Object.keys(result.metadata||{}).length === 0 ? (
                    <div className="p-8 text-center text-gray-500 text-sm">
                      No EXIF metadata found in this image
                    </div>
                  ) : (
                    <div className="max-h-80 overflow-y-auto">
                      {Object.entries(result.metadata||{}).map(([k,v],i) => (
                        <div key={k} className={`flex items-start gap-3 px-4 py-2.5 text-sm
                                                  ${i%2===0?'bg-gray-900':'bg-gray-800/50'}`}>
                          <span className="text-gray-500 w-44 flex-shrink-0 text-xs mt-0.5">{k}</span>
                          <span className="text-white font-medium break-all text-xs">
                            {Array.isArray(v) ? v.join(', ') : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Manipulation */}
              {activeTab === 'manipulation' && (
                <div className="space-y-3">
                  <div className={`card p-4 border ${
                    result.manipulation?.manipulation_risk === 'HIGH' ? 'border-red-900 bg-red-950/10' :
                    result.manipulation?.manipulation_risk === 'MEDIUM' ? 'border-amber-900 bg-amber-950/10' :
                    'border-green-900 bg-green-950/10'
                  }`}>
                    <div className="flex items-center gap-3 mb-3">
                      <i className={`ti ti-shield text-2xl ${
                        result.manipulation?.manipulation_risk === 'HIGH' ? 'text-red-400' :
                        result.manipulation?.manipulation_risk === 'MEDIUM' ? 'text-amber-400' :
                        'text-green-400'
                      }`} />
                      <div>
                        <div className={`font-semibold text-sm ${
                          result.manipulation?.manipulation_risk === 'HIGH' ? 'text-red-400' :
                          result.manipulation?.manipulation_risk === 'MEDIUM' ? 'text-amber-400' :
                          'text-green-400'
                        }`}>
                          Manipulation risk: {result.manipulation?.manipulation_risk}
                        </div>
                        <div className="text-xs text-gray-500 mt-0.5">
                          {result.manipulation?.is_likely_edited
                            ? 'Signs of editing detected'
                            : 'No manipulation indicators found'}
                        </div>
                      </div>
                    </div>
                    {result.manipulation?.manipulation_flags?.length > 0 ? (
                      <div className="space-y-2">
                        {result.manipulation.manipulation_flags.map((f: string, i: number) => (
                          <div key={i} className="flex items-start gap-2 text-sm">
                            <i className="ti ti-alert-triangle text-amber-400 flex-shrink-0 mt-0.5" />
                            <span className="text-amber-200">{f}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-green-400 text-sm">
                        <i className="ti ti-check mr-2" />No manipulation indicators detected
                      </p>
                    )}
                  </div>
                  <div className="card p-4">
                    <p className="text-xs text-gray-500 leading-relaxed">
                      <i className="ti ti-info-circle mr-1 text-blue-400" />
                      Manipulation detection is based on metadata analysis — software signatures,
                      timestamp inconsistencies, and JPEG structure analysis.
                      For court evidence, use a certified forensic tool (FTK, Autopsy).
                    </p>
                  </div>
                </div>
              )}

              {/* Hashes */}
              {activeTab === 'hashes' && (
                <div className="card p-4">
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                    <i className="ti ti-hash mr-1 text-purple-400" />File integrity hashes
                  </h3>
                  <p className="text-xs text-gray-600 mb-3">
                    Use these hashes to verify file integrity in court (Section 65B IT Act)
                  </p>
                  <div className="space-y-3">
                    {Object.entries(result.hashes||{}).map(([algo, hash]) => (
                      <div key={algo} className="bg-gray-800 rounded-xl p-3">
                        <div className="text-xs text-gray-500 uppercase mb-1">{algo.toUpperCase()}</div>
                        <div className="font-mono text-xs text-green-400 break-all select-all">
                          {String(hash)}
                        </div>
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
