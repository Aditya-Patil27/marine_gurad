import { Component, useSyncExternalStore } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Bell, Droplet, FileText, Map, Settings, Ship } from 'lucide-react'
import { vesselsApi } from '../lib/api'
import usePolling from '../lib/usePolling'
import { sourceLabel, timeIST } from '../lib/format'
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
      // The badge alone reads as "1Alerts"; say what the number counts
      aria-label={count > 0 ? `${label}, ${count} high risk` : undefined}
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

/** A page that fails to draw (no WebGL, a response it can't read) must not take the rail down with it. */
class PageBoundary extends Component {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="grid h-full place-items-center p-6">
        <div role="alert" className="card max-w-md p-8">
          <h1 className="text-2xl">This screen stopped working</h1>
          <p className="mt-2 text-[15px] text-muted">Something on it failed to draw. The rest of the console still works.</p>
          <button type="button" className="btn btn-primary mt-6" onClick={() => this.setState({ failed: false })}>
            Try again
          </button>
        </div>
      </div>
    )
  }
}

function subscribeOnline(callback) {
  window.addEventListener('online', callback)
  window.addEventListener('offline', callback)
  return () => {
    window.removeEventListener('online', callback)
    window.removeEventListener('offline', callback)
  }
}

const getOnlineSnapshot = () => navigator.onLine

function DataModeBanner({ fleet }) {
  const isOnline = useSyncExternalStore(subscribeOnline, getOnlineSnapshot)
  const isOffline = !isOnline

  let text
  let warning = false

  if (isOffline) {
    warning = true
    text = fleet.data
      ? `Offline · last sync ${timeIST(fleet.updatedAt)} IST · Live AIS and new satellite data need a connection.`
      : 'Offline · nothing synced yet · Live AIS and new satellite data need a connection.'
  } else if (fleet.error) {
    warning = true
    text = fleet.data
      ? `Can't reach the API · last sync ${timeIST(fleet.updatedAt)} IST · Showing the last data received, not live.`
      : "Can't reach the API · no data loaded yet"
  } else if (!fleet.data) {
    warning = false
    text = 'Checking the data source…'
  } else {
    warning = false
    text = `Data mode: ${sourceLabel(fleet.data)}`
  }

  return (
    <div
      role="region"
      aria-label="Data mode"
      aria-live="polite"
      className={`border-b border-line px-4 py-1.5 text-[13px] ${warning ? 'pill-amber' : 'bg-white text-muted'}`}
    >
      {text}
    </div>
  )
}

export default function Shell() {
  // The fleet is shared by the rail badge and every page, refreshed every 30 s
  const fleet = usePolling(() => vesselsApi.list(24), 30000)
  const flagged = fleet.data?.vessels.filter((v) => v.level === 'high').length ?? 0
  const { pathname } = useLocation()

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
      <div className="flex min-h-0 min-w-0 flex-col">
        <DataModeBanner fleet={fleet} />
        <main className="relative min-h-0 min-w-0 flex-1">
        {/* Keyed by page, so opening another one leaves the failure behind */}
        <PageBoundary key={pathname}>
          <Outlet context={fleet} />
        </PageBoundary>
        </main>
      </div>
    </div>
  )
}
