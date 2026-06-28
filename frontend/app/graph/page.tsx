'use client'
import { useState, useEffect, useRef } from 'react'
import { api } from '@/lib/api'

const NODE_COLORS: Record<string, string> = {
  person:  '#3B82F6', email:   '#10B981', phone:   '#F59E0B',
  upi:     '#EF4444', wallet:  '#F97316', social:  '#EC4899',
  domain:  '#14B8A6', ip:      '#8B5CF6', company: '#6366F1',
  device:  '#84CC16', victim:  '#6B7280', aggregator:'#EF4444',
  destination:'#7C3AED', mule: '#DC2626',
}
const NODE_ICONS: Record<string, string> = {
  person:'ti-user', email:'ti-mail', phone:'ti-phone', upi:'ti-qrcode',
  wallet:'ti-currency-bitcoin', social:'ti-brand-instagram', domain:'ti-world',
  ip:'ti-server', company:'ti-building', device:'ti-device-laptop',
  victim:'ti-user-x', mule:'ti-users', aggregator:'ti-git-merge',
  destination:'ti-flag',
}

// Simple force-layout positions
function layoutNodes(nodes: any[], width = 600, height = 400) {
  const positions: Record<string, {x:number, y:number}> = {}
  const centre = nodes.find(n => n.is_centre || n.id === 'centre')
  if (centre) {
    positions[centre.id] = { x: width/2, y: height/2 }
    const others = nodes.filter(n => n.id !== centre.id)
    others.forEach((n, i) => {
      const angle  = (i / others.length) * Math.PI * 2
      const radius = Math.min(width, height) * 0.35
      positions[n.id] = {
        x: width/2  + Math.cos(angle) * radius,
        y: height/2 + Math.sin(angle) * radius,
      }
    })
  } else {
    nodes.forEach((n, i) => {
      const angle  = (i / nodes.length) * Math.PI * 2
      const radius = Math.min(width, height) * 0.4
      positions[n.id] = { x: width/2 + Math.cos(angle)*radius, y: height/2 + Math.sin(angle)*radius }
    })
  }
  return positions
}

export default function GraphPage() {
  const [entityId, setEntityId]   = useState('')
  const [entityType, setEntityType] = useState('upi')
  const [loading, setLoading]     = useState(false)
  const [graph, setGraph]         = useState<any>(null)
  const [selected, setSelected]   = useState<any>(null)
  const [error, setError]         = useState('')
  const svgRef = useRef<SVGSVGElement>(null)

  const W = 640, H = 420

  const QUICK = [
    { label:'suspect@paytm',  id:'suspect@paytm',  type:'upi'    },
    { label:'rahul@gmail.com',id:'rahul@gmail.com', type:'email'  },
    { label:'+919876543210',  id:'+919876543210',   type:'phone'  },
    { label:'8.8.8.8',        id:'8.8.8.8',         type:'ip'     },
  ]

  const load = async (id?: string, type?: string) => {
    const qid   = id   || entityId.trim()
    const qtype = type || entityType
    if (!qid) return
    setLoading(true); setGraph(null); setSelected(null); setError('')
    try {
      const res = await api.get(`/graph/${encodeURIComponent(qid)}`, {
        params: { entity_type: qtype, depth: 2 }
      })
      setGraph(res.data)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load graph')
    } finally { setLoading(false) }
  }

  const positions = graph ? layoutNodes(graph.nodes, W, H) : {}

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-purple-950 flex items-center justify-center">
          <i className="ti ti-topology-star text-purple-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Entity Relationship Graph</h1>
          <p className="text-gray-500 text-sm">Neo4j-powered relationship mapping · Click any node to expand</p>
        </div>
      </div>

      {/* Quick searches */}
      <div className="flex flex-wrap gap-2 mb-4">
        {QUICK.map(q => (
          <button key={q.id} onClick={() => { setEntityId(q.id); setEntityType(q.type); load(q.id, q.type) }}
            className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border
                       border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors">
            <i className={`ti ${NODE_ICONS[q.type] || 'ti-circle'} mr-1`}
               style={{color: NODE_COLORS[q.type]}} />{q.label}
          </button>
        ))}
      </div>

      <div className="card p-4 mb-5">
        <div className="flex gap-3 flex-wrap">
          <select value={entityType} onChange={e => setEntityType(e.target.value)}
            className="select-field w-36">
            {Object.keys(NODE_COLORS).filter(t => !['victim','mule','aggregator','destination'].includes(t))
              .map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input value={entityId} onChange={e => setEntityId(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load()}
            placeholder="UPI ID, email, IP, domain, phone…"
            className="input-field flex-1 min-w-48" />
          <button onClick={() => load()} disabled={!entityId.trim() || loading}
            className="btn-primary px-6">
            {loading ? <><span className="spinner w-4 h-4" />Loading…</> : <><i className="ti ti-topology-star" />Build graph</>}
          </button>
        </div>
        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
      </div>

      {loading && (
        <div className="card p-10 text-center">
          <span className="spinner w-8 h-8 block mx-auto mb-3" />
          <p className="text-gray-400 text-sm">Building entity relationship graph…</p>
        </div>
      )}

      {graph && !loading && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-4 gap-3 mb-5">
            {[
              { label:'Nodes',      value: graph.stats.total_nodes,   color:'text-blue-400'   },
              { label:'Edges',      value: graph.stats.total_edges,   color:'text-green-400'  },
              { label:'High risk',  value: graph.stats.high_risk,     color:'text-red-400'    },
              { label:'Node types', value: graph.stats.node_types?.length || 0, color:'text-purple-400'},
            ].map(s => (
              <div key={s.label} className="card p-3 text-center">
                <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
                <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* SVG Graph */}
            <div className="lg:col-span-2 card overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
                <i className="ti ti-topology-star text-purple-400" />
                <span className="text-sm font-semibold text-white">Relationship graph</span>
                <span className="ml-auto text-xs text-gray-600">Click nodes to inspect</span>
              </div>
              <div className="relative bg-gray-950" style={{height: H}}>
                <svg ref={svgRef} width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
                  {/* Edges */}
                  {graph.edges.map((e: any, i: number) => {
                    const s = positions[e.source || e.from]
                    const t = positions[e.target || e.to]
                    if (!s || !t) return null
                    const mx = (s.x + t.x) / 2
                    const my = (s.y + t.y) / 2
                    return (
                      <g key={i}>
                        <line x1={s.x} y1={s.y} x2={t.x} y2={t.y}
                          stroke="#374151" strokeWidth="1" strokeDasharray="4,2" />
                        {e.label && (
                          <text x={mx} y={my-4} fill="#6B7280" fontSize="8"
                            textAnchor="middle">{e.label}</text>
                        )}
                      </g>
                    )
                  })}
                </svg>
                {/* Nodes as HTML overlays */}
                {graph.nodes.map((n: any) => {
                  const pos   = positions[n.id]
                  if (!pos) return null
                  const color = NODE_COLORS[n.type] || '#6B7280'
                  const isSel = selected?.id === n.id
                  const size  = n.is_centre ? 44 : 34
                  return (
                    <div key={n.id} onClick={() => setSelected(n)}
                      style={{
                        position:'absolute',
                        left: pos.x, top: pos.y,
                        transform:'translate(-50%,-50%)',
                        cursor:'pointer', zIndex: 10,
                      }}>
                      <div style={{
                        width:size, height:size, borderRadius:'50%',
                        background: color+'22',
                        border:`2px solid ${isSel ? '#FBBF24' : color}`,
                        boxShadow: isSel ? `0 0 14px ${color}` : `0 0 6px ${color}44`,
                        display:'flex', alignItems:'center', justifyContent:'center',
                        transition:'all 0.2s',
                      }}>
                        <i className={`ti ${NODE_ICONS[n.type]||'ti-circle'}`}
                           style={{color, fontSize: n.is_centre ? 18 : 13}} />
                      </div>
                      <div style={{
                        textAlign:'center', fontSize:9, color:'#9CA3AF',
                        marginTop:2, maxWidth:70, wordBreak:'break-all', lineHeight:1.2,
                      }}>{n.label}</div>
                      {n.risk_score > 0.7 && (
                        <div style={{
                          position:'absolute', top:-4, right:-4,
                          width:10, height:10, borderRadius:'50%',
                          background:'#EF4444', border:'1px solid #1F2937',
                        }} title="High risk" />
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Node detail */}
            <div className="card p-4">
              {selected ? (
                <>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center"
                      style={{
                        background:(NODE_COLORS[selected.type]||'#6B7280')+'22',
                        border:`2px solid ${NODE_COLORS[selected.type]||'#6B7280'}`,
                      }}>
                      <i className={`ti ${NODE_ICONS[selected.type]||'ti-circle'}`}
                         style={{color:NODE_COLORS[selected.type]||'#6B7280', fontSize:18}} />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-white break-all">{selected.full_label || selected.label}</div>
                      <div className="text-xs text-gray-500 capitalize mt-0.5">{selected.type}</div>
                    </div>
                  </div>

                  {selected.risk_score !== undefined && (
                    <div className="mb-4">
                      <div className="text-xs text-gray-500 mb-1">Risk score</div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                          <div className="h-full rounded-full"
                            style={{
                              width:`${selected.risk_score*100}%`,
                              background: selected.risk_score>0.7?'#EF4444':selected.risk_score>0.4?'#F59E0B':'#10B981',
                            }} />
                        </div>
                        <span className={`text-sm font-bold ${
                          selected.risk_score>0.7?'text-red-400':selected.risk_score>0.4?'text-amber-400':'text-green-400'}`}>
                          {Math.round(selected.risk_score*100)}
                        </span>
                      </div>
                    </div>
                  )}

                  {selected.flags?.length > 0 && (
                    <div className="mb-4">
                      <div className="text-xs text-gray-500 mb-2">Flags</div>
                      <div className="flex flex-wrap gap-1">
                        {selected.flags.map((f:string) => (
                          <span key={f} className="badge badge-red text-[10px]">{f.replace(/_/g,' ')}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="pt-3 border-t border-gray-800">
                    <div className="text-xs text-gray-500 mb-2">Connected to</div>
                    {graph.edges
                      .filter((e:any) => e.source===selected.id || e.target===selected.id ||
                                         e.from===selected.id || e.to===selected.id)
                      .slice(0, 6)
                      .map((e:any, i:number) => {
                        const otherId = e.source===selected.id||e.from===selected.id
                          ? (e.target||e.to) : (e.source||e.from)
                        const other = graph.nodes.find((n:any) => n.id===otherId)
                        return other ? (
                          <div key={i} onClick={() => setSelected(other)}
                            className="flex items-center gap-2 py-1.5 cursor-pointer
                                       hover:text-white text-gray-400 text-xs group">
                            <i className={`ti ${NODE_ICONS[other.type]||'ti-circle'} flex-shrink-0`}
                               style={{color:NODE_COLORS[other.type]||'#6B7280'}} />
                            <span className="flex-1 truncate group-hover:text-white">{other.label}</span>
                            <span className="text-gray-700 text-[10px] capitalize">{e.relationship||e.label}</span>
                          </div>
                        ) : null
                      })}
                  </div>

                  <div className="mt-4 flex gap-2">
                    <button onClick={() => load(selected.full_label||selected.label, selected.type)}
                      className="btn-secondary text-xs flex-1 justify-center">
                      <i className="ti ti-zoom-in" />Expand
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-center py-10 text-gray-500">
                  <i className="ti ti-cursor-text text-3xl block mb-2" />
                  <p className="text-sm">Click any node to inspect</p>
                </div>
              )}
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-3 mt-4">
            {Object.entries(NODE_COLORS)
              .filter(([t]) => !['aggregator','destination'].includes(t))
              .map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs text-gray-500">
                <div className="w-2.5 h-2.5 rounded-full" style={{background:color}} />
                <span className="capitalize">{type}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
