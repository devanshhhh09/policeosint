'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/authStore'
import { useState } from 'react'

const NAV = [
  { section: 'Overview', items: [
    { label: 'Dashboard',        href: '/dashboard',            icon: 'ti-layout-dashboard' },
    { label: 'Cases',            href: '/cases',                icon: 'ti-folder-open' },
  ]},
  { section: 'Investigate', items: [
    { label: 'Identity Intel',   href: '/investigate/identity', icon: 'ti-user-search' },
    { label: 'Social Media',     href: '/investigate/social',   icon: 'ti-brand-twitter' },
    { label: 'Domain & Website', href: '/investigate/domain',   icon: 'ti-world' },
    { label: 'IP Intelligence',  href: '/investigate/ip',       icon: 'ti-server' },
    { label: 'UPI Fraud',        href: '/investigate/upi',      icon: 'ti-qrcode',          badge: 'HOT' },
    { label: 'Crypto Intel',     href: '/investigate/crypto',   icon: 'ti-currency-bitcoin' },
    { label: 'Media Forensics',  href: '/investigate/media',    icon: 'ti-photo-scan' },
    { label: 'IPDR Analyzer',      href: '/investigate/ipdr',     icon: 'ti-file-search' },
  ]},
  { section: 'Intelligence', items: [
    { label: 'Threat Intel',     href: '/threat',               icon: 'ti-bug' },
    { label: 'Dark Web',         href: '/darkweb',              icon: 'ti-moon' },
    { label: 'GEOINT',           href: '/geoint',               icon: 'ti-map-pin' },
    { label: 'Entity Graph',     href: '/graph',                icon: 'ti-topology-star' },
  ]},
  { section: 'Net Scrapper', items: [
    { label: 'Internet Scam Hub',    href: '/net-scrapper/internet',    icon: 'ti-world-search',    badge: 'NEW' },
    { label: 'Telegram Intel',       href: '/net-scrapper/telegram',    icon: 'ti-brand-telegram' },
    { label: 'X / Twitter Intel',    href: '/net-scrapper/twitter',     icon: 'ti-brand-x' },
    { label: 'Instagram Intel',      href: '/net-scrapper/instagram',   icon: 'ti-brand-instagram' },
    { label: 'OSINT Repo Hub',       href: '/net-scrapper/osint-repo',  icon: 'ti-git-branch' },
    { label: 'Cross-Platform Corr.', href: '/net-scrapper/correlation', icon: 'ti-topology-star-3' },
  ]},
  { section: 'Tools', items: [
    { label: 'OSINT Framework',  href: '/osint',                icon: 'ti-tree' },
    { label: 'AI Copilot',       href: '/ai',                   icon: 'ti-robot',           badge: 'AI' },
    { label: 'Reports',          href: '/reports',              icon: 'ti-file-report' },
    { label: 'Audit Logs',       href: '/settings/audit',       icon: 'ti-clipboard-list' },
  ]},
]

const ROLE_COLORS: Record<string, string> = {
  super_admin:  'bg-red-950 text-red-400',
  commissioner: 'bg-purple-950 text-purple-400',
  inspector:    'bg-blue-950 text-blue-400',
  analyst:      'bg-green-950 text-green-400',
  trainee:      'bg-gray-800 text-gray-400',
}

export default function Sidebar() {
  const pathname         = usePathname()
  const router           = useRouter()
  const { user, logout } = useAuthStore()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside className={`${collapsed ? 'w-14' : 'w-56'} flex-shrink-0 bg-gray-900
                       border-r border-gray-800 flex flex-col transition-all duration-200`}>
      {/* Brand */}
      <div className="p-3 border-b border-gray-800 flex items-center gap-2 min-h-[52px]">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <i className="ti ti-shield-lock text-white text-base" />
        </div>
        {!collapsed && (
          <div className="flex-1 min-w-0">
            <div className="text-blue-400 font-bold text-sm tracking-wider">POLICEOSINT</div>
            <div className="text-gray-600 text-[10px]">GPCSSI · Cyber Cell</div>
          </div>
        )}
        <button onClick={() => setCollapsed(!collapsed)}
          className="text-gray-600 hover:text-gray-400 ml-auto flex-shrink-0">
          <i className={`ti ${collapsed ? 'ti-chevron-right' : 'ti-chevron-left'} text-sm`} />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV.map(section => (
          <div key={section.section} className="mb-1">
            {!collapsed && (
              <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-600 uppercase tracking-widest">
                {section.section}
              </div>
            )}
            {section.items.map((item: any) => {
              const active = pathname === item.href || pathname.startsWith(item.href + '/')
              return (
                <Link key={item.href} href={item.href} title={collapsed ? item.label : ''}
                  className={`flex items-center gap-2.5 px-3 py-2 text-sm transition-colors
                              border-l-2 ${active
                                ? 'bg-blue-950/50 text-blue-300 border-blue-500'
                                : 'text-gray-500 hover:text-white hover:bg-gray-800 border-transparent'}`}>
                  <i className={`ti ${item.icon} text-base flex-shrink-0`} />
                  {!collapsed && (
                    <>
                      <span className="flex-1 truncate">{item.label}</span>
                      {item.badge && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                          item.badge === 'HOT' ? 'bg-red-900 text-red-400' :
                          item.badge === 'AI'  ? 'bg-purple-900 text-purple-400' :
                                                 'bg-gray-700 text-gray-400'}`}>
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                </Link>
              )
            })}
          </div>
        ))}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-gray-800">
        <div className={`flex items-center gap-2 ${collapsed ? 'justify-center' : ''}`}>
          <div className="w-7 h-7 rounded-full bg-blue-700 flex items-center justify-center
                          text-xs font-bold text-white flex-shrink-0">
            {user?.full_name?.[0] || '?'}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-white truncate">{user?.full_name}</div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded inline-block mt-0.5
                               ${ROLE_COLORS[user?.role || ''] || 'bg-gray-800 text-gray-400'}`}>
                {user?.role}
              </span>
            </div>
          )}
        </div>
        {!collapsed && (
          <button onClick={() => { logout(); router.push('/login') }}
            className="mt-2 text-xs text-gray-600 hover:text-red-400 transition-colors flex items-center gap-1">
            <i className="ti ti-logout text-sm" />Logout
          </button>
        )}
      </div>
    </aside>
  )
}
