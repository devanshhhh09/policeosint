'use client'
import { useEffect, useState } from 'react'

interface NodeInfo {
  id:            string
  address:       string
  risk_score:    number
  is_mixer:      boolean
  is_high_risk:  boolean
  received_usd:  number
  sent_usd:      number
  exchange:      string
  chain:         string
  tx_count:      number
  label?:        string
  is_center:     boolean
}

interface Props {
  node:      NodeInfo | null
  onClose:   () => void
  onRecenter:(address: string) => void
}

export default function InfoDrawer({ node, onClose, onRecenter }: Props) {
  const [copied, setCopied] = useState(false)

  useEffect(() => { setCopied(false) }, [node])

  if (!node) return null

  const copyAddress = () => {
    navigator.clipboard.writeText(node.address)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const riskColor =
    node.risk_score >= 70 ? 'text-red-400'   :
    node.risk_score >= 40 ? 'text-amber-400' : 'text-green-400'

  const riskBg =
    node.risk_score >= 70 ? 'bg-red-950/40 border-red-800'   :
    node.risk_score >= 40 ? 'bg-amber-950/40 border-amber-800' :
                            'bg-green-950/40 border-green-800'

  const riskLabel =
    node.risk_score >= 70 ? '🔴 HIGH RISK'     :
    node.risk_score >= 40 ? '🟡 SUSPICIOUS'    : '🟢 CLEAN'

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full z-50 w-80
                      bg-gray-900 border-l border-gray-700
                      shadow-2xl flex flex-col">

        {/* Header */}
        <div className={`px-5 py-4 border-b ${riskBg} flex items-center justify-between`}>
          <div>
            <div className="text-xs text-gray-400 mb-1">
              {node.is_center ? 'Nucleus — Starting wallet' : 'Distribution node'}
            </div>
            <div className={`text-sm font-bold ${riskColor}`}>{riskLabel}</div>
          </div>
          <button onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-gray-800">
            <i className="ti ti-x text-xl" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">

          {/* Wallet address */}
          <div>
            <div className="text-xs text-gray-500 mb-1.5 font-medium uppercase tracking-wider">
              Wallet address
            </div>
            <div className="flex items-center gap-2 bg-gray-800 rounded-xl p-3 border border-gray-700">
              <span className="font-mono text-xs text-white break-all flex-1 leading-relaxed">
                {node.address}
              </span>
              <button onClick={copyAddress}
                className={`flex-shrink-0 text-xs px-2 py-1 rounded-lg transition-colors ${
                  copied ? 'bg-green-900 text-green-400' : 'bg-gray-700 text-gray-400 hover:text-white'
                }`}>
                <i className={`ti ${copied ? 'ti-check' : 'ti-copy'} text-sm`} />
              </button>
            </div>
          </div>

          {/* Risk score bar */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-gray-500 uppercase tracking-wider">Risk score</span>
              <span className={`text-sm font-bold ${riskColor}`}>{node.risk_score}/100</span>
            </div>
            <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${node.risk_score}%`,
                  background: node.risk_score >= 70 ? '#EF4444' :
                              node.risk_score >= 40 ? '#F59E0B' : '#10B981',
                }} />
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Received',  value: `$${node.received_usd.toLocaleString('en-IN', {maximumFractionDigits:2})}`, icon: 'ti-arrow-down',   color: 'text-green-400' },
              { label: 'Sent',      value: `$${node.sent_usd.toLocaleString('en-IN',     {maximumFractionDigits:2})}`, icon: 'ti-arrow-up',     color: 'text-red-400'   },
              { label: 'TX count',  value: node.tx_count,                                                               icon: 'ti-arrows-exchange',color:'text-blue-400'  },
              { label: 'Chain',     value: node.chain.toUpperCase(),                                                    icon: 'ti-link',         color: 'text-purple-400'},
            ].map(s => (
              <div key={s.label} className="bg-gray-800 rounded-xl p-3 border border-gray-700">
                <div className="flex items-center gap-1.5 mb-1">
                  <i className={`ti ${s.icon} text-xs ${s.color}`} />
                  <span className="text-[10px] text-gray-500 uppercase tracking-wider">{s.label}</span>
                </div>
                <div className={`text-sm font-bold ${s.color}`}>{String(s.value)}</div>
              </div>
            ))}
          </div>

          {/* Flags */}
          <div className="space-y-2">
            <div className="text-xs text-gray-500 uppercase tracking-wider">Detection flags</div>

            <div className={`flex items-center gap-3 p-3 rounded-xl border ${
              node.is_mixer
                ? 'bg-red-950/40 border-red-800'
                : 'bg-gray-800 border-gray-700'
            }`}>
              <i className={`ti ti-arrows-shuffle text-lg ${
                node.is_mixer ? 'text-red-400' : 'text-gray-500'
              }`} />
              <div>
                <div className={`text-xs font-semibold ${
                  node.is_mixer ? 'text-red-400' : 'text-gray-400'
                }`}>Mixer / Tumbler</div>
                <div className="text-[10px] text-gray-500">
                  {node.is_mixer ? 'DETECTED — Funds obfuscated' : 'Not detected'}
                </div>
              </div>
              <div className="ml-auto">
                {node.is_mixer
                  ? <span className="badge badge-red text-[10px]">YES</span>
                  : <span className="badge badge-green text-[10px]">NO</span>}
              </div>
            </div>

            <div className={`flex items-center gap-3 p-3 rounded-xl border ${
              node.is_high_risk
                ? 'bg-red-950/40 border-red-800'
                : 'bg-gray-800 border-gray-700'
            }`}>
              <i className={`ti ti-shield-exclamation text-lg ${
                node.is_high_risk ? 'text-red-400' : 'text-gray-500'
              }`} />
              <div>
                <div className={`text-xs font-semibold ${
                  node.is_high_risk ? 'text-red-400' : 'text-gray-400'
                }`}>High risk wallet</div>
                <div className="text-[10px] text-gray-500">
                  {node.is_high_risk ? 'Flagged for investigation' : 'No flags'}
                </div>
              </div>
              <div className="ml-auto">
                {node.is_high_risk
                  ? <span className="badge badge-red text-[10px]">YES</span>
                  : <span className="badge badge-green text-[10px]">NO</span>}
              </div>
            </div>
          </div>

          {/* Exchange */}
          {node.exchange && node.exchange !== 'Unknown' && (
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1.5">
                Associated exchange
              </div>
              <div className="flex items-center gap-2 bg-blue-950/40 border border-blue-800
                              rounded-xl p-3">
                <i className="ti ti-building-bank text-blue-400 text-lg" />
                <span className="text-sm text-blue-300 font-medium">{node.exchange}</span>
                <span className="text-[10px] text-gray-500 ml-auto">LEA notice available</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="p-4 border-t border-gray-800 space-y-2">
          {!node.is_center && (
            <button onClick={() => { onRecenter(node.address); onClose() }}
              className="w-full btn-primary justify-center py-2.5">
              <i className="ti ti-atom" />Make this the new center
            </button>
          )}
          <a href={`/investigate/crypto?q=${node.address}`}
            className="w-full btn-secondary justify-center py-2.5 flex items-center gap-2 text-sm">
            <i className="ti ti-search" />Full investigation
          </a>
        </div>
      </div>
    </>
  )
}
