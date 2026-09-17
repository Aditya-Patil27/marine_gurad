import { useEffect, useRef, useState } from 'react'
import maplibregl from 'maplibre-gl'
import { hoursLabel, timeIST, vesselName } from '../../lib/format'
import { STATE_STYLE } from '../../components/StateGlyph'

const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean'

const STYLE = {
  version: 8,
  sources: {
    ocean: {
      type: 'raster',
      tiles: [`${ESRI}/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}`],
      tileSize: 256,
      maxzoom: 10, // Esri has no ocean tiles past 10; MapLibre overzooms instead of showing "no data"
      attribution: 'Basemap © Esri, GEBCO, NOAA',
    },
    labels: {
      type: 'raster',
      tiles: [`${ESRI}/World_Ocean_Reference/MapServer/tile/{z}/{y}/{x}`],
      tileSize: 256,
      maxzoom: 10,
    },
  },
  layers: [
    { id: 'ocean', type: 'raster', source: 'ocean' },
    { id: 'labels', type: 'raster', source: 'labels', paint: { 'raster-opacity': 0.8 } },
  ],
}

const EMPTY = { type: 'FeatureCollection', features: [] }
// Leave room for the floating cards when fitting the selected track
const FIT_PADDING = { top: 96, bottom: 130, left: 400, right: 460 }

/** Arrow drawn as an SDF so one image can be tinted per state. */
function arrowImage(size = 32) {
  const c = document.createElement('canvas')
  c.width = c.height = size
  const g = c.getContext('2d')
  const s = size / 12
  g.fillStyle = '#000'
  g.beginPath()
  g.moveTo(6 * s, 1 * s)
  g.lineTo(10 * s, 11 * s)
  g.lineTo(6 * s, 8.5 * s)
  g.lineTo(2 * s, 11 * s)
  g.closePath()
  g.fill()
  return g.getImageData(0, 0, size, size)
}

function vesselFeatures(vessels, showAll, selectedMmsi) {
  return {
    type: 'FeatureCollection',
    features: vessels
      .filter((v) => showAll || v.state !== 'tracked' || v.mmsi === selectedMmsi)
      .map((v) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [v.position.lon, v.position.lat] },
        properties: {
          mmsi: v.mmsi,
          state: v.state,
          course: v.course ?? 0,
          dark: v.dark,
          selected: v.mmsi === selectedMmsi,
        },
      })),
  }
}

/** Solid line while transmitting; dashed where AIS went quiet between two pings. */
function trackFeatures(detail) {
  if (!detail) return EMPTY
  const pts = detail.track
  const gapStarts = new Set(detail.gaps.filter((g) => !g.open).map((g) => g.start))
  const features = []
  let run = []
  for (let i = 0; i < pts.length; i++) {
    run.push([pts[i].lon, pts[i].lat])
    const next = pts[i + 1]
    if (next && gapStarts.has(pts[i].t)) {
      if (run.length > 1) features.push(line(run, 'on'))
      features.push(line([[pts[i].lon, pts[i].lat], [next.lon, next.lat]], 'gap'))
      run = []
    }
  }
  if (run.length > 1) features.push(line(run, 'on'))
  return { type: 'FeatureCollection', features }
}

const line = (coordinates, kind) => ({ type: 'Feature', geometry: { type: 'LineString', coordinates }, properties: { kind } })

function tag(text, className = '') {
  const el = document.createElement('span')
  el.className = `maptag ${className}`
  el.textContent = text
  return el
}

export default function OceanMap({ vessels, zones, detail, showZones, showAll, onSelect, openedOn }) {
  const container = useRef(null)
  const map = useRef(null)
  const markers = useRef([])
  const fitted = useRef(null)
  const [ready, setReady] = useState(false)
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect

  useEffect(() => {
    const m = new maplibregl.Map({
      container: container.current,
      style: STYLE,
      center: [78.95, 8.7],
      zoom: 8.6,
      maxZoom: 12,
      attributionControl: { compact: true },
      dragRotate: false,
      pitchWithRotate: false,
    })
    map.current = m
    m.touchZoomRotate.disableRotation()

    m.on('load', () => {
      m.addImage('arrow', arrowImage(), { sdf: true, pixelRatio: 2 })

      m.addSource('zones', { type: 'geojson', data: EMPTY })
      m.addLayer({ id: 'zone-fill', type: 'fill', source: 'zones', filter: ['==', ['get', 'kind'], 'outline'], paint: { 'fill-color': '#A3339A', 'fill-opacity': 0.08 } })
      m.addLayer({ id: 'zone-line', type: 'line', source: 'zones', filter: ['==', ['get', 'kind'], 'outline'], paint: { 'line-color': '#A3339A', 'line-width': 2 } })
      m.addLayer({ id: 'zone-buffer', type: 'line', source: 'zones', filter: ['==', ['get', 'kind'], 'buffer'], paint: { 'line-color': '#A3339A', 'line-width': 1.2, 'line-dasharray': [4, 3], 'line-opacity': 0.8 } })

      m.addSource('track', { type: 'geojson', data: EMPTY })
      m.addLayer({ id: 'track-on', type: 'line', source: 'track', filter: ['==', ['get', 'kind'], 'on'], layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#08337F', 'line-width': 3, 'line-opacity': 0.85 } })
      m.addLayer({ id: 'track-gap', type: 'line', source: 'track', filter: ['==', ['get', 'kind'], 'gap'], paint: { 'line-color': '#D64545', 'line-width': 2.5, 'line-dasharray': [1, 2.5] } })

      m.addSource('vessels', { type: 'geojson', data: EMPTY })
      m.addLayer({
        id: 'vessel-ring',
        type: 'circle',
        source: 'vessels',
        filter: ['!=', ['get', 'state'], 'tracked'],
        paint: {
          'circle-radius': ['case', ['get', 'selected'], 20, 14],
          'circle-color': ['match', ['get', 'state'], 'flagged', STATE_STYLE.flagged.color, STATE_STYLE.watch.color],
          'circle-opacity': 0.08,
          'circle-stroke-width': 2,
          'circle-stroke-color': ['match', ['get', 'state'], 'flagged', STATE_STYLE.flagged.color, STATE_STYLE.watch.color],
        },
      })
      m.addLayer({
        id: 'vessel-arrow',
        type: 'symbol',
        source: 'vessels',
        layout: {
          'icon-image': 'arrow',
          'icon-size': ['case', ['get', 'selected'], 0.95, 0.8],
          'icon-rotate': ['get', 'course'],
          'icon-rotation-alignment': 'map',
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
        },
        paint: {
          'icon-color': ['match', ['get', 'state'], 'flagged', STATE_STYLE.flagged.color, 'watch', STATE_STYLE.watch.color, STATE_STYLE.tracked.color],
          // Last known position of a vessel that has gone dark: faded arrow
          'icon-opacity': ['case', ['get', 'dark'], 0.45, 1],
          'icon-halo-color': '#fff',
          'icon-halo-width': 1,
        },
      })

      for (const id of ['vessel-arrow', 'vessel-ring']) {
        m.on('click', id, (e) => onSelectRef.current(e.features[0].properties.mmsi))
        m.on('mouseenter', id, () => (m.getCanvas().style.cursor = 'pointer'))
        m.on('mouseleave', id, () => (m.getCanvas().style.cursor = ''))
      }
      setReady(true)
    })
    return () => m.remove()
  }, [])

  useEffect(() => {
    if (!ready) return
    map.current.getSource('zones').setData(zones ?? EMPTY)
    for (const id of ['zone-fill', 'zone-line', 'zone-buffer']) {
      map.current.setLayoutProperty(id, 'visibility', showZones ? 'visible' : 'none')
    }
  }, [ready, zones, showZones])

  useEffect(() => {
    if (!ready) return
    map.current.getSource('vessels').setData(vesselFeatures(vessels ?? [], showAll, detail?.mmsi))
  }, [ready, vessels, showAll, detail?.mmsi])

  // Selected vessel: track, story tags, and zone name labels
  useEffect(() => {
    if (!ready) return
    const m = map.current
    m.getSource('track').setData(trackFeatures(detail))
    markers.current.forEach((mk) => mk.remove())
    markers.current = []
    // Tags sit left of the vessel so they never slide under the detail card on the right
    const add = (el, lngLat, offset) => markers.current.push(new maplibregl.Marker({ element: el, anchor: 'right', offset }).setLngLat(lngLat).addTo(m))

    // Zone names give way to the selected vessel's tags
    if (showZones && zones && !detail) {
      for (const f of zones.features.filter((f) => f.properties.kind === 'outline')) {
        const el = document.createElement('span')
        el.className = 'font-head text-[12px] font-semibold uppercase tracking-[.06em] text-[#7F2378] pointer-events-none whitespace-nowrap'
        el.textContent = f.properties.name
        markers.current.push(new maplibregl.Marker({ element: el }).setLngLat(f.properties.label).addTo(m))
      }
    }
    if (!detail) {
      fitted.current = null
      return
    }

    const open = detail.gaps.find((g) => g.open && g.hours >= 1)
    if (open) {
      add(tag(`AIS off ${timeIST(open.start)} · ${hoursLabel(open.hours)}`, 'text-[#A82E2E]'), [detail.position.lon, detail.position.lat], [-26, 16])
    }
    const enc = detail.encounters[0]
    if (enc) {
      add(tag(`Met ${vesselName(enc)} · ${enc.closest_m} m`, 'text-[#A82E2E]'), [enc.lon, enc.lat], [-26, -16])
    }

    // Frame the track once per selection, not on every 30 s refresh
    const coords = detail.track.map((p) => [p.lon, p.lat])
    if (coords.length && fitted.current !== detail.mmsi) {
      // A link that opens straight onto a vessel lands there; later selections fly
      const instant = fitted.current === null && detail.mmsi === openedOn
      fitted.current = detail.mmsi
      const bounds = coords.reduce((b, c) => b.extend(c), new maplibregl.LngLatBounds(coords[0], coords[0]))
      const { clientWidth, clientHeight } = m.getContainer()
      const roomy = clientWidth > FIT_PADDING.left + FIT_PADDING.right + 200 && clientHeight > FIT_PADDING.top + FIT_PADDING.bottom + 200
      m.fitBounds(bounds, { padding: roomy ? FIT_PADDING : 40, maxZoom: 9, duration: instant ? 0 : 600 })
    }
  }, [ready, detail, zones, showZones, openedOn])

  return <div ref={container} className="absolute inset-0" aria-label="Ocean map" role="region" />
}
