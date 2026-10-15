import { useCallback, useMemo, useRef, useState } from 'react'
import { useOutletContext, useSearchParams } from 'react-router-dom'
import { CircleAlert, Search } from 'lucide-react'
import OceanMap from '../features/map/OceanMap'
import AttentionCard from '../features/map/AttentionCard'
import VesselPanel from '../features/map/VesselPanel'
import TrackTimeline from '../features/map/TrackTimeline'
import StateGlyph, { STATE_STYLE } from '../components/StateGlyph'
import { mapApi, vesselsApi } from '../lib/api'
import usePolling from '../lib/usePolling'
import { timeIST, vesselName } from '../lib/format'

/** The address bar is typed by people: only a whole number of up to nine digits is an MMSI. */
const mmsiFrom = (value) => (/^[1-9]\d{0,8}$/.test(value ?? '') ? Number(value) : null)

function VesselSearch({ vessels, onSelect }) {
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const q = query.trim().toLowerCase()
  const matches = q
    ? vessels.filter((v) => vesselName(v).toLowerCase().includes(q) || String(v.mmsi).includes(q)).slice(0, 6)
    : []
  // The fleet refreshes under the list, so the highlighted row can outlive its vessel
  const current = matches[Math.min(active, matches.length - 1)]

  const type = (text) => {
    setQuery(text)
    setActive(0)
  }
  const choose = (mmsi) => {
    onSelect(mmsi)
    type('')
  }
  const step = (by) => setActive((matches.indexOf(current) + by + matches.length) % matches.length)

  const onKeyDown = (e) => {
    if (e.key === 'Escape' && query) type('')
    if (!current) return
    if (e.key === 'Enter') choose(current.mmsi)
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault() // or the caret jumps to the end of the text
      step(e.key === 'ArrowDown' ? 1 : -1)
    }
  }

  return (
    <div className="relative w-[340px]">
      <label className="card flex h-11 items-center gap-2.5 px-3.5 text-faint focus-within:ring-2 focus-within:ring-navy-2">
        <Search size={18} aria-hidden="true" />
        <span className="sr-only">Search vessels</span>
        <input
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={Boolean(current)}
          aria-controls="vessel-results"
          aria-activedescendant={current ? `vessel-result-${current.mmsi}` : undefined}
          value={query}
          onChange={(e) => type(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Search vessel or MMSI"
          className="h-full flex-1 bg-transparent text-[14px] text-ink outline-none placeholder:text-faint"
        />
      </label>
      {current && (
        <ul id="vessel-results" role="listbox" aria-label="Vessels found" className="card absolute left-0 right-0 top-12 overflow-hidden py-1">
          {matches.map((v, i) => (
            // Focus stays in the box; the keyboard reaches a row with the arrow keys
            <li
              key={v.mmsi}
              id={`vessel-result-${v.mmsi}`}
              role="option"
              aria-selected={v === current}
              onMouseEnter={() => setActive(i)}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => choose(v.mmsi)}
              className={`flex cursor-pointer items-center gap-2.5 px-3.5 py-2 ${v === current ? 'bg-canvas' : ''}`}
            >
              <StateGlyph state={v.state} />
              <span className="flex-1">{vesselName(v)}</span>
              <span className="num text-xs text-faint">{v.mmsi}</span>
            </li>
          ))}
        </ul>
      )}
      {q && !current && (
        <p role="status" className="card absolute left-0 right-0 top-12 px-3.5 py-3 text-muted">
          No vessel matches “{query}”
        </p>
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
  const selected = mmsiFrom(params.get('vessel'))
  const openedOn = useRef(selected).current
  const [showZones, setShowZones] = useState(true)
  const [showAll, setShowAll] = useState(true)

  const zones = usePolling(() => mapApi.zones(), 10 * 60e3)
  const detail = usePolling(selected ? () => vesselsApi.get(selected) : null, 30e3, [selected])

  const select = useCallback(
    (mmsi) => {
      // Picking the vessel that is already open must not stack a second history entry
      if ((mmsi ?? null) !== selected) setParams(mmsi ? { vessel: String(mmsi) } : {}, { replace: false })
    },
    [setParams, selected],
  )

  const vessels = fleet.data?.vessels ?? []
  const attention = useMemo(() => vessels.filter((v) => v.level !== 'low'), [vessels])
  const current = detail.data?.mmsi === selected ? detail.data : null
  const updated = fleet.updatedAt && timeIST(fleet.updatedAt)

  return (
    <div className="absolute inset-0 overflow-hidden">
      <OceanMap vessels={vessels} zones={zones.data} detail={current} showZones={showZones} showAll={showAll} onSelect={select} openedOn={openedOn} />

      {/* One layer above the cards: the search results open over the attention list, not behind it */}
      <div className="absolute left-5 right-5 top-[18px] z-20 flex items-center gap-2.5">
        <VesselSearch vessels={vessels} onSelect={select} />
        {zones.error && !zones.data ? (
          // An empty map must not read as "no protected area here"
          <button type="button" onClick={zones.refresh} className="chip hover:border-peri">
            <CircleAlert size={14} className="text-risk-amber" aria-hidden="true" />
            Protected areas didn't load. Try again
          </button>
        ) : (
          <Toggle on={showZones} onChange={setShowZones}>
            <span className="h-[11px] w-[11px] rounded-[3px] border-[1.8px] border-zone" aria-hidden="true" />
            Protected areas
          </Toggle>
        )}
        <Toggle on={showAll} onChange={setShowAll}>
          <StateGlyph state="tracked" size={11} />
          All vessels
        </Toggle>
        <span className="card ml-auto flex h-9 items-center gap-2 px-3.5 text-[13px] text-muted" role="status">
          <span className={`h-2 w-2 rounded-full ${fleet.error ? 'bg-risk-red' : 'bg-risk-green'}`} aria-hidden="true" />
          {fleet.error
            ? `Can't reach the API${updated ? ` · last update ${updated}` : ''}`
            : updated
              ? `${vessels.length} ${vessels.length === 1 ? 'vessel' : 'vessels'} · updated ${updated}`
              : 'Connecting…'}
        </span>
      </div>

      <AttentionCard
        vessels={attention}
        allVessels={vessels}
        selectedMmsi={selected}
        onSelect={select}
        loading={fleet.loading}
        error={fleet.error}
        updatedAt={fleet.updatedAt}
        onRetry={fleet.refresh}
      />

      {selected && (
        <VesselPanel
          detail={current}
          mmsi={selected}
          error={detail.error}
          loading={detail.loading}
          onClose={() => select(null)}
          onRetry={detail.refresh}
          names={vessels}
        />
      )}

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
