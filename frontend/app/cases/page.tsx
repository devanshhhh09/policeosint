'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { casesAPI } from '@/lib/api'

const STATUS_CLS: Record<string, string> = {
  active: 'badge-blue', open: 'badge-blue', closed: 'badge-green',
  under_review: 'badge-amber', escalated: 'badge-red', draft: 'badge-gray',
}
const PRIORITY_CLS: Record<string, string> = {
  critical: 'text-red-400 font-bold', high: 'text-orange-400 font-semibold',
  medium: 'text-amber-400', low: 'text-green-400',
}

export default function CasesPage() {
  const router = useRouter()
  const [cases, setCases]         = useState<any[]>([])
  const [loading, setLoading]     = useState(true)
  const [search, setSearch]       = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating]   = useState(false)
  const [form, setForm] = useState({
    title: '', case_type: 'upi_fraud', priority: 'medium',
    victim_name: '', victim_phone: '', amount_lost: '', ipc_sections: '',
  })

  const load = async () => {
    setLoading(true)
    try {
      const res = await casesAPI.list({ per_page: 50 })
      setCases(res.data.cases || [])
    } catch { setCases([]) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const filtered = cases.filter(c =>
    !search ||
    c.title?.toLowerCase().includes(search.toLowerCase()) ||
    c.case_number?.toLowerCase().includes(search.toLowerCase())
  )

  const handleCreate = async () => {
    if (!form.title) return
    setCreating(true)
    try {
      await casesAPI.create({
        ...form,
        ipc_sections: form.ipc_sections.split(',').map(s => s.trim()).filter(Boolean),
      })
      setShowCreate(false)
      setForm({ title:'', case_type:'upi_fraud', priority:'medium', victim_name:'', victim_phone:'', amount_lost:'', ipc_sections:'' })
      load()
    } catch {}
    finally { setCreating(false) }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="page-title">Case Management</h1>
          <p className="text-gray-500 text-sm mt-1">{cases.length} cases total</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <i className="ti ti-plus" />New Case
        </button>
      </div>

      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-sm">
          <i className="ti ti-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by title or case number…" className="input-field pl-9" />
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="grid grid-cols-[130px_1fr_120px_80px_90px] gap-3 px-4 py-2.5
                        border-b border-gray-800 text-xs font-semibold text-gray-500 uppercase tracking-wider">
          <span>Case No.</span><span>Title</span><span>Type</span>
          <span>Priority</span><span>Status</span>
        </div>
        {loading ? (
          <div className="p-10 text-center text-gray-500 text-sm">Loading…</div>
        ) : filtered.length === 0 ? (
          <div className="p-10 text-center text-gray-500 text-sm">
            <i className="ti ti-folder-off text-4xl block mb-3" />No cases found
          </div>
        ) : filtered.map((c, i) => (
          <div key={c.id} onClick={() => router.push(`/cases/${c.id}`)}
            className={`grid grid-cols-[130px_1fr_120px_80px_90px] gap-3 px-4 py-3
                        items-center cursor-pointer hover:bg-gray-800/50 transition-colors
                        ${i < filtered.length - 1 ? 'border-b border-gray-800' : ''}`}>
            <span className="font-mono text-xs text-gray-500">{c.case_number}</span>
            <div>
              <div className="text-sm text-white font-medium truncate">{c.title}</div>
              {c.victim_name && <div className="text-xs text-gray-600 mt-0.5">Victim: {c.victim_name}</div>}
            </div>
            <span className="text-xs text-gray-400 truncate">{c.case_type?.replace(/_/g, ' ')}</span>
            <span className={`text-xs uppercase ${PRIORITY_CLS[c.priority] || 'text-gray-400'}`}>{c.priority}</span>
            <span className={`badge text-xs ${STATUS_CLS[c.status] || 'badge-gray'}`}>{c.status}</span>
          </div>
        ))}
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-lg">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-white">Create New Case</h2>
              <button onClick={() => setShowCreate(false)} className="text-gray-500 hover:text-white">
                <i className="ti ti-x text-xl" />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Case title *</label>
                <input value={form.title} onChange={e => setForm({...form, title: e.target.value})}
                  placeholder="Brief description of the cyber crime" className="input-field" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Case type *</label>
                  <select value={form.case_type}
                    onChange={e => setForm({...form, case_type: e.target.value})}
                    className="select-field w-full">
                    <option value="upi_fraud">UPI Fraud</option>
                    <option value="phishing">Phishing</option>
                    <option value="ransomware">Ransomware</option>
                    <option value="investment_fraud">Investment Fraud</option>
                    <option value="loan_scam">Loan Scam</option>
                    <option value="identity_theft">Identity Theft</option>
                    <option value="data_breach">Data Breach</option>
                    <option value="crypto_fraud">Crypto Fraud</option>
                    <option value="cyber_crime">Cyber Crime</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Priority *</label>
                  <select value={form.priority}
                    onChange={e => setForm({...form, priority: e.target.value})}
                    className="select-field w-full">
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Victim name</label>
                  <input value={form.victim_name}
                    onChange={e => setForm({...form, victim_name: e.target.value})}
                    placeholder="Full name" className="input-field" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Victim phone</label>
                  <input value={form.victim_phone}
                    onChange={e => setForm({...form, victim_phone: e.target.value})}
                    placeholder="+91-XXXXXXXXXX" className="input-field" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Amount lost (₹)</label>
                  <input value={form.amount_lost}
                    onChange={e => setForm({...form, amount_lost: e.target.value})}
                    placeholder="e.g. 420000" className="input-field" />
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">IPC sections</label>
                  <input value={form.ipc_sections}
                    onChange={e => setForm({...form, ipc_sections: e.target.value})}
                    placeholder="419, 420, 66C" className="input-field" />
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={handleCreate} disabled={!form.title || creating}
                className="btn-primary flex-1 justify-center">
                {creating ? <><span className="spinner w-4 h-4" />Creating…</> : <><i className="ti ti-plus" />Create case</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
