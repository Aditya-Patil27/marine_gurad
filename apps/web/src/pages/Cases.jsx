import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { assessmentsApi, casesApi, vesselsApi, reportsApi, weatherApi, sarApi, environmentApi, isConflict, isNotFound, serverDetail } from '../lib/api'
import { formatEnvironmentalReading } from '../lib/environment'
import { dateTimeIST, hoursLabel, modeLabel, score, sourceLabel, vesselName, withDisplayNames, windowRangeIST } from '../lib/format'
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
  </Page>
}

export function InvestigationCasesPage() {
  const [params] = useSearchParams()
  const [cases, setCases] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const id = params.get('id')
  useEffect(() => { casesApi.list().then(setCases).catch(() => setError('Unable to load cases. Sign in to view them.')) }, [])
  useEffect(() => {
    setSelected(null)
    if (id) casesApi.get(id).then(setSelected).catch(() => setError('Unable to load this case.'))
  }, [id])
  return <Page title="Investigation cases">
    <p className="mb-5 text-muted">Cases link a saved screening assessment to report snapshots. Source coverage remains unknown; these are not findings of an offence.</p>
    {error && <p role="alert" className="text-risk-red">{error}</p>}
    {!cases && !error && <p>Loading cases…</p>}
    {cases?.length === 0 && <p>No cases yet. Open vessel evidence to create one.</p>}
    {cases && <div className="grid gap-5 md:grid-cols-2"><section className={surface}>
      {cases.map(c => <Link className="block border-b border-line py-2" to={`/cases?id=${c.id}`} key={c.id}>{c.title} · MMSI {c.mmsi} · {c.status}</Link>)}
    </section><section className={surface}>
      {!id ? <p>Select a case.</p> : !selected ? <p>Loading case…</p> : <><h2 className="text-xl">{selected.title}</h2>
        <p className="mt-2 text-muted">Created by {selected.created_by} · version {selected.version} · {selected.status}</p>
        {selected.revisions.length === 0 && <p className="mt-4">No report revision linked yet.</p>}
        {selected.revisions.map(r => <div className="mt-3 border-t border-line pt-3" key={r.version}>
          <Link className="underline" to={`/reports?id=${r.report_id}`}>Report #{r.report_id} · revision {r.version}</Link>
          <p>{r.integrity_ok ? 'Snapshot hash verified' : 'Integrity check failed'} · added by {r.created_by}</p>
        </div>)}
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
  // A case created before a failure; a retry resumes it instead of creating another
  const [pending, setPending] = useState(null)
  const [conflict, setConflict] = useState(false)
  const [detail, setDetail] = useState(null)
  const [vesselError, setVesselError] = useState(null)
  const [reportError, setReportError] = useState('')
  const [sarError, setSarError] = useState(false)
  const [weather, setWeather] = useState(null)
  const [detections, setDetections] = useState(null)
  const [regionalEnv, setRegionalEnv] = useState(null)
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
    setWeather(null); setReportError(''); setPending(null); setConflict(false)
    weatherApi.vessel(mmsi).then(setWeather).catch(() => setWeather({ status: 'unavailable', reason: 'Weather service unavailable.' }))
    loadSar()
    environmentApi.regional().then(setRegionalEnv).catch(() => setRegionalEnv(null))
  }, [mmsi])

  async function createReport() {
    setReportError('')
    try { const r = await reportsApi.create(Number(mmsi), null, bounds, gfwEvent); navigate(`/reports?id=${r.id}`) }
    catch (error) { setReportError(serverDetail(error) || 'Could not create an evidence snapshot. Check the API and database migration.') }
  }

  async function createCase() {
    setCreatingCase(true); setReportError(''); setConflict(false)
    // A resumed case keeps the window and event it was started with
    let step = pending ?? { caseId: null, reportId: null, window: selectedWindow, bounds, gfwEvent }
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
        const report = await reportsApi.create(Number(mmsi), assessment.id, step.bounds, step.gfwEvent)
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

  if (!mmsi) return <Page title="Vessel evidence"><p>Select a vessel from the <Link className="text-navy underline" to="/map">map</Link> or <Link className="text-navy underline" to="/alerts">alert triage</Link>.</p></Page>

  const envReading = formatEnvironmentalReading(regionalEnv)

  return <Page title={detail ? vesselName(detail) : 'Vessel evidence'}>
    {reportError && <p role="alert" className="mb-4 text-risk-red">{reportError}</p>}
    {conflict && <button type="button" className="btn mb-4" disabled={creatingCase} onClick={createCase}>Re-sync with the same window and retry</button>}
    <ObservationWindowNotice window={selectedWindow} className="mb-4" />
    {gfwEvent && <div className="mb-4 border-l-2 border-line pl-3">
      <p>GFW event <span className="num">{gfwEvent.gfw_event_id}</span> will be attached to the next report (page {gfwEvent.gfw_start_date} to {gfwEvent.gfw_end_date}, offset {gfwEvent.gfw_offset}, limit {gfwEvent.gfw_limit}).</p>
      <p className="text-muted">A historical inferred event point: not a vessel track, not a live position, not proof of fishing or illegality.</p>
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
        <div className="mt-3 border-t border-line pt-3"><b>Weather at AIS gap:</b> {!weather ? 'Checking…' : weather.status === 'available' ? `${weather.wind_kn} kn wind, ${weather.wave_m} m waves at ${dateTimeIST(weather.time_utc)}. ${weather.source ? `Source: ${weather.source}` : 'Source not reported'} · Weather data: ${modeLabel(weather)}${weather.note ? ` · ${weather.note}` : ''}` : weather.reason}</div>
        <p className="mt-4 text-muted">AIS gaps and encounters are indicators, not proof of an offence.</p>
      </section>
      <section className={surface}>
        <h2 className="mb-3 text-xl">Track and encounters</h2>
        <p>{plural(detail.track.length, 'AIS position', 'AIS positions')} · {plural(detail.gaps.length, 'gap', 'gaps')} · {plural(detail.encounters.length, 'encounter', 'encounters')}</p>
        {detail.encounters.map(e => <p key={e.mmsi} className="mt-3 border-t border-line pt-3">{vesselName(e)} · closest {e.closest_m} m · {hoursLabel(e.hours)}</p>)}
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

export function ReportsPage() {
  const [params] = useSearchParams()
  const [reports, setReports] = useState(null)
  const [reviewed, setReviewed] = useState(false)
  const [error, setError] = useState('')
  const reportId = params.get('id')
  const selected = reportId ? reports?.find(r => String(r.id) === reportId) : reports?.[0]
  const selectedIdRef = useRef(selected?.id)
  selectedIdRef.current = selected?.id
  const reportNotFound = Boolean(reportId && reports && !selected)
  const refresh = () => reportsApi.list().then(setReports).catch(() => setError('Unable to load reports.'))
  useEffect(() => { refresh() }, [])
  useEffect(() => { setReviewed(false); setError('') }, [selected?.id])
  async function sign() {
    const signingId = selected?.id
    setError('')
    try {
      await reportsApi.sign(signingId, 'Authenticated reviewer', reviewed)
      // The list must learn of the signature even if another report is open by now
      await refresh()
      if (selectedIdRef.current !== signingId) return
      setReviewed(false)
    } catch (e) {
      if (selectedIdRef.current !== signingId) return
      const detail = e.response?.data?.detail
      if (typeof detail === 'string') {
        setError(detail)
      } else if (e.response?.status === 422 || (detail !== undefined && detail !== null)) {
        setError('The API rejected this sign-off. Check the officer name and try again.')
      } else {
        setError('Could not sign report.')
      }
    }
  }
  return <Page title="Incident reports">
    <p className="mb-5 text-muted">Evidence snapshots are stored locally. Sign-off records the authenticated reviewer and does not send a report.</p>
    {error && <p role="alert" className="mb-4 text-risk-red">{error}</p>}
    {!reports && !error && <p>Loading reports…</p>}
    {reports?.length === 0 && <p>No reports yet. Open a vessel and create a report snapshot.</p>}
    {reports && reports.length > 0 && <div className="grid gap-5 lg:grid-cols-[220px_1fr_300px]">
      <nav className={surface}>{reports.map(r => <Link className="block border-b border-line py-2" to={`/reports?id=${r.id}`} key={r.id}>#{r.id} · {vesselName(r.snapshot)}<span className="block text-[13px] text-muted">{dateTimeIST(r.created_at)} · {r.signed_at ? 'Signed' : 'Awaiting review'}</span></Link>)}</nav>
      {reportNotFound ? (
        <p role="alert" className={surface}>Report #{reportId} was not found.</p>
      ) : selected ? (
        <>
          <article className={surface}><p className="text-muted">REPORT #{selected.id} · {selected.signed_at ? 'Signed' : 'Awaiting review'}</p><h2 className="my-4 text-2xl">Vessel investigation: {vesselName(selected.snapshot)}</h2>
            <p>MMSI <b className="num">{selected.mmsi}</b> · Risk <b className="num">{score(selected.snapshot.score)}</b> · Last observed {dateTimeIST(selected.snapshot.last_seen)}</p>
            <h3 className="mb-2 mt-6 text-lg">Evidence and source</h3>
            <p className="text-muted">Values below come from the preserved AIS track and risk-engine calculation in this snapshot.</p>
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
          </article>
          <aside className={surface}><h2 className="text-xl">Evidence integrity</h2><p className="mt-2">{selected.integrity_ok ? 'Snapshot hash verified' : 'Hash mismatch — sign-off blocked'}</p><p className="mt-2 text-xs text-muted">The hash detects accidental changes; it is stored alongside the evidence and is not a digital signature.</p><p className="num mt-2 break-all text-xs text-muted">SHA-256 {selected.sha256}</p>
            {selected.signed_at ? <p className="mt-5">Signed by {selected.signed_by} at {dateTimeIST(selected.signed_at)}</p> : <div className="mt-5"><p className="text-muted">Your signed-in account will be recorded as reviewer.</p><label className="my-4 flex gap-2"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />I reviewed the evidence and source snapshot.</label><button className="btn btn-primary w-full" disabled={!selected.integrity_ok || !reviewed} onClick={sign}>Record sign-off</button></div>}
          </aside>
        </>
      ) : null}
    </div>}
  </Page>
}
