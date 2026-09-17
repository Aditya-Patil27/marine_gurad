const istTime = new Intl.DateTimeFormat('en-IN', {
  timeZone: 'Asia/Kolkata',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

/** 14:32 in India Standard Time, which is what officers on this coast read. */
export const timeIST = (iso) => (iso ? istTime.format(new Date(iso)) : '—')

export const score = (value) => (value ?? 0).toFixed(2)

const ROMAN = /^[IVX]+$/

/** AIS names are upper case ("SEA PEARL II"); show them as "Sea Pearl II". */
export function vesselName(v) {
  if (!v?.name) return `MMSI ${v?.mmsi ?? ''}`.trim()
  return v.name
    .split(/\s+/)
    .map((w) => (ROMAN.test(w) || /\d/.test(w) ? w : w.charAt(0) + w.slice(1).toLowerCase()))
    .join(' ')
}

/** Titles from the API embed raw AIS names; swap each one for its display form. */
export function withDisplayNames(text, vessels) {
  let out = text
  for (const v of vessels) {
    if (v.name && out.includes(v.name)) out = out.split(v.name).join(vesselName(v))
  }
  return out
}

const TYPES = {
  FISHING: 'Fishing vessel',
  CARGO: 'Cargo ship',
  TANKER: 'Tanker',
  PASSENGER: 'Passenger ship',
  TUG: 'Tug',
  OTHER: 'Vessel',
}
export const vesselType = (t) => TYPES[t] ?? 'Vessel'

export function hoursLabel(hours) {
  const total = Math.round(hours * 60)
  const h = Math.floor(total / 60)
  const m = total % 60
  if (h && m) return `${h} h ${m} m`
  return h ? `${h} h` : `${m} m`
}

export const LEVEL = {
  high: { label: 'High risk', color: 'text-risk-red', pill: 'pill-red' },
  medium: { label: 'Watch', color: 'text-risk-amber', pill: 'pill-amber' },
  low: { label: 'Normal', color: 'text-muted', pill: 'pill-navy' },
}

/** How each behaviour would stop counting, for "What would clear it". */
export const CLEARS = {
  ais_gap: 'AIS comes back on',
  encounter: 'the meeting at sea is explained',
  loitering: 'it leaves protected waters',
  position_jump: 'the jump turns out to be a GPS fault',
  fishing_in_park: 'it leaves the park',
}
