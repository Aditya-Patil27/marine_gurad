import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CircleAlert, CircleCheck, CircleHelp, CircleMinus, X } from 'lucide-react'
import { isNotFound, reportsApi } from '../../lib/api'
import { formatEnvironmentalReading } from '../../lib/environment'
import { CLEARS, dateTimeIST, levelStyle, score, sourceLabel, vesselName, vesselType, withDisplayNames } from '../../lib/format'

const CHECK_ICON = {
  ruled_out: { Icon: CircleCheck, className: 'text-risk-green', label: 'Ruled out' },
  not_ruled_out: { Icon: CircleAlert, className: 'text-risk-amber', label: 'Not ruled out' },
  not_checked: { Icon: CircleMinus, className: 'text-faint', label: 'Not checked' },
}
// A status this build doesn't know: show the check with its own text rather than guess what it means
const UNKNOWN_CHECK = { Icon: CircleHelp, className: 'text-faint', label: 'Unknown result' }

function Factor({ factor, scale, names }) {
  return (
    <div className="grid grid-cols-[1fr_96px_44px] items-center gap-2.5 py-[7px]">
      <div className="text-[13.5px]">
        {withDisplayNames(factor.label, names)}
        <small className="block font-mono text-xs text-faint">{withDisplayNames(factor.detail, names)}</small>
      </div>
      <div className="h-2 overflow-hidden rounded bg-peri-soft" aria-hidden="true">
        <i className="block h-full rounded bg-risk-red" style={{ width: `${Math.round((factor.points / scale) * 100)}%` }} />
      </div>
      <span className="num text-right text-[13px] font-medium">+{score(factor.points)}</span>
    </div>
  )
}

function ClearIf({ clearIf }) {
  const how = clearIf.without.map((k) => CLEARS[k] ?? k)
  const joined = how.length > 1 ? `${how.slice(0, -1).join(', ')} and ${how.at(-1)}` : how[0]
  return (
    <div className="border-t border-line bg-canvas px-5 py-3">
      <h3 className="mb-1.5 text-sm">What would clear it</h3>
      <p className="text-[13.5px] text-muted">
        Score drops to <b className="num font-medium text-ink">{score(clearIf.score)}</b>, below the alert line, if {joined}.
      </p>
    </div>
  )
}

export default function VesselPanel({ detail, mmsi, error, loading, onClose, onRetry, names, environmental }) {
  const [drafting, setDrafting] = useState(false)
  const [draftError, setDraftError] = useState('')
  const navigate = useNavigate()

  async function handleDraftReport() {
    if (drafting) return
    setDrafting(true)
    setDraftError('')
    try {
      const r = await reportsApi.create(Number(detail.mmsi))
      navigate(`/reports?id=${r.id}`)
    } catch {
      setDraftError('Could not create an evidence snapshot. Check the API and database migration.')
    } finally {
      setDrafting(false)
    }
  }

  if (!detail && error && !loading) {
    // Only a 404 means the vessel is missing; anything else is the connection, and worth another try
    const missing = isNotFound(error)
    return (
      <aside className="card absolute right-5 top-[76px] z-10 w-[400px] p-5" aria-label="Vessel details">
        <p role="alert" className="text-muted">
          {missing ? `No positions for MMSI ${mmsi} in the last 24 h.` : "Can't reach the API, so this vessel's details didn't load."}
        </p>
        <div className="mt-4 flex gap-2.5">
          {!missing && <button type="button" className="btn btn-primary" onClick={onRetry}>Try again</button>}
          <button type="button" className="btn" onClick={onClose}>Close</button>
        </div>
      </aside>
    )
  }
  if (!detail) {
    return (
      <aside className="card absolute right-5 top-[76px] z-10 w-[400px] p-5 text-muted" aria-label="Vessel details" aria-busy="true">
        Loading vessel…
      </aside>
    )
  }

  const level = levelStyle(detail.level)
  const scale = Math.max(...Object.values(detail.max_points))
  const meta = [vesselType(detail.vessel_type), detail.length && `${detail.length} m`].filter(Boolean).join(' · ')
  const envReading = formatEnvironmentalReading(environmental)

  return (
    <aside className="card absolute right-5 top-[76px] z-10 flex max-h-[calc(100%-96px)] w-[400px] flex-col overflow-hidden" aria-labelledby="vessel-title">
      <div className="overflow-y-auto">
        <div className="relative px-5 pb-3.5 pt-[18px]">
          <button type="button" onClick={onClose} className="absolute right-3 top-3 rounded-md p-1.5 text-faint hover:bg-canvas hover:text-navy" aria-label="Close vessel details">
            <X size={18} />
          </button>
          <div className="flex flex-wrap gap-1.5 pr-8">
            <span className={`pill ${level.pill}`}>{level.label}</span>
            {detail.dark && <span className="pill pill-red">AIS off</span>}
            {detail.zone && (
              <span className="pill pill-zone">
                {detail.zone.relation === 'inside' ? 'Inside ' : `${detail.zone.distance_km} km from `}
                {detail.zone.name.replace(' Marine National Park', ' park')}
              </span>
            )}
          </div>
          <h2 id="vessel-title" className="mb-0.5 mt-2 text-2xl">{vesselName(detail)}</h2>
          <div className="text-muted">
            {meta} · <span className="num text-[12.5px]">MMSI {detail.mmsi}</span>
          </div>
          <div className="text-[13px] text-faint">Last position {dateTimeIST(detail.last_seen)}</div>
          <div className="text-[13px] text-faint">AIS data: {sourceLabel(detail)}</div>
          <div className="text-[13px] text-faint">
            {envReading ? (
              <Link to={`/map?vessel=${detail.mmsi}#environmental-context`} className="text-navy hover:underline">
                Regional ocean context ({envReading.dateIST})
              </Link>
            ) : (
              <Link to={`/map?vessel=${detail.mmsi}#environmental-context`} className="text-muted hover:underline">
                Regional ocean context (Environmental data not available)
              </Link>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 border-t border-line px-5 pb-1.5 pt-3.5">
          <span className={`font-head text-[34px] font-semibold leading-none ${level.color}`}>{score(detail.score)}</span>
          <div>
            <b className="font-medium">{level.label}</b>
            <div className="text-[12.5px] text-faint">Alert line {score(detail.threshold)}</div>
          </div>
        </div>

        <div className="px-5 pb-3 pt-1">
          {detail.factors.length ? (
            <>
              <div className="mb-0.5 text-[12.5px] text-faint">Why it was flagged. The score is the sum of these.</div>
              {detail.factors.map((f) => (
                <Factor key={f.key} factor={f} scale={scale} names={names} />
              ))}
            </>
          ) : (
            <p className="py-2 text-[13.5px] text-muted">Nothing unusual in the last 24 hours.</p>
          )}
        </div>

        {detail.checks.length > 0 && (
          <div className="border-t border-line px-5 py-3">
            <h3 className="mb-1.5 text-sm">Checks</h3>
            <ul>
              {detail.checks.map((c) => {
                const { Icon, className, label } = CHECK_ICON[c.status] ?? UNKNOWN_CHECK
                return (
                  <li key={c.key} className="flex gap-2 py-[3px] text-[13.5px] text-muted">
                    <Icon size={16} className={`mt-0.5 flex-none ${className}`} aria-label={label} />
                    <span>
                      <span className="text-ink">{c.label}</span>: {c.detail}
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {detail.clear_if && <ClearIf clearIf={detail.clear_if} />}
      </div>

      {draftError && (
        <p role="alert" className="border-t border-line px-5 py-2 text-sm text-risk-red">
          {draftError}
        </p>
      )}

      <div className="flex gap-2.5 border-t border-line px-5 pb-[18px] pt-3.5">
        <Link to={`/vessels/${detail.mmsi}`} className="btn btn-primary flex-1">Open evidence</Link>
        <button type="button" className="btn" disabled={drafting} onClick={handleDraftReport}>
          Draft report
        </button>
      </div>
    </aside>
  )
}
