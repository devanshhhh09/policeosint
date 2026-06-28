'use client'
import { useState } from 'react'

const TREE = [
  { id: 'identity', label: 'Identity Intelligence', icon: 'ti-user-search', color: '#3B82F6',
    tools: [
      { name: 'Sherlock',      url: 'https://github.com/sherlock-project/sherlock', tag: 'T', desc: 'Username enumeration' },
      { name: 'Maigret',       url: 'https://github.com/soxoj/maigret',             tag: 'T', desc: 'OSINT from username' },
      { name: 'WhatsMyName',   url: 'https://whatsmyname.app',                      tag: 'T', desc: 'Username search' },
      { name: 'Holehe',        url: 'https://github.com/megadose/holehe',            tag: 'T', desc: 'Email to accounts' },
      { name: 'GHunt',         url: 'https://github.com/mxrch/GHunt',               tag: 'T', desc: 'Google account OSINT' },
      { name: 'IntelX',        url: 'https://intelx.io',                            tag: 'M', desc: 'Search intelligence' },
    ]},
  { id: 'social', label: 'Social Media OSINT', icon: 'ti-brand-twitter', color: '#8B5CF6',
    tools: [
      { name: 'Social Searcher', url: 'https://social-searcher.com', tag: 'T', desc: 'Social media search' },
      { name: 'Tinfoleak',       url: 'https://tinfoleak.com',        tag: 'T', desc: 'Twitter OSINT' },
      { name: 'WhoPostedWhat',   url: 'https://whopostedwhat.com',    tag: 'T', desc: 'Facebook keyword search' },
      { name: 'Osintgram',       url: 'https://github.com/Datalux/Osintgram', tag: 'T', desc: 'Instagram OSINT' },
      { name: 'Maltego',         url: 'https://maltego.com',          tag: 'M', desc: 'Graph-based OSINT' },
    ]},
  { id: 'threat', label: 'Threat Intelligence', icon: 'ti-shield-lock', color: '#EF4444',
    tools: [
      { name: 'OTX AlienVault',  url: 'https://otx.alienvault.com',   tag: 'T', desc: 'Threat feeds' },
      { name: 'VirusTotal',      url: 'https://virustotal.com',        tag: 'T', desc: 'File/URL/IP analysis' },
      { name: 'MISP',            url: 'https://www.misp-project.org',  tag: 'T', desc: 'Threat sharing platform' },
      { name: 'OpenCTI',         url: 'https://filigran.io/solutions/open-cti/', tag: 'T', desc: 'Threat intelligence' },
      { name: 'MalwareBazaar',   url: 'https://bazaar.abuse.ch',       tag: 'T', desc: 'Malware samples' },
      { name: 'Any.run',         url: 'https://app.any.run',           tag: 'M', desc: 'Interactive malware sandbox' },
    ]},
  { id: 'darkweb', label: 'Dark Web Intelligence', icon: 'ti-moon', color: '#6366F1',
    tools: [
      { name: 'Ahmia',           url: 'https://ahmia.fi',              tag: 'T', desc: 'Tor search engine' },
      { name: 'DarkOwl',         url: 'https://darkowl.com',           tag: 'M', desc: 'Dark web monitoring' },
      { name: 'Recorded Future', url: 'https://recordedfuture.com',    tag: 'M', desc: 'Threat intelligence' },
      { name: 'IntelX Darknet',  url: 'https://intelx.io',            tag: 'M', desc: 'Dark web search' },
    ]},
  { id: 'fraud', label: 'Fraud Intelligence', icon: 'ti-qrcode', color: '#F59E0B',
    tools: [
      { name: 'Cybercrime.gov.in',url: 'https://cybercrime.gov.in',   tag: 'T', desc: 'India cyber complaint portal' },
      { name: 'NPCI',             url: 'https://www.npci.org.in',      tag: 'T', desc: 'National Payments Corporation' },
      { name: 'I4C',              url: 'https://www.mha.gov.in/en/commando/cyber-and-information-security-division', tag: 'T', desc: 'Indian Cyber Crime Coordination Centre' },
      { name: '1930 Helpline',    url: 'tel:1930',                     tag: 'T', desc: 'National Cyber Crime Helpline' },
    ]},
  { id: 'crypto', label: 'Crypto Intelligence', icon: 'ti-currency-bitcoin', color: '#10B981',
    tools: [
      { name: 'Blockchain.com',   url: 'https://blockchain.com/explorer', tag: 'T', desc: 'BTC explorer' },
      { name: 'Etherscan',        url: 'https://etherscan.io',          tag: 'T', desc: 'ETH explorer' },
      { name: 'Blockchair',       url: 'https://blockchair.com',        tag: 'T', desc: 'Multi-chain explorer' },
      { name: 'Chainalysis',      url: 'https://chainalysis.com',       tag: 'M', desc: 'Crypto compliance' },
      { name: 'Crystal',          url: 'https://crystalblockchain.com', tag: 'M', desc: 'Blockchain analytics' },
    ]},
  { id: 'media', label: 'Media Intelligence', icon: 'ti-photo-scan', color: '#EC4899',
    tools: [
      { name: 'TinEye',          url: 'https://tineye.com',            tag: 'T', desc: 'Reverse image search' },
      { name: 'PimEyes',         url: 'https://pimeyes.com',           tag: 'M', desc: 'Facial recognition search' },
      { name: 'InVID',           url: 'https://www.invid-project.eu',  tag: 'T', desc: 'Video verification' },
      { name: 'ExifTool',        url: 'https://exiftool.org',          tag: 'T', desc: 'Metadata extraction' },
      { name: 'FotoForensics',   url: 'https://fotoforensics.com',     tag: 'T', desc: 'Image forensics' },
      { name: 'Ghiro',           url: 'https://www.getghiro.org',      tag: 'T', desc: 'Image analysis platform' },
    ]},
  { id: 'geoint', label: 'GEOINT', icon: 'ti-map-pin', color: '#F97316',
    tools: [
      { name: 'Google Earth',    url: 'https://earth.google.com',      tag: 'T', desc: 'Satellite imagery' },
      { name: 'Mapillary',       url: 'https://mapillary.com',         tag: 'T', desc: 'Street-level photos' },
      { name: 'SunCalc',         url: 'https://suncalc.org',           tag: 'T', desc: 'Sun position analysis' },
      { name: 'GeoSpy',          url: 'https://geospy.ai',             tag: 'T', desc: 'AI photo geolocation' },
      { name: 'OpenStreetMap',   url: 'https://openstreetmap.org',     tag: 'T', desc: 'Open mapping' },
      { name: 'Wikimapia',       url: 'https://wikimapia.org',         tag: 'T', desc: 'Collaborative mapping' },
    ]},
  { id: 'domain', label: 'Domain & Network', icon: 'ti-world', color: '#14B8A6',
    tools: [
      { name: 'Whois',           url: 'https://whois.domaintools.com', tag: 'T', desc: 'Domain registration' },
      { name: 'DNSdumpster',     url: 'https://dnsdumpster.com',       tag: 'T', desc: 'DNS reconnaissance' },
      { name: 'Sublist3r',       url: 'https://github.com/aboul3la/Sublist3r', tag: 'T', desc: 'Subdomain enumeration' },
      { name: 'Shodan',          url: 'https://shodan.io',             tag: 'M', desc: 'Device search engine' },
      { name: 'Censys',          url: 'https://censys.io',             tag: 'M', desc: 'Internet scanning' },
      { name: 'crt.sh',          url: 'https://crt.sh',               tag: 'T', desc: 'SSL certificate search' },
      { name: 'URLScan',         url: 'https://urlscan.io',            tag: 'T', desc: 'URL/domain scanner' },
    ]},
  { id: 'docs', label: 'Documentation & Legal', icon: 'ti-file-text', color: '#6B7280',
    tools: [
      { name: 'OpenCorporates',  url: 'https://opencorporates.com',    tag: 'T', desc: 'Company database' },
      { name: 'MCA21',           url: 'https://www.mca.gov.in',        tag: 'T', desc: 'India company registry' },
      { name: 'GSTIN Search',    url: 'https://www.gstin.gov.in',      tag: 'T', desc: 'GST number lookup' },
      { name: 'Court Records',   url: 'https://ecourts.gov.in',        tag: 'T', desc: 'Indian court records' },
    ]},
]

const TAG_CLS: Record<string, string> = {
  T: 'bg-green-950 text-green-400 border border-green-900',
  M: 'bg-blue-950 text-blue-400 border border-blue-900',
  R: 'bg-amber-950 text-amber-400 border border-amber-900',
}

export default function OsintPage() {
  const [open, setOpen]     = useState<string[]>([])
  const [search, setSearch] = useState('')

  const toggle = (id: string) =>
    setOpen(o => o.includes(id) ? o.filter(x => x !== id) : [...o, id])

  const filtered = search
    ? TREE.filter(c =>
        c.label.toLowerCase().includes(search.toLowerCase()) ||
        c.tools.some(t => t.name.toLowerCase().includes(search.toLowerCase()) ||
                          t.desc.toLowerCase().includes(search.toLowerCase()))
      )
    : TREE

  const totalTools = TREE.reduce((a, c) => a + c.tools.length, 0)

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <i className="ti ti-tree text-green-400" />OSINT Framework
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            {totalTools} tools across {TREE.length} categories — click to expand
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setOpen(TREE.map(c => c.id))}
            className="btn-secondary text-xs px-3 py-1.5">Expand all</button>
          <button onClick={() => setOpen([])}
            className="btn-secondary text-xs px-3 py-1.5">Collapse all</button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex gap-4 mb-4">
        {[['T','Free tool'],['M','Membership required'],['R','Registration required']].map(([tag,label]) => (
          <div key={tag} className="flex items-center gap-1.5 text-xs text-gray-500">
            <span className={`badge ${TAG_CLS[tag]} text-[10px]`}>{tag}</span>{label}
          </div>
        ))}
      </div>

      <div className="relative mb-5">
        <i className="ti ti-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search tools and categories…" className="input-field pl-9" />
      </div>

      <div className="space-y-2">
        {filtered.map(cat => {
          const isOpen  = open.includes(cat.id) || !!search
          const tools   = search
            ? cat.tools.filter(t =>
                t.name.toLowerCase().includes(search.toLowerCase()) ||
                t.desc.toLowerCase().includes(search.toLowerCase()) ||
                cat.label.toLowerCase().includes(search.toLowerCase())
              )
            : cat.tools
          return (
            <div key={cat.id} className="card overflow-hidden">
              <button onClick={() => toggle(cat.id)}
                className="w-full flex items-center gap-3 px-4 py-3
                           hover:bg-gray-800/50 transition-colors text-left">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: cat.color+'22', border:`1px solid ${cat.color}44` }}>
                  <i className={`ti ${cat.icon} text-sm`} style={{ color: cat.color }} />
                </div>
                <span className="text-sm font-semibold text-white flex-1">{cat.label}</span>
                <span className="text-xs text-gray-600">{cat.tools.length} tools</span>
                <i className={`ti ti-chevron-down text-gray-500 text-sm transition-transform ${isOpen?'rotate-180':''}`} />
              </button>

              {isOpen && tools.length > 0 && (
                <div className="px-4 pb-4 border-t border-gray-800 pt-3">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {tools.map(tool => (
                      <a key={tool.name} href={tool.url} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-3 p-3 bg-gray-800 hover:bg-gray-750
                                   border border-gray-700 hover:border-gray-600 rounded-lg
                                   transition-colors group">
                        <span className={`badge ${TAG_CLS[tool.tag]} text-[10px] flex-shrink-0`}>{tool.tag}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors">
                            {tool.name}
                          </div>
                          <div className="text-xs text-gray-500 mt-0.5 truncate">{tool.desc}</div>
                        </div>
                        <i className="ti ti-external-link text-gray-600 group-hover:text-gray-400 text-sm flex-shrink-0" />
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
