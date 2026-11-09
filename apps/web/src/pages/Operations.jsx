import { useEffect, useState } from 'react'
import { adminApi, authApi, operationsApi, serverDetail, sourcesApi } from '../lib/api'
import { dateTimeIST, modeLabel } from '../lib/format'

const SOURCE_NAMES = {
  local_vessel_records: 'Local replay',
  copernicus_sst: 'Copernicus SST',
  global_fishing_watch: 'GFW',
  aisstream: 'AISStream',
  open_meteo_marine: 'Open-Meteo',
}

const isAdmin = (user) => (user?.roles ?? []).includes('ADMINISTRATOR')

const word = (value) => String(value ?? '').replaceAll('_', ' ').replace(/^\w/, (c) => c.toUpperCase())

const bboxInput = (bbox, index) => bbox?.[Math.floor(index / 2)]?.[index % 2] ?? ''

/** Read-only deployment readiness, plus Administrator-only settings and local accounts. */
export default function Operations() {
  const [user, setUser] = useState(null)
  const [authError, setAuthError] = useState('')
  const [health, setHealth] = useState(null)
  const [healthError, setHealthError] = useState('')
  const [settings, setSettings] = useState(null)
  const [adminError, setAdminError] = useState('')
  const [users, setUsers] = useState([])
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newUser, setNewUser] = useState({ username: '', password: '', roles: [] })
  const [operations, setOperations] = useState(null)
  const [jobs, setJobs] = useState(null)
  const [operationsError, setOperationsError] = useState('')
  const [jobBusy, setJobBusy] = useState(false)

  useEffect(() => {
    let alive = true
    Promise.allSettled([authApi.me(), sourcesApi.health()]).then(async ([meResult, healthResult]) => {
      if (!alive) return
      if (meResult.status === 'rejected') {
        setAuthError(
          meResult.reason?.response?.status === 401
            ? 'Sign in to view operations, source health and deployment settings.'
            : 'Your account could not be loaded. Operations may be incomplete.',
        )
      } else {
        setUser(meResult.value)
        if (isAdmin(meResult.value)) {
          const [settingsResult, usersResult] = await Promise.allSettled([adminApi.settings(), adminApi.users()])
          if (!alive) return
          if (settingsResult.status === 'fulfilled') setSettings(settingsResult.value)
          else setAdminError(serverDetail(settingsResult.reason) || 'Deployment settings could not be loaded.')
          if (usersResult.status === 'fulfilled') setUsers(usersResult.value)
          else setAdminError((current) => current || serverDetail(usersResult.reason) || 'Local accounts could not be loaded.')
        }
      }
      if (healthResult.status === 'fulfilled') {
        setHealth(healthResult.value)
        setHealthError('')
      } else if (healthResult.reason?.response?.status !== 401 || meResult.status === 'fulfilled') {
        setHealthError(
          healthResult.reason?.response?.status === 403
            ? 'You do not have permission to view source health.'
            : serverDetail(healthResult.reason) || 'Source health could not be loaded.',
        )
      }
    })
    return () => { alive = false }
  }, [])

  useEffect(() => {
    let alive = true
    Promise.allSettled([operationsApi.status(), sourcesApi.jobs()]).then(([statusResult, jobsResult]) => {
      if (!alive) return
      if (statusResult.status === 'fulfilled') setOperations(statusResult.value)
      else setOperationsError(serverDetail(statusResult.reason) || 'Operational status is unavailable.')
      if (jobsResult.status === 'fulfilled') setJobs(jobsResult.value)
      else setOperationsError((current) => current || serverDetail(jobsResult.reason) || 'Source job history is unavailable.')
    })
    return () => { alive = false }
  }, [])

  async function triggerSource(provider) {
    setJobBusy(true); setMessage(''); setOperationsError('')
    try {
      const today = new Date()
      const start = new Date(today); start.setUTCDate(start.getUTCDate() - 7)
      const result = await sourcesApi.run(provider === 'aisstream'
        ? { provider: 'aisstream', max_positions: 30, duration_seconds: 12, persist_positions: false }
        : { provider: 'gfw', start_date: start.toISOString().slice(0, 10), end_date: today.toISOString().slice(0, 10), offset: 0, limit: 20 })
      setMessage(`${provider === 'aisstream' ? 'AISStream' : 'GFW'} bounded source check finished: ${word(result.run?.status ?? 'status not reported')}.`)
      setHealth(await sourcesApi.health())
      sourcesApi.jobs().then(setJobs).catch(() => {})
    } catch (error) { setOperationsError(serverDetail(error) || 'The source check could not be started.') }
    finally { setJobBusy(false) }
  }

  async function cancelJob(job) {
    setJobBusy(true); setOperationsError('')
    try {
      await sourcesApi.cancelJob(job.id, job.version)
      setJobs(await sourcesApi.jobs())
      setMessage(`Job ${job.id} cancelled.`)
    } catch (error) { setOperationsError(serverDetail(error) || 'The job could not be cancelled.') }
    finally { setJobBusy(false) }
  }

  async function saveSettings(event) {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setAdminError('')
    try {
      const saved = await adminApi.updateSettings({
        organization: settings.organization,
        aoi_name: settings.aoi_name,
        aoi_bbox: [
          [Number(bboxInput(settings.aoi_bbox, 0)), Number(bboxInput(settings.aoi_bbox, 1))],
          [Number(bboxInput(settings.aoi_bbox, 2)), Number(bboxInput(settings.aoi_bbox, 3))],
        ],
        display_timezone: settings.display_timezone,
        alert_threshold: Number(settings.alert_threshold),
        report_recipients: String(settings.report_recipients).split(',').map((s) => s.trim()).filter(Boolean),
        retention_days: Number(settings.retention_days),
      })
      setSettings(saved)
      setMessage('Deployment settings saved.')
    } catch (error) {
      setAdminError(serverDetail(error) || 'Deployment settings could not be saved.')
    } finally {
      setSaving(false)
    }
  }

  async function createUser(event) {
    event.preventDefault()
    setCreating(true)
    setMessage('')
    setAdminError('')
    try {
      const created = await adminApi.createUser({
        username: newUser.username,
        password: newUser.password,
        roles: newUser.roles,
      })
      setUsers((current) => [...current, created])
      setNewUser({ username: '', password: '', roles: [] })
      setMessage(`${created.username} has been created.`)
    } catch (error) {
      setAdminError(serverDetail(error) || 'The local user could not be created.')
    } finally {
      setCreating(false)
    }
  }

  async function toggleUser(account) {
    setMessage('')
    setAdminError('')
    try {
      const updated = await adminApi.setUserActive(account.id, !account.is_active)
      setUsers((current) => current.map((item) => (item.id === account.id ? updated : item)))
      setMessage(`${account.username} is now ${updated.is_active ? 'enabled' : 'disabled'}.`)
    } catch (error) {
      setAdminError(
        error?.response?.status === 409
          ? 'You cannot change your own active state.'
          : serverDetail(error) || 'The account state could not be changed.',
      )
    }
  }

  const sources = health?.sources && typeof health.sources === 'object' ? Object.entries(health.sources) : []
  const sourceJobs = Array.isArray(jobs) ? jobs : jobs?.items ?? []
  const canRunSources = (user?.roles ?? []).some((role) => role === 'ANALYST' || role === 'ADMINISTRATOR')

  return <div className="h-full overflow-y-auto p-6 md:p-10">
    <header className="mb-6">
      <p className="text-sm font-medium uppercase tracking-wide text-muted">Operations</p>
      <h1 className="mt-1 text-3xl font-semibold">Operations</h1>
      <p className="mt-2 max-w-2xl text-[15px] text-muted">
        Deployment readiness and local administration. Source status is an operational check, not a live-provider or coverage claim.
      </p>
    </header>

    {authError && <div role="alert" className="mb-5 rounded-card border border-risk-red/30 bg-risk-red/5 p-4 text-[15px]">{authError}</div>}

    {!authError && healthError && <div role="alert" className="mb-5 rounded-card border border-risk-red/30 bg-risk-red/5 p-4 text-[15px]">{healthError}</div>}

    {message && <p role="status" className="mb-5 rounded-card border border-line bg-mint p-4 text-[15px]">{message}</p>}
    {adminError && <div role="alert" className="mb-5 rounded-card border border-risk-red/30 bg-risk-red/5 p-4 text-[15px]">{adminError}</div>}

    <section aria-label="Source health">
      <h2 className="text-xl">Source health</h2>
      <p className="mt-1 text-sm text-muted">
        Read-only: this check makes no external calls and writes nothing. Configured or not checked does not mean reachable.
      </p>
      {healthError ? (
        <p className="mt-4 text-[15px] text-muted">Source health is unavailable.</p>
      ) : !health ? (
        <p className="mt-4 text-[15px] text-muted">Loading source health…</p>
      ) : sources.length === 0 ? (
        <p className="mt-4 text-[15px] text-muted">Source health not reported.</p>
      ) : (
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sources.map(([key, entry]) => <SourceCard key={key} sourceKey={key} entry={entry ?? {}} />)}
        </div>
      )}
    </section>

    <section aria-label="System readiness" className="mt-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h2 className="text-xl">System readiness</h2><p className="mt-1 text-sm text-muted">Cache validity, worker state and bounded background work. Credentials are never returned here.</p></div>
        {canRunSources && <div className="flex gap-2"><button className="btn" type="button" disabled={jobBusy} onClick={() => triggerSource('aisstream')}>Check AIS source</button><button className="btn" type="button" disabled={jobBusy} onClick={() => triggerSource('gfw')}>Check GFW source</button></div>}
      </div>
      {operationsError && <p role="alert" className="mt-3 text-risk-red">{operationsError}</p>}
      {!operations && !operationsError && <p className="mt-3 text-muted">Loading operational status…</p>}
      {operations && <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatusCard label="Connectivity" value={operations.offline?.status ?? operations.offline ?? operations.connectivity ?? 'unknown'} detail={operations.offline?.detail ?? operations.cache?.validity} />
        <StatusCard label="Worker" value={operations.worker?.status ?? operations.worker ?? 'unknown'} detail={operations.worker?.detail ?? (operations.queue?.depth != null ? `Queue depth ${operations.queue.depth}` : '')} />
        <StatusCard label="Storage" value={operations.disk?.status ?? 'unknown'} detail={operations.disk?.free_bytes != null ? `${Math.round(operations.disk.free_bytes / 1073741824)} GB free` : operations.disk?.detail} />
        <StatusCard label="Backup" value={operations.backup?.status ?? 'unknown'} detail={operations.backup?.last_completed_at ? `Last complete ${dateTimeIST(operations.backup.last_completed_at)}` : operations.backup?.detail} />
      </div>}
      <div className="card mt-4 overflow-x-auto p-5">
        <h3 className="text-lg">Source jobs</h3>
        {!jobs && !operationsError && <p className="mt-2 text-muted">Loading source jobs…</p>}
        {sourceJobs.length === 0 && jobs && <p className="mt-2 text-muted">No source jobs have been recorded.</p>}
        {sourceJobs.map((job) => <div className="mt-3 grid items-center gap-3 border-t border-line pt-3 text-sm md:grid-cols-[minmax(150px,1fr)_120px_120px_minmax(160px,1fr)_auto]" key={job.id}>
          <span className="num">{job.id}</span><span className={`pill ${job.state === 'succeeded' ? 'pill-green' : job.state === 'failed' ? 'pill-red' : 'pill-amber'}`}>{word(job.state)}</span><span>{job.progress != null ? `${job.progress}%` : 'Progress unknown'}</span><span className="text-muted">Attempt {job.attempts ?? 0}{job.checkpoint ? ' · checkpoint saved' : ''}</span>{job.cancellable && <button className="btn" disabled={jobBusy} type="button" onClick={() => cancelJob(job)}>Cancel</button>}
        </div>)}
      </div>
    </section>

    {!isAdmin(user) ? (
      user && <p className="mt-6 max-w-3xl text-sm text-muted">
        Administrator access is required to change deployment settings, manage local accounts and edit alert thresholds.
      </p>
    ) : (
      <>
        <section aria-label="Deployment settings" className="mt-8">
          <h2 className="text-xl">Deployment settings</h2>
          {settings ? (
            <form onSubmit={saveSettings} className="card mt-3 grid max-w-3xl gap-4 p-5 md:grid-cols-2">
              <label className="grid gap-1 text-sm font-medium">Organisation
                <input className="input" value={settings.organization ?? ''} onChange={(e) => setSettings({ ...settings, organization: e.target.value })} required />
              </label>
              <label className="grid gap-1 text-sm font-medium">Area of interest
                <input className="input" value={settings.aoi_name ?? ''} onChange={(e) => setSettings({ ...settings, aoi_name: e.target.value })} required />
              </label>
              <fieldset className="grid grid-cols-2 gap-2 md:col-span-2">
                <legend className="mb-1 text-sm font-medium">Bounding box (WGS84 longitude, latitude)</legend>
                {['West', 'South', 'East', 'North'].map((label, index) => (
                  <label key={label} className="grid gap-1 text-sm font-medium">{label}
                    <input
                      className="input"
                      type="number"
                      step="any"
                      value={bboxInput(settings.aoi_bbox, index)}
                      onChange={(e) => {
                        const bbox = Array.isArray(settings.aoi_bbox) ? settings.aoi_bbox.map((pair) => [...pair]) : [[0, 0], [0, 0]]
                        bbox[Math.floor(index / 2)][index % 2] = e.target.value
                        setSettings({ ...settings, aoi_bbox: bbox })
                      }}
                    />
                  </label>
                ))}
              </fieldset>
              <label className="grid gap-1 text-sm font-medium">Display timezone
                <input className="input" value={settings.display_timezone ?? ''} onChange={(e) => setSettings({ ...settings, display_timezone: e.target.value })} required />
              </label>
              <label className="grid gap-1 text-sm font-medium">Alert threshold (0–1)
                <input className="input" type="number" min="0" max="1" step="0.01" value={settings.alert_threshold ?? ''} onChange={(e) => setSettings({ ...settings, alert_threshold: e.target.value })} required />
              </label>
              <label className="grid gap-1 text-sm font-medium md:col-span-2">Report recipients
                <input className="input" placeholder="Comma-separated email addresses" value={Array.isArray(settings.report_recipients) ? settings.report_recipients.join(', ') : settings.report_recipients ?? ''} onChange={(e) => setSettings({ ...settings, report_recipients: e.target.value })} />
              </label>
              <label className="grid gap-1 text-sm font-medium">Retention days
                <input className="input" type="number" min="1" value={settings.retention_days ?? ''} onChange={(e) => setSettings({ ...settings, retention_days: e.target.value })} required />
              </label>
              <div className="flex items-end">
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : 'Save deployment settings'}
                </button>
              </div>
              {settings.updated_at && <p className="text-sm text-muted md:col-span-2">
                Last updated {dateTimeIST(settings.updated_at)}{settings.updated_by ? ` by ${settings.updated_by}` : ''}.
              </p>}
            </form>
          ) : <p className="mt-3 text-[15px] text-muted">Deployment settings are not loaded.</p>}
        </section>

        <section aria-label="Local accounts" className="mt-8">
          <h2 className="text-xl">Local accounts</h2>
          <p className="mt-1 text-sm text-muted">Accounts approve and export reports. Passwords are stored only by the API and are never shown again.</p>
          <div className="card mt-3 max-w-3xl p-5">
            {users.length === 0 ? <p className="text-[15px] text-muted">No local accounts loaded.</p> : (
              <ul className="divide-y divide-line">
                {users.map((account) => {
                  const self = account.id === user?.id
                  return <li key={account.id} className="flex flex-wrap items-center gap-3 py-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{account.username} {self && <span className="text-sm text-muted">(you)</span>}</p>
                      <p className="text-sm text-muted">{(account.roles ?? []).join(', ') || 'No role'} · {account.is_active ? 'Active' : 'Disabled'}</p>
                    </div>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      aria-label={`${account.is_active ? 'Disable' : 'Enable'} ${account.username}`}
                      disabled={self}
                      onClick={() => toggleUser(account)}
                    >
                      {account.is_active ? 'Disable' : 'Enable'} {account.username}
                    </button>
                  </li>
                })}
              </ul>
            )}
            <p className="mt-3 text-sm text-muted">You cannot deactivate your own account.</p>
          </div>

          <form onSubmit={createUser} className="card mt-4 grid max-w-3xl gap-4 p-5 md:grid-cols-2">
            <h3 className="text-lg md:col-span-2">Create local user</h3>
            <label className="grid gap-1 text-sm font-medium">Username
              <input className="input" autoComplete="off" value={newUser.username} onChange={(e) => setNewUser({ ...newUser, username: e.target.value })} required />
            </label>
            <label className="grid gap-1 text-sm font-medium">Password
              <input className="input" type="password" autoComplete="new-password" value={newUser.password} onChange={(e) => setNewUser({ ...newUser, password: e.target.value })} required />
            </label>
            <fieldset className="md:col-span-2">
              <legend className="mb-1 text-sm font-medium">Roles</legend>
              <div className="flex flex-wrap gap-4">
                {['VIEWER', 'ANALYST', 'APPROVER', 'ADMINISTRATOR'].map((role) => (
                  <label key={role} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={newUser.roles.includes(role)}
                      onChange={(e) => setNewUser({
                        ...newUser,
                        roles: e.target.checked
                          ? [...newUser.roles, role]
                          : newUser.roles.filter((item) => item !== role),
                      })}
                    />
                    {role}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="flex items-end">
              <button type="submit" className="btn btn-primary" disabled={creating || newUser.roles.length === 0}>
                {creating ? 'Creating…' : 'Create local user'}
              </button>
            </div>
          </form>
        </section>
      </>
    )}
  </div>
}

function SourceCard({ sourceKey, entry }) {
  const label = SOURCE_NAMES[sourceKey] ?? word(sourceKey)
  return <article className="card p-5">
    <h3 className="text-lg">{label}</h3>
    <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
      <dt className="text-muted">Status</dt><dd>{word(entry.status) || 'Not reported'}</dd>
      <dt className="text-muted">Mode</dt><dd>{modeLabel(entry)}</dd>
      {entry.availability && <><dt className="text-muted">Availability</dt><dd>{word(entry.availability)}</dd></>}
      {entry.positions != null && <><dt className="text-muted">Positions</dt><dd>{entry.positions}</dd></>}
      {entry.vessels != null && <><dt className="text-muted">Vessels</dt><dd>{entry.vessels}</dd></>}
      {entry.last_run && <><dt className="text-muted">Last run</dt><dd>{word(entry.last_run.status)}{entry.last_run.finished_at ? ` · ${dateTimeIST(entry.last_run.finished_at)}` : ''}</dd></>}
      {/* A local replay table has no scheduled provider run; only report a missing run where a run is expected. */}
      {entry.last_run === null && sourceKey !== 'local_vessel_records' && <><dt className="text-muted">Last run</dt><dd>No persisted run</dd></>}
      {entry.latest_observed_at && <><dt className="text-muted">Latest observed</dt><dd>{dateTimeIST(entry.latest_observed_at)}</dd></>}
      {entry.value != null && <><dt className="text-muted">Value</dt><dd>{entry.value}{entry.unit ? ` ${entry.unit}` : ''}</dd></>}
    </dl>
    {entry.last_run_note && <p className="mt-2 text-sm text-muted">{entry.last_run_note}</p>}
    {entry.coverage && <p className="mt-2 text-sm text-muted">Coverage: {entry.coverage}</p>}
    {entry.limitations && <p className="mt-2 text-sm text-muted">{entry.limitations}</p>}
  </article>
}

function StatusCard({ label, value, detail }) {
  const status = typeof value === 'object' ? value?.status ?? 'unknown' : value
  return <article className="card p-5"><p className="text-sm font-medium uppercase tracking-wide text-muted">{label}</p><p className="mt-2 text-lg font-semibold text-navy">{word(status)}</p>{detail && <p className="mt-1 text-sm text-muted">{String(detail)}</p>}</article>
}
