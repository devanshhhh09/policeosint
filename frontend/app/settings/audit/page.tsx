'use client'
import { useEffect, useState } from 'react'
import { auditAPI } from '@/lib/api'

export default function AuditPage() {
  const [logs, setLogs]     = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    auditAPI.list().then(r => setLogs(r.data.logs || [])).catch(() => {}).finally(() => setLoading(false))
  }, [])
  return (
    <div className="p-6">
      <h1 className="page-title mb-5">Audit Logs</h1>
      <div className="card overflow-hidden">
        <div className="grid grid-cols-[150px_100px_120px_1fr_80px] gap-3 px-4 py-2.5
                        border-b border-gray-800 text-xs font-semibold text-gray-500 uppercase tracking-wider">
          <span>Time</span><span>Officer</span><span>Action</span><span>Description</span><span>Status</span>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-500 text-sm">Loading…</div>
        ) : logs.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">No audit logs found</div>
        ) : logs.map((l, i) => (
          <div key={l.id} className={`grid grid-cols-[150px_100px_120px_1fr_80px] gap-3 px-4 py-3
                                      items-center text-sm ${i<logs.length-1?'border-b border-gray-800':''}`}>
            <span className="text-xs text-gray-500 font-mono">
              {new Date(l.created_at).toLocaleString('en-IN')}
            </span>
            <span className="text-gray-400 text-xs truncate">{l.user_id?.slice(0,8)}…</span>
            <span className="badge badge-blue text-xs">{l.action}</span>
            <span className="text-gray-300 text-xs truncate">{l.description || '—'}</span>
            <span className={`text-xs font-medium ${l.status==='success'?'text-green-400':'text-red-400'}`}>
              {l.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
