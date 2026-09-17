import { useCallback, useMemo, useRef, useState } from 'react'
import { useOutletContext, useSearchParams } from 'react-router-dom'
import { Search } from 'lucide-react'
import OceanMap from '../features/map/OceanMap'
import AttentionCard from '../features/map/AttentionCard'
import VesselPanel from '../features/map/VesselPanel'
import TrackTimeline from '../features/map/TrackTimeline'
import StateGlyph, { STATE_STYLE } from '../components/StateGlyph'
import { mapApi, vesselsApi } from '../lib/api'
import usePolling from '../lib/usePolling'
import { vesselName } from '../lib/format'

function VesselSearch({ vessels, onSelect }) {
  const [query, setQuery] = useState('')
  const q = query.trim().toLowerCase()
  const matches = q
    ? vessels.filter((v) => vesselName(v).toLowerCase().includes(q) || String(v.mmsi).includes(q)).slice(0, 6)
    : []

  const choose = (mmsi) => {
    onSelect(mmsi)
    setQuery('')
  }

  return (
    <div className="relative w-[340px]">
      <label className="card flex h-11 items-center gap-2.5 px-3.5 text-faint focus-within:ring-2 focus-within:ring-navy-2">
        <Search size={18} aria-hidden="true" />
        <span className="sr-only">Search vessels</span>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && matches[0] && choose(matches[0].mmsi)}
          placeholder="Search vessel or MMSI"
          className="h-full flex-1 bg-transparent text-[14px] text-ink outline-none placeholder:text-faint"
        />
      </label>
      {q && (
        <ul className="card absolute left-0 right-0 top-12 z-20 overflow-hidden py-1">
          {matches.length ? (
            matches.map((v) => (
              <li key={v.mmsi}>
                <button type="button" onClick={() => choose(v.mmsi)} className="flex w-full items-center gap-2.5 px-3.5 py-2 text-left hover:bg-canvas">
                  <StateGlyph state={v.state} />
                  <span className="flex-1">{vesselName(v)}</span>
                  <span className="num text-xs text-faint">{v.mmsi}</span>
                </button>
              </li>
            ))
          ) : (
            <li className="px-3.5 py-2 text-muted">No vessel matches “{query}”</li>
          )}
        </ul>
      )}
    </div>
  )
}

function Toggle({ on, onChange, children }) {
  return (
    <button type="button" aria-pressed={on} onClick={() => onChange(!on)} className={`chip ${on ? 'chip-on' : 'hover:border-peri'}`}>
      {children}
    </button>
  )
}

export default function MapPage() {
  const fleet = useOutletContext()
  const [params, setParams] = useSearchParams()
  const selected = Number(params.get('vessel')) || null
  const openedOn = useRef(selected).current
  const [showZones, setShowZones] = useState(true)
  const [showAll, setShowAll] = useState(true)

  const zones = usePolling(() => mapApi.zones(), 10 * 60e3)
  const detail = usePolling(selected ? () => vesselsApi.get(selected) : null, 30e3, [selected])

  const select = useCallback(
    (mmsi) => setParams(mmsi ? { vessel: String(mmsi) } : {}, { replace: false }),
    [setParams],
  )

  const vessels = fleet.data?.vessels ?? []
  const attention = useMemo(() => vessels.filter((v) => v.level !== 'low'), [vessels])
  const current = detail.data?.mmsi === selected ? detail.data : null

  return (
    <div className="absolute inset-0 overflow-hidden">
      <OceanMap vessels={vessels} zones={zones.data} detail={current} showZones={showZones} showAll={showAll} onSelect={select} openedOn={openedOn} />

      <div className="absolute left-5 right-5 top-[18px] z-10 flex items-center gap-2.5">
        <VesselSearch vessels={vessels} onSelect={select} />
        <Toggle on={showZones} onChange={setShowZones}>
          <span className="h-[11px] w-[11px] rounded-[3px] border-[1.8px] border-zone" aria-hidden="true" />
          Protected areas
        </Toggle>
        <Toggle on={showAll} onChange={setShowAll}>
          <StateGlyph state="tracked" size={11} />
          All vessels
        </Toggle>
        <span className="card ml-auto flex h-9 items-center gap-2 px-3.5 text-[13px] text-muted" role="status">
          <span className={`h-2 w-2 rounded-full ${fleet.error ? 'bg-risk-red' : 'bg-risk-green'}`} aria-hidden="true" />
          {fleet.error
            ? "Can't reach the API"
            : fleet.updatedAt
              ? `${vessels.length} vessels · updated ${fleet.updatedAt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })}`
              : 'Connecting…'}
        </span>
      </div>

      <AttentionCard vessels={attention} allVessels={vessels} selectedMmsi={selected} onSelect={select} loading={fleet.loading} />

      {selected && <VesselPanel detail={current} error={detail.error && !current} onClose={() => select(null)} names={vessels} />}

      {current && <TrackTimeline detail={current} />}

      <div className={`card absolute bottom-[112px] z-10 flex gap-3.5 px-3 py-2 text-[12.5px] text-muted ${selected ? 'right-[440px]' : 'right-5'}`}>
        {Object.entries(STATE_STYLE).map(([state, { label }]) => (
          <span key={state} className="inline-flex items-center gap-1.5">
            <StateGlyph state={state} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
