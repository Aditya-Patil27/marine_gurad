const istTime = new Intl.DateTimeFormat('en-IN', {
  timeZone: 'Asia/Kolkata',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

/** 14:32 in India Standard Time, which is what officers on this coast read. */
export const timeIST = (iso) => (iso ? istTime.format(new Date(iso)) : '—')

const istDateTime = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Kolkata',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

const HAS_TZ = /\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}(?::?\d{2})?)$/i

/** 13 Oct 2026, 12:10 IST. Rejects timestamps without explicit timezone. */
export function dateTimeIST(iso) {
  if (typeof iso !== 'string' || !iso.trim()) return 'Time not reported'
  if (!HAS_TZ.test(iso.trim())) return 'Time not reported'
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return 'Time not reported'
    const parts = istDateTime.formatToParts(d)
    const p = {}
    for (const part of parts) {
      p[part.type] = part.value
    }
    return `${p.day} ${p.month} ${p.year}, ${p.hour}:${p.minute} IST`
  } catch {
    return 'Time not reported'
  }
}

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

/** A level this build doesn't know still renders: neutral colours and the API's own word for it. */
export const levelStyle = (level) => LEVEL[level] ?? { label: level || 'Not scored', color: 'text-muted', pill: 'pill-navy' }

/** How each behaviour would stop counting, for "What would clear it". */
export const CLEARS = {
  ais_gap: 'AIS comes back on',
  encounter: 'the meeting at sea is explained',
  loitering: 'it leaves protected waters',
  position_jump: 'the jump turns out to be a GPS fault',
  fishing_in_park: 'it leaves the park',
}

const DATA_MODES = {
  live: 'Live data',
  historical: 'Historical data',
  cached: 'Cached data',
  synthetic: 'Synthetic data',
}

/** Never guess: a missing or unknown mode must not read as live. Only this helper reads `data_mode`, so a contract rename is one line. */
export const sourceLabel = (record) =>
  Object.hasOwn(DATA_MODES, record?.data_mode ?? '') ? DATA_MODES[record.data_mode] : 'Source not reported'

export function modeLabel(record) {
  const label = sourceLabel(record)
  return label === 'Source not reported' ? 'Mode not reported' : label
}
