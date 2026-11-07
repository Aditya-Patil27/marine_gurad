import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { assessmentsApi, casesApi, vesselsApi, reportsApi, weatherApi, sarApi, environmentApi, isNotFound, serverDetail } from '../lib/api'
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
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { vesselsApi.list(168).then(setData).catch(() => setError('Unable to load vessels.')) }, [])
  return <Page title="Alert triage">
    <p className="mb-5 text-muted">Current risk signals from the last 7 days. Weather does not change these scores. Open a vessel to see its weather, and Reports to see review status.</p>
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

export function EvidencePage() {
  const { mmsi } = useParams()
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
    setVesselError(null)
    setDetail(null)
    vesselsApi.get(mmsi).then(setDetail).catch(setVesselError)
  }

  const loadSar = () => {
    setSarError(false)
    setDetections(null)
    sarApi.detections().then(setDetections).catch(() => setSarError(true))
  }

  useEffect(() => {
    if (!mmsi) return
    setWeather(null); setReportError('')
    loadVessel()
    weatherApi.vessel(mmsi).then(setWeather).catch(() => setWeather({ status: 'unavailable', reason: 'Weather service unavailable.' }))
    loadSar()
    environmentApi.regional().then(setRegionalEnv).catch(() => setRegionalEnv(null))
  }, [mmsi])

  async function createReport() {
    try { const r = await reportsApi.create(Number(mmsi)); navigate(`/reports?id=${r.id}`) }
    catch { setReportError('Could not create an evidence snapshot. Check the API and database migration.') }
  }

  async function createCase() {
    setCreatingCase(true); setReportError('')
    let caseId = null
    let reportId = null
    try {
      const syncResult = await assessmentsApi.sync(Number(mmsi))
      if (!syncResult.synced) throw new Error('No assessment could be generated for this vessel in the selected lookback window.')
      const result = await assessmentsApi.vessel(Number(mmsi))
      const assessment = result.assessments.find(a => a.rule_version === 'v1' && a.source_mode === 'unknown')
      if (!assessment) throw new Error('No current assessment exists for this vessel.')
      const created = await casesApi.create(assessment.id, `Vessel investigation: ${vesselName(detail)}`)
      caseId = created.id
      const report = await reportsApi.create(Number(mmsi), assessment.id)
      reportId = report.id
      await casesApi.addRevision(caseId, reportId, 0)
      navigate(`/cases?id=${caseId}`)
    } catch (error) {
      const detailMessage = error.response?.data?.detail || error.message || 'Unable to create case.'
      setReportError(`${detailMessage}${caseId ? ` Case ${caseId} was created${reportId ? ` and report ${reportId} was saved` : ''}; do not retry without reviewing these records.` : ' Sign in as an analyst or administrator if required.'}`)
    } finally { setCreatingCase(false) }
  }

  if (!mmsi) return <Page title="Vessel evidence"><p>Select a vessel from the <Link className="text-navy underline" to="/map">map</Link> or <Link className="text-navy underline" to="/alerts">alert triage</Link>.</p></Page>

  const envReading = formatEnvironmentalReading(regionalEnv)

  return <Page title={detail ? vesselName(detail) : 'Vessel evidence'}>
    {reportError && <p role="alert" className="mb-4 text-risk-red">{reportError}</p>}
    {vesselError && (
      <div className="mb-4">
        <p role="alert" className="text-risk-red">
          {isNotFound(vesselError)
            ? `No positions for MMSI ${mmsi} in the last 24 h.`
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
        <div className="mt-5 flex flex-wrap gap-3"><Link className="btn" to={`/map?vessel=${detail.mmsi}`}>View track on map</Link><button className="btn btn-primary" onClick={createReport}>Create report snapshot</button><button className="btn" disabled={creatingCase} onClick={createCase}>{creatingCase ? 'Creating case…' : 'Create investigation case'}</button></div>
      </section>
    </div>}
  </Page>
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
            {selected.snapshot.factors.map(f => {
              const names = [selected.snapshot, ...(selected.snapshot.encounters ?? [])]
              return <div key={f.key} className="border-b border-line py-3"><b>{withDisplayNames(f.label, names)}</b> · {withDisplayNames(f.detail, names)} · +{score(f.points)}</div>
            })}
            {selected.snapshot.sar_candidates?.map(d => <div key={d.id} className="border-b border-line py-3"><b>SAR candidate:</b> {d.source} · scene {d.scene_id} · {dateTimeIST(d.observed_at)} · {Math.round(d.match_distance_m)} m from AIS · SAR data: {modeLabel(d)}. Identity not confirmed.</div>)}
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
