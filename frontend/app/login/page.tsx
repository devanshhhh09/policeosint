'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authAPI } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'

export default function LoginPage() {
  const [badge, setBadge]     = useState('')
  const [password, setPass]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const { setAuth }           = useAuthStore()
  const router                = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const res = await authAPI.login(badge, password)
      const { access_token, refresh_token, user } = res.data
      setAuth(access_token, refresh_token, user)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.')
    } finally { setLoading(false) }
  }

  const fill = (b: string, p: string) => { setBadge(b); setPass(p) }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center
                          mx-auto mb-4 shadow-lg shadow-blue-900/40">
            <i className="ti ti-shield-lock text-white text-3xl" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">PoliceOSINT</h1>
          <p className="text-gray-400 mt-1 text-sm">AI-Powered Cyber Crime Investigation Platform</p>
          <div className="flex justify-center gap-2 mt-3 flex-wrap">
            {['GPCSSI', 'Gurugram Cyber Cell', 'CERT'].map(t => (
              <span key={t} className="text-xs text-blue-400 bg-blue-950 border
                                       border-blue-900 px-2 py-0.5 rounded-full">{t}</span>
            ))}
          </div>
        </div>

        <div className="card p-8">
          <h2 className="text-sm font-semibold text-white mb-5 flex items-center gap-2">
            <i className="ti ti-id-badge text-blue-400" />Officer Login
          </h2>

          {error && (
            <div className="bg-red-950 border border-red-800 text-red-300 rounded-lg
                            px-4 py-3 mb-4 text-sm flex items-center gap-2">
              <i className="ti ti-alert-circle" />{error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="text-xs text-gray-400 mb-1.5 block font-medium">
                Badge / Employee ID
              </label>
              <div className="relative">
                <i className="ti ti-id-badge-2 absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input type="text" value={badge} onChange={e => setBadge(e.target.value)}
                  className="input-field pl-10" placeholder="e.g. GGN/CYB/2024/001" required />
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-400 mb-1.5 block font-medium">Password</label>
              <div className="relative">
                <i className="ti ti-lock absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input type="password" value={password} onChange={e => setPass(e.target.value)}
                  className="input-field pl-10" placeholder="••••••••" required />
              </div>
            </div>
            <button type="submit" disabled={loading}
              className="w-full btn-primary justify-center py-3 mt-2">
              {loading
                ? <><span className="spinner w-4 h-4" />Authenticating…</>
                : <><i className="ti ti-login" />Login to Platform</>}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-gray-800">
            <p className="text-xs text-gray-600 mb-3 text-center">Demo credentials — click to fill</p>
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'Super Admin',   badge: 'GGN/CYB/ADMIN/001', pass: 'Admin@1234' },
                { label: 'Inspector',     badge: 'GGN/CYB/2024/001',  pass: 'Inspector@1234' },
                { label: 'Analyst',       badge: 'GGN/CYB/2024/002',  pass: 'Analyst@1234' },
                { label: 'GPCSSI Intern', badge: 'GPCSSI/2025/001',   pass: 'Intern@1234' },
              ].map(d => (
                <button key={d.label} type="button" onClick={() => fill(d.badge, d.pass)}
                  className="text-left text-xs bg-gray-800 hover:bg-gray-700 border
                             border-gray-700 rounded-lg px-3 py-2 transition-colors">
                  <div className="font-medium text-gray-300">{d.label}</div>
                  <div className="text-gray-600 font-mono text-[10px] mt-0.5 truncate">{d.badge}</div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-xs text-gray-700 text-center mt-4">
          Authorised personnel only · All access is logged and audited
        </p>
      </div>
    </div>
  )
}
