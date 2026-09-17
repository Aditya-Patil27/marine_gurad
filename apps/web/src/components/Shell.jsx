import { NavLink, Outlet } from 'react-router-dom'
import { Bell, Droplet, FileText, Map, Settings, Ship } from 'lucide-react'
import { vesselsApi } from '../lib/api'
import usePolling from '../lib/usePolling'
import Logo from './Logo'

const NAV = [
  { to: '/map', label: 'Map', icon: Map },
  { to: '/alerts', label: 'Alerts', icon: Bell, badge: true },
  { to: '/vessels', label: 'Vessels', icon: Ship },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/spills', label: 'Spills', icon: Droplet },
]

function RailLink({ to, label, icon: Icon, count }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `relative flex w-[62px] flex-col items-center gap-1 rounded-[10px] pb-[7px] pt-[9px] text-[11px] font-medium transition-colors ${
          isActive ? 'bg-peri-soft text-navy' : 'text-muted hover:bg-canvas hover:text-navy'
        }`
      }
    >
      {count > 0 && (
        <span className="absolute right-2.5 top-1 h-[17px] min-w-[17px] rounded-[9px] bg-risk-red px-1 text-center text-[10.5px] font-semibold leading-[17px] text-white">
          {count}
        </span>
      )}
      <Icon size={20} strokeWidth={1.7} aria-hidden="true" />
      {label}
    </NavLink>
  )
}

export default function Shell() {
  // The fleet is shared by the rail badge and every page, refreshed every 30 s
  const fleet = usePolling(() => vesselsApi.list(24), 30000)
  const flagged = fleet.data?.vessels.filter((v) => v.level === 'high').length ?? 0

  return (
    <div className="grid h-screen grid-cols-[76px_1fr]">
      <nav aria-label="Main" className="flex flex-col items-center gap-1.5 border-r border-line bg-white py-3.5">
        <Logo className="mb-3.5" />
        {NAV.map((item) => (
          <RailLink key={item.to} {...item} count={item.badge ? flagged : 0} />
        ))}
        <div className="mt-auto">
          <RailLink to="/settings" label="Settings" icon={Settings} />
        </div>
      </nav>
      <main className="relative min-w-0">
        <Outlet context={fleet} />
      </main>
    </div>
  )
}
