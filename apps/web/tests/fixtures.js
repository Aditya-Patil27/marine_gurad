// Trimmed copies of what the API returned for the seeded demo on 13 Oct 2026 (track shortened).

export const seaPearl = {
  mmsi: 419007431,
  name: 'SEA PEARL II',
  vessel_type: 'FISHING',
  length: 23.4,
  last_seen: '2026-10-13T06:40:48Z',
  position: { lat: 8.90034690978783, lon: 78.94997513887748 },
  course: 94.3,
  speed: 0.8,
  score: 0.63,
  level: 'high',
  state: 'flagged',
  headline: 'SEA PEARL II went dark for 6.4 h',
  reasons: ['AIS switched off', 'Met HAI FENG 818', 'Loitering in protected waters'],
  dark: true,
}

export const lakshmiMatha = {
  mmsi: 419001265,
  name: 'LAKSHMI MATHA',
  vessel_type: 'FISHING',
  length: 14.2,
  last_seen: '2026-10-13T12:52:48Z',
  position: { lat: 8.941756864232591, lon: 78.75943284810737 },
  course: 5,
  speed: 1.3,
  score: 0.48,
  level: 'medium',
  state: 'watch',
  headline: 'LAKSHMI MATHA jumped 36 km',
  reasons: ['Position jumped', 'Loitering in protected waters', 'Fishing vessel inside park'],
  dark: false,
}

export const haiFeng = {
  mmsi: 412440918,
  name: 'HAI FENG 818',
  vessel_type: 'CARGO',
  length: 86,
  last_seen: '2026-10-13T12:52:48Z',
  position: { lat: 8.3, lon: 79.6 },
  course: 132.9,
  speed: 7.7,
  score: 0.32,
  level: 'medium',
  state: 'watch',
  headline: 'HAI FENG 818 met SEA PEARL II',
  reasons: ['Met SEA PEARL II', 'Loitering in protected waters'],
  dark: false,
}

export const nila = {
  mmsi: 419001877,
  name: 'NILA',
  vessel_type: 'FISHING',
  length: 11.5,
  last_seen: '2026-10-13T12:52:48Z',
  position: { lat: 8.208148970334861, lon: 78.95054054054022 },
  course: 30,
  speed: 4.7,
  score: 0,
  level: 'low',
  state: 'tracked',
  headline: 'NILA is behaving normally',
  reasons: [],
  dark: false,
}

export const fleet = {
  generated_at: '2026-10-13T13:03:27Z',
  threshold: 0.6,
  vessels: [seaPearl, lakshmiMatha, haiFeng, nila],
}

export const seaPearlDetail = {
  ...seaPearl,
  generated_at: '2026-10-13T13:03:27Z',
  threshold: 0.6,
  max_points: { ais_gap: 0.31, position_jump: 0.22, encounter: 0.18, loitering: 0.14, fishing_in_park: 0.12 },
  zone: { name: 'Gulf of Mannar Marine National Park', relation: 'buffer', distance_km: 7.2 },
  factors: [
    { key: 'ais_gap', label: 'AIS switched off', detail: '6.4 h so far · rule ≥ 4 h', points: 0.31, max_points: 0.31 },
    { key: 'encounter', label: 'Met HAI FENG 818', detail: '371 m apart · 2 h 28 m · both under 2 kn', points: 0.18, max_points: 0.18 },
    {
      key: 'loitering',
      label: 'Loitering in protected waters',
      detail: '2 h 38 m under 2 kn · Gulf of Mannar Marine National Park',
      points: 0.14,
      max_points: 0.14,
    },
  ],
  checks: [
    { key: 'receiver_outage', label: 'AIS receiver outage', status: 'ruled_out', detail: '9 other vessels within 50 km kept reporting' },
    {
      key: 'weather',
      label: 'Bad weather',
      status: 'not_checked',
      detail: "No marine weather feed is connected yet, so storm sheltering can't be ruled out.",
    },
  ],
  clear_if: { score: 0.32, without: ['ais_gap'], labels: ['AIS switched off'] },
  gaps: [{ start: '2026-10-13T06:40:48Z', end: '2026-10-13T13:03:27Z', hours: 6.377574593888889, open: true }],
  encounters: [
    {
      mmsi: 412440918,
      name: 'HAI FENG 818',
      vessel_type: 'CARGO',
      start: '2026-10-13T04:03:00Z',
      end: '2026-10-13T06:30:56Z',
      hours: 2.47,
      closest_m: 371,
      lat: 8.900205806679477,
      lon: 78.95000652069834,
    },
  ],
  track: [
    { t: '2026-10-13T00:52:48Z', lat: 8.55, lon: 78.7, speed: 9.6, course: 35.5 },
    { t: '2026-10-13T01:02:48Z', lat: 8.569444444444445, lon: 78.71388888888889, speed: 9.4, course: 35.5 },
    { t: '2026-10-13T06:40:48Z', lat: 8.90034690978783, lon: 78.94997513887748, speed: 0.8, course: 94.3 },
  ],
}

/** Shaped like the axios error for an HTTP error status. */
export const httpError = (status) => Object.assign(new Error(`Request failed with status code ${status}`), { response: { status } })

/** Shaped like the axios error when nothing answers. */
export const networkError = () => Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK' })

export const regionalEnvironment = {
  variable: 'Sea surface temperature',
  value: 29.4,
  unit: '°C',
  observed_at: '2026-10-13T06:00:00Z',
  attribution: 'Copernicus Marine Service',
}
