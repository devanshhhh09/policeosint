'use client'
import { useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'

/* ── constants ──────────────────────────────────────────────────────────────── */
const CRIT: Record<string, { badge: string; dot: string; label: string }> = {
  critical:   { badge: 'bg-red-950 border-red-700 text-red-300',    dot: 'bg-red-400',    label: '🔴 CRITICAL'   },
  suspicious: { badge: 'bg-amber-950 border-amber-700 text-amber-300', dot: 'bg-amber-400', label: '🟡 SUSPICIOUS' },
  normal:     { badge: 'bg-green-950 border-green-700 text-green-300', dot: 'bg-green-400', label: '🟢 NORMAL'     },
  unknown:    { badge: 'bg-gray-800 border-gray-700 text-gray-400',  dot: 'bg-gray-500',  label: '⚪ UNKNOWN'    },
}
const CATEGORY_COLORS: Record<string, string> = {
  fake_job: 'badge-amber', investment_scam: 'badge-red', crypto_scam: 'badge-red',
  illegal_content: 'badge-red', leaked_data: 'badge-purple',
  normal: 'badge-green', unclassified: 'badge-gray',
}
const RISK_COLOR = (r: number) => r >= 70 ? 'text-red-400' : r >= 40 ? 'text-amber-400' : 'text-green-400'

export default function TelegramPage() {
  const [tab, setTab] = useState<'feed'|'members'|'indicators'|'sources'>('feed')

  /* feed state */
  const [sources, setSources]       = useState<any[]>([])
  const [content, setContent]       = useState<any[]>([])
  const [indicators, setIndicators] = useState<any[]>([])
  const [stats, setStats]           = useState<any>(null)
  const [identifier, setIdentifier] = useState('')
  const [adding, setAdding]         = useState(false)
  const [scraping, setScraping]     = useState<string|null>(null)
  const pollRef = useRef<any>(null)

  /* member state */
  const [members, setMembers]             = useState<any[]>([])
  const [memberStats, setMemberStats]     = useState<any>(null)
  const [memberSearch, setMemberSearch]   = useState('')
  const [memberFilter, setMemberFilter]   = useState('all')
  const [memberPage, setMemberPage]       = useState(1)
  const [memberTotal, setMemberTotal]     = useState(0)
  const [loadingMembers, setLoadingMembers] = useState(false)
  const [fetchingFor, setFetchingFor]     = useState<string|null>(null)

  /* message modal */
  const [modalMember, setModalMember]   = useState<any>(null)
  const [modalMessages, setModalMessages] = useState<any[]>([])
  const [modalLoading, setModalLoading] = useState(false)
  const [modalPage, setModalPage]       = useState(1)
  const [modalTotal, setModalTotal]     = useState(0)

  /* load feed data */
  const loadFeed = async () => {
    try {
      const [s, c, i, st] = await Promise.all([
        api.get('/scrapper/sources?platform=telegram'),
        api.get('/scrapper/content?platform=telegram&per_page=30'),
        api.get('/scrapper/indicators?platform=telegram&per_page=20'),
        api.get('/scrapper/stats'),
      ])
      setSources(s.data); setContent(c.data.content || [])
      setIndicators(i.data.indicators || []); setStats(st.data)
    } catch {}
  }

  /* load members */
  const loadMembers = async (page = 1) => {
    setLoadingMembers(true)
    try {
      const params: any = { page, per_page: 20 }
      if (memberSearch)                  params.search           = memberSearch
      if (memberFilter !== 'all')        params.criticality_flag = memberFilter
      const [m, ms] = await Promise.all([
        api.get('/scrapper/members', { params }),
        api.get('/scrapper/members/stats/summary'),
      ])
      setMembers(m.data.members || [])
      setMemberTotal(m.data.total || 0)
      setMemberStats(ms.data)
      setMemberPage(page)
    } catch {} finally { setLoadingMembers(false) }
  }

  useEffect(() => {
    loadFeed()
    pollRef.current = setInterval(loadFeed, 15000)
    return () => clearInterval(pollRef.current)
  }, [])

  useEffect(() => { if (tab === 'members') loadMembers(1) }, [tab, memberFilter])

  /* add source */
  const addSource = async () => {
    if (!identifier.trim()) return
    setAdding(true)
    try {
      await api.post('/scrapper/sources', { platform: 'telegram', identifier: identifier.trim() })
      setIdentifier('')
      await loadFeed()
    } catch (e: any) { alert(e.response?.data?.detail || 'Failed') }
    finally { setAdding(false) }
  }

  /* scrape */
  const scrape = async (sourceId: string) => {
    setScraping(sourceId)
    try {
      const r = await api.post(`/scrapper/sources/${sourceId}/scrape?limit=50`)
      alert(`Scraped ${r.data.messages_scraped} messages. ${r.data.flagged} flagged.`)
      await loadFeed()
    } catch {} finally { setScraping(null) }
  }

  /* fetch members */
  const fetchMembers = async (sourceId: string) => {
    setFetchingFor(sourceId)
    try {
      const r = await api.post(`/scrapper/sources/${sourceId}/fetch-members`)
      alert(`Fetched ${r.data.total} members from ${r.data.channel_id}${r.data.status==='demo' ? ' (demo mode)' : ''}`)
      await loadMembers(1)
    } catch (e: any) { alert(e.response?.data?.detail || 'Failed') }
    finally { setFetchingFor(null) }
  }

  /* open messages modal */
  const openMessages = async (member: any, page = 1) => {
    setModalMember(member); setModalLoading(true); setModalMessages([]); setModalPage(page)
    try {
      const r = await api.get(`/scrapper/members/${member.telegram_id}/messages`, {
        params: { page, per_page: 20 }
      })
      setModalMessages(r.data.messages || [])
      setModalTotal(r.data.total || 0)
    } catch {} finally { setModalLoading(false) }
  }

  const searchMembers = () => loadMembers(1)

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-blue-950 flex items-center justify-center">
          <i className="ti ti-brand-telegram text-blue-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Telegram Intelligence Dashboard</h1>
          <p className="text-gray-500 text-sm">
            Real-time monitoring · Member profiling · Behavioral analysis · IOC extraction
          </p>
        </div>
        <div className="ml-auto flex gap-2">
          {stats && (
            <>
              <div className="card px-3 py-2 text-center">
                <div className="text-lg font-bold text-red-400">{stats.flagged_content||0}</div>
                <div className="text-xs text-gray-500">Flagged</div>
              </div>
              <div className="card px-3 py-2 text-center">
                <div className="text-lg font-bold text-amber-400">{stats.high_risk_indicators||0}</div>
                <div className="text-xs text-gray-500">High IOCs</div>
              </div>
              {memberStats && (
                <div className="card px-3 py-2 text-center">
                  <div className="text-lg font-bold text-blue-400">{memberStats.total||0}</div>
                  <div className="text-xs text-gray-500">Members</div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Add source */}
      <div className="card p-4 mb-5 border-blue-900">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <i className="ti ti-brand-telegram absolute left-3 top-1/2 -translate-y-1/2 text-blue-400" />
            <input value={identifier} onChange={e => setIdentifier(e.target.value)}
              onKeyDown={e => e.key==='Enter' && addSource()}
              placeholder="@channel_username  or  t.me/joinchat/abc  or  @BotName"
              className="input-field pl-10" />
          </div>
          <button onClick={addSource} disabled={!identifier.trim() || adding} className="btn-primary px-5">
            {adding ? <><span className="spinner w-4 h-4" />Adding…</> : <><i className="ti ti-plus" />Monitor</>}
          </button>
        </div>
        <p className="text-xs text-gray-600 mt-2">
          <i className="ti ti-info-circle mr-1" />
          After adding a channel, click <strong className="text-blue-400">Fetch Members</strong> in
          Sources tab to build member profiles. Requires TELEGRAM_API_ID in .env for live data.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800 mb-5">
        {([
          { id:'feed',       label:'Live feed',       count: content.length     },
          { id:'members',    label:'Member analysis', count: memberTotal        },
          { id:'indicators', label:'Indicators',      count: indicators.length  },
          { id:'sources',    label:'Sources',         count: sources.length     },
        ] as const).map(t => (
          <button key={t.id} onClick={() => setTab(t.id as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab===t.id
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}>
            {t.label}
            {t.count > 0 && (
              <span className="ml-1.5 text-xs bg-gray-800 text-gray-400 px-1.5 py-0.5 rounded-full">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Feed tab ── */}
      {tab === 'feed' && (
        <div className="space-y-3">
          {content.length === 0 ? (
            <div className="card p-10 text-center text-gray-500">
              <i className="ti ti-brand-telegram text-5xl block mb-3 opacity-20" />
              <p className="font-medium text-white mb-1">No messages yet</p>
              <p className="text-sm">Add a channel above and click Scrape in Sources tab</p>
            </div>
          ) : content.map((c: any) => (
            <div key={c.id} className={`card p-4 border ${
              c.risk_score>=70?'border-red-900 bg-red-950/10':
              c.risk_score>=40?'border-amber-900 bg-amber-950/10':'border-gray-800'}`}>
              <div className="flex items-start gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  c.risk_score>=70?'bg-red-950':c.risk_score>=40?'bg-amber-950':'bg-gray-800'}`}>
                  <i className="ti ti-brand-telegram text-sm text-blue-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className={`badge ${CATEGORY_COLORS[c.category]||'badge-gray'} text-xs`}>
                      {c.category?.replace(/_/g,' ')}
                    </span>
                    <span className={`text-xs font-bold ${RISK_COLOR(c.risk_score)}`}>
                      Risk: {c.risk_score}/100
                    </span>
                    {c.is_flagged && <span className="badge badge-red text-xs">⚠ FLAGGED</span>}
                    {c.author && <span className="text-xs text-blue-400 font-mono">@{c.author}</span>}
                    <span className="text-xs text-gray-600 ml-auto">
                      {new Date(c.scraped_at).toLocaleTimeString('en-IN')}
                    </span>
                  </div>
                  <p className="text-sm text-gray-300 leading-relaxed break-words">{c.content_text}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Member Analysis tab ── */}
      {tab === 'members' && (
        <>
          {/* Member stats row */}
          {memberStats && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
              {[
                { label:'Total members',  value: memberStats.total,          color:'text-white'      },
                { label:'🔴 Critical',    value: memberStats.critical,       color:'text-red-400'    },
                { label:'🟡 Suspicious',  value: memberStats.suspicious,     color:'text-amber-400'  },
                { label:'🟢 Normal',      value: memberStats.normal,         color:'text-green-400'  },
                { label:'Total messages', value: memberStats.total_messages,  color:'text-blue-400'   },
              ].map(s => (
                <div key={s.label} className="card p-3 text-center">
                  <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                  <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Search + filter */}
          <div className="flex gap-3 mb-4 flex-wrap">
            <div className="relative flex-1 min-w-48">
              <i className="ti ti-search absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500 text-xs" />
              <input value={memberSearch}
                onChange={e => setMemberSearch(e.target.value)}
                onKeyDown={e => e.key==='Enter' && searchMembers()}
                placeholder="Search by username, name, or Telegram ID…"
                className="input-field pl-7 text-sm" />
            </div>
            <select value={memberFilter} onChange={e => setMemberFilter(e.target.value)}
              className="select-field text-sm w-44">
              <option value="all">All members</option>
              <option value="critical">🔴 Critical only</option>
              <option value="suspicious">🟡 Suspicious only</option>
              <option value="normal">🟢 Normal only</option>
              <option value="unknown">⚪ Unknown only</option>
            </select>
            <button onClick={searchMembers} className="btn-secondary text-sm px-4">
              <i className="ti ti-filter" />Filter
            </button>
          </div>

          {/* Members table */}
          <div className="card overflow-hidden">
            {/* Header */}
            <div className="grid grid-cols-[200px_100px_110px_80px_1fr_100px_100px] gap-2
                            px-4 py-2.5 border-b border-gray-800
                            text-xs font-semibold text-gray-500 uppercase tracking-wider">
              <span>Profile</span>
              <span>Unique ID</span>
              <span>Criticality</span>
              <span>Messages</span>
              <span>Threat indicators</span>
              <span>Last active</span>
              <span>Action</span>
            </div>

            {loadingMembers ? (
              <div className="p-8 text-center text-gray-500">
                <span className="spinner w-6 h-6 block mx-auto mb-2" />Loading members…
              </div>
            ) : members.length === 0 ? (
              <div className="p-8 text-center text-gray-500 text-sm">
                <i className="ti ti-users-off text-3xl block mb-2 opacity-30" />
                No members found. Add a channel and click
                <strong className="text-blue-400 mx-1">Fetch Members</strong>
                in the Sources tab.
              </div>
            ) : members.map((m: any, i: number) => {
              const crit = CRIT[m.criticality_flag] || CRIT.unknown
              return (
                <div key={m.telegram_id}
                  className={`grid grid-cols-[200px_100px_110px_80px_1fr_100px_100px] gap-2
                              px-4 py-3 items-center text-sm
                              ${i < members.length-1 ? 'border-b border-gray-800' : ''}
                              hover:bg-gray-800/30 transition-colors`}>

                  {/* Profile */}
                  <div className="flex items-center gap-2 min-w-0">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center
                                    flex-shrink-0 border ${crit.badge}`}>
                      <span className="text-xs font-bold">
                        {(m.first_name||m.username||'?')[0].toUpperCase()}
                      </span>
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-white truncate">
                        {m.first_name} {m.last_name}
                      </div>
                      {m.username && (
                        <div className="text-[10px] text-blue-400 font-mono truncate">@{m.username}</div>
                      )}
                    </div>
                  </div>

                  {/* Unique ID */}
                  <span className="font-mono text-xs text-gray-400">{m.telegram_id}</span>

                  {/* Criticality */}
                  <div className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${crit.dot}`} />
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${crit.badge}`}>
                      {m.criticality_flag?.toUpperCase()}
                    </span>
                  </div>

                  {/* Messages */}
                  <span className={`text-sm font-bold text-center ${RISK_COLOR(m.risk_score)}`}>
                    {m.message_count}
                  </span>

                  {/* Threat indicators */}
                  <div className="flex flex-wrap gap-1">
                    {m.extracted_phones?.slice(0,2).map((p:string,j:number) => (
                      <span key={j} className="text-[10px] bg-amber-950 border border-amber-800
                                                text-amber-300 rounded px-1.5 py-0.5 font-mono">
                        📞 {p}
                      </span>
                    ))}
                    {m.extracted_upis?.slice(0,2).map((u:string,j:number) => (
                      <span key={j} className="text-[10px] bg-red-950 border border-red-800
                                                text-red-300 rounded px-1.5 py-0.5 font-mono">
                        💸 {u}
                      </span>
                    ))}
                    {m.extracted_wallets?.slice(0,1).map((w:string,j:number) => (
                      <span key={j} className="text-[10px] bg-orange-950 border border-orange-800
                                                text-orange-300 rounded px-1.5 py-0.5 font-mono">
                        ₿ {w.slice(0,12)}…
                      </span>
                    ))}
                    {(!m.extracted_phones?.length && !m.extracted_upis?.length && !m.extracted_wallets?.length) && (
                      <span className="text-[10px] text-gray-600">None detected</span>
                    )}
                  </div>

                  {/* Last active */}
                  <span className="text-[10px] text-gray-500">
                    {m.last_active
                      ? new Date(m.last_active).toLocaleDateString('en-IN',{day:'numeric',month:'short'})
                      : '—'}
                  </span>

                  {/* Action */}
                  <button
                    onClick={() => openMessages(m)}
                    className="btn-secondary text-xs px-2 py-1.5 flex items-center gap-1">
                    <i className="ti ti-messages text-sm" />Messages
                  </button>
                </div>
              )
            })}
          </div>

          {/* Pagination */}
          {memberTotal > 20 && (
            <div className="flex justify-center gap-2 mt-4">
              {memberPage > 1 && (
                <button onClick={() => loadMembers(memberPage-1)} className="btn-secondary text-xs px-4">
                  ← Prev
                </button>
              )}
              <span className="text-xs text-gray-500 self-center">
                Page {memberPage} of {Math.ceil(memberTotal/20)}
              </span>
              {memberPage < Math.ceil(memberTotal/20) && (
                <button onClick={() => loadMembers(memberPage+1)} className="btn-secondary text-xs px-4">
                  Next →
                </button>
              )}
            </div>
          )}
        </>
      )}

      {/* ── Indicators tab ── */}
      {tab === 'indicators' && (
        <div className="card overflow-hidden">
          <div className="grid grid-cols-[120px_1fr_80px_60px_100px] gap-3 px-4 py-2.5
                          border-b border-gray-800 text-xs font-semibold text-gray-500
                          uppercase tracking-wider">
            <span>Type</span><span>Value</span><span>Platform</span><span>Risk</span><span>First seen</span>
          </div>
          {indicators.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">No indicators yet</div>
          ) : indicators.map((ind:any, i:number) => (
            <div key={ind.id}
              className={`grid grid-cols-[120px_1fr_80px_60px_100px] gap-3 px-4 py-3
                          items-center text-sm ${i<indicators.length-1?'border-b border-gray-800':''}`}>
              <span className="badge badge-blue text-xs capitalize">
                {ind.indicator_type?.replace(/_/g,' ')}
              </span>
              <span className="font-mono text-xs text-white truncate">{ind.value}</span>
              <span className="text-xs text-gray-400 capitalize">{ind.platform}</span>
              <span className={`text-xs font-bold ${RISK_COLOR(ind.risk_score)}`}>
                {ind.risk_score?.toFixed(0)}
              </span>
              <span className="text-xs text-gray-600">
                {new Date(ind.first_seen).toLocaleDateString('en-IN')}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* ── Sources tab ── */}
      {tab === 'sources' && (
        <div className="card overflow-hidden">
          {sources.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">No channels added yet.</div>
          ) : sources.map((s:any, i:number) => (
            <div key={s.id}
              className={`flex items-center gap-3 px-4 py-3
                          ${i<sources.length-1?'border-b border-gray-800':''}`}>
              <div className="w-8 h-8 rounded-full bg-blue-950 flex items-center justify-center flex-shrink-0">
                <i className="ti ti-brand-telegram text-blue-400 text-sm" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-white">{s.display_name}</div>
                <div className="text-xs text-gray-500 font-mono">{s.identifier}</div>
              </div>
              <span className="text-xs text-gray-500">{s.message_count} msgs</span>
              {s.is_monitoring && (
                <span className="flex items-center gap-1 text-xs text-green-400">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse inline-block" />Live
                </span>
              )}
              <button onClick={() => scrape(s.id)} disabled={scraping===s.id}
                className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1">
                {scraping===s.id ? <><span className="spinner w-3 h-3" />Scraping…</> : <><i className="ti ti-download" />Scrape</>}
              </button>
              <button onClick={() => fetchMembers(s.id)} disabled={fetchingFor===s.id}
                className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1">
                {fetchingFor===s.id ? <><span className="spinner w-3 h-3" />Fetching…</> : <><i className="ti ti-users" />Fetch members</>}
              </button>
              <button onClick={() => api.delete(`/scrapper/sources/${s.id}`).then(loadFeed)}
                className="text-red-400 hover:text-red-300 text-xs px-2">
                <i className="ti ti-trash" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* ── Message History Modal ── */}
      {modalMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          onClick={e => { if (e.target === e.currentTarget) setModalMember(null) }}>
          <div className="absolute inset-0 bg-black/70" />
          <div className="relative bg-gray-900 border border-gray-700 rounded-2xl
                          w-full max-w-2xl max-h-[80vh] flex flex-col shadow-2xl">

            {/* Modal header */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-gray-800">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center border
                              ${(CRIT[modalMember.criticality_flag]||CRIT.unknown).badge}`}>
                <span className="text-sm font-bold">
                  {(modalMember.first_name||modalMember.username||'?')[0].toUpperCase()}
                </span>
              </div>
              <div>
                <div className="text-white font-semibold">
                  {modalMember.first_name} {modalMember.last_name}
                  {modalMember.username && <span className="text-blue-400 ml-2 text-sm">@{modalMember.username}</span>}
                </div>
                <div className="text-xs text-gray-500">
                  ID: {modalMember.telegram_id} ·
                  <span className={`ml-1 font-semibold ${
                    (CRIT[modalMember.criticality_flag]||CRIT.unknown).badge.includes('red') ? 'text-red-400' :
                    (CRIT[modalMember.criticality_flag]||CRIT.unknown).badge.includes('amber') ? 'text-amber-400' :
                    (CRIT[modalMember.criticality_flag]||CRIT.unknown).badge.includes('green') ? 'text-green-400' : 'text-gray-400'
                  }`}>{(CRIT[modalMember.criticality_flag]||CRIT.unknown).label}</span>
                  · {modalTotal} messages
                </div>
              </div>
              <button onClick={() => setModalMember(null)}
                className="ml-auto text-gray-500 hover:text-white p-1">
                <i className="ti ti-x text-xl" />
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {modalLoading ? (
                <div className="text-center py-8 text-gray-500">
                  <span className="spinner w-6 h-6 block mx-auto mb-2" />Loading messages…
                </div>
              ) : modalMessages.length === 0 ? (
                <div className="text-center py-8 text-gray-500 text-sm">No messages found</div>
              ) : modalMessages.map((msg:any) => (
                <div key={msg.id} className={`rounded-xl p-3 border text-sm ${
                  msg.is_flagged ? 'border-red-900 bg-red-950/20' : 'border-gray-800 bg-gray-800/50'
                }`}>
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    {msg.is_flagged && <span className="badge badge-red text-[10px]">⚠ FLAGGED</span>}
                    <span className={`text-xs font-bold ${RISK_COLOR(msg.risk_score)}`}>
                      Risk: {msg.risk_score?.toFixed(0)}/100
                    </span>
                    <span className="badge badge-gray text-[10px] capitalize">{msg.message_type}</span>
                    <span className="text-[10px] text-gray-600 ml-auto">
                      {msg.scraped_at ? new Date(msg.scraped_at).toLocaleString('en-IN') : ''}
                    </span>
                  </div>
                  <p className="text-gray-300 break-words leading-relaxed">{msg.message_text}</p>
                  {/* IOCs in this message */}
                  {(msg.extracted_upis?.length || msg.extracted_phones?.length || msg.extracted_wallets?.length) > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-gray-700">
                      {msg.extracted_phones?.map((p:string,j:number) => (
                        <span key={j} className="text-[10px] bg-amber-950 border border-amber-800
                                                  text-amber-300 rounded px-1.5 py-0.5 font-mono">📞 {p}</span>
                      ))}
                      {msg.extracted_upis?.map((u:string,j:number) => (
                        <span key={j} className="text-[10px] bg-red-950 border border-red-800
                                                  text-red-300 rounded px-1.5 py-0.5 font-mono">💸 {u}</span>
                      ))}
                      {msg.extracted_wallets?.map((w:string,j:number) => (
                        <span key={j} className="text-[10px] bg-orange-950 border border-orange-800
                                                  text-orange-300 rounded px-1.5 py-0.5 font-mono">₿ {w.slice(0,16)}…</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Modal pagination */}
            {modalTotal > 20 && (
              <div className="flex justify-center gap-2 px-5 py-3 border-t border-gray-800">
                {modalPage > 1 && (
                  <button onClick={() => openMessages(modalMember, modalPage-1)}
                    className="btn-secondary text-xs px-4">← Prev</button>
                )}
                <span className="text-xs text-gray-500 self-center">
                  {modalPage} / {Math.ceil(modalTotal/20)}
                </span>
                {modalPage < Math.ceil(modalTotal/20) && (
                  <button onClick={() => openMessages(modalMember, modalPage+1)}
                    className="btn-secondary text-xs px-4">Next →</button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
