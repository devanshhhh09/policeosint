'use client'
import { useState, useEffect } from 'react'
import { casesAPI, api } from '@/lib/api'

const REPORT_TYPES = [
  {
    id:      'fir_support',
    label:   'FIR Support Report',
    icon:    'ti-file-report',
    color:   'text-red-400',
    bg:      'bg-red-950/30',
    border:  'border-red-900',
    desc:    'IPC sections · Evidence checklist · Notice templates · Escalation · Signature block',
    pdf_endpoint: 'fir-pdf',
    json_endpoint:'fir-notes',
  },
  {
    id:      'intelligence',
    label:   'Intelligence Report',
    icon:    'ti-file-analytics',
    color:   'text-blue-400',
    bg:      'bg-blue-950/30',
    border:  'border-blue-900',
    desc:    'OSINT findings · Risk scores · Sources queried · Investigation summary',
    pdf_endpoint: 'intelligence-pdf',
    json_endpoint: null,
  },
  {
    id:      'suspect_profile',
    label:   'Suspect Profile',
    icon:    'ti-user-shield',
    color:   'text-purple-400',
    bg:      'bg-purple-950/30',
    border:  'border-purple-900',
    desc:    'Digital identifiers · Risk assessment · Modus operandi · Arrest grounds',
    pdf_endpoint: 'suspect-pdf',
    json_endpoint:'suspect-profile',
  },
  {
    id:      'fraud',
    label:   'Fraud Investigation',
    icon:    'ti-file-dollar',
    color:   'text-amber-400',
    bg:      'bg-amber-950/30',
    border:  'border-amber-900',
    desc:    'Transaction graph · Mule accounts · Financial trail · VASP contacts',
    pdf_endpoint: 'fraud-pdf',
    json_endpoint: null,
  },
  {
    id:      'threat',
    label:   'Threat Report',
    icon:    'ti-file-shield',
    color:   'text-green-400',
    bg:      'bg-green-950/30',
    border:  'border-green-900',
    desc:    'Threat actor profile · MITRE ATT&CK mapping · IOC list · Countermeasures',
    pdf_endpoint: 'threat-pdf',
    json_endpoint: null,
  },
  {
    id:      'evidence_summary',
    label:   'Evidence Summary',
    icon:    'ti-certificate',
    color:   'text-teal-400',
    bg:      'bg-teal-950/30',
    border:  'border-teal-900',
    desc:    'Chain of custody · SHA256 verification · Exhibit register · Integrity status',
    pdf_endpoint: 'evidence-pdf',
    json_endpoint: null,
  },
]

export default function ReportsPage() {
  const [cases, setCases]         = useState<any[]>([])
  const [caseId, setCaseId]       = useState('')
  const [generating, setGenerating] = useState<string | null>(null)
  const [preview, setPreview]     = useState<any>(null)
  const [previewType, setPreviewType] = useState<string | null>(null)
  const [error, setError]         = useState('')

  useEffect(() => {
    casesAPI.list({ per_page: 50 })
      .then(r => { const cases = r.data.cases || []; setCases(cases); if (cases.length) setCaseId(cases[0].id) })
      .catch(() => {})
  }, [])

  const selectedCase = cases.find(c => c.id === caseId)

  const downloadPDF = async (pdfEndpoint: string, label: string) => {
    if (!caseId) { setError('Select a case first'); return }
    setGenerating(label); setError('')
    try {
      const res = await api.get(`/reports/${caseId}/download/${pdfEndpoint}`, {
        responseType: 'blob'
      })
      const url  = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href  = url
      link.setAttribute('download', `${label.replace(/\s/g,'_')}_${selectedCase?.case_number?.replace(/\//g,'_')}.pdf`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (e: any) {
      if (e.response?.status === 503) {
        setError('PDF generation unavailable. ReportLab not installed in container. Use JSON preview instead.')
      } else {
        setError(e.response?.data?.detail || 'PDF generation failed')
      }
    } finally { setGenerating(null) }
  }

  const previewJSON = async (jsonEndpoint: string, type: string) => {
    if (!caseId) { setError('Select a case first'); return }
    setGenerating(type); setPreview(null); setPreviewType(null); setError('')
    try {
      const res = await api.get(`/reports/${caseId}/${jsonEndpoint}`)
      setPreview(res.data)
      setPreviewType(type)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to generate report')
    } finally { setGenerating(null) }
  }

  const handleGenerate = async (r: any) => {
    if (!caseId) { setError('Select a case first'); return }
    if (r.pdf_endpoint) {
      await downloadPDF(r.pdf_endpoint, r.label)
    } else if (r.json_endpoint) {
      await previewJSON(r.json_endpoint, r.id)
    } else {
      setError(`${r.label} generation failed. Please try again.`)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-blue-950 flex items-center justify-center">
          <i className="ti ti-file-report text-blue-400 text-xl" />
        </div>
        <div>
          <h1 className="page-title">Report Generator</h1>
          <p className="text-gray-500 text-sm">Court-ready PDF reports · FIR support · Intelligence · Suspect profiles</p>
        </div>
      </div>

      {/* Case selector */}
      <div className="card p-5 mb-6">
        <label className="text-xs text-gray-400 mb-2 block font-medium">
          Select case to generate report for *
        </label>
        <div className="flex gap-3 items-center flex-wrap">
          <select value={caseId} onChange={e => { setCaseId(e.target.value); setPreview(null); setError('') }}
            className="select-field flex-1 max-w-lg">
            <option value="">— Select a case —</option>
            {cases.map(c => (
              <option key={c.id} value={c.id}>
                {c.case_number} — {c.title}
              </option>
            ))}
          </select>
          {selectedCase && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span className={`badge ${selectedCase.priority==='critical'?'badge-red':selectedCase.priority==='high'?'badge-amber':'badge-gray'}`}>
                {selectedCase.priority}
              </span>
              <span className="badge badge-blue">{selectedCase.status}</span>
            </div>
          )}
        </div>
        {error && (
          <div className="mt-3 p-3 bg-red-950/30 border border-red-900 rounded-lg text-red-400 text-sm">
            <i className="ti ti-alert-circle mr-2" />{error}
          </div>
        )}
      </div>

      {/* Report types */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {REPORT_TYPES.map(r => (
          <div key={r.id} className={`card p-5 border ${r.border} ${r.bg}`}>
            <i className={`ti ${r.icon} text-2xl ${r.color} mb-3 block`} />
            <h3 className="text-sm font-semibold text-white mb-1">{r.label}</h3>
            <p className="text-xs text-gray-500 mb-4 leading-relaxed">{r.desc}</p>
            <div className="flex gap-2">
              {r.pdf_endpoint && (
                <button
                  onClick={() => downloadPDF(r.pdf_endpoint!, r.label)}
                  disabled={generating === r.label || !caseId}
                  className="btn-primary text-xs py-2 px-3 flex items-center gap-1.5 flex-1 justify-center">
                  {generating === r.label
                    ? <><span className="spinner w-3 h-3" />Generating…</>
                    : <><i className="ti ti-download" />Download PDF</>}
                </button>
              )}
              {r.json_endpoint && (
                <button
                  onClick={() => previewJSON(r.json_endpoint!, r.id)}
                  disabled={generating === r.id || !caseId}
                  className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5 flex-1 justify-center">
                  {generating === r.id
                    ? <><span className="spinner w-3 h-3" />Loading…</>
                    : <><i className="ti ti-eye" />Preview</>}
                </button>
              )}

            </div>
          </div>
        ))}
      </div>

      {/* JSON Preview */}
      {preview && previewType && (
        <div className="card overflow-hidden">
          <div className="px-5 py-4 bg-gray-800 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <i className="ti ti-file-text text-blue-400" />
              {REPORT_TYPES.find(r => r.id === previewType)?.label} — Preview
            </h2>
            <div className="flex gap-2">
              {REPORT_TYPES.find(r => r.id === previewType)?.pdf_endpoint && (
                <button
                  onClick={() => downloadPDF(
                    REPORT_TYPES.find(r => r.id === previewType)!.pdf_endpoint!,
                    REPORT_TYPES.find(r => r.id === previewType)!.label
                  )}
                  className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5">
                  <i className="ti ti-download" />Download PDF
                </button>
              )}
              <button onClick={() => setPreview(null)}
                className="btn-secondary text-xs px-3 py-1.5">
                <i className="ti ti-x" />Close
              </button>
            </div>
          </div>

          <div className="p-5 space-y-5">
            {/* Generated at */}
            <div className="flex items-center gap-3 text-xs text-gray-500 bg-gray-800 rounded-lg p-3">
              <i className="ti ti-calendar text-blue-400" />
              Generated: {new Date(preview.generated_at || Date.now()).toLocaleString('en-IN')}
              <span className="mx-2">·</span>
              <i className="ti ti-user text-blue-400" />
              By: {preview.generated_by || preview.case_number}
            </div>

            {/* Case details */}
            {preview.case_details && (
              <PreviewSection title="Case Details" icon="ti-folder-open">
                <KVTable rows={Object.entries(preview.case_details)} />
              </PreviewSection>
            )}

            {/* Victim */}
            {preview.victim_details && (
              <PreviewSection title="Victim Details" icon="ti-user">
                <KVTable rows={Object.entries(preview.victim_details)} />
              </PreviewSection>
            )}

            {/* IPC sections */}
            {preview.applicable_sections?.length > 0 && (
              <PreviewSection title="Applicable Sections" icon="ti-scale">
                <div className="space-y-2">
                  {preview.applicable_sections.map((s: any, i: number) => (
                    <div key={i} className="flex items-start gap-3 p-3 bg-gray-800 rounded-lg">
                      <span className="badge badge-purple font-mono text-xs flex-shrink-0">§ {s.section}</span>
                      <span className="text-sm text-gray-300">{s.description}</span>
                    </div>
                  ))}
                </div>
              </PreviewSection>
            )}

            {/* Legal provisions */}
            {preview.legal_provisions?.length > 0 && (
              <PreviewSection title="Legal Provisions" icon="ti-gavel">
                <div className="flex flex-wrap gap-2">
                  {preview.legal_provisions.map((p: string, i: number) => (
                    <span key={i} className="badge badge-blue text-xs">{p}</span>
                  ))}
                </div>
              </PreviewSection>
            )}

            {/* Evidence checklist */}
            {preview.digital_evidence_checklist?.length > 0 && (
              <PreviewSection title="Digital Evidence Checklist" icon="ti-checklist">
                <div className="space-y-1">
                  {preview.digital_evidence_checklist.map((item: string, i: number) => (
                    <div key={i} className="flex items-center gap-2 text-sm text-gray-300 py-1">
                      <div className="w-4 h-4 border border-gray-600 rounded flex-shrink-0 flex items-center justify-center">
                        <i className="ti ti-check text-green-400 text-xs" />
                      </div>
                      {item}
                    </div>
                  ))}
                </div>
              </PreviewSection>
            )}

            {/* Recommended actions */}
            {preview.recommended_actions?.length > 0 && (
              <PreviewSection title="Recommended Actions" icon="ti-list-check">
                <div className="space-y-1">
                  {preview.recommended_actions.map((a: string, i: number) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-gray-300 py-1">
                      <span className="text-blue-400 font-bold flex-shrink-0 w-5">{i+1}.</span>{a}
                    </div>
                  ))}
                </div>
              </PreviewSection>
            )}

            {/* Notice templates */}
            {preview.notice_templates && (
              <PreviewSection title="Notice Templates (u/s 91 CrPC)" icon="ti-mail">
                {Object.entries(preview.notice_templates).map(([key, text]: any) => (
                  <div key={key} className="mb-3">
                    <div className="text-xs text-gray-500 mb-1 capitalize font-medium">{key.replace(/_/g,' ')}</div>
                    <div className="bg-gray-800 rounded-lg p-3 text-sm text-gray-300 border border-blue-900/50">
                      {text}
                    </div>
                  </div>
                ))}
              </PreviewSection>
            )}

            {/* Escalation */}
            {preview.escalation && (
              <PreviewSection title="Escalation Required" icon="ti-arrow-up-circle">
                <div className="flex flex-wrap gap-2">
                  {Object.entries(preview.escalation)
                    .filter(([,v]) => v === true)
                    .map(([k]) => (
                    <span key={k} className="badge badge-amber text-xs uppercase">{k.replace(/_/g,' ')}</span>
                  ))}
                  {Object.values(preview.escalation).every(v => !v) && (
                    <span className="text-green-400 text-sm">No escalation required</span>
                  )}
                </div>
              </PreviewSection>
            )}

            {/* Suspect profile specific sections */}
            {preview.known_identifiers && (
              <PreviewSection title="Known Digital Identifiers" icon="ti-fingerprint">
                <KVTable rows={
                  Object.entries(preview.known_identifiers)
                    .filter(([,v]: any) => v.length > 0)
                    .map(([k,v]: any) => [k.replace(/_/g,' '), v.join(', ')])
                } />
              </PreviewSection>
            )}

            {preview.modus_operandi && (
              <PreviewSection title="Modus Operandi" icon="ti-script">
                <p className="text-sm text-gray-300 leading-relaxed bg-gray-800 p-4 rounded-lg">
                  {preview.modus_operandi}
                </p>
              </PreviewSection>
            )}

            {preview.arrest_grounds && (
              <PreviewSection title="Grounds for Arrest" icon="ti-gavel">
                {preview.arrest_grounds.map((g: string, i: number) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-gray-300 py-1">
                    <span className="text-red-400 font-bold flex-shrink-0 w-5">{i+1}.</span>{g}
                  </div>
                ))}
              </PreviewSection>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function PreviewSection({ title, icon, children }: { title:string; icon:string; children:any }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2 pb-2 border-b border-gray-800">
        <i className={`ti ${icon} text-blue-400`} />{title}
      </h3>
      {children}
    </div>
  )
}

function KVTable({ rows }: { rows: any[] }) {
  return (
    <table className="w-full text-sm">
      <tbody>
        {rows.map(([k,v],i) => (
          <tr key={i} className="border-b border-gray-800/50 last:border-0">
            <td className="py-2 text-gray-500 w-44 capitalize align-top pr-4">
              {String(k).replace(/_/g,' ')}
            </td>
            <td className="py-2 text-white font-medium align-top">{String(v)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
