import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { vesselsApi, reportsApi, weatherApi, sarApi, isNotFound } from '../lib/api'
import { score, timeIST, vesselName } from '../lib/format'

const surface = 'card p-5'

function Page({ title, children }) {
  return <div className="h-full overflow-y-auto p-6 md:p-10"><h1 className="mb-6 text-3xl font-semibold">{title}</h1>{children}</div>
}

export function AlertsPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { vesselsApi.list().then(setData).catch(() => setError('Unable to load vessels.')) }, [])
  return <Page title="Alert triage">
    <p className="mb-5 text-muted">Current risk signals from the last 24 hours. Weather and review status are not yet automated.</p>
    {error && <p role="alert">{error}</p>}
    {!data && !error && <p>Loading alerts…</p>}
    {data && <div className="grid gap-5 md:grid-cols-2">{['high', 'medium'].map(level => <section className={surface} key={level}>
      <h2 className="mb-3 text-xl">{level === 'high' ? 'Needs review' : 'Watch'}</h2>
      {data.vessels.filter(v => v.level === level).map(v => <Link className="block border-t border-line py-3 hover:text-navy" to={`/vessels/${v.mmsi}`} key={v.mmsi}>
        <b>{vesselName(v)}</b><span className="num float-right">{score(v.score)}</span><p className="text-muted">{v.headline}</p>
      </Link>)}
      {!data.vessels.some(v => v.level === level) && <p className="text-muted">No vessels in this category.</p>}
    </section>)}</div>}
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
  }, [mmsi])

  async function createReport() {
    try { const r = await reportsApi.create(Number(mmsi)); navigate(`/reports?id=${r.id}`) }
    catch { setReportError('Could not create an evidence snapshot. Check the API and database migration.') }
  }

  if (!mmsi) return <Page title="Vessel evidence"><p>Select a vessel from the <Link className="text-navy underline" to="/map">map</Link> or <Link className="text-navy underline" to="/alerts">alert triage</Link>.</p></Page>

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
        <p className="mb-2 text-muted">MMSI {detail.mmsi} · Last observed {timeIST(detail.last_seen)} IST</p>
        <p className="mb-4 text-3xl font-semibold text-navy">{score(detail.score)} <span className="text-base font-normal text-muted">risk score</span></p>
        <h2 className="mb-2 text-xl">Why it was flagged</h2>
        {detail.factors.length ? detail.factors.map(f => <div className="border-t border-line py-3" key={f.key}><b>{f.label}</b><span className="num float-right">+{score(f.points)}</span><p className="text-muted">{f.detail}</p></div>) : <p>No risk factors found.</p>}
        <h2 className="mb-2 mt-5 text-xl">Checks</h2>
        {detail.checks.map(c => <p className="border-t border-line py-2" key={c.key}><b>{c.label}:</b> {c.detail}</p>)}
        <div className="mt-3 border-t border-line pt-3"><b>Weather at AIS gap:</b> {!weather ? 'Checking…' : weather.status === 'available' ? `${weather.wind_kn} kn wind, ${weather.wave_m} m waves at ${weather.time_utc}. Model estimate; review manually.` : weather.reason}</div>
        <p className="mt-4 text-muted">AIS gaps and encounters are indicators, not proof of an offence.</p>
      </section>
      <section className={surface}>
        <h2 className="mb-3 text-xl">Track and encounters</h2>
        <p>{detail.track.length} AIS positions · {detail.gaps.length} gaps · {detail.encounters.length} encounters</p>
        {detail.encounters.map(e => <p key={e.mmsi} className="mt-3 border-t border-line pt-3">{e.name} · closest {e.closest_m} m · {e.hours} h</p>)}
        <h2 className="mb-2 mt-5 text-xl">SAR candidates</h2>
        {sarError ? (
          <div>
            <p className="text-muted">SAR detections didn't load, so a match can't be ruled out.</p>
            <button type="button" className="btn btn-primary mt-2" onClick={loadSar}>Try again</button>
          </div>
        ) : !detections ? <p>Loading detections…</p> : detections.filter(d => d.matched_mmsi === detail.mmsi).length ? detections.filter(d => d.matched_mmsi === detail.mmsi).map(d => <p key={d.id} className="border-t border-line py-2">{d.source} · {d.scene_id} · {Math.round(d.match_distance_m)} m from AIS. Candidate match, not confirmed identity.</p>) : <p className="text-muted">No candidate SAR detection recorded for this vessel.</p>}
        <div className="mt-5 flex flex-wrap gap-3"><Link className="btn" to={`/map?vessel=${detail.mmsi}`}>View track on map</Link><button className="btn btn-primary" onClick={createReport}>Create report snapshot</button></div>
      </section>
    </div>}
  </Page>
}

export function ReportsPage() {
  const [params] = useSearchParams()
  const [reports, setReports] = useState(null)
  const [officer, setOfficer] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const [error, setError] = useState('')
  const reportId = params.get('id')
  const selected = reportId ? reports?.find(r => String(r.id) === reportId) : reports?.[0]
  const reportNotFound = Boolean(reportId && reports && !selected)
  const refresh = () => reportsApi.list().then(setReports).catch(() => setError('Unable to load reports.'))
  useEffect(() => { refresh() }, [])
  async function sign() {
    setError('')
    try {
      await reportsApi.sign(selected.id, officer, reviewed)
      await refresh()
      setReviewed(false)
    } catch (e) {
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
    <p className="mb-5 text-muted">Evidence snapshots are stored locally. Sign-off records a review without identity verification and does not send a report.</p>
    {error && <p role="alert" className="mb-4 text-risk-red">{error}</p>}
    {!reports && !error && <p>Loading reports…</p>}
    {reports?.length === 0 && <p>No reports yet. Open a vessel and create a report snapshot.</p>}
    {reports && reports.length > 0 && <div className="grid gap-5 lg:grid-cols-[220px_1fr_300px]">
      <nav className={surface}>{reports.map(r => <Link className="block border-b border-line py-2" to={`/reports?id=${r.id}`} key={r.id}>#{r.id} · {vesselName(r.snapshot)}</Link>)}</nav>
      {reportNotFound ? (
        <p role="alert" className={surface}>Report #{reportId} was not found.</p>
      ) : selected ? (
        <>
          <article className={surface}><p className="text-muted">REPORT #{selected.id} · {selected.signed_at ? 'Signed' : 'Awaiting review'}</p><h2 className="my-4 text-2xl">Vessel investigation: {vesselName(selected.snapshot)}</h2>
            <p>MMSI <b className="num">{selected.mmsi}</b> · Risk <b className="num">{score(selected.snapshot.score)}</b> · Last observed {selected.snapshot.last_seen}</p>
            <h3 className="mb-2 mt-6 text-lg">Evidence and source</h3>
            <p className="text-muted">Values below come from the preserved AIS track and risk-engine calculation in this snapshot.</p>
            {selected.snapshot.factors.map(f => <div key={f.key} className="border-b border-line py-3"><b>{f.label}</b> · {f.detail} · +{score(f.points)}</div>)}
            {selected.snapshot.sar_candidates?.map(d => <div key={d.id} className="border-b border-line py-3"><b>SAR candidate:</b> {d.source} · scene {d.scene_id} · {d.observed_at} · {Math.round(d.match_distance_m)} m from AIS. Identity not confirmed.</div>)}
            <details className="mt-4"><summary>View source snapshot ({selected.snapshot.track.length} AIS positions)</summary><pre className="mt-2 max-h-64 overflow-auto text-xs">{JSON.stringify(selected.snapshot, null, 2)}</pre></details>
          </article>
          <aside className={surface}><h2 className="text-xl">Evidence integrity</h2><p className="mt-2">{selected.integrity_ok ? 'Snapshot hash verified' : 'Hash mismatch — sign-off blocked'}</p><p className="mt-2 text-xs text-muted">The hash detects accidental changes; it is stored alongside the evidence and is not a digital signature.</p><p className="num mt-2 break-all text-xs text-muted">SHA-256 {selected.sha256}</p>
            {selected.signed_at ? <p className="mt-5">Signed by {selected.signed_by} at {selected.signed_at}</p> : <div className="mt-5"><label className="block">Officer name<input className="mt-1 w-full rounded border border-line p-2" value={officer} onChange={e => setOfficer(e.target.value)} /></label><label className="my-4 flex gap-2"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />I reviewed the evidence and source snapshot.</label><button className="btn btn-primary w-full" disabled={!selected.integrity_ok || !reviewed || !officer.trim()} onClick={sign}>Record sign-off</button></div>}
          </aside>
        </>
      ) : null}
    </div>}
  </Page>
}
