'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { dashboardAPI, api } from '@/lib/api'

const QUICK = [
  { label:'Internet Scam Hub', icon:'ti-world-search',    href:'/net-scrapper/telegram', color:'text-blue-400',   hot:true  },
  { label:'UPI Fraud',         icon:'ti-qrcode',          href:'/investigate/upi',       color:'text-red-400'          },
  { label:'IP Intel',          icon:'ti-server',          href:'/investigate/ip',        color:'text-green-400'        },
  { label:'Identity Intel',    icon:'ti-user-search',     href:'/investigate/identity',  color:'text-purple-400'       },
  { label:'Threat Intel',      icon:'ti-bug',             href:'/threat',                color:'text-red-400'          },
  { label:'Crypto Trace',      icon:'ti-currency-bitcoin',href:'/investigate/crypto',    color:'text-amber-400'        },
  { label:'Entity Graph',      icon:'ti-topology-star',   href:'/graph',                 color:'text-purple-400'       },
  { label:'AI Copilot',        icon:'ti-robot',           href:'/ai',                    color:'text-pink-400'         },
]

const STATUS_CLS: Record<string,string> = {
  active:'badge-blue', open:'badge-blue', closed:'badge-green',
  under_review:'badge-amber', escalated:'badge-red', draft:'badge-gray',
}
const PRIORITY_CLS: Record<string,string> = {
  critical:'text-red-400 font-bold', high:'text-orange-400 font-semibold',
  medium:'text-amber-400', low:'text-green-400',
}
const TYPE_ICONS: Record<string,string> = {
  upi_fraud:'ti-qrcode', phishing:'ti-fish', ransomware:'ti-lock',
  investment_fraud:'ti-trending-up', loan_scam:'ti-coin',
  data_breach:'ti-database-leak', cyber_crime:'ti-bug',
  crypto_fraud:'ti-currency-bitcoin', other:'ti-folder',
}
const SEV_CLS: Record<string,string> = {
  critical:'border-red-900 bg-red-950/30',
  high:'border-orange-900 bg-orange-950/20',
  medium:'border-amber-900 bg-amber-950/20',
  low:'border-gray-800 bg-gray-900',
}
const SEV_ICON: Record<string,{icon:string,color:string}> = {
  critical:{icon:'ti-alert-triangle', color:'text-red-400'},
  high:    {icon:'ti-alert-circle',   color:'text-orange-400'},
  medium:  {icon:'ti-info-circle',    color:'text-amber-400'},
  low:     {icon:'ti-bell',           color:'text-gray-400'},
}
const INV_ICONS: Record<string,string> = {
  identity:'ti-user-search', ip:'ti-server', domain:'ti-world',
  upi_fraud:'ti-qrcode', crypto:'ti-currency-bitcoin',
  threat:'ti-bug', dark_web:'ti-moon', geoint:'ti-map-pin',
  social_media:'ti-brand-twitter', media:'ti-photo-scan',
}

export default function Dashboard() {
  const { user }  = useAuthStore()
  const router    = useRouter()
  const [stats, setStats]       = useState<any>(null)
  const [alerts, setAlerts]     = useState<any[]>([])
  const [timeline, setTimeline] = useState<any[]>([])
  const [casesByTime, setCasesByTime] = useState<any[]>([])
  const [activeInvs, setActiveInvs]   = useState<any[]>([])
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState<'alerts'|'timeline'|'cases_time'|'investigations'>('alerts')

  useEffect(() => {
    Promise.all([
      dashboardAPI.stats().catch(() => null),
      api.get('/dashboard/alerts').catch(() => ({ data: { alerts: [] } })),
      api.get('/dashboard/timeline').catch(() => ({ data: { events: [] } })),
      api.get('/dashboard/cases-by-time').catch(() => ({ data: { days: [] } })),
      api.get('/dashboard/active-investigations').catch(() => ({ data: [] })),
    ]).then(([s, a, t, c, i]) => {
      setStats(s?.data)
      setAlerts(a?.data?.alerts || [])
      setTimeline(t?.data?.events || [])
      setCasesByTime(c?.data?.days || [])
      setActiveInvs(Array.isArray(i?.data) ? i.data : [])
    }).finally(() => setLoading(false))
  }, [])

  const netScams = stats?.internet_scams || {}

  return (
    <div className="p-6 space-y-6">
      {/* Greeting */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Welcome back, {user?.full_name?.split(' ').at(-1) || 'Officer'} 👋
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {user?.station_name || 'Gurugram Cyber Cell'} ·{' '}
            {new Date().toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric'})}
          </p>
        </div>
        <div className="hidden md:flex items-center gap-2 text-xs text-gray-500
                        bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5">
          <span className="w-2 h-2 rounded-full bg-green-500 inline-block animate-pulse" />
          All systems operational
        </div>
      </div>

      {/* Main stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label:'Active cases',
            value: loading ? '…' : stats?.cases?.active ?? 0,
            sub:   `${stats?.cases?.new_this_week ?? 0} new this week`,
            color:'text-white', icon:'ti-folder-open', bg:'bg-blue-950/30',
            href: '/cases',
          },
          {
            label:'Critical cases',
            value: loading ? '…' : stats?.cases?.critical ?? 0,
            sub:   'Require immediate action',
            color:'text-red-400', icon:'ti-alert-triangle', bg:'bg-red-950/30',
            href: '/cases',
          },
          {
            label:'Investigations',
            value: loading ? '…' : stats?.investigations?.last_30_days ?? 0,
            sub:   `${stats?.investigations?.running ?? 0} running now`,
            color:'text-purple-400', icon:'ti-search', bg:'bg-purple-950/30',
            href: '/cases',
          },
          {
            label:'Amount tracked',
            value: loading ? '…' : `₹${stats?.financial?.total_loss_lakh ?? 0}L`,
            sub:   `${stats?.financial?.cases_with_amount ?? 0} cases`,
            color:'text-amber-400', icon:'ti-currency-rupee', bg:'bg-amber-950/30',
            href: '/reports',
          },
        ].map(s => (
          <div key={s.label} onClick={() => router.push(s.href)}
            className={`card p-4 ${s.bg} cursor-pointer hover:opacity-90 transition-opacity`}>
            <div className="flex items-start justify-between mb-2">
              <span className="text-xs text-gray-500">{s.label}</span>
              <i className={`ti ${s.icon} text-lg ${s.color} opacity-70`} />
            </div>
            <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-gray-600 text-xs mt-1">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Internet Scam Intelligence row */}
      {netScams.available !== false && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="section-title mb-0 flex items-center gap-2">
              <i className="ti ti-world-search text-blue-400" />
              Internet Scam Intelligence
            </h2>
            <button onClick={() => router.push('/net-scrapper/telegram')}
              className="text-xs text-blue-400 hover:text-blue-300">
              Open hub →
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              { label:'Scams found',    value: netScams.total_scams_found ?? 0,  color:'text-white'      },
              { label:'Flagged',        value: netScams.flagged           ?? 0,  color:'text-red-400'    },
              { label:'Critical',       value: netScams.critical          ?? 0,  color:'text-red-400'    },
              { label:'High risk IOCs', value: netScams.high_risk_iocs    ?? 0,  color:'text-amber-400'  },
              { label:'Fake jobs',      value: netScams.by_category?.fake_job          ?? 0, color:'text-amber-400' },
              { label:'Investment scam',value: netScams.by_category?.investment_scam   ?? 0, color:'text-red-400'   },
              { label:'Sources live',   value: netScams.active_sources    ?? 0,  color:'text-green-400'  },
            ].map(s => (
              <div key={s.label}
                onClick={() => router.push('/net-scrapper/telegram')}
                className="card p-3 text-center cursor-pointer hover:border-gray-700 transition-colors">
                <div className={`text-xl font-bold ${s.color}`}>
                  {loading ? '…' : s.value}
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick investigate */}
      <div>
        <h2 className="section-title">Quick investigate</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {QUICK.map(m => (
            <button key={m.label} onClick={() => router.push(m.href)}
              className="card-hover p-4 text-left group relative">
              {(m as any).hot && (
                <span className="absolute top-2 right-2 text-[10px] bg-blue-600 text-white
                                 px-1.5 py-0.5 rounded font-bold">LIVE</span>
              )}
              <i className={`ti ${m.icon} text-2xl ${m.color} mb-2 block
                            group-hover:scale-110 transition-transform`} />
              <div className="text-sm font-semibold text-white">{m.label}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Tabs section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Left: tabs */}
        <div>
          <div className="flex gap-1 border-b border-gray-800 mb-4 overflow-x-auto">
            {([
              {id:'alerts',         label:'Alerts'},
              {id:'timeline',       label:'Timeline'},
              {id:'cases_time',     label:'Cases by time'},
              {id:'investigations', label:'Investigations'},
            ] as const).map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`px-3 py-2 text-xs font-semibold border-b-2 -mb-px whitespace-nowrap transition-colors ${
                  tab===t.id
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                }`}>{t.label}</button>
            ))}
          </div>

          {/* Alerts */}
          {tab === 'alerts' && (
            loading ? <div className="text-center py-8 text-gray-500 text-sm">Loading…</div>
            : alerts.length === 0 ? (
              <div className="card p-6 text-center text-gray-500 text-sm">No active alerts</div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {alerts.map((a: any) => {
                  const sty = SEV_CLS[a.severity]  || SEV_CLS.low
                  const ico = SEV_ICON[a.severity] || SEV_ICON.low
                  return (
                    <div key={a.id}
                      onClick={() => a.url && router.push(a.url)}
                      className={`border rounded-xl p-3.5 cursor-pointer hover:opacity-90 transition-opacity ${sty}`}>
                      <div className="flex items-start gap-2.5">
                        <i className={`ti ${ico.icon} ${ico.color} text-lg mt-0.5 flex-shrink-0`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-white leading-snug">{a.title}</p>
                          <p className="text-xs text-gray-400 mt-0.5 truncate">{a.description}</p>
                        </div>
                        {!a.is_read && (
                          <span className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0 mt-1.5" />
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          )}

          {/* Timeline */}
          {tab === 'timeline' && (
            loading ? <div className="text-center py-8 text-gray-500 text-sm">Loading…</div>
            : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {timeline.map((e: any, i: number) => (
                  <div key={i}
                    onClick={() => e.url && router.push(e.url)}
                    className="flex items-start gap-3 p-3 card cursor-pointer hover:border-gray-700">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center
                                    flex-shrink-0 ${
                      e.color==='red'    ? 'bg-red-950'    :
                      e.color==='purple' ? 'bg-purple-950' :
                      e.color==='blue'   ? 'bg-blue-950'   : 'bg-gray-800'
                    }`}>
                      <i className={`ti ${e.icon} text-sm ${
                        e.color==='red'    ? 'text-red-400'    :
                        e.color==='purple' ? 'text-purple-400' :
                        e.color==='blue'   ? 'text-blue-400'   : 'text-gray-400'
                      }`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white">{e.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5 truncate">{e.description}</p>
                    </div>
                    <span className="text-xs text-gray-600 flex-shrink-0">
                      {e.timestamp
                        ? new Date(e.timestamp).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})
                        : ''}
                    </span>
                  </div>
                ))}
              </div>
            )
          )}

          {/* Cases by time */}
          {tab === 'cases_time' && (
            loading ? <div className="text-center py-8 text-gray-500 text-sm">Loading…</div>
            : casesByTime.length === 0 ? (
              <div className="card p-6 text-center text-gray-500 text-sm">No cases in last 30 days</div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {casesByTime.map((day: any) => (
                  <div key={day.date} className="card overflow-hidden">
                    <div className="flex items-center gap-3 px-4 py-2.5 bg-gray-800/50 border-b border-gray-800">
                      <span className="text-xs font-semibold text-white">
                        {new Date(day.date).toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'})}
                      </span>
                      <span className="badge badge-blue text-xs">{day.total} cases</span>
                      {day.critical > 0 && <span className="badge badge-red text-xs">{day.critical} critical</span>}
                      {day.active   > 0 && <span className="text-xs text-green-400">{day.active} active</span>}
                    </div>
                    {day.cases.slice(0,3).map((c: any, i: number) => (
                      <div key={i}
                        onClick={() => router.push('/cases')}
                        className={`flex items-center gap-2 px-4 py-2 cursor-pointer
                                    hover:bg-gray-800/50 text-xs
                                    ${i < Math.min(day.cases.length,3)-1 ? 'border-b border-gray-800/50' : ''}`}>
                        <span className="font-mono text-gray-600 flex-shrink-0">{c.case_number}</span>
                        <span className="text-white truncate flex-1">{c.title}</span>
                        <span className={`flex-shrink-0 ${PRIORITY_CLS[c.priority] || 'text-gray-400'}`}>
                          {c.priority}
                        </span>
                      </div>
                    ))}
                    {day.cases.length > 3 && (
                      <div className="px-4 py-1.5 text-xs text-gray-600">
                        +{day.cases.length - 3} more cases
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )
          )}

          {/* Investigations */}
          {tab === 'investigations' && (
            loading ? <div className="text-center py-8 text-gray-500 text-sm">Loading…</div>
            : activeInvs.length === 0 ? (
              <div className="card p-6 text-center text-gray-500 text-sm">No investigations yet</div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {activeInvs.map((inv: any) => (
                  <div key={inv.id}
                    onClick={() => router.push(`/investigate/${inv.investigation_type.toLowerCase()}`)}
                    className="card p-3 cursor-pointer hover:border-gray-700 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        inv.risk_score >= 70 ? 'bg-red-950' :
                        inv.risk_score >= 40 ? 'bg-amber-950' : 'bg-gray-800'
                      }`}>
                        <i className={`ti ${INV_ICONS[inv.investigation_type] || 'ti-search'} text-sm ${
                          inv.risk_score >= 70 ? 'text-red-400' :
                          inv.risk_score >= 40 ? 'text-amber-400' : 'text-gray-400'
                        }`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-semibold text-white capitalize">
                            {inv.investigation_type.replace(/_/g,' ')}
                          </span>
                          <span className={`badge text-[10px] ${
                            inv.status==='completed' ? 'badge-green' :
                            inv.status==='running'   ? 'badge-blue'  :
                            inv.status==='failed'    ? 'badge-red'   : 'badge-gray'
                          }`}>{inv.status}</span>
                        </div>
                        <p className="text-xs text-gray-500 truncate">{inv.query}</p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <span className={`text-sm font-bold ${
                          inv.risk_score >= 70 ? 'text-red-400' :
                          inv.risk_score >= 40 ? 'text-amber-400' : 'text-green-400'
                        }`}>{inv.risk_score?.toFixed(0)}</span>
                        <div className="text-[10px] text-gray-600">risk</div>
                      </div>
                    </div>
                    {inv.summary && (
                      <p className="text-[10px] text-gray-600 mt-1.5 truncate">{inv.summary}</p>
                    )}
                  </div>
                ))}
              </div>
            )
          )}
        </div>

        {/* Right: Recent cases */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="section-title mb-0">Recent cases</h2>
            <button onClick={() => router.push('/cases')}
              className="text-xs text-blue-400 hover:text-blue-300">View all →</button>
          </div>
          <div className="card overflow-hidden mb-4">
            {loading ? (
              <div className="p-6 text-center text-gray-500 text-sm">Loading…</div>
            ) : (stats?.recent_cases || []).length === 0 ? (
              <div className="p-6 text-center text-gray-500 text-sm">
                <i className="ti ti-folder-off text-3xl block mb-2" />No cases yet
              </div>
            ) : (stats?.recent_cases || []).map((c: any, i: number) => (
              <div key={c.id} onClick={() => router.push(`/cases/${c.id}`)}
                className={`flex items-center gap-3 px-4 py-3 cursor-pointer
                            hover:bg-gray-800/50 transition-colors
                            ${i<(stats.recent_cases.length-1)?'border-b border-gray-800':''}`}>
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${
                  c.priority==='critical' ? 'bg-red-950' : 'bg-gray-800'
                }`}>
                  <i className={`ti ${TYPE_ICONS[c.case_type]||'ti-folder'} text-sm ${
                    c.priority==='critical' ? 'text-red-400' : 'text-gray-400'
                  }`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white font-medium truncate">{c.title}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="font-mono text-[10px] text-gray-600">{c.case_number}</span>
                    {c.amount_lost && (
                      <span className="text-[10px] text-amber-400">
                        ₹{Number(c.amount_lost).toLocaleString('en-IN')}
                      </span>
                    )}
                    <span className="text-[10px] text-gray-600">
                      {new Date(c.created_at).toLocaleDateString('en-IN')}
                    </span>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <span className={`badge text-xs ${STATUS_CLS[c.status]||'badge-gray'}`}>
                    {c.status}
                  </span>
                  <span className={`text-[10px] font-semibold ${PRIORITY_CLS[c.priority]||'text-gray-400'}`}>
                    {c.priority}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Case type breakdown */}
          {stats?.cases?.by_type && Object.keys(stats.cases.by_type).length > 0 && (
            <div className="card p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Cases by type
              </h3>
              <div className="space-y-2">
                {Object.entries(stats.cases.by_type)
                  .sort(([,a],[,b]) => (b as number)-(a as number))
                  .map(([type, count]: any) => (
                  <div key={type} className="flex items-center gap-3">
                    <i className={`ti ${TYPE_ICONS[type]||'ti-folder'} text-sm text-gray-500 flex-shrink-0`} />
                    <span className="text-xs text-gray-500 flex-1 capitalize">{type.replace(/_/g,' ')}</span>
                    <div className="flex-1 max-w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-600 rounded-full"
                        style={{width:`${Math.round(count/stats.cases.total*100)}%`}} />
                    </div>
                    <span className="text-xs text-gray-400 w-4 text-right">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
