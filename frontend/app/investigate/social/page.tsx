'use client'
import { useState, useEffect } from 'react'
import { investigateAPI } from '@/lib/api'

const CATEGORY_ICONS: Record<string, string> = {
  social:       'ti-brand-instagram',
  developer:    'ti-brand-github',
  messaging:    'ti-brand-telegram',
  professional: 'ti-briefcase',
  video:        'ti-brand-youtube',
  gaming:       'ti-device-gamepad',
  blog:         'ti-pencil',
  data:         'ti-database',
}
const CATEGORY_COLORS: Record<string, string> = {
  social:       'text-pink-400',
  developer:    'text-gray-300',
  messaging:    'text-blue-400',
  professional: 'text-blue-300',
  video:        'text-red-400',
  gaming:       'text-purple-400',
  blog:         'text-green-400',
  data:         'text-amber-400',
}
const PLATFORM_COLORS: Record<string, string> = {
  'GitHub':     '#24292e',
  'Reddit':     '#FF4500',
  'Instagram':  '#E1306C',
  'Twitter/X':  '#000000',
  'TikTok':     '#010101',
  'Pinterest':  '#E60023',
  'Telegram':   '#0088cc',
  'LinkedIn':   '#0A66C2',
  'YouTube':    '#FF0000',
  'Snapchat':   '#FFFC00',
  'Quora':      '#B92B27',
  'Medium':     '#000000',
  'Twitch':     '#9146FF',
  'Steam':      '#1b2838',
  'Pastebin':   '#02A8F3',
  'Koo':        '#F7C948',
  'ShareChat':  '#5f67ee',
}

const QUICK_TARGETS = [
  'invest_guru99', 'kyc.helpdesk', 'earn_daily_now',
  'crypto_signals_india', 'rahul_sharma',
]

export default function SocialPage() {
  const [username, setUsername] = useState('')
  const [loading, setLoading]   = useState(false)
  const [invId, setInvId]       = useState('')
  const [result, setResult]     = useState<any>(null)
  const [error, setError]       = useState('')
  const [activeTab, setActiveTab] = useState<'found'|'not_found'|'analysis'>('found')

  const run = async (uname?: string) => {
    const q = (uname || username).trim().replace(/^@/, '')
    if (!q) return
    setLoading(true); setResult(null); setError(''); setInvId('')
    try {
      const res = await investigateAPI.start({
        investigation_type: 'social_media',
        query:              q,
        query_type:         'username',
      })
      setInvId(res.data.id)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to start investigation')
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!invId) return
    const t = setInterval(async () => {
      try {
        const res = await investigateAPI.get(invId)
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          setResult(res.data)
          setLoading(false)
          clearInterval(t)
        }
      } catch { clearInterval(t); setLoading(false) }
    }, 2000)
    return () => clearInterval(t)
  }, [invId])

  const data      = result?.results?.[0]?.parsed_data || result
  const platforms = data?.platforms || {}
  const found     = platforms.found     || []
  const notFound  = platforms.not_found || []
  const analysis  = data?.analysis      || {}
  const risk      = result?.risk_score  || data?.risk_score || 0
  const flags     = data?.flags         || []

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-pink-950 flex items-center justify-center">
          <i className="ti ti-social text-pink-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Social Media Intelligence</h1>
          <p className="text-gray-500 text-sm">
            Username enumeration across 17 platforms · Profile analysis · Scam indicator detection
          </p>
        </div>
      </div>

      {/* Quick targets */}
      <div className="flex flex-wrap gap-2 mb-4">
        {QUICK_TARGETS.map(t => (
          <button key={t} onClick={() => { setUsername(t); run(t) }}
            className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border
                       border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors">
            @{t}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="card p-4 mb-5">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm font-bold">@</span>
            <input value={username} onChange={e => setUsername(e.target.value.replace(/^@/,''))}
              onKeyDown={e => e.key === 'Enter' && run()}
              placeholder="username_to_investigate"
              className="input-field pl-7" />
          </div>
          <button onClick={() => run()} disabled={!username.trim() || loading}
            className="btn-primary px-6">
            {loading
              ? <><span className="spinner w-4 h-4" />Searching {platforms.total_checked || 0} platforms…</>
              : <><i className="ti ti-search" />Search all platforms</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
        <p className="text-xs text-gray-600 mt-2">
          <i className="ti ti-info-circle mr-1" />
          Checks GitHub, Reddit, Instagram, Twitter/X, TikTok, Telegram, LinkedIn, YouTube + 9 more
        </p>
      </div>

      {loading && (
        <div className="card p-8 text-center space-y-3">
          <span className="spinner w-8 h-8 block mx-auto" />
          <p className="text-gray-400 text-sm">Searching across 17 social platforms simultaneously…</p>
          <p className="text-gray-600 text-xs">This may take 15–30 seconds</p>
        </div>
      )}

      {result && !loading && (
        <>
          {/* Risk + summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
            <div className="card p-4 text-center">
              <div className={`text-3xl font-bold ${
                risk >= 60 ? 'text-red-400' : risk >= 30 ? 'text-amber-400' : 'text-green-400'
              }`}>{risk}/100</div>
              <div className="text-xs text-gray-500 mt-1">Risk score</div>
            </div>
            <div className="card p-4 text-center">
              <div className="text-3xl font-bold text-green-400">{found.length}</div>
              <div className="text-xs text-gray-500 mt-1">Platforms found</div>
            </div>
            <div className="card p-4 text-center">
              <div className="text-3xl font-bold text-gray-500">{notFound.length}</div>
              <div className="text-xs text-gray-500 mt-1">Not found</div>
            </div>
            <div className="card p-4 text-center">
              <div className="text-3xl font-bold text-amber-400">{flags.length}</div>
              <div className="text-xs text-gray-500 mt-1">Risk flags</div>
            </div>
          </div>

          {/* Risk flags */}
          {flags.length > 0 && (
            <div className="card p-4 mb-5 border-amber-900 bg-amber-950/20">
              <h3 className="text-sm font-semibold text-amber-400 mb-2 flex items-center gap-2">
                <i className="ti ti-alert-triangle text-lg" />Risk flags detected
              </h3>
              <div className="space-y-1">
                {flags.map((f: string, i: number) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-amber-200">
                    <i className="ti ti-chevron-right text-amber-400 flex-shrink-0 mt-0.5" />{f}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Username analysis */}
          {analysis.scam_patterns?.length > 0 && (
            <div className="card p-4 mb-5 border-red-900 bg-red-950/10">
              <h3 className="text-sm font-semibold text-red-400 mb-2">
                <i className="ti ti-alert-circle mr-2" />Username pattern analysis
              </h3>
              <div className="flex flex-wrap gap-2">
                {analysis.scam_patterns?.map((p: string) => (
                  <span key={p} className="badge badge-red text-xs">{p}</span>
                ))}
                {analysis.brand_impersonation?.map((b: string) => (
                  <span key={b} className="badge badge-amber text-xs">Brand: {b}</span>
                ))}
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-1 border-b border-gray-800 mb-4">
            {([
              { id:'found',    label:`Found (${found.length})`       },
              { id:'not_found',label:`Not found (${notFound.length})` },
              { id:'analysis', label:'Username analysis'              },
            ] as const).map(t => (
              <button key={t.id} onClick={() => setActiveTab(t.id)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab===t.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}>{t.label}</button>
            ))}
          </div>

          {/* Found platforms */}
          {activeTab === 'found' && (
            found.length === 0 ? (
              <div className="card p-8 text-center text-gray-500 text-sm">
                <i className="ti ti-search-off text-3xl block mb-2 opacity-30" />
                Username not found on any checked platform
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {found.map((p: any) => (
                  <div key={p.platform} className="card p-4 hover:border-gray-700 transition-colors">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                        style={{
                          background: (PLATFORM_COLORS[p.platform] || '#374151') + '33',
                          border:     `1px solid ${PLATFORM_COLORS[p.platform] || '#374151'}55`,
                        }}>
                        <i className={`ti ${CATEGORY_ICONS[p.category]||'ti-world'} text-lg
                                       ${CATEGORY_COLORS[p.category]||'text-gray-400'}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-sm font-semibold text-white">{p.platform}</span>
                          <span className="badge badge-green text-[10px]">FOUND</span>
                        </div>
                        {p.display_name && (
                          <p className="text-xs text-gray-400 truncate">{p.display_name}</p>
                        )}
                        {p.bio && (
                          <p className="text-xs text-gray-500 truncate mt-0.5">{p.bio}</p>
                        )}
                        {p.followers && (
                          <p className="text-xs text-blue-400 mt-0.5">
                            <i className="ti ti-users mr-1" />{p.followers} followers
                          </p>
                        )}
                      </div>
                      <a href={p.url} target="_blank" rel="noopener noreferrer"
                        className="flex-shrink-0 text-blue-400 hover:text-blue-300">
                        <i className="ti ti-external-link text-lg" />
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )
          )}

          {/* Not found */}
          {activeTab === 'not_found' && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {notFound.map((p: any) => (
                <div key={p.platform}
                  className="card p-3 flex items-center gap-2 opacity-50">
                  <i className={`ti ${CATEGORY_ICONS[p.category]||'ti-world'} text-gray-500`} />
                  <span className="text-xs text-gray-500">{p.platform}</span>
                  <i className="ti ti-x text-red-400 ml-auto text-xs" />
                </div>
              ))}
            </div>
          )}

          {/* Username analysis */}
          {activeTab === 'analysis' && (
            <div className="card p-5">
              <table className="w-full text-sm">
                <tbody>
                  {[
                    ['Username',        `@${analysis.username}`],
                    ['Length',          analysis.length],
                    ['Contains numbers',analysis.has_numbers ? '✓ Yes' : '✗ No'],
                    ['Contains special',analysis.has_special ? '✓ Yes (_.-) ' : '✗ No'],
                    ['Risk score',      `${analysis.risk_score}/100 — ${analysis.risk_label}`],
                    ['Scam patterns',   analysis.scam_patterns?.join(', ') || 'None detected'],
                    ['Brand impersonation', analysis.brand_impersonation?.join(', ') || 'None detected'],
                  ].map(([k, v]) => (
                    <tr key={k} className="border-b border-gray-800 last:border-0">
                      <td className="py-2.5 text-gray-500 w-44">{k}</td>
                      <td className={`py-2.5 font-medium ${
                        String(v).includes('None') ? 'text-green-400' :
                        String(v).includes('HIGH') ? 'text-red-400'   :
                        String(v).includes('MEDIUM') ? 'text-amber-400' : 'text-white'
                      }`}>{String(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {analysis.flags?.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-800">
                  <h4 className="text-xs text-gray-500 uppercase tracking-wider mb-2">Risk flags</h4>
                  {analysis.flags.map((f: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-amber-300 py-1">
                      <i className="ti ti-alert-circle text-amber-400 flex-shrink-0 mt-0.5" />{f}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Summary */}
          <div className="card p-4 mt-4 border-gray-700">
            <p className="text-xs text-gray-500">{result.summary || data?.summary}</p>
          </div>

          <div className="flex gap-3 mt-4">
            <button onClick={() => { setResult(null); setUsername('') }} className="btn-secondary">
              <i className="ti ti-refresh" />New search
            </button>
            <button onClick={() => window.print()} className="btn-secondary">
              <i className="ti ti-printer" />Print results
            </button>
          </div>
        </>
      )}
    </div>
  )
}
