import { useEffect, useState } from 'react'
import { oceanApi, serverDetail } from '../lib/api'
import { dateTimeIST } from '../lib/format'

const valuesFrom = (data) => data?.values ?? data?.observations ?? []
const cellsFrom = (data) => data?.ranked_cells ?? data?.cells ?? data?.plan?.cells ?? []

export default function OceanPage() {
  const [observations, setObservations] = useState(null)
  const [baseline, setBaseline] = useState(null)
  const [errors, setErrors] = useState({})
  const [budget, setBudget] = useState(8)
  const [plan, setPlan] = useState(null)
  const [planning, setPlanning] = useState(false)

  useEffect(() => {
    let alive = true
    Promise.allSettled([oceanApi.observations(), oceanApi.baseline()]).then(([observed, evaluated]) => {
      if (!alive) return
      if (observed.status === 'fulfilled') setObservations(observed.value)
      else setErrors((current) => ({ ...current, observations: serverDetail(observed.reason) || 'Historical ocean observations are unavailable.' }))
      if (evaluated.status === 'fulfilled') setBaseline(evaluated.value)
      else setErrors((current) => ({ ...current, baseline: serverDetail(evaluated.reason) || 'The prioritisation baseline is unavailable.' }))
    })
    return () => { alive = false }
  }, [])

  async function createPlan(event) {
    event.preventDefault()
    setPlanning(true); setErrors((current) => ({ ...current, plan: '' })); setPlan(null)
    try { setPlan(await oceanApi.scanPlan(Number(budget), 0.2)) }
    catch (error) { setErrors((current) => ({ ...current, plan: serverDetail(error) || 'A scan plan could not be prepared.' })) }
    finally { setPlanning(false) }
  }

  const observationsList = valuesFrom(observations)
  const cells = cellsFrom(plan)
  const factors = baseline?.factors ?? baseline?.features ?? []

  return <div className="h-full overflow-y-auto p-6 md:p-10">
    <header className="mb-6 flex flex-wrap items-end gap-4">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium uppercase tracking-wide text-muted">Ocean intelligence</p>
        <h1 className="mt-1 text-3xl font-semibold">Conditions and scan planning</h1>
        <p className="mt-2 max-w-3xl text-[15px] text-muted">Review dated regional observations and use the prepared activity baseline to allocate a bounded scan budget. Ranking is prioritisation support, not a finding of illegal activity.</p>
      </div>
    </header>

    <div className="grid items-start gap-5 xl:grid-cols-2">
      <section className="card p-5" aria-labelledby="ocean-observations-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 id="ocean-observations-heading" className="text-xl">Regional observations</h2><p className="mt-1 text-sm text-muted">Historical prepared subset; dates and units are preserved from the source.</p></div>
          {observations?.status && <span className={`pill ${observations.status === 'available' ? 'pill-green' : 'pill-amber'}`}>{String(observations.status).replaceAll('_', ' ')}</span>}
        </div>
        {errors.observations && <p role="alert" className="mt-4 text-risk-red">{errors.observations}</p>}
        {!observations && !errors.observations && <p className="mt-4 text-muted">Loading ocean observations…</p>}
        {observations && <>
          <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="text-muted">Source</dt><dd>{observations.source ?? 'Not reported'}</dd>
            <dt className="text-muted">Dataset</dt><dd className="break-all">{observations.dataset ?? observations.product ?? 'Not reported'}</dd>
            <dt className="text-muted">Variable</dt><dd>{observations.variable ?? 'Sea surface temperature'}</dd>
            <dt className="text-muted">Unit</dt><dd>{observations.unit ?? 'Not reported'}</dd>
            <dt className="text-muted">Mode</dt><dd>{observations.mode ?? observations.data_mode ?? 'historical'}</dd>
          </dl>
          {observationsList.length === 0 ? <p className="mt-4 text-muted">No observation values were returned.</p> : <div className="mt-4 max-h-64 overflow-auto border-y border-line">
            {observationsList.slice(0, 24).map((item, index) => <div className="grid grid-cols-2 gap-3 border-b border-line py-2 text-sm last:border-b-0" key={item.observed_at ?? item.time ?? index}>
              <span>{item.observed_at ? dateTimeIST(item.observed_at) : item.time ?? item.date ?? 'Date not reported'}</span>
              <span className="num text-right">{item.value ?? item.temperature_c ?? 'Unknown'} {item.unit ?? observations.unit ?? ''}</span>
            </div>)}
          </div>}
          {observations.limitations && <p className="mt-4 text-sm text-muted">{observations.limitations}</p>}
        </>}
      </section>

      <section className="card p-5" aria-labelledby="baseline-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 id="baseline-heading" className="text-xl">Prioritisation baseline</h2><p className="mt-1 text-sm text-muted">Prepared descriptive or persistence baseline, never a crime classifier.</p></div>
          {baseline?.status && <span className={`pill ${baseline.status === 'available' ? 'pill-green' : 'pill-amber'}`}>{String(baseline.status).replaceAll('_', ' ')}</span>}
        </div>
        {errors.baseline && <p role="alert" className="mt-4 text-risk-red">{errors.baseline}</p>}
        {!baseline && !errors.baseline && <p className="mt-4 text-muted">Loading baseline status…</p>}
        {baseline && <>
          <p className="mt-4 text-sm">Evaluation: <b>{String(baseline.evaluation?.status ?? 'not reported').replaceAll('_', ' ')}</b></p>
          {baseline.availability && <p className="mt-2 text-sm text-muted">{typeof baseline.availability === 'string' ? baseline.availability : baseline.availability.detail ?? JSON.stringify(baseline.availability)}</p>}
          {factors.length > 0 && <ul className="mt-3 list-inside list-disc text-sm text-muted">{factors.map((factor, index) => <li key={factor.key ?? index}>{factor.label ?? factor.name ?? String(factor)}</li>)}</ul>}
          {baseline.limitations && <p className="mt-4 text-sm text-muted">{baseline.limitations}</p>}
        </>}
      </section>
    </div>

    <section className="card mt-5 p-5" aria-labelledby="scan-plan-heading">
      <div className="grid items-end gap-4 md:grid-cols-[minmax(0,1fr)_180px_auto]">
        <div><h2 id="scan-plan-heading" className="text-xl">Scan plan</h2><p className="mt-1 text-sm text-muted">Allocate 80% to ranked cells and reserve 20% for broader coverage. This does not task a satellite or acquire imagery.</p></div>
        <form className="contents" onSubmit={createPlan}>
          <label className="grid gap-1 text-sm font-medium">Cell budget<input className="input" type="number" min="1" max="100" value={budget} onChange={(event) => setBudget(event.target.value)} required /></label>
          <button className="btn btn-primary" disabled={planning || !baseline} type="submit">{planning ? 'Preparing…' : 'Prepare plan'}</button>
        </form>
      </div>
      {errors.plan && <p role="alert" className="mt-4 text-risk-red">{errors.plan}</p>}
      {plan && <>
        <p role="status" className="mt-4 text-sm">{plan.summary ?? `${cells.length} cells selected.`}</p>
        {cells.length === 0 ? <p className="mt-3 text-muted">No ranked cells were returned.</p> : <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-line text-muted"><th className="py-2">Rank</th><th>Cell</th><th>Priority</th><th>Basis</th></tr></thead><tbody>{cells.map((cell, index) => <tr className="border-b border-line" key={cell.id ?? cell.cell_id ?? index}><td className="py-2 num">{cell.rank ?? index + 1}</td><td>{cell.name ?? cell.cell_id ?? cell.id ?? 'Unnamed cell'}</td><td className="num">{cell.score ?? cell.priority ?? 'Not reported'}</td><td>{cell.reserved ? 'Reserved coverage' : cell.reason ?? 'Ranked activity proxy'}</td></tr>)}</tbody></table></div>}
        {plan.limitations && <p className="mt-4 text-sm text-muted">{plan.limitations}</p>}
      </>}
    </section>
  </div>
}
