'use client'
import { useState, useRef, useEffect } from 'react'
import { api } from '@/lib/api'

interface Msg { role: 'user' | 'assistant'; content: string }

export default function AIPage() {
  const [messages, setMessages] = useState<Msg[]>([{
    role: 'assistant',
    content: 'Namaste! I am PoliceOSINT AI Copilot 🛡️\n\nI can help you:\n• Draft FIR support notes\n• Correlate digital evidence\n• Explain MITRE ATT&CK techniques\n• Suggest investigative next steps\n• Reference Indian cyber laws (IT Act, IPC)\n\nHow can I assist your investigation today?',
  }])
  const [input, setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg) return
    setInput('')
    const next: Msg[] = [...messages, { role: 'user', content: msg }]
    setMessages(next)
    setLoading(true)
    try {
      const res = await api.post('/ai/chat', { messages: next })
      setMessages([...next, { role: 'assistant', content: res.data.message }])
    } catch {
      setMessages([...next, { role: 'assistant', content: '⚠️ AI service unavailable. Add OPENAI_API_KEY to .env or set up Ollama locally.' }])
    } finally { setLoading(false) }
  }

  const QUICK = [
    'Draft FIR notes for UPI fraud case',
    'Explain Section 66D IT Act',
    'What are KYC scam indicators?',
    'MITRE ATT&CK T1566.001 explanation',
  ]

  return (
    <div className="flex flex-col h-full p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <i className="ti ti-robot text-purple-400" />AI Investigation Copilot
          </h1>
          <p className="text-gray-500 text-sm mt-1">OpenAI GPT-4o · Ollama · Local LLM</p>
        </div>
        <button onClick={() => setMessages([{ role:'assistant', content:'Session cleared.' }])}
          className="btn-secondary text-xs px-3 py-1.5">
          <i className="ti ti-refresh mr-1" />Clear
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {QUICK.map(q => (
          <button key={q} onClick={() => send(q)}
            className="text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border
                       border-gray-700 rounded-lg text-gray-300 hover:text-white transition-colors">
            {q}
          </button>
        ))}
      </div>

      <div className="flex-1 card overflow-y-auto p-4 mb-4 min-h-0 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role==='user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0
                            ${m.role==='assistant' ? 'bg-purple-900 text-purple-300' : 'bg-blue-900 text-blue-300'}`}>
              <i className={`ti ${m.role==='assistant' ? 'ti-robot' : 'ti-user'} text-base`} />
            </div>
            <div className={`max-w-[80%] rounded-xl px-4 py-3 text-sm whitespace-pre-wrap leading-relaxed
                            ${m.role==='user'
                              ? 'bg-blue-900/40 text-blue-100 border border-blue-900'
                              : 'bg-gray-800 text-gray-200 border border-gray-700'}`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-900 flex items-center justify-center flex-shrink-0">
              <i className="ti ti-robot text-purple-300 text-base" />
            </div>
            <div className="bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 flex items-center gap-2">
              <span className="spinner w-4 h-4" /><span className="text-sm text-gray-400">Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottom} />
      </div>

      <div className="flex gap-2">
        <input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key==='Enter' && !e.shiftKey && send()}
          placeholder="Ask about a case, IPC section, threat, or investigation step…"
          className="input-field flex-1" disabled={loading} />
        <button onClick={() => send()} disabled={!input.trim() || loading}
          className="btn-primary px-5">
          <i className="ti ti-send" />Send
        </button>
      </div>
    </div>
  )
}
