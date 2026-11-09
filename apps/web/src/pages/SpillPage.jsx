import { useEffect, useState } from 'react'
import { serverDetail, spillApi } from '../lib/api'
import { dateTimeIST } from '../lib/format'

const INITIAL = {
  longitude: '78.35', latitude: '8.75', release_at: '', duration_hours: '24', particle_count: '500', mode: 'real',
}

export default function SpillPage() {
  const [capability, setCapability] = useState(null)
  const [jobs, setJobs] = useState(null)
  const [form, setForm] = useState(INITIAL)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let alive = true
    Promise.allSettled([spillApi.capabilities(), spillApi.jobs()]).then(([capabilityResult, jobsResult]) => {
      if (!alive) return
      if (capabilityResult.status === 'fulfilled') setCapability(capabilityResult.value)
      else setError(serverDetail(capabilityResult.reason) || 'Spill engine capability is unavailable.')
      if (jobsResult.status === 'fulfilled') setJobs(jobsResult.value)
      else setError((current) => current || serverDetail(jobsResult.reason) || 'Spill job history is unavailable.')
    })
    return () => { alive = false }
  }, [])

  async function run(event) {
    event.preventDefault(); setSubmitting(true); setError(''); setMessage('')
    try {
      const created = await spillApi.create({
        longitude: Number(form.longitude), latitude: Number(form.latitude),
        release_at: new Date(form.release_at).toISOString(), duration_hours: Number(form.duration_hours),
        particle_count: Number(form.particle_count), mode: form.mode,
      })
      setMessage(`Scenario job ${created.id} queued.`)
      setJobs(await spillApi.jobs())
    } catch (requestError) { setError(serverDetail(requestError) || 'The scenario could not be queued.') }
    finally { setSubmitting(false) }
  }

  const available = capability?.status === 'available'
  const jobItems = Array.isArray(jobs) ? jobs : jobs?.items ?? []
  const modes = capability?.supported_modes?.length ? capability.supported_modes : ['real']

  return <div className="h-full overflow-y-auto p-6 md:p-10">
    <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div><p className="text-sm font-medium uppercase tracking-wide text-muted">Pollution response planning</p><h1 className="mt-1 text-3xl font-semibold">Spill scenarios</h1><p className="mt-2 max-w-3xl text-[15px] text-muted">Submit a bounded trajectory job using configured wind and current forcing, then inspect its status, time steps and potentially affected areas.</p></div>
      {capability && <span className={`pill ${available ? 'pill-green' : 'pill-amber'}`} role="status">{available ? 'Scenario engine ready' : 'Scenario engine unavailable'}</span>}
    </header>

    {error && <p role="alert" className="mb-5 rounded-card border border-risk-red/30 bg-risk-red/5 p-4">{error}</p>}
    {message && <p role="status" className="mb-5 rounded-card border border-line bg-mint p-4">{message}</p>}

    {!capability && !error && <p className="mb-5 text-muted">Checking scenario capability…</p>}
    {capability && <section className="card mb-5 p-5" aria-labelledby="spill-capability-heading">
      <div className="flex flex-wrap items-center gap-3"><h2 id="spill-capability-heading" className="text-xl">Engine and forcing</h2><span className={`pill ${available ? 'pill-green' : 'pill-amber'}`}>{capability.status}</span></div>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm"><dt className="text-muted">Engine</dt><dd>{capability.engine ?? 'Not reported'}{capability.engine_version ? ` ${capability.engine_version}` : ''}</dd><dt className="text-muted">Wind</dt><dd>{String(capability.forcing?.wind ?? 'unknown').replaceAll('_', ' ')}</dd><dt className="text-muted">Current</dt><dd>{String(capability.forcing?.current ?? 'unknown').replaceAll('_', ' ')}</dd></dl>
      {capability.reason && <p className="mt-3 text-sm">{capability.reason}</p>}
      {capability.limitations && <p className="mt-2 text-sm text-muted">{capability.limitations}</p>}
    </section>}

    <div className="grid items-start gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
      <form className="card space-y-4 p-5" onSubmit={run}>
        <h2 className="text-xl">Scenario inputs</h2>
        <p className="text-sm text-muted">A missing current field never becomes zero flow. Synthetic forcing is accepted only when the configured engine explicitly supports that mode.</p>
        <div className="grid grid-cols-2 gap-3"><label className="grid gap-1 text-sm font-medium">Latitude<input className="input" type="number" min="-90" max="90" step="any" value={form.latitude} onChange={(event) => setForm({ ...form, latitude: event.target.value })} required /></label><label className="grid gap-1 text-sm font-medium">Longitude<input className="input" type="number" min="-180" max="180" step="any" value={form.longitude} onChange={(event) => setForm({ ...form, longitude: event.target.value })} required /></label></div>
        <label className="grid gap-1 text-sm font-medium">Release time (UTC)<input className="input" type="datetime-local" value={form.release_at} onChange={(event) => setForm({ ...form, release_at: event.target.value })} required /></label>
        <label className="grid gap-1 text-sm font-medium">Duration (hours)<input className="input" type="number" min="1" max="72" value={form.duration_hours} onChange={(event) => setForm({ ...form, duration_hours: event.target.value })} required /></label>
        <label className="grid gap-1 text-sm font-medium">Particles<input className="input" type="number" min="100" max="5000" step="100" value={form.particle_count} onChange={(event) => setForm({ ...form, particle_count: event.target.value })} required /></label>
        <label className="grid gap-1 text-sm font-medium">Forcing mode<select className="input" value={form.mode} onChange={(event) => setForm({ ...form, mode: event.target.value })}>{modes.map((mode) => <option key={mode} value={mode}>{String(mode).replaceAll('_', ' ')}</option>)}</select></label>
        <button className="btn btn-primary w-full" disabled={!available || submitting} type="submit">{submitting ? 'Queueing…' : 'Run scenario'}</button>
        {!available && <p className="text-sm text-muted">Scenario submission is disabled until PyGNOME and compatible wind/current forcing are available in the worker.</p>}
      </form>

      <section className="card p-5" aria-labelledby="spill-jobs-heading">
        <h2 id="spill-jobs-heading" className="text-xl">Scenario jobs</h2>
        {!jobs && !error && <p className="mt-3 text-muted">Loading scenario jobs…</p>}
        {jobs && jobItems.length === 0 && <p className="mt-3 text-muted">No spill scenarios have been submitted.</p>}
        {jobItems.map((job) => <article className="mt-3 border-t border-line pt-3" key={job.id}>
          <div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">Scenario {job.id}</h3><span className={`pill ${job.state === 'complete' ? 'pill-green' : job.state === 'failed' ? 'pill-red' : 'pill-amber'}`}>{String(job.state ?? job.status ?? 'unknown').replaceAll('_', ' ')}</span></div>
          <p className="mt-1 text-sm text-muted">{job.release_at ? `Release ${dateTimeIST(job.release_at)}` : 'Release time not reported'} · {job.duration_hours ?? '?'} h · {job.particle_count ?? '?'} particles</p>
          {job.progress != null && <p className="mt-2 text-sm">Progress {job.progress}%</p>}
          {job.outputs?.time_steps?.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{job.outputs.time_steps.map((step) => <span className="pill pill-navy" key={step.hour}>{step.hour} h</span>)}</div>}
          {job.outputs?.affected_areas?.length > 0 && <p className="mt-2 text-sm">Potentially affected areas: {job.outputs.affected_areas.map((area) => area.name ?? area).join(', ')}</p>}
          {job.error && <p className="mt-2 text-sm text-risk-red">{job.error}</p>}
        </article>)}
      </section>
    </div>
  </div>
}
