import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { alertsApi, assessmentsApi, casesApi, encountersApi, triageApi, vesselsApi, reportsApi, weatherApi, sarApi, environmentApi, isConflict, isNotFound, serverDetail } from '../lib/api'
import { formatEnvironmentalReading } from '../lib/environment'
import { dateTimeIST, hoursLabel, modeLabel, score, sentence, sourceLabel, vesselName, withDisplayNames, windowRangeIST } from '../lib/format'
import { useReplayWindow } from '../lib/replayWindow'
import ObservationWindowNotice from '../components/ObservationWindowNotice'

const plural = (n, singular, pluralForm) => `${n} ${n === 1 ? singular : pluralForm}`

const surface = 'card p-5'

/** A user-actionable stop (no observations, no matching assessment), not an auth or network failure. */
class ExpectedCaseError extends Error {}

const isHistorical = (window) => window?.mode === 'historical'

const noObservationsMessage = (window) =>
  isHistorical(window)
    ? `No observations in this window: ${windowRangeIST(window)}. Nothing was created.`
    : 'No observations in the rolling 7-day window. Nothing was created.'

/** The persisted anchors must match exactly; a re-sync can keep the same UUID but not a stale window. */
const assessmentMatchesWindow = (assessment, window) => {
  const stored = assessment?.window
  if (!stored) return false
  if (isHistorical(window)) return stored.mode === 'historical' && stored.start === window.start && stored.end === window.end
  return stored.mode === 'rolling'
}

const pickAssessment = (assessments, window) => (assessments ?? []).find((item) => assessmentMatchesWindow(item, window))

function Page({ title, children }) {
  return <div className="h-full overflow-y-auto p-6 md:p-10"><h1 className="mb-6 text-3xl font-semibold">{title}</h1>{children}</div>
}

/** Explicit provider and screening limitations supplied by the API. */
function DataLimitations({ items, rule }) {
  const row = `${rule} border-line py-2 text-muted`
  if (!Array.isArray(items) || !items.length) return <p className={row}>Data limitations not reported</p>
  return items.map((lim, i) => (
    <p className={row} key={lim.key ?? i}>
      {typeof lim === 'string' ? lim : <>{lim.label && <b className="text-ink">{lim.label}: </b>}{lim.detail}</>}
    </p>
  ))
}

export function AlertsPage() {
  const { window: selectedWindow, bounds, key: windowKey } = useReplayWindow()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let current = true
    setData(null); setError('')
    vesselsApi.list(168, bounds).then((d) => current && setData(d)).catch(() => current && setError('Unable to load vessels.'))
    return () => { current = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [windowKey])
  return <Page title="Alert triage">
    <p className="mb-5 text-muted">{isHistorical(selectedWindow) ? 'Risk signals in the selected historical window.' : 'Current risk signals from the last 7 days.'} Weather does not change these scores. Open a vessel to see its weather, and Reports to see review status.</p>
    <ObservationWindowNotice window={selectedWindow} className="mb-5" />
    {data?.vessels.length === 0 && isHistorical(selectedWindow) && <p>{`No observations in this window: ${windowRangeIST(selectedWindow)}.`}</p>}
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p>Loading alerts…</p>}
    {data && <div className="grid gap-5 md:grid-cols-2">{['high', 'medium'].map(level => <section className={surface} key={level}>
      <h2 className="mb-3 text-xl">{level === 'high' ? 'Needs review' : 'Watch'}</h2>
      {data.vessels.filter(v => v.level === level).map(v => <Link className="block border-t border-line py-3 hover:text-navy" to={`/vessels/${v.mmsi}`} key={v.mmsi}>
        <b>{vesselName(v)}</b><span className="num float-right">{score(v.score)}</span><p className="text-muted">{withDisplayNames(v.headline, data.vessels)}</p>
      </Link>)}
      {!data.vessels.some(v => v.level === level) && <p className="text-muted">No vessels in this category.</p>}
    </section>)}</div>}
    <ReviewQueue />
    <StoredAlerts window={selectedWindow} />
  </Page>
}

const REVIEW_STATES = { under_review: 'Under review (open case)', needs_review: 'Needs review', monitor: 'Monitor' }

/** Persisted review priorities over every saved assessment; read-only, no provider calls. */
function ReviewQueue() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let current = true
    triageApi.queue().then((d) => current && setData(d)).catch((e) => current && setError(serverDetail(e) || 'Unable to load the review queue.'))
    return () => { current = false }
  }, [])
  return <section className={`${surface} mt-5`} aria-label="Review queue">
    <h2 className="mb-1 text-xl">Review queue</h2>
    <p className="mb-3 text-muted">Saved assessments from every window, open cases first. {data?.limitation}</p>
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p>Loading review queue…</p>}
    {data?.items.length === 0 && <p className="text-muted">No saved assessments yet.</p>}
    {data?.items.map(item => <Link className="block border-t border-line py-3 hover:text-navy" to={`/vessels/${item.mmsi}`} key={item.id}>
      <b>{vesselName({ name: item.vessel_name, mmsi: item.mmsi })}</b> · {REVIEW_STATES[item.review_state] ?? item.review_state}<span className="num float-right">{score(item.score)}</span>
      <p className="text-muted">Alerts: {item.alerts.open} open, {item.alerts.acknowledged} acknowledged, {item.alerts.resolved} resolved · Cases: {item.cases.open} open, {item.cases.closed} closed · Evaluated {dateTimeIST(item.evaluated_at)}</p>
    </Link>)}
    {data && data.total > data.items.length && <p className="mt-2 text-muted">Showing {data.items.length} of {data.total}.</p>}
    {data?.weather?.reason && <p className="mt-2 text-muted">{data.weather.reason}</p>}
  </section>
}

// The weather API reports `model_or_observation`, not `data_mode`
const weatherMode = (weather) => (!weather.data_mode && weather.model_or_observation === 'model_forecast' ? 'Model forecast, not a measurement' : modeLabel(weather))

const ALERT_ACTIONS = { open: ['acknowledge', 'resolve'], acknowledged: ['resolve'], resolved: ['reopen'] }
const ACTION_LABELS = { acknowledge: 'Acknowledge', resolve: 'Resolve', reopen: 'Reopen' }
const ACTION_DONE = { acknowledge: 'acknowledged', resolve: 'resolved', reopen: 'reopened' }

/** Stored alert records and their analyst lifecycle; every change sends the version the analyst saw. */
function StoredAlerts({ window }) {
  const [status, setStatus] = useState('open')
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [notes, setNotes] = useState({})
  const [review, setReview] = useState({})
  const [analystNotes, setAnalystNotes] = useState({})
  const request = useRef(0)

  const load = useCallback(() => {
    // Only the answer to the latest filter may paint
    const mine = ++request.current
    setError('')
    return alertsApi.stored(status)
      .then((d) => mine === request.current && setData(d))
      .catch((e) => mine === request.current && setError(serverDetail(e) || 'Unable to load stored alerts.'))
  }, [status])
  useEffect(() => { setData(null); load() }, [load])

  async function run(work, describe) {
    setBusy(true); setMessage('')
    try { setMessage(describe(await work())) }
    catch (e) { setMessage(`${sentence(serverDetail(e) || 'The request failed.')}${isConflict(e) ? ' Nothing was changed.' : ''} The list was reloaded.`) }
    finally { await load(); setBusy(false) }
  }
  const sync = () => run(
    () => alertsApi.sync(window),
    (r) => {
      const selected = isHistorical(r.window)
        ? `historical window ${windowRangeIST(r.window)}`
        : `rolling ${r.window?.hours ?? window?.hours ?? 168}-hour window ${windowRangeIST(r.window)}`
      const scope = r.stored_scope === 'global' ? 'Stored history remains global.' : 'Stored scope was not reported.'
      return `Synced ${plural(r.observed, 'screening alert', 'screening alerts')} for the ${selected}: ${r.created} new, ${r.updated} updated, ${r.unchanged} unchanged, ${r.skipped_resolved} left resolved. Source: ${sourceLabel(r)}. ${scope}`
    },
  )
  const act = (alert, action) => run(
    () => alertsApi.transition(alert.id, action, alert.version, action === 'resolve' ? notes[alert.id]?.trim() : undefined),
    () => `${alert.title} (MMSI ${alert.mmsi}) ${ACTION_DONE[action]}.`,
  )
  const saveReview = (alert) => {
    const draft = review[alert.id] ?? {}
    return run(
      () => alertsApi.review(alert.id, alert.version, draft.state ?? alert.reviewer_state ?? 'new', draft.assigned_to ?? alert.assigned_to, draft.reason),
      () => `${alert.title} review state updated.`,
    )
  }
  const addAnalystNote = (alert) => run(
    () => alertsApi.addNote(alert.id, alert.version, analystNotes[alert.id]?.trim()),
    () => {
      setAnalystNotes((current) => ({ ...current, [alert.id]: '' }))
      return `Note added to ${alert.title}.`
    },
  )

  return <section className={`${surface} mt-5`} aria-label="Stored alerts">
    <div className="mb-1 flex flex-wrap items-center gap-3">
      <h2 className="text-xl">Stored alerts</h2>
      <label className="ml-auto text-muted">Status{' '}
        <select value={status} disabled={busy} onChange={(e) => { setStatus(e.target.value); setMessage('') }}>
          <option value="open">Open</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
          <option value="">All</option>
        </select>
      </label>
      <button type="button" className="btn" disabled={busy} onClick={sync}>Sync stored alerts</button>
    </div>
    <p className="mb-3 text-muted">Protected-area screening alerts saved across sync runs for analyst review. This is global stored history, not a list filtered to the selected window. {data?.limitation}</p>
    {message && <p role="status" className="mb-3">{message}</p>}
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p>Loading stored alerts…</p>}
    {data?.alerts.length === 0 && <p className="text-muted">No stored alerts with this status.</p>}
    {data?.alerts.map(a => <div className="border-t border-line py-3" key={a.id}>
      <div className="flex flex-wrap items-center gap-2"><b>{a.title}</b><span className="pill pill-navy">{String(a.reviewer_state ?? 'new').replaceAll('_', ' ')}</span><span className="text-muted">{a.severity} · {a.status}</span><span className="ml-auto text-muted">{sourceLabel(a)}</span></div>
      <p className="text-muted">
        <Link className="underline" to={`/vessels/${a.mmsi}`}>MMSI {a.mmsi}</Link> · Last observed {dateTimeIST(a.last_observed_at)}
        {/* The server keeps these fields after a reopen; only show what still describes the current status */}
        {a.status !== 'open' && a.acknowledged_by && ` · Acknowledged by ${a.acknowledged_by}`}
        {a.status === 'resolved' && a.resolved_by && ` · Resolved by ${a.resolved_by}${a.resolution_note ? `: ${a.resolution_note}` : ''}`}
      </p>
      <p className="mt-1 text-sm text-muted">Assignee: {a.assigned_to || 'Unassigned'}{a.resolution_reason ? ` · Resolution: ${a.resolution_reason}` : ''}</p>
      {a.clear_scenario && <p className="mt-1 rounded border border-line bg-canvas p-2 text-sm"><b>Clear scenario:</b> {typeof a.clear_scenario === 'string' ? a.clear_scenario : a.clear_scenario.summary ?? a.clear_scenario.reason ?? 'Supporting conditions are recorded; review the evidence detail.'}</p>}
      {a.notes?.length > 0 && <div className="mt-2 text-sm">{a.notes.slice(-3).map((note) => <p className="border-l-2 border-peri pl-2" key={note.id}>{note.note} <span className="text-muted">· {note.actor ?? 'Analyst'}{note.created_at ? ` · ${dateTimeIST(note.created_at)}` : ''}</span></p>)}</div>}
      <div className="mt-3 grid gap-2 rounded border border-line p-3 md:grid-cols-[160px_minmax(160px,1fr)_minmax(180px,1fr)_auto]">
        <label className="grid gap-1 text-sm">Review state<select className="input" value={review[a.id]?.state ?? a.reviewer_state ?? 'new'} onChange={(e) => setReview({ ...review, [a.id]: { ...review[a.id], state: e.target.value } })}><option value="new">New</option><option value="watch">Watch</option><option value="in_review">In review</option><option value="closed">Closed</option></select></label>
        <label className="grid gap-1 text-sm">Assignee<input className="input" maxLength={100} value={review[a.id]?.assigned_to ?? a.assigned_to ?? ''} onChange={(e) => setReview({ ...review, [a.id]: { ...review[a.id], assigned_to: e.target.value } })} /></label>
        <label className="grid gap-1 text-sm">Reason<input className="input" maxLength={500} value={review[a.id]?.reason ?? ''} onChange={(e) => setReview({ ...review, [a.id]: { ...review[a.id], reason: e.target.value } })} /></label>
        <button type="button" className="btn self-end" disabled={busy} onClick={() => saveReview(a)}>Save review</button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2"><input className="input min-w-[240px] flex-1" maxLength={1000} aria-label={`Analyst note for ${a.title}`} placeholder="Add an analyst note" value={analystNotes[a.id] ?? ''} onChange={(e) => setAnalystNotes({ ...analystNotes, [a.id]: e.target.value })} /><button type="button" className="btn" disabled={busy || !analystNotes[a.id]?.trim()} onClick={() => addAnalystNote(a)}>Add note</button></div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {ALERT_ACTIONS[a.status]?.includes('resolve') && <input className="border border-line px-2 py-1" maxLength={500} placeholder="Resolution note (optional)"
          aria-label={`Resolution note for ${a.title} (MMSI ${a.mmsi})`} value={notes[a.id] ?? ''} onChange={(e) => setNotes({ ...notes, [a.id]: e.target.value })} />}
        {(ALERT_ACTIONS[a.status] ?? []).map(action => <button type="button" className="btn" key={action} disabled={busy}
          aria-label={`${ACTION_LABELS[action]} ${a.title} (MMSI ${a.mmsi})`} onClick={() => act(a, action)}>{ACTION_LABELS[action]}</button>)}
      </div>
    </div>)}
    {data && data.total > data.alerts.length && <p className="mt-2 text-muted">Showing {data.alerts.length} of {data.total}.</p>}
  </section>
}

export function InvestigationCasesPage() {
  const [params] = useSearchParams()
  const [cases, setCases] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [actionMessage, setActionMessage] = useState('')
  const id = params.get('id')
  const loadList = () => casesApi.list().then(setCases).catch(() => setError('Unable to load cases. Sign in to view them.'))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadList() }, [])
  useEffect(() => {
    setSelected(null); setNote(''); setActionMessage('')
    if (id) casesApi.get(id).then(setSelected).catch(() => setError('Unable to load this case.'))
  }, [id])

  async function transition(action) {
    setBusy(true); setActionMessage('')
    try {
      // Sends the version on screen; a 409 means someone else changed the case first
      setSelected(await casesApi.transition(selected.id, action, selected.version, note.trim()))
      setNote('')
      setActionMessage(action === 'close' ? 'Case closed.' : 'Case reopened.')
    } catch (e) {
      setActionMessage(`${sentence(serverDetail(e) || 'Unable to change this case.')}${isConflict(e) ? ' Nothing was changed; the case was reloaded.' : ''}`)
      casesApi.get(selected.id).then(setSelected).catch(() => {})
    } finally { setBusy(false); loadList() }
  }
  return <Page title="Investigation cases">
    <p className="mb-5 text-muted">Cases link a saved screening assessment to report snapshots. Source coverage remains unknown; these are not findings of an offence.</p>
    {error && <p role="alert" className="text-risk-red">{error}</p>}
    {!cases && !error && <p>Loading cases…</p>}
    {cases?.length === 0 && <p>No cases yet. Open vessel evidence to create one.</p>}
    {cases && <div className="grid gap-5 md:grid-cols-2"><section className={surface}>
      {cases.map(c => <Link className="block border-b border-line py-2" to={`/cases?id=${c.id}`} key={c.id}>{c.title} · {c.mmsi ? `MMSI ${c.mmsi}` : c.sar_detection_id ? `SAR observation ${c.sar_detection_id}` : 'Object reference unavailable'} · {c.status}</Link>)}
    </section><section className={surface}>
      {!id ? <p>Select a case.</p> : !selected ? <p>Loading case…</p> : <><h2 className="text-xl">{selected.title}</h2>
        <p className="mt-2 text-muted">Created by {selected.created_by} · version {selected.version} · {selected.status}</p>
        {selected.sar_detection && <div className="mt-4 rounded border border-line p-3"><h3 className="font-semibold">Unidentified SAR observation</h3><p className="mt-1 text-sm text-muted">{selected.sar_detection.scene_id} · {selected.sar_detection.source} · {selected.sar_detection.association_state?.replaceAll('_', ' ')}</p><p className="mt-1 text-sm">No vessel identity is inferred. Candidate associations remain evidence for review.</p></div>}
        {selected.revisions.length === 0 && <p className="mt-4">No report revision linked yet.</p>}
        {selected.revisions.map(r => <div className="mt-3 border-t border-line pt-3" key={r.version}>
          <Link className="underline" to={`/reports?id=${r.report_id}`}>Report #{r.report_id} · revision {r.version}</Link>
          <p>{r.integrity_ok ? 'Snapshot hash verified' : 'Integrity check failed'} · added by {r.created_by}</p>
        </div>)}
        {['open', 'closed'].includes(selected.status) && <div className="mt-5 border-t border-line pt-4">
          {selected.status === 'closed' && <p className="mb-2 text-muted">A closed case accepts no new report revisions until it is reopened.</p>}
          <label className="block text-muted">Note (optional)
            <textarea className="mt-1 block w-full border border-line p-2 text-ink" maxLength={500} rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
          <button type="button" className="btn mt-2" disabled={busy} onClick={() => transition(selected.status === 'open' ? 'close' : 'reopen')}>
            {selected.status === 'open' ? 'Close case' : 'Reopen case'}
          </button>
          {actionMessage && <p role="status" className="mt-2">{actionMessage}</p>}
        </div>}
        {selected.events?.length > 0 && <section aria-label="Case history" className="mt-5">
          <h3 className="mb-1 text-lg">History</h3>
          {selected.events.map(e => <p className="border-t border-line py-2" key={e.id}>
            {e.event} by {e.actor} · {dateTimeIST(e.created_at)}{e.note && <span className="text-muted"> · {e.note}</span>}
          </p>)}
        </section>}
      </>}
    </section></div>}
  </Page>
}

/** The exact GFW page identity carried from the map; null when no event was selected. */
const gfwEventFrom = (params) => {
  const id = params.get('gfw_event_id')
  if (!id) return null
  return {
    gfw_event_id: id,
    gfw_start_date: params.get('gfw_start_date'),
    gfw_end_date: params.get('gfw_end_date'),
    gfw_offset: Number(params.get('gfw_offset')),
    gfw_limit: Number(params.get('gfw_limit')),
  }
}

export function EvidencePage() {
  const { mmsi } = useParams()
  const [params, setParams] = useSearchParams()
  const gfwEvent = gfwEventFrom(params)
  const { window: selectedWindow, bounds, key: windowKey } = useReplayWindow()
  const vesselRequest = useRef(0)
  // Blocks a second event-only write while one is in flight, even before React re-renders
  const eventWrite = useRef(false)
  // A case created before a failure; a retry resumes it instead of creating another
  const [pending, setPending] = useState(null)
  // The event-only report saved before a failed case request; a retry reuses it
  const [eventReview, setEventReview] = useState(null)
  const [conflict, setConflict] = useState(false)
  const [detail, setDetail] = useState(null)
  const [vesselError, setVesselError] = useState(null)
  const [reportError, setReportError] = useState('')
  const [sarError, setSarError] = useState(false)
  const [weather, setWeather] = useState(null)
  const [detections, setDetections] = useState(null)
  const [regionalEnv, setRegionalEnv] = useState(null)
  const [evidenceSummary, setEvidenceSummary] = useState(null)
  const [encounterGraph, setEncounterGraph] = useState(null)
  const [contextError, setContextError] = useState('')
  const [creatingCase, setCreatingCase] = useState(false)
  const navigate = useNavigate()

  const loadVessel = () => {
    // Only the answer to the latest vessel/window request may paint
    const mine = ++vesselRequest.current
    setVesselError(null)
    setDetail(null)
    vesselsApi.get(mmsi, bounds)
      .then((d) => mine === vesselRequest.current && setDetail(d))
      .catch((e) => mine === vesselRequest.current && setVesselError(e))
  }

  const loadSar = () => {
    setSarError(false)
    setDetections(null)
    sarApi.detections().then(setDetections).catch(() => setSarError(true))
  }

  useEffect(() => {
    if (mmsi) loadVessel()
    return () => { vesselRequest.current += 1 }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mmsi, windowKey])

  useEffect(() => {
    if (!mmsi) return
    setWeather(null); setReportError(''); setPending(null); setConflict(false); setEventReview(null)
    setEvidenceSummary(null); setEncounterGraph(null); setContextError('')
    // A server answer such as 404 "No recent vessel positions" (the weather route looks back 24 h, so every replay vessel) means
    // the weather service was never asked; only a failure with no answer may be called unavailable
    weatherApi.vessel(mmsi).then(setWeather).catch((e) => setWeather({ status: 'unavailable', reason: e?.response && serverDetail(e) ? `Weather not checked: ${sentence(serverDetail(e))}` : 'Weather service unavailable.' }))
    loadSar()
    environmentApi.regional().then(setRegionalEnv).catch(() => setRegionalEnv(null))
    Promise.allSettled([triageApi.evidence(mmsi), encountersApi.graph(mmsi)]).then(([evidence, encounters]) => {
      if (evidence.status === 'fulfilled') setEvidenceSummary(evidence.value)
      if (encounters.status === 'fulfilled') setEncounterGraph(encounters.value)
      if (evidence.status === 'rejected' || encounters.status === 'rejected') setContextError('Some aligned evidence context is unavailable. Missing context remains unknown.')
    })
  }, [mmsi])

  // Ask for the regional SST subset only when it loaded; a missing subset makes the server refuse the whole report
  const oceanContext = Boolean(regionalEnv)

  async function createReport() {
    setReportError('')
    try { const r = await reportsApi.create(Number(mmsi), null, bounds, gfwEvent, oceanContext); navigate(`/reports?id=${r.id}`) }
    catch (error) { setReportError(serverDetail(error) || 'Could not create an evidence snapshot. Check the API and database migration.') }
  }

  async function createCase() {
    setCreatingCase(true); setReportError(''); setConflict(false)
    // A resumed case keeps the window, event and SST choice it was started with
    let step = pending ?? { caseId: null, reportId: null, window: selectedWindow, bounds, gfwEvent, oceanContext }
    try {
      const syncResult = await assessmentsApi.sync(Number(mmsi), step.bounds)
      if (!syncResult.synced) throw new ExpectedCaseError(noObservationsMessage(step.window))
      const result = await assessmentsApi.vessel(Number(mmsi))
      const assessment = pickAssessment(result.assessments, step.window)
      if (!assessment) throw new ExpectedCaseError('No saved assessment matches the selected window. Nothing was linked.')
      if (!step.caseId) {
        const created = await casesApi.create(assessment.id, `Vessel investigation: ${vesselName(detail)}`)
        step = { ...step, caseId: created.id }
        setPending(step)
      }
      if (!step.reportId) {
        const report = await reportsApi.create(Number(mmsi), assessment.id, step.bounds, step.gfwEvent, step.oceanContext)
        step = { ...step, reportId: report.id }
        setPending(step)
      }
      await casesApi.addRevision(step.caseId, step.reportId, 0)
      navigate(`/cases?id=${step.caseId}`)
    } catch (error) {
      setConflict(isConflict(error))
      const message = error instanceof ExpectedCaseError ? error.message : serverDetail(error) || 'Unable to create case.'
      const kept = step.caseId
        ? ` Case ${step.caseId} was created${step.reportId ? ` and report ${step.reportId} was saved` : ''}; retrying resumes it and does not create another case.`
        : isConflict(error) || error instanceof ExpectedCaseError ? '' : ' Sign in as an analyst or administrator if required.'
      setReportError(`${message}${isConflict(error) ? ' No report was created.' : ''}${kept}`)
    } finally { setCreatingCase(false) }
  }

  async function createEventOnlyCase() {
    if (eventWrite.current) return
    eventWrite.current = true
    setCreatingCase(true); setReportError('')
    // Keep a saved report across a failed case so a retry cannot create another report
    let reportId = eventReview?.reportId ?? null
    try {
      if (!reportId) {
        const report = await reportsApi.createEventOnly(Number(mmsi), gfwEvent, oceanContext)
        reportId = report.id
        setEventReview({ reportId })
      }
      const created = await casesApi.createFromReport(reportId, `GFW event review: MMSI ${mmsi}`)
      navigate(`/cases?id=${created.id}`)
    } catch (error) {
      const message = sentence(serverDetail(error) || 'Unable to create the event-only review.')
      setReportError(reportId
        ? `${message} Report ${reportId} is saved. Check Cases before retrying in case the case was already created; retrying uses the saved report.`
        : `${message} Nothing was saved.`)
    } finally { eventWrite.current = false; setCreatingCase(false) }
  }

  if (!mmsi) return <Page title="Vessel evidence"><p>Select a vessel from the <Link className="text-navy underline" to="/map">map</Link> or <Link className="text-navy underline" to="/alerts">alert triage</Link>.</p></Page>

  const envReading = formatEnvironmentalReading(regionalEnv)

  return <Page title={detail ? vesselName(detail) : 'Vessel evidence'}>
    {reportError && <p role="alert" className="mb-4 text-risk-red">{reportError}</p>}
    {conflict && <button type="button" className="btn mb-4" disabled={creatingCase} onClick={createCase}>Re-sync with the same window and retry</button>}
    <ObservationWindowNotice window={selectedWindow} className="mb-4" />
    {gfwEvent && <div className="mb-4 border-l-2 border-line pl-3">
      <p>GFW event <span className="num">{gfwEvent.gfw_event_id}</span> will be attached to the next report (page {gfwEvent.gfw_start_date} to {gfwEvent.gfw_end_date}, offset {gfwEvent.gfw_offset}, limit {gfwEvent.gfw_limit}).</p>
      <p className="text-muted">A historical inferred event point: not a vessel track, not a live position, not proof of fishing or illegality.</p>
      <p className="text-muted">{oceanContext ? 'Regional historical SST context will be included.' : 'Regional SST context is unavailable, so the event is attached without it.'}</p>
      <button type="button" className="mt-1 underline" disabled={Boolean(pending)} onClick={() => setParams({})}>Don't attach this event</button>
    </div>}
    {vesselError && (
      <div className="mb-4">
        <p role="alert" className="text-risk-red">
          {isNotFound(vesselError)
            ? isHistorical(selectedWindow)
              ? `No observations for MMSI ${mmsi} in this window: ${windowRangeIST(selectedWindow)}.`
              : `No positions for MMSI ${mmsi} in the last 24 h.`
            : "Can't reach the API, so this vessel's evidence didn't load."}
        </p>
        {!isNotFound(vesselError) && (
          <button type="button" className="btn btn-primary mt-3" onClick={loadVessel}>
            Try again
          </button>
        )}
        {isNotFound(vesselError) && gfwEvent && (
          <div className="mt-3">
            <p className="text-muted">No AIS observation supports this event, so the review can be created from the event alone. It is not a vessel track and carries no risk score.</p>
            <button type="button" className="btn btn-primary mt-2" disabled={creatingCase} onClick={createEventOnlyCase}>
              {creatingCase ? 'Creating event-only review…' : eventReview?.reportId ? `Retry case from saved report ${eventReview.reportId}` : 'Create event-only review'}
            </button>
          </div>
        )}
      </div>
    )}
    {!detail && !vesselError && <p>Loading evidence…</p>}
    {detail && <div className="grid gap-5 lg:grid-cols-2">
      <section className={surface}>
        <p className="mb-2 text-muted">MMSI {detail.mmsi} · Last observed {dateTimeIST(detail.last_seen)}</p>
        <p className="mb-2 text-muted">AIS data: {sourceLabel(detail)}</p>
        <p className="mb-2 text-muted">
          {envReading ? (
            <Link to="/map#environmental-context" className="text-navy underline">
              Regional ocean context ({envReading.dateIST})
            </Link>
          ) : (
            <Link to="/map#environmental-context" className="text-muted underline">
              Regional ocean context (Environmental data not available)
            </Link>
          )}
        </p>
        <p className="mb-4 text-3xl font-semibold text-navy">{score(detail.score)} <span className="text-base font-normal text-muted">risk score</span></p>
        <h2 className="mb-2 text-xl">Why it was flagged</h2>
        {detail.factors.length ? detail.factors.map(f => {
          const names = [detail, ...(detail.encounters ?? [])]
          return <div className="border-t border-line py-3" key={f.key}><b>{withDisplayNames(f.label, names)}</b><span className="num float-right">+{score(f.points)}</span><p className="text-muted">{withDisplayNames(f.detail, names)}</p></div>
        }) : <p>No risk factors found.</p>}
        <h2 className="mb-2 mt-5 text-xl">Data limitations</h2>
        <DataLimitations items={detail.limitations} rule="border-t" />
        <h2 className="mb-2 mt-5 text-xl">Checks</h2>
        {detail.checks && detail.checks.length > 0 ? (
          detail.checks.map(c => <p className="border-t border-line py-2" key={c.key}><b>{c.label}:</b> {c.detail}</p>)
        ) : (
          <p className="border-t border-line py-2 text-muted">Checks not reported</p>
        )}
        <div className="mt-3 border-t border-line pt-3"><b>Weather at AIS gap:</b> {!weather ? 'Checking…' : weather.status === 'available' ? `${weather.wind_kn} kn wind, ${weather.wave_m} m waves at ${dateTimeIST(weather.time_utc)}. ${weather.source ? `Source: ${weather.source}` : 'Source not reported'} · Weather data: ${weatherMode(weather)}${weather.note ? ` · ${weather.note}` : ''}` : weather.reason}</div>
        <p className="mt-4 text-muted">AIS gaps and encounters are indicators, not proof of an offence.</p>
      </section>
      <section className={surface}>
        <h2 className="mb-3 text-xl">Track and encounters</h2>
        <p>{plural(detail.track.length, 'AIS position', 'AIS positions')} · {plural(detail.gaps.length, 'gap', 'gaps')} · {plural(detail.encounters.length, 'encounter', 'encounters')}</p>
        {detail.encounters.map(e => <p key={e.mmsi} className="mt-3 border-t border-line pt-3">{vesselName(e)} · closest {e.closest_m} m · {hoursLabel(e.hours)}</p>)}
        <section className="mt-5 rounded border border-line p-4" aria-labelledby="aligned-evidence-heading">
          <h3 id="aligned-evidence-heading" className="font-semibold">Aligned evidence context</h3>
          {contextError && <p role="alert" className="mt-2 text-sm text-muted">{contextError}</p>}
          {!evidenceSummary && !contextError && <p className="mt-2 text-sm text-muted">Loading weather, coverage and clear-scenario context…</p>}
          {evidenceSummary && <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-2 text-sm">
            <dt className="text-muted">Weather</dt><dd>{String(evidenceSummary.weather?.status ?? 'unknown').replaceAll('_', ' ')}{evidenceSummary.weather?.summary ? ` · ${evidenceSummary.weather.summary}` : ''}</dd>
            <dt className="text-muted">AIS coverage</dt><dd>{String(evidenceSummary.coverage?.status ?? 'unknown').replaceAll('_', ' ')}{evidenceSummary.coverage?.summary ? ` · ${evidenceSummary.coverage.summary}` : ''}</dd>
            <dt className="text-muted">Clear scenario</dt><dd>{typeof evidenceSummary.clear_scenario === 'string' ? evidenceSummary.clear_scenario : evidenceSummary.clear_scenario?.summary ?? 'Not established'}</dd>
          </dl>}
          {evidenceSummary?.limitations && <p className="mt-2 text-sm text-muted">{Array.isArray(evidenceSummary.limitations) ? evidenceSummary.limitations.join(' ') : evidenceSummary.limitations}</p>}
        </section>
        <section className="mt-5" aria-labelledby="encounter-network-heading">
          <h3 id="encounter-network-heading" className="font-semibold">Encounter network</h3>
          {!encounterGraph && !contextError && <p className="mt-2 text-sm text-muted">Loading encounter links…</p>}
          {encounterGraph?.nodes?.length === 0 && <p className="mt-2 text-sm text-muted">No encounter links were found in this window.</p>}
          {encounterGraph?.nodes?.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{encounterGraph.nodes.map((node) => <span className={`pill ${String(node.mmsi) === String(encounterGraph.root_mmsi) ? 'pill-navy' : 'pill-green'}`} key={node.mmsi}>{node.name || `MMSI ${node.mmsi}`}</span>)}</div>}
          {encounterGraph?.edges?.map((edge, index) => <p className="mt-2 border-t border-line pt-2 text-sm" key={edge.id ?? index}>{edge.source_mmsi ?? edge.source} ↔ {edge.target_mmsi ?? edge.target} · {edge.distance_m != null ? `${Math.round(edge.distance_m)} m` : 'distance unknown'} · {edge.duration_minutes != null ? `${edge.duration_minutes} min` : 'duration unknown'} · coverage {String(edge.coverage_status ?? 'unknown').replaceAll('_', ' ')}</p>)}
          {encounterGraph?.limitations && <p className="mt-2 text-sm text-muted">{Array.isArray(encounterGraph.limitations) ? encounterGraph.limitations.join(' ') : encounterGraph.limitations}</p>}
        </section>
        <h2 className="mb-2 mt-5 text-xl">SAR candidates</h2>
        {sarError ? (
          <div>
            <p role="alert" className="text-muted">SAR detections didn't load, so a match can't be ruled out.</p>
            <button type="button" className="btn btn-primary mt-2" onClick={loadSar}>Try again</button>
          </div>
        ) : !detections ? <p>Loading detections…</p> : detections.filter(d => d.matched_mmsi === detail.mmsi).length ? detections.filter(d => d.matched_mmsi === detail.mmsi).map(d => <p key={d.id} className="border-t border-line py-2">{d.source} · {d.scene_id} · {Math.round(d.match_distance_m)} m from AIS · SAR data: {modeLabel(d)}. Candidate match, not confirmed identity.</p>) : <p className="text-muted">No candidate SAR detection recorded for this vessel.</p>}
        <div className="mt-5 flex flex-wrap gap-3"><Link className="btn" to={`/map?vessel=${detail.mmsi}`}>View track on map</Link><button className="btn btn-primary" onClick={createReport}>Create report snapshot</button><button className="btn" disabled={creatingCase} onClick={createCase}>{creatingCase ? 'Creating case…' : pending ? `Resume case ${pending.caseId}` : 'Create investigation case'}</button></div>
      </section>
    </div>}
  </Page>
}

/** Persisted A-004E evidence; every value is the stored one, timestamps shown as stored UTC. */
function GfwEventEvidence({ evidence }) {
  const snap = evidence.snapshot ?? {}
  const event = snap.event ?? {}
  const sst = snap.regional_ocean_context
  const observed = (sst?.values ?? []).map((v) => v.observed_at).filter(Boolean).sort()
  const row = 'border-b border-line py-2'
  return <section aria-label="GFW event evidence">
    <h3 className="mb-2 mt-6 text-lg">GFW event evidence</h3>
    <p className="text-muted">A historical inferred event point. It is not a vessel track, not a live vessel position, not proof of fishing and not proof of illegality.</p>
    <p className={row}><b>Source:</b> {snap.source ?? 'Not reported'} · dataset {snap.dataset ?? 'not reported'}</p>
    <p className={row}><b>Event:</b> <span className="num">{event.id ?? 'Not reported'}</span>{event.type ? ` · ${event.type}` : ''}</p>
    <p className={row}><b>Event start/end (UTC, as stored):</b> {event.start ?? 'not reported'} to {event.end ?? 'not reported'}</p>
    <p className={row}><b>Event position:</b> {event.position ? `${event.position.lat}, ${event.position.lon}` : 'Not reported'}</p>
    <p className={row}><b>Requested page:</b> {snap.requested_start ?? '?'} to {snap.requested_end_exclusive ?? '?'} (end exclusive){snap.retrieved_at ? ` · retrieved ${snap.retrieved_at}` : ''}</p>
    <p className={`${row} num break-all text-xs`}>Evidence SHA-256 {evidence.sha256 ?? 'not reported'}</p>
    {evidence.integrity_note && <p className={`${row} text-muted`}>{evidence.integrity_note}</p>}
    <p className={`${row} text-muted`}><b className="text-ink">Limitations: </b>{snap.limitations || 'Not reported'}</p>
    {sst && <div className={row}>
      <p><b>Sea surface temperature (dated independently of the event):</b> {sst.source ?? 'Source not reported'}{sst.dataset ? ` · ${sst.dataset}` : ''}{sst.mode ? ` · ${sst.mode}` : ''}</p>
      <p className="text-muted">Observed {observed.length ? `${observed[0]} to ${observed[observed.length - 1]}` : 'dates not reported'} · {plural(sst.values?.length ?? 0, 'value', 'values')}{sst.unit ? ` in ${sst.unit}` : ''}</p>
      {sst.association && <p className="text-muted">{sst.association}</p>}
      {sst.limitations && <p className="text-muted">{sst.limitations}</p>}
    </div>}
  </section>
}

/** Top-level items of a JSON array as their exact source text, so numbers keep the server's form. Expects an array of objects. */
function rawArrayItems(text) {
  const items = []
  let depth = 0, start = 0, inString = false
  for (let i = 0; i < text.length; i++) {
    const c = text[i]
    if (inString) { if (c === '\\') i++; else if (c === '"') inString = false }
    else if (c === '"') inString = true
    else if (c === '{' || c === '[') { if (depth === 1) start = i; depth++ }
    else if (c === '}' || c === ']') { depth--; if (depth === 1) items.push(text.slice(start, i + 1)) }
  }
  return items
}

/** Saves the stored report exactly as the server sent it, so the SHA-256 can be checked against the snapshot outside the app. */
async function exportReport(report) {
  const raw = rawArrayItems(await reportsApi.listText()).find((item) => JSON.parse(item).id === report.id)
  if (!raw) throw new Error('report not in list')
  const header = JSON.stringify({
    exported_at: new Date().toISOString(),
    hash_method: 'SHA-256 of report.snapshot as UTF-8 JSON with sorted keys and no whitespace (Python json.dumps sort_keys=True, separators=(",", ":"), ensure_ascii=False). '
      + 'report is the server response text, unchanged: a number such as 59.0 must stay a float, so read it with a parser that keeps that, such as Python json.',
    integrity_verified_by_server: report.integrity_ok,
    notice: 'AIS gaps and encounters are indicators, not proof of an offence. Sign-off records a review; this file was not sent anywhere.',
  }, null, 2)
  const text = `${header.slice(0, -2)},\n  "report": ${raw}\n}\n`
  const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }))
  const link = Object.assign(document.createElement('a'), { href: url, download: `samudrasense-report-${report.id}.json` })
  link.click()
  URL.revokeObjectURL(url)
}

/** Only a server-issued checksum can be sent as the approval guard. */
const validChecksum = (value) => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)

const evidenceBasisLabel = (snapshot) => {
  if (snapshot?.evidence_basis === 'gfw_event_only') return 'Selected GFW event only'
  if (snapshot?.persisted_assessment) return 'Vessel and assessment evidence'
  return 'Generated vessel evidence snapshot'
}

const sourceNames = (snapshot) => {
  const names = [snapshot?.source, snapshot?.dataset && `dataset ${snapshot.dataset}`, snapshot?.regional_ocean_context?.source]
  for (const sar of snapshot?.sar_candidates ?? []) names.push(sar?.source)
  const gfw = snapshot?.gfw_event_evidence?.snapshot
  if (gfw?.source) names.push(gfw.source)
  return [...new Set(names.filter(Boolean))]
}

function EvidenceBasis({ snapshot, showSources = true }) {
  const sources = showSources ? sourceNames(snapshot) : []
  return <section aria-label="Evidence basis and sources" className="my-4 rounded border border-line p-3 text-sm">
    <p>Evidence basis: {evidenceBasisLabel(snapshot)}</p>
    {snapshot?.persisted_assessment?.id && <p>Persisted assessment: {snapshot.persisted_assessment.id}</p>}
    {snapshot?.evidence_basis && <p className="text-muted">Basis code: {snapshot.evidence_basis}</p>}
    {showSources && <p>Sources: {sources.length ? sources.join(' · ') : 'not reported'}</p>}
    {snapshot?.evidence_basis === 'gfw_event_only' && <p className="text-muted">A historical inferred event point, not a track and not proof of illegality. AIS coverage is unknown.</p>}
  </section>
}

/** A-004F event-only reports carry no vessel detail, assessment or score; show that absence plainly. */
const isEventOnlyReport = (report) => report?.snapshot?.evidence_basis === 'gfw_event_only'

function EventOnlyReport({ report }) {
  const snap = report.snapshot
  return <>
    <p className="text-muted">REPORT #{report.id} · Event-only · {report.signed_at ? 'Signed' : 'Awaiting review'}</p>
    <h2 className="my-4 text-2xl">GFW event review: {vesselName(snap)}</h2>
    <p>MMSI <b className="num">{report.mmsi}</b></p>
    <p className="mt-2 text-muted">AIS evidence: unavailable · Assessment: unavailable. No risk score is attached or inferred.</p>
    <EvidenceBasis snapshot={snap} showSources={false} />
    {snap.ais_evidence?.note && <p className="text-muted">{snap.ais_evidence.note}</p>}
    {snap.ais_evidence?.limitation && <p className="text-muted">{snap.ais_evidence.limitation}</p>}
    {snap.assessment?.note && <p className="text-muted">{snap.assessment.note}</p>}
    <GfwEventEvidence evidence={snap.gfw_event_evidence} />
    <h3 className="mb-2 mt-6 text-lg">Data limitations</h3>
    <DataLimitations items={snap.limitations ? [snap.limitations] : []} rule="border-b" />
  </>
}

/** Downloads bytes the server returned, without rewriting them. */
function downloadFile(data, filename, type) {
  const url = URL.createObjectURL(new Blob([data], { type }))
  const link = Object.assign(document.createElement('a'), { href: url, download: filename })
  link.click()
  URL.revokeObjectURL(url)
}

export function ReportsPage() {
  const [params] = useSearchParams()
  const { id: routeId } = useParams()
  const reportId = routeId ?? params.get('id')
  const [reports, setReports] = useState(null)
  const [detail, setDetail] = useState(null)
  const [reviewed, setReviewed] = useState(false)
  const [error, setError] = useState('')
  const [conflict, setConflict] = useState(false)
  const [deliveries, setDeliveries] = useState(null)
  const [recipients, setRecipients] = useState('')
  const [delivering, setDelivering] = useState(false)
  const [deliveryMessage, setDeliveryMessage] = useState('')
  const listSelected = reportId ? reports?.find(r => String(r.id) === String(reportId)) : reports?.[0]
  const selected = reportId && detail && String(detail.id) === String(reportId) ? detail : listSelected
  const selectedIdRef = useRef(selected?.id)
  selectedIdRef.current = selected?.id
  const reportNotFound = Boolean(reportId && reports && !selected)
  const refresh = useCallback(() => reportsApi.list().then(setReports).catch(() => setError('Unable to load reports.')), [])
  // The detail endpoint is the source of truth; a failure falls back to the already-loaded list.
  const loadDetail = useCallback((id) => {
    if (typeof reportsApi.get !== 'function') return Promise.resolve()
    return reportsApi.get(Number(id)).then(setDetail).catch(() => {})
  }, [])
  useEffect(() => {
    refresh()
    setDetail(null)
    if (reportId) loadDetail(reportId)
  }, [reportId])
  useEffect(() => {
    setReviewed(false); setError(''); setConflict(false); setDeliveries(null); setDeliveryMessage('')
    if (selected?.id) reportsApi.deliveries(selected.id).then(setDeliveries).catch(() => setDeliveries([]))
  }, [selected?.id])
  async function sign() {
    const signingId = selected?.id
    setError('')
    setConflict(false)
    try {
      const signed = validChecksum(selected.sha256)
        ? await reportsApi.sign(signingId, 'Authenticated reviewer', reviewed, selected.sha256)
        : await reportsApi.sign(signingId, 'Authenticated reviewer', reviewed)
      setDetail(d => (d && String(d.id) === String(signingId) ? { ...d, ...signed } : d))
      // The list must learn of the signature even if another report is open by now
      await refresh()
      if (selectedIdRef.current !== signingId) return
      setReviewed(false)
    } catch (e) {
      if (selectedIdRef.current !== signingId) return
      const detail = e.response?.data?.detail
      if (e.response?.status === 409) setConflict(true)
      if (typeof detail === 'string') {
        setError(detail)
      } else if (e.response?.status === 422 || (detail !== undefined && detail !== null)) {
        setError('The API rejected this sign-off. Reload the report and try again.')
      } else {
        setError('Could not sign report.')
      }
    }
  }
  function reload() {
    setError('')
    setConflict(false)
    setReviewed(false)
    if (reportId) loadDetail(reportId)
    refresh()
  }
  async function exportPdf() {
    try {
      downloadFile(await reportsApi.exportPdf(selected.id), `samudrasense-report-${selected.id}.pdf`, 'application/pdf')
    } catch (e) {
      setError(serverDetail(e) || 'Could not export the approved PDF.')
    }
  }
  async function downloadManifest() {
    try {
      const manifest = await reportsApi.manifest(selected.id)
      downloadFile(manifest.canonical_json, `samudrasense-report-${selected.id}-manifest.json`, 'application/json')
    } catch (e) {
      setError(serverDetail(e) || 'Could not download the manifest.')
    }
  }
  async function deliverReport(event) {
    event.preventDefault()
    const addressList = recipients.split(',').map((value) => value.trim()).filter(Boolean)
    if (!addressList.length) return
    setDelivering(true); setDeliveryMessage('')
    try {
      const key = globalThis.crypto?.randomUUID?.() ?? `report-${selected.id}-${Date.now()}`
      const result = await reportsApi.deliver(selected.id, selected.sha256, addressList, key)
      setDeliveryMessage(`Delivery ${result.state ?? result.status ?? 'queued'}. Provider acceptance does not mean received or read.`)
      setRecipients('')
      setDeliveries(await reportsApi.deliveries(selected.id))
    } catch (deliveryError) { setDeliveryMessage(serverDetail(deliveryError) || 'The approved report could not be queued for delivery.') }
    finally { setDelivering(false) }
  }
  async function submitDelivery(delivery) {
    setDelivering(true); setDeliveryMessage('')
    try {
      const submitted = await reportsApi.submitDelivery(delivery.id)
      setDeliveryMessage(`Delivery ${submitted.state}. Submitted means written to the configured local sink, not received or read.`)
      setDeliveries(await reportsApi.deliveries(selected.id))
    } catch (deliveryError) { setDeliveryMessage(serverDetail(deliveryError) || 'The queued delivery could not be submitted.') }
    finally { setDelivering(false) }
  }
  return <Page title="Incident reports">
    <p className="mb-5 text-muted">Evidence snapshots are stored locally. Approval and delivery are separate actions; delivery always uses the exact approved checksum and administrator-approved recipients.</p>
    {error && <p role="alert" className="mb-4 text-risk-red">{error}</p>}
    {!reports && !error && <p>Loading reports…</p>}
    {reports?.length === 0 && <p>No reports yet. Open a vessel and create a report snapshot.</p>}
    {reports && reports.length > 0 && <div className="grid gap-5 lg:grid-cols-[220px_1fr_300px]">
      <nav className={surface}>{reports.map(r => <Link className="block border-b border-line py-2" to={`/reports?id=${r.id}`} key={r.id}>#{r.id} · {vesselName(r.snapshot)}<span className="block text-[13px] text-muted">{dateTimeIST(r.created_at)} · {r.signed_at ? 'Signed' : 'Awaiting review'}</span></Link>)}</nav>
      {reportNotFound ? (
        <p role="alert" className={surface}>Report #{reportId} was not found.</p>
      ) : selected ? (
        <>
          <article className={surface}>{isEventOnlyReport(selected) ? <EventOnlyReport report={selected} /> : <><p className="text-muted">REPORT #{selected.id} · {selected.signed_at ? 'Signed' : 'Awaiting review'}</p><p className="text-sm font-medium">{selected.signed_at ? 'Approved' : 'Draft — awaiting approval'}</p><h2 className="my-4 text-2xl">Vessel investigation: {vesselName(selected.snapshot)}</h2>
            <p>MMSI <b className="num">{selected.mmsi}</b> · Risk <b className="num">{score(selected.snapshot.score)}</b> · Last observed {dateTimeIST(selected.snapshot.last_seen)}</p>
            <h3 className="mb-2 mt-6 text-lg">Evidence and source</h3>
            <p className="text-muted">Values below come from the preserved AIS track and risk-engine calculation in this snapshot.</p>
            <EvidenceBasis snapshot={selected.snapshot} />
            <p className="text-muted">AIS data: {sourceLabel(selected.snapshot)}</p>
            <ObservationWindowNotice className="my-2" window={selected.snapshot.window} assessmentWindow={selected.snapshot.persisted_assessment?.window} windowMatch={selected.snapshot.persisted_assessment?.window_match} />
            {selected.snapshot.factors.map(f => {
              const names = [selected.snapshot, ...(selected.snapshot.encounters ?? [])]
              return <div key={f.key} className="border-b border-line py-3"><b>{withDisplayNames(f.label, names)}</b> · {withDisplayNames(f.detail, names)} · +{score(f.points)}</div>
            })}
            {selected.snapshot.sar_candidates?.map(d => <div key={d.id} className="border-b border-line py-3"><b>SAR candidate:</b> {d.source} · scene {d.scene_id} · {dateTimeIST(d.observed_at)} · {Math.round(d.match_distance_m)} m from AIS · SAR data: {modeLabel(d)}. Identity not confirmed.</div>)}
            {selected.snapshot.gfw_event_evidence && <GfwEventEvidence evidence={selected.snapshot.gfw_event_evidence} />}
            <h3 className="mb-2 mt-6 text-lg">Checks</h3>
            {selected.snapshot.checks && selected.snapshot.checks.length > 0 ? (
              selected.snapshot.checks.map(c => (
                <div key={c.key} className="border-b border-line py-2">
                  <b>{c.label}:</b> {c.detail}
                </div>
              ))
            ) : (
              <p className="border-b border-line py-2 text-muted">Checks not reported</p>
            )}
            <h3 className="mb-2 mt-6 text-lg">Data limitations</h3>
            <DataLimitations items={selected.snapshot.limitations} rule="border-b" />
            <p className="mt-4 text-muted">AIS gaps and encounters are indicators, not proof of an offence.</p>
            <details className="mt-4"><summary>View source snapshot ({plural(selected.snapshot.track.length, 'AIS position', 'AIS positions')})</summary><pre className="mt-2 max-h-64 overflow-auto text-xs">{JSON.stringify(selected.snapshot, null, 2)}</pre></details>
          </>}</article>
          <aside className={surface}><h2 className="text-xl">Evidence integrity</h2><p className="mt-2">{selected.integrity_ok ? 'Snapshot hash verified' : 'Hash mismatch — sign-off blocked'}</p><p className="mt-2 text-xs text-muted">The SHA-256 value is an integrity checksum, not a digital signature.</p><p className="num mt-2 break-all text-xs text-muted">SHA-256 {selected.sha256}</p>
            <button className="btn mt-4 w-full" onClick={() => exportReport(selected).catch(() => setError('Could not export this report. Reload the page and try again.'))}>Export evidence record (JSON)</button>
            <p className="mt-2 text-xs text-muted">Downloads the stored snapshot, its hash and the review state{selected.integrity_ok ? '' : ', including the failed integrity check'}.</p>
            <button className="btn mt-2 w-full" onClick={downloadManifest}>Download manifest (canonical JSON)</button>
            <p className="mt-2 text-xs text-muted">The manifest keeps the server's canonical JSON and its checksum for independent verification.</p>
            {selected.signed_at && <button className="btn mt-2 w-full" onClick={exportPdf}>Export approved PDF</button>}
            {conflict && <button className="btn mt-3 w-full" onClick={reload}>Reload report</button>}
            {selected.signed_at ? <p className="mt-5">Signed by {selected.signed_by} at {dateTimeIST(selected.signed_at)}</p> : <div className="mt-5"><p className="text-muted">Your signed-in account will be recorded as reviewer.</p><label className="my-4 flex gap-2"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />I reviewed the evidence and source snapshot.</label><button className="btn btn-primary w-full" disabled={!selected.integrity_ok || !reviewed} onClick={sign}>Record sign-off</button></div>}
            {selected.signed_at && <section className="mt-5 border-t border-line pt-4" aria-labelledby="delivery-heading">
              <h3 id="delivery-heading" className="text-lg">Delivery</h3>
              <p className="mt-1 text-xs text-muted">Only recipients approved in deployment settings are accepted. Submitted does not mean received or read.</p>
              <form className="mt-3 space-y-2" onSubmit={deliverReport}><label className="grid gap-1 text-sm">Local sink recipients<input className="input" type="text" placeholder="operations@example.test" value={recipients} onChange={(event) => setRecipients(event.target.value)} required /></label><button className="btn btn-primary w-full" disabled={delivering || !validChecksum(selected.sha256)} type="submit">{delivering ? 'Queueing…' : 'Queue approved version'}</button></form>
              {deliveryMessage && <p role="status" className="mt-2 text-sm">{deliveryMessage}</p>}
              {deliveries === null ? <p className="mt-3 text-sm text-muted">Loading delivery history…</p> : (deliveries.items ?? deliveries).length === 0 ? <p className="mt-3 text-sm text-muted">No delivery attempts.</p> : (deliveries.items ?? deliveries).map((delivery) => <div className="mt-2 border-t border-line pt-2 text-sm" key={delivery.id}><p>{String(delivery.state ?? delivery.status ?? 'unknown').replaceAll('_', ' ')} · {delivery.created_at ? dateTimeIST(delivery.created_at) : 'time not reported'}{delivery.attempts != null ? ` · ${delivery.attempts} attempts` : ''}</p>{delivery.state === 'queued' && <button className="btn mt-2 w-full" type="button" disabled={delivering} onClick={() => submitDelivery(delivery)}>Submit to local sink</button>}</div>)}
            </section>}
          </aside>
        </>
      ) : null}
    </div>}
  </Page>
}
