import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { boundariesApi, casesApi, sarApi, serverDetail } from '../lib/api'
import { dateTimeIST } from '../lib/format'

const INITIAL = { observed_at: '', latitude: '', longitude: '', source: '', scene_id: '', confidence: '' }

const associationLabel = (detection) => String(detection.association_state ?? (detection.matched_mmsi ? 'matched' : 'unmatched')).replaceAll('_', ' ')

export default function DetectionsPage() {
  const [detections, setDetections] = useState(null)
  const [boundaries, setBoundaries] = useState(null)
  const [errors, setErrors] = useState({})
  const [form, setForm] = useState(INITIAL)
  const [saving, setSaving] = useState(false)
  const [caseBusy, setCaseBusy] = useState(null)
  const [caseResult, setCaseResult] = useState(null)

  const load = () => Promise.allSettled([sarApi.detections(), boundariesApi.list()]).then(([sar, zones]) => {
    if (sar.status === 'fulfilled') setDetections(sar.value)
    else setErrors((current) => ({ ...current, detections: serverDetail(sar.reason) || 'SAR detections are unavailable.' }))
    if (zones.status === 'fulfilled') setBoundaries(zones.value)
    else setErrors((current) => ({ ...current, boundaries: serverDetail(zones.reason) || 'Boundary references are unavailable.' }))
  })

  useEffect(() => { load() }, [])

  async function record(event) {
    event.preventDefault(); setSaving(true); setErrors((current) => ({ ...current, create: '' }))
    try {
      const created = await sarApi.create({
        observed_at: new Date(form.observed_at).toISOString(), latitude: Number(form.latitude), longitude: Number(form.longitude),
        source: form.source.trim(), scene_id: form.scene_id.trim(), ...(form.confidence !== '' ? { confidence: Number(form.confidence) } : {}),
      })
      setDetections((current) => [created, ...(Array.isArray(current) ? current : [])]); setForm(INITIAL)
    } catch (error) { setErrors((current) => ({ ...current, create: serverDetail(error) || 'The observation could not be recorded.' })) }
    finally { setSaving(false) }
  }

  async function openCase(detection) {
    setCaseBusy(detection.id); setErrors((current) => ({ ...current, case: '' })); setCaseResult(null)
    try {
      const created = await casesApi.createFromSar(detection.id, `Unidentified SAR observation · ${detection.scene_id}`)
      setCaseResult(created)
    } catch (error) { setErrors((current) => ({ ...current, case: serverDetail(error) || 'An investigation case could not be opened.' })) }
    finally { setCaseBusy(null) }
  }

  const items = boundaries?.items ?? []
  return <div className="h-full overflow-y-auto p-6 md:p-10">
    <header className="mb-6"><p className="text-sm font-medium uppercase tracking-wide text-muted">Corroboration</p><h1 className="mt-1 text-3xl font-semibold">SAR observations and boundaries</h1><p className="mt-2 max-w-3xl text-[15px] text-muted">Record georeferenced observations, inspect candidate AIS associations and verify the exact source behind protected-area context. An association is not confirmed identity.</p></header>
    <div className="grid items-start gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
      <form className="card space-y-3 p-5" onSubmit={record}>
        <h2 className="text-xl">Record observation</h2>
        <p className="text-sm text-muted">Use source metadata supplied with the scene. MMSI is never required.</p>
        <label className="grid gap-1 text-sm font-medium">Observed at (UTC)<input className="input" type="datetime-local" value={form.observed_at} onChange={(e) => setForm({ ...form, observed_at: e.target.value })} required /></label>
        <div className="grid grid-cols-2 gap-3"><label className="grid gap-1 text-sm font-medium">Latitude<input className="input" type="number" min="-90" max="90" step="any" value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} required /></label><label className="grid gap-1 text-sm font-medium">Longitude<input className="input" type="number" min="-180" max="180" step="any" value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} required /></label></div>
        <label className="grid gap-1 text-sm font-medium">Source<input className="input" maxLength="200" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} required /></label>
        <label className="grid gap-1 text-sm font-medium">Scene ID<input className="input" maxLength="300" value={form.scene_id} onChange={(e) => setForm({ ...form, scene_id: e.target.value })} required /></label>
        <label className="grid gap-1 text-sm font-medium">Detector confidence (optional)<input className="input" type="number" min="0" max="1" step="0.01" value={form.confidence} onChange={(e) => setForm({ ...form, confidence: e.target.value })} /></label>
        {errors.create && <p role="alert" className="text-risk-red">{errors.create}</p>}
        <button className="btn btn-primary w-full" disabled={saving} type="submit">{saving ? 'Recording…' : 'Record observation'}</button>
      </form>

      <section className="card p-5" aria-labelledby="sar-list-heading">
        <h2 id="sar-list-heading" className="text-xl">Observation register</h2>
        {caseResult && <p role="status" className="mt-3 rounded border border-line bg-mint p-3">Case opened. <Link className="underline" to={`/cases?id=${caseResult.id}`}>Open case {caseResult.id}</Link></p>}
        {errors.case && <p role="alert" className="mt-3 text-risk-red">{errors.case}</p>}
        {errors.detections && <p role="alert" className="mt-3 text-risk-red">{errors.detections}</p>}
        {!detections && !errors.detections && <p className="mt-3 text-muted">Loading observations…</p>}
        {detections?.length === 0 && <p className="mt-3 text-muted">No SAR observations have been recorded.</p>}
        {detections?.map((item) => <article className="mt-3 border-t border-line pt-3" key={item.id ?? `${item.scene_id}-${item.observed_at}`}>
          <div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{item.scene_id}</h3><span className={`pill ${item.association_state === 'matched' ? 'pill-green' : item.association_state === 'ambiguous' ? 'pill-amber' : 'pill-navy'}`}>{associationLabel(item)}</span></div>
          <p className="mt-1 text-sm text-muted">{item.source} · {item.observed_at ? dateTimeIST(item.observed_at) : 'Time not reported'} · {item.latitude}, {item.longitude}</p>
          {item.matched_mmsi && <p className="mt-1 text-sm">Candidate MMSI {item.matched_mmsi}{item.match_distance_m != null ? ` · ${Math.round(item.match_distance_m)} m` : ''}</p>}
          {item.candidates?.length > 1 && <p className="mt-1 text-sm text-muted">{item.candidates.length} plausible AIS candidates; identity remains ambiguous.</p>}
          <p className="mt-1 text-sm text-muted">{item.interpretation ?? 'Coverage and identity must be reviewed.'}</p>
          {['ambiguous', 'unmatched', 'insufficient_coverage'].includes(item.association_state) && <button className="btn mt-2" type="button" disabled={caseBusy === item.id} onClick={() => openCase(item)}>{caseBusy === item.id ? 'Opening case…' : 'Open unidentified-object case'}</button>}
        </article>)}
      </section>
    </div>

    <section className="card mt-5 p-5" aria-labelledby="boundary-heading">
      <h2 id="boundary-heading" className="text-xl">Boundary and rule references</h2>
      <p className="mt-1 text-sm text-muted">Legal applicability must be verified against the cited publisher and effective version.</p>
      {errors.boundaries && <p role="alert" className="mt-3 text-risk-red">{errors.boundaries}</p>}
      {!boundaries && !errors.boundaries && <p className="mt-3 text-muted">Loading boundary references…</p>}
      {items.length === 0 && boundaries && <p className="mt-3 text-muted">No verified boundary references are available.</p>}
      <div className="mt-3 grid gap-4 lg:grid-cols-2">{items.map((item) => <article className="rounded border border-line p-4" key={item.id}>
        <div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{item.name}</h3><span className="pill pill-navy">{item.restriction?.verification_status ?? 'verification unknown'}</span></div>
        <p className="mt-1 text-sm text-muted">{item.designation ?? 'Designation not reported'} · {item.publisher ?? 'Publisher not reported'}{item.version ? ` · ${item.version}` : ''}</p>
        <p className="mt-3 text-sm">{item.restriction?.description ?? 'Restriction description is unknown.'}</p>
        <p className="mt-2 text-sm text-muted">Citation: {item.citation ?? 'Not reported'} · Permitted use: {item.permitted_use ?? 'Unknown'}</p>
      </article>)}</div>
      {boundaries?.limitations && <p className="mt-4 text-sm text-muted">{boundaries.limitations}</p>}
    </section>
  </div>
}
