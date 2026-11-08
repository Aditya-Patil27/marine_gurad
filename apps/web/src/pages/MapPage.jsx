import { useCallback, useMemo, useRef, useState } from 'react'
import { Link, useOutletContext, useSearchParams } from 'react-router-dom'
import { CircleAlert, Search } from 'lucide-react'
import OceanMap from '../features/map/OceanMap'
import AttentionCard from '../features/map/AttentionCard'
import VesselPanel from '../features/map/VesselPanel'
import TrackTimeline from '../features/map/TrackTimeline'
import StateGlyph, { STATE_STYLE } from '../components/StateGlyph'
import { API_URL, environmentApi, gfwApi, mapApi, vesselsApi } from '../lib/api'
import usePolling from '../lib/usePolling'
import useOnline from '../lib/useOnline'
import { formatEnvironmentalReading } from '../lib/environment'
import { sourceLabel, timeIST, vesselName, windowRangeIST } from '../lib/format'
import { useReplayWindow } from '../lib/replayWindow'

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
  const isOnline = useOnline()
  const { window: selectedWindow, bounds, key: windowKey } = useReplayWindow()
  const historical = selectedWindow.mode === 'historical'
  const [params, setParams] = useSearchParams()
  const selected = mmsiFrom(params.get('vessel'))
  const openedOn = useRef(selected).current
  const [showZones, setShowZones] = useState(true)
  const [showAll, setShowAll] = useState(true)
  const [events, setEvents] = useState(null)
  const [eventError, setEventError] = useState('')
  const [eventLoading, setEventLoading] = useState(false)
  const [eventStart, setEventStart] = useState('2024-01-01')
  const [eventEnd, setEventEnd] = useState('2024-02-01')
  const [eventOffset, setEventOffset] = useState(0)
  const [eventId, setEventId] = useState('')

  async function loadEvents(offset = 0) {
    setEventLoading(true); setEventError('')
    try { setEvents(await gfwApi.events(eventStart, eventEnd, offset)); setEventOffset(offset); setEventId('') }
    catch { setEvents(null); setEventError('Historical events unavailable. Check the dates and provider access.') }
    finally { setEventLoading(false) }
  }

  const selectedEvent = events?.features.find((f) => f.properties.event_id === eventId)
  const zones = usePolling(() => mapApi.zones(), 10 * 60e3)
  const detail = usePolling(selected ? () => vesselsApi.get(selected, bounds) : null, 30e3, [selected, windowKey])
  const regionalEnv = usePolling(() => environmentApi.regional(), 10 * 60e3)

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
  const fleetSummary = !updated
    ? 'Connecting…'
    : historical
      ? `${vessels.length} ${vessels.length === 1 ? 'vessel' : 'vessels'} · historical ${windowRangeIST(selectedWindow)}`
      : `${vessels.length} ${vessels.length === 1 ? 'vessel' : 'vessels'} · updated ${updated}`
  const envReading = formatEnvironmentalReading(regionalEnv.data)

  return (
    <div className="absolute inset-0 overflow-hidden">
      <OceanMap vessels={vessels} zones={zones.data} detail={current} showZones={showZones} showAll={showAll} onSelect={select} openedOn={openedOn} historicalEvents={events} />

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
          <span className={`h-2 w-2 rounded-full ${fleet.error ? 'bg-risk-red' : !isOnline || historical ? 'bg-faint' : sourceLabel(fleet.data) === 'Live data' ? 'bg-risk-green' : 'bg-faint'}`} aria-hidden="true" />
          {fleet.error
            ? `Can't reach the API${updated ? ` · last update ${updated}` : ''}`
            : fleetSummary}
        </span>
      </div>

      {!selected && <section className="card absolute right-5 top-20 z-10 w-72 p-3 text-xs" aria-label="Historical fishing events">
        <strong>GFW historical apparent fishing events</strong>
        <p className="my-1 text-muted">Event locations, not live ships or tracks. Not proof of an offence.</p>
        <div className="flex gap-1"><label>From <input type="date" value={eventStart} onChange={e => { setEventStart(e.target.value); setEvents(null) }} className="w-28 border" /></label>
          <label>Until (exclusive) <input type="date" value={eventEnd} onChange={e => { setEventEnd(e.target.value); setEvents(null) }} className="w-28 border" /></label></div>
        <button className="mt-2 underline" disabled={eventLoading} onClick={() => loadEvents(0)}>{eventLoading ? 'Loading…' : 'Load historical events'}</button>
        {events && <div className="mt-1"><p>{events.features.length} shown · {events.total ?? 'unknown'} total · source: Global Fishing Watch</p>
          <button className="mr-3 underline" disabled={eventOffset === 0 || eventLoading} onClick={() => loadEvents(Math.max(0, eventOffset - 50))}>Previous</button>
          <button className="mr-3 underline" disabled={eventLoading || eventOffset + 50 >= (events.total ?? eventOffset + events.features.length)} onClick={() => loadEvents(eventOffset + 50)}>Next</button>
          <button className="underline" onClick={() => setEvents(null)}>Hide</button>
          <label className="mt-2 block">Select an event for evidence
            <select className="w-full border" value={eventId} onChange={e => setEventId(e.target.value)}>
              <option value="">Select event</option>
              {events.features.filter(f => f.properties.event_id).map(f => <option key={f.properties.event_id} value={f.properties.event_id}>{f.properties.vessel_name || f.properties.mmsi || 'Unknown vessel'} · {f.properties.start}</option>)}
            </select>
          </label>
          {selectedEvent && (selectedEvent.properties.mmsi
            ? <Link className="mt-1 block underline" to={`/vessels/${selectedEvent.properties.mmsi}?${new URLSearchParams({
                gfw_event_id: eventId, gfw_start_date: events.requested_start, gfw_end_date: events.requested_end_exclusive,
                gfw_offset: String(events.offset), gfw_limit: String(events.limit) })}`}>Open vessel evidence to attach this event</Link>
            : <p className="mt-1 text-muted">This event has no MMSI, so it can't be attached to a vessel report.</p>)}
          {eventId && <a className="mt-1 block underline" href={`${API_URL}/api/v1/gfw/events/evidence?${new URLSearchParams({ event_id: eventId, start_date: eventStart, end_date: eventEnd, offset: String(eventOffset), limit: '50', include_regional_ocean_context: String(Boolean(regionalEnv.data)) })}`} target="_blank" rel="noreferrer">{regionalEnv.data ? 'Download event evidence and historical SST' : 'Download event evidence (SST unavailable)'}</a>}
        </div>}
        {eventError && <p role="alert" className="text-risk-red">{eventError}</p>}
      </section>}

      <AttentionCard
        vessels={attention}
        allVessels={vessels}
        selectedMmsi={selected}
        onSelect={select}
        loading={fleet.loading}
        error={fleet.error}
        updatedAt={fleet.updatedAt}
        onRetry={fleet.refresh}
        window={selectedWindow}
      />

      {selected && (
        <VesselPanel
          key={`${selected}-${windowKey}`}
          detail={current}
          mmsi={selected}
          error={detail.error}
          loading={detail.loading}
          onClose={() => select(null)}
          onRetry={detail.refresh}
          names={vessels}
          environmental={regionalEnv.data}
          window={selectedWindow}
        />
      )}

      {current && <TrackTimeline detail={current} />}

      <div
        id="environmental-context"
        role="region"
        aria-label="Regional environmental conditions"
        className={`card absolute bottom-5 left-5 z-10 flex max-w-[340px] flex-wrap items-center gap-x-2 px-3.5 py-2 text-[12.5px] text-muted ${current ? 'max-xl:bottom-[106px]' : ''}`}
      >
        {envReading ? (
          <>
            <span className="font-medium text-ink">{envReading.variable}: {envReading.value} {envReading.unit}</span>
            <span aria-hidden="true">·</span>
            <span>{envReading.dateIST}</span>
            <span aria-hidden="true">·</span>
            <span>{envReading.attribution}</span>
          </>
        ) : (
          <span>Environmental data not available</span>
        )}
      </div>

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
