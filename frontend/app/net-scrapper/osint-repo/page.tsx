'use client'
import { useState } from 'react'
import { api } from '@/lib/api'

const TOOLS = [
  { id:'sherlock',     label:'Sherlock',       icon:'ti-user-search',    color:'text-blue-400',   input:'username', placeholder:'suspect_username',       desc:'Username search across 400+ platforms' },
  { id:'maigret',      label:'Maigret',        icon:'ti-user-circle',    color:'text-purple-400', input:'username', placeholder:'target_username',         desc:'Deep username OSINT with relationship mapping' },
  { id:'holehe',       label:'Holehe',         icon:'ti-mail-search',    color:'text-green-400',  input:'email',    placeholder:'suspect@email.com',       desc:'Find accounts linked to email address' },
  { id:'theharvester', label:'TheHarvester',   icon:'ti-rake',           color:'text-amber-400',  input:'domain',   placeholder:'suspect-domain.com',      desc:'Email & subdomain reconnaissance' },
]

export default function OsintRepoPage() {
  const [results, setResults]   = useState<Record<string, any>>({})
  const [loading, setLoading]   = useState<string | null>(null)
  const [inputs, setInputs]     = useState<Record<string, string>>({})

  const run = async (tool: typeof TOOLS[0]) => {
    const target = inputs[tool.id]?.trim()
    if (!target) return
    setLoading(tool.id)
    try {
      const payload: any = {}
      payload[tool.input] = target
      if (tool.id === 'theharvester') payload.sources = 'google,bing,linkedin'
      const res = await api.post(`/scrapper/osint/${tool.id}`, payload)
      setResults(prev => ({ ...prev, [tool.id]: res.data }))
    } catch (e: any) {
      setResults(prev => ({ ...prev, [tool.id]: { error: e.response?.data?.detail || 'Failed' } }))
    } finally { setLoading(null) }
  }

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-green-950 flex items-center justify-center">
          <i className="ti ti-git-branch text-green-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">OSINT Repository Orchestrator</h1>
          <p className="text-gray-500 text-sm">TheHarvester · Sherlock · Maigret · Holehe — unified interface</p>
        </div>
      </div>

      <div className="card p-4 mb-5 border-amber-900 bg-amber-950/10">
        <p className="text-xs text-amber-400 flex items-center gap-2">
          <i className="ti ti-info-circle text-lg" />
          Tools run in demo mode until installed. Install with:
          <code className="font-mono bg-gray-800 px-2 py-0.5 rounded">
            pip install sherlock-project maigret holehe theHarvester
          </code>
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {TOOLS.map(tool => (
          <div key={tool.id} className="card p-5">
            <div className="flex items-center gap-3 mb-3">
              <i className={`ti ${tool.icon} text-2xl ${tool.color}`} />
              <div>
                <h3 className="text-sm font-bold text-white">{tool.label}</h3>
                <p className="text-xs text-gray-500">{tool.desc}</p>
              </div>
            </div>
            <div className="flex gap-2 mb-3">
              <input
                value={inputs[tool.id] || ''}
                onChange={e => setInputs(prev => ({ ...prev, [tool.id]: e.target.value }))}
                onKeyDown={e => e.key === 'Enter' && run(tool)}
                placeholder={tool.placeholder}
                className="input-field flex-1 text-xs" />
              <button onClick={() => run(tool)}
                disabled={!inputs[tool.id]?.trim() || loading === tool.id}
                className="btn-primary text-xs px-4">
                {loading === tool.id
                  ? <><span className="spinner w-3 h-3" />Running…</>
                  : <><i className="ti ti-play" />Run</>}
              </button>
            </div>

            {results[tool.id] && (
              <div className="bg-gray-800 rounded-lg p-3 text-xs">
                {results[tool.id].error ? (
                  <p className="text-red-400">{results[tool.id].error}</p>
                ) : (
                  <>
                    {results[tool.id].status === 'demo' && (
                      <p className="text-amber-400 mb-2">⚠ Demo data — tool not installed</p>
                    )}
                    {results[tool.id].note && (
                      <p className="text-gray-500 mb-2 text-[10px]">{results[tool.id].note}</p>
                    )}
                    {(results[tool.id].found_on || results[tool.id].results || []).length > 0 && (
                      <div>
                        <p className="text-green-400 font-medium mb-1">
                          Found: {(results[tool.id].found_on || results[tool.id].results || []).length} results
                        </p>
                        <div className="space-y-0.5 max-h-32 overflow-y-auto">
                          {(results[tool.id].found_on || results[tool.id].results || []).slice(0,10).map((r: any, i: number) => (
                            <div key={i} className="text-gray-300">
                              {typeof r === 'string' ? r : `${r.platform}: ${r.url}`}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {results[tool.id].emails?.length > 0 && (
                      <div className="mt-2">
                        <p className="text-blue-400 font-medium mb-1">Emails:</p>
                        {results[tool.id].emails.slice(0,5).map((e: string, i: number) => (
                          <div key={i} className="text-gray-300">{e}</div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
