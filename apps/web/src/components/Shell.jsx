import { Component, useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Bell, Briefcase, Droplet, FileText, Home, Map, Radar, Settings, Ship, Waves } from 'lucide-react'
import { authApi, operationsApi, vesselsApi } from '../lib/api'
import usePolling from '../lib/usePolling'
import useOnline from '../lib/useOnline'
import { sourceLabel, timeIST } from '../lib/format'
import { useReplayWindow } from '../lib/replayWindow'
import Logo from './Logo'
import ReplayWindowControl from './ReplayWindowControl'

const NAV = [
  { to: '/overview', label: 'Overview', icon: Home },
  { to: '/map', label: 'Map', icon: Map },
  { to: '/alerts', label: 'Alerts', icon: Bell, badge: true },
  { to: '/vessels', label: 'Vessels', icon: Ship },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/cases', label: 'Cases', icon: Briefcase },
  { to: '/ocean', label: 'Ocean', icon: Waves },
  { to: '/detections', label: 'SAR', icon: Radar },
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

function DataModeBanner({ fleet, operations }) {
  const isOnline = useOnline()
  const isOffline = !isOnline

  let text
  let warning = false

  if (isOffline) {
    warning = true
    const cache = operations?.cache?.environment ? ` Cached environment: ${String(operations.cache.environment).replaceAll('_', ' ')}.` : ''
    text = fleet.data
      ? `Offline · last sync ${timeIST(fleet.updatedAt)} IST · Live AIS and new satellite data need a connection.${cache}`
      : `Offline · nothing synced yet · Live AIS and new satellite data need a connection.${cache}`
  } else if (operations?.remote_fetch_paused) {
    warning = true
    text = 'Remote acquisition is paused · cached and local records remain available.'
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

function Account() {
  const [user, setUser] = useState(null)
  const [open, setOpen] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  useEffect(() => { authApi.me().then(setUser).catch(() => setUser(null)) }, [])
  async function login(event) {
    event.preventDefault()
    setError('')
    try {
      const result = await authApi.login(username, password)
      setUser(result.user); setPassword(''); setOpen(false)
      window.location.reload()
    } catch { setPassword(''); setError('Sign-in failed. Check your account and password.') }
  }
  async function logout() {
    try { await authApi.logout(); setUser(null); window.location.reload() }
    catch { setError('Sign-out failed. Please try again.') }
  }
  return <div className="relative border-b border-line bg-white px-4 py-1 text-right text-sm">
    {user ? <span>Signed in as {user.username} ({user.roles?.join(', ')}) <button className="ml-2 underline" onClick={logout}>Sign out</button></span>
      : <button className="underline" onClick={() => setOpen(!open)}>Sign in to create or review reports</button>}
    {error && <span role="alert" className="ml-2 text-risk-red">{error}</span>}
    {open && !user && <form onSubmit={login} className="absolute right-4 top-8 z-50 grid w-72 gap-2 rounded bg-white p-4 text-left shadow-lg">
      <label>Username<input autoComplete="username" className="w-full rounded border p-1" value={username} onChange={e => setUsername(e.target.value)} required /></label>
      <label>Password<input type="password" autoComplete="current-password" className="w-full rounded border p-1" value={password} onChange={e => setPassword(e.target.value)} required /></label>
      <button className="btn btn-primary" type="submit">Sign in</button>
    </form>}
  </div>
}

export default function Shell() {
  const { bounds, key: windowKey } = useReplayWindow()
  // The fleet is shared by the rail badge and every page, refreshed every 30 s.
  // Changing the window drops the previous answer instead of letting it repaint.
  const fleet = usePolling(() => vesselsApi.list(168, bounds), 30000, [windowKey])
  const operations = usePolling(() => operationsApi.status(), 60000)
  const flagged = fleet.data?.vessels.filter((v) => v.level === 'high').length ?? 0
  const { pathname } = useLocation()

  return (
    <div className="grid h-screen grid-cols-[76px_1fr]">
      <nav aria-label="Main" className="flex min-h-0 flex-col items-center gap-1.5 overflow-y-auto border-r border-line bg-white py-3.5">
        <Logo className="mb-3.5 shrink-0" />
        {NAV.map((item) => (
          <RailLink key={item.to} {...item} count={item.badge ? flagged : 0} />
        ))}
        <div className="mt-auto">
          <RailLink to="/settings" label="Settings" icon={Settings} />
        </div>
      </nav>
      <div className="flex min-h-0 min-w-0 flex-col">
        <DataModeBanner fleet={fleet} operations={operations.data} />
        <ReplayWindowControl />
        <Account />
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
