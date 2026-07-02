'use client'
import { useState } from 'react'
import { api } from '@/lib/api'

interface Props {
  file:     File | null
  mode:     'upload' | 'url'
  mediaUrl: string
  token:    string
}

export default function ReverseSearchPanel({ file, mode, mediaUrl }: Props) {
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error,   setError]   = useState('')

  const search = async () => {
    setLoading(true); setResults(null); setError('')
    try {
      const form = new FormData()
      if (file) {
        form.append('file', file)
      } else if (mediaUrl) {
        const res  = await fetch(mediaUrl)
        const blob = await res.blob()
        form.append('file', blob, 'image.jpg')
      } else {
        setError('No image to search'); setLoading(false); return
      }
      const res = await api.post('/media-forensics/reverse-search', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000,
      })
      setResults(res.data)
    } catch (e: any) {
      setError(e.response?.data?.error || 'Search failed')
    } finally { setLoading(false) }
  }

  const hasApiKey  = results?.status === 'success'
  const noApiKey   = results?.status === 'no_api_key'
  const hasResults = results && (
    (results.full_matches?.length    || 0) +
    (results.partial_matches?.length || 0) +
    (results.pages_with_image?.length|| 0) +
    (results.similar_images?.length  || 0) > 0
  )

  return (
    <div className="space-y-4">
      {/* Search trigger */}
      <div className="card p-4 border-purple-900 bg-purple-950/10">
        <div className="flex items-center gap-3 mb-3">
          <i className="ti ti-search text-purple-400 text-xl" />
          <div>
            <div className="text-sm font-semibold text-white">Google Vision — Web Detection</div>
            <div className="text-xs text-gray-500">Finds where this image appears across the web</div>
          </div>
          <button onClick={search} disabled={loading || (!file && !mediaUrl)}
            className="btn-primary ml-auto text-sm px-4">
            {loading
              ? <><span className="spinner w-4 h-4" />Searching…</>
              : <><i className="ti ti-search" />Search web</>}
          </button>
        </div>
        <p className="text-xs text-gray-600">
          <i className="ti ti-info-circle mr-1 text-blue-400" />
          Requires GOOGLE_VISION_API_KEY in .env (free 1000/month at console.cloud.google.com).
          Without key, manual search links are shown below.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-red-950/30 border border-red-900 rounded-xl text-red-400 text-sm">
          <i className="ti ti-alert-circle mr-2" />{error}
        </div>
      )}

      {/* Manual links — always shown */}
      <div className="card p-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Manual reverse search
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {[
            { name:'Google Images', url:'https://images.google.com/',        icon:'ti-brand-google', color:'text-blue-400'  },
            { name:'TinEye',        url:'https://tineye.com/',               icon:'ti-eye',          color:'text-green-400' },
            { name:'Yandex Images', url:'https://yandex.com/images/',       icon:'ti-search',       color:'text-red-400'   },
            { name:'Bing Visual',   url:'https://www.bing.com/visualsearch', icon:'ti-brand-bing',   color:'text-sky-400'   },
          ].map(s => (
            <a key={s.name} href={s.url} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 p-3 bg-gray-800 rounded-xl border
                         border-gray-700 hover:border-purple-600 transition-all">
              <i className={`ti ${s.icon} ${s.color} text-lg`} />
              <div>
                <div className="text-sm text-white">{s.name}</div>
                <div className="text-[10px] text-gray-500">Upload image manually</div>
              </div>
              <i className="ti ti-external-link text-gray-600 ml-auto text-xs" />
            </a>
          ))}
        </div>
        {noApiKey && (
          <p className="text-xs text-amber-400 mt-3">
            <i className="ti ti-key mr-1" />
            Add GOOGLE_VISION_API_KEY to .env for automatic results
          </p>
        )}
      </div>

      {/* API Results */}
      {hasApiKey && (
        <>
          <div className="grid grid-cols-4 gap-2">
            {[
              { label:'Exact matches',   value:results.full_matches?.length    ||0, color:'text-red-400'   },
              { label:'Partial matches', value:results.partial_matches?.length ||0, color:'text-amber-400' },
              { label:'Pages found',     value:results.pages_with_image?.length||0, color:'text-blue-400'  },
              { label:'Similar images',  value:results.similar_images?.length  ||0, color:'text-green-400' },
            ].map(s => (
              <div key={s.label} className="card p-3 text-center">
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                <div className="text-[10px] text-gray-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {results.best_guess_labels?.length > 0 && (
            <div className="card p-4">
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Google identifies as</div>
              <div className="flex flex-wrap gap-2">
                {results.best_guess_labels.map((l: string) => (
                  <span key={l} className="badge badge-blue">{l}</span>
                ))}
              </div>
            </div>
          )}

          {!hasResults && (
            <div className="card p-8 text-center text-gray-500">
              <i className="ti ti-search-off text-3xl block mb-2 opacity-30" />
              <p className="text-white font-medium mb-1">No matches found</p>
              <p className="text-sm">Image does not appear elsewhere on the web</p>
            </div>
          )}

          {[
            { items:results.full_matches,     title:'Exact matches',                icon:'ti-copy',  color:'text-red-400',   badge:'badge-red',   type:'image' as const },
            { items:results.pages_with_image, title:'Pages containing this image',  icon:'ti-world', color:'text-blue-400',  badge:'badge-blue',  type:'page'  as const },
            { items:results.partial_matches,  title:'Partial matches',              icon:'ti-crop',  color:'text-amber-400', badge:'badge-amber', type:'image' as const },
            { items:results.similar_images,   title:'Visually similar images',      icon:'ti-photo', color:'text-green-400', badge:'badge-green', type:'image' as const },
          ].filter(s => s.items?.length > 0).map(s => (
            <div key={s.title} className="card overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                <i className={`ti ${s.icon} ${s.color}`} />
                <span className="text-sm font-semibold text-white">{s.title}</span>
                <span className={`badge ${s.badge} text-xs ml-auto`}>{s.items.length}</span>
              </div>
              <div className="max-h-64 overflow-y-auto">
                {s.items.map((item: any, i: number) => (
                  <div key={i} className={`flex items-start gap-3 px-4 py-3 text-xs
                                           ${i < s.items.length-1 ? 'border-b border-gray-800' : ''}
                                           hover:bg-gray-800/50`}>
                    <i className={`ti ${s.type==='page'?'ti-world':'ti-photo'} text-gray-500 flex-shrink-0 mt-0.5`} />
                    <div className="flex-1 min-w-0">
                      {item.title && (
                        <div className="text-white font-medium truncate mb-0.5">{item.title}</div>
                      )}
                      <a href={item.url} target="_blank" rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 underline break-all">
                        {item.url?.slice(0,80)}{item.url?.length>80?'…':''}
                      </a>
                    </div>
                    {item.score && (
                      <span className="text-gray-600 flex-shrink-0">{(item.score*100).toFixed(0)}%</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
