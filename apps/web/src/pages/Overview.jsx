import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { alertsApi, casesApi, reportsApi, sourcesApi, vesselsApi } from '../lib/api'
import { sourceLabel } from '../lib/format'

const surface = 'card p-5'

const loaded = (value, ok, failed, failedText = 'Count not loaded') => (!ok ? (failed ? failedText : 'Loading…') : value)

/** Operational landing page; every number comes from an existing endpoint. */
export default function Overview() {
  const [fleet, setFleet] = useState(null)
  const [alerts, setAlerts] = useState(null)
  const [cases, setCases] = useState(null)
  const [reports, setReports] = useState(null)
  const [health, setHealth] = useState(null)
  const [failed, setFailed] = useState({})

  useEffect(() => {
    let alive = true
    Promise.allSettled([
      vesselsApi.list(),
      alertsApi.stored('open'),
      casesApi.list(),
      reportsApi.list(),
      sourcesApi.health(),
    ]).then(([fleetResult, alertsResult, casesResult, reportsResult, healthResult]) => {
      if (!alive) return
      const fail = {}
      if (fleetResult.status === 'fulfilled') setFleet(fleetResult.value)
      else fail.fleet = true
      if (alertsResult.status === 'fulfilled') setAlerts(alertsResult.value)
      else fail.alerts = true
      if (casesResult.status === 'fulfilled') setCases(casesResult.value)
      else fail.cases = true
      if (reportsResult.status === 'fulfilled') setReports(reportsResult.value)
      else fail.reports = true
      if (healthResult.status === 'fulfilled') setHealth(healthResult.value)
      else fail.health = true
      setFailed(fail)
    })
    return () => { alive = false }
  }, [])

  const vessels = fleet?.vessels ?? []
  const detectCount = loaded(
    vessels.length === 0 ? 'No vessels in the current view' : `${vessels.length} vessels in the current view`,
    Boolean(fleet),
    failed.fleet,
  )
  const alertCount = loaded(
    alerts?.total === 0 ? 'No open stored alerts' : `${alerts?.total} open stored alerts`,
    Boolean(alerts),
    failed.alerts,
  )
  const caseItems = cases ?? []
  const reportItems = reports ?? []
  const actCount = loaded(
    caseItems.length === 0 && reportItems.length === 0
      ? 'No cases yet · no reports yet'
      : `${caseItems.length} ${caseItems.length === 1 ? 'case' : 'cases'} · ${reportItems.length} ${reportItems.length === 1 ? 'report' : 'reports'}`,
    Boolean(cases) && Boolean(reports),
    failed.cases || failed.reports,
  )
  const sources = health?.sources ? Object.values(health.sources) : []
  const available = sources.filter((source) => source?.status === 'available').length
  const prepareCount = loaded(
    sources.length === 0
      ? 'Source health not reported'
      : `${available} of ${sources.length} sources available`,
    Boolean(health?.sources),
    failed.health,
    'Source status unavailable',
  )
  const recentCases = caseItems.slice(0, 4)
  const sourceEntries = Object.entries(health?.sources ?? {}).slice(0, 6)

  return <div className="h-full overflow-y-auto p-6 md:p-10">
    <header className="mb-6 flex flex-wrap items-end gap-4">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium uppercase tracking-wide text-muted">SamudraSense · Gulf of Mannar</p>
        <h1 className="mt-1 text-3xl font-semibold">Regional marine investigation console</h1>
        <p className="mt-2 max-w-2xl text-[15px] text-muted">
          Move from sourced activity to explainable evidence, a reviewed case and a traceable export. Evidence supports human review; it does not prove illegal activity.
        </p>
      </div>
      <Link className="btn btn-primary" to="/map">Start investigation</Link>
    </header>

    <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
      <Link className={`${surface} block no-underline hover:bg-canvas`} to="/map">
        <p className="text-sm font-medium uppercase tracking-wide text-muted">Fleet picture</p>
        <h2 className="mt-2 text-xl">Regional activity</h2>
        <p className="mt-1 text-muted">Vessels, observation windows and sourced events.</p>
        <p className="mt-3 font-medium">{detectCount}</p>
        {fleet && <p className="mt-1 text-sm text-muted">Data mode: {sourceLabel(fleet)}</p>}
      </Link>
      <Link className={`${surface} block no-underline hover:bg-canvas`} to="/alerts">
        <p className="text-sm font-medium uppercase tracking-wide text-muted">Triage</p>
        <h2 className="mt-2 text-xl">Open alerts</h2>
        <p className="mt-1 text-muted">Review assignments, evidence factors and context.</p>
        <p className="mt-3 font-medium">{alertCount}</p>
      </Link>
      <Link className={`${surface} block no-underline hover:bg-canvas`} to="/cases">
        <p className="text-sm font-medium uppercase tracking-wide text-muted">Investigations</p>
        <h2 className="mt-2 text-xl">Cases and reports</h2>
        <p className="mt-1 text-muted">Human review, revisions and traceable exports.</p>
        <p className="mt-3 font-medium">{actCount}</p>
      </Link>
      <Link className={`${surface} block no-underline hover:bg-canvas`} to="/settings">
        <p className="text-sm font-medium uppercase tracking-wide text-muted">Operations</p>
        <h2 className="mt-2 text-xl">Source readiness</h2>
        <p className="mt-1 text-muted">Connections, data freshness and deployment settings.</p>
        <p className="mt-3 font-medium">{prepareCount}</p>
      </Link>
    </div>

    <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,.85fr)]">
      <section className={surface} aria-labelledby="recent-investigations-heading">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 id="recent-investigations-heading" className="text-xl">Recent investigations</h2>
            <p className="mt-1 text-sm text-muted">Latest case activity available to your account.</p>
          </div>
          <Link className="btn" to="/cases">View all cases</Link>
        </div>
        {!cases && !failed.cases && <p className="mt-4 text-muted">Loading investigations…</p>}
        {failed.cases && <p className="mt-4 text-muted">Investigation activity is unavailable.</p>}
        {cases && recentCases.length === 0 && <p className="mt-4 text-muted">No investigations have been opened.</p>}
        {recentCases.map((item) => <Link key={item.id} className="block border-t border-line py-3 first:mt-3" to={`/cases?id=${item.id}`}>
          <span className="font-medium">{item.title || `Case ${item.id}`}</span>
          <span className="float-right pill pill-navy">{item.status || 'Status unknown'}</span>
          <p className="mt-1 text-sm text-muted">{item.mmsi ? `MMSI ${item.mmsi}` : 'Vessel reference unavailable'}</p>
        </Link>)}
      </section>

      <section className={surface} aria-labelledby="source-readiness-heading">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 id="source-readiness-heading" className="text-xl">Source readiness</h2>
            <p className="mt-1 text-sm text-muted">Availability reported by configured adapters.</p>
          </div>
          <Link className="btn" to="/settings">Operations</Link>
        </div>
        {!health && !failed.health && <p className="mt-4 text-muted">Loading source status…</p>}
        {failed.health && <p className="mt-4 text-muted">Source status is unavailable.</p>}
        {health && sourceEntries.length === 0 && <p className="mt-4 text-muted">No source status has been reported.</p>}
        <dl className="mt-3">
          {sourceEntries.map(([key, entry]) => <div className="flex items-center gap-3 border-t border-line py-2.5" key={key}>
            <dt className="min-w-0 flex-1 truncate font-medium capitalize">{key.replaceAll('_', ' ')}</dt>
            <dd className={`pill ${entry?.status === 'available' ? 'pill-green' : entry?.status === 'error' ? 'pill-red' : 'pill-amber'}`}>
              {String(entry?.status || entry?.availability || 'unknown').replaceAll('_', ' ')}
            </dd>
          </div>)}
        </dl>
      </section>
    </div>

    <p className="mt-6 max-w-3xl text-sm text-muted">
      Historical, replay, synthetic, live and cached sources stay labelled separately. A GFW event is an inferred historical event point, not a vessel track. Missing AIS is unknown coverage, not proof of deliberate absence.
    </p>
  </div>
}
