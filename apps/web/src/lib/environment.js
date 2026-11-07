import { dateTimeIST } from './format'

export const ENVIRONMENTAL_FIELDS = {
  VARIABLE: 'variable',
  VALUE: 'value',
  UNIT: 'unit',
  OBSERVED_AT: 'observed_at',
  ATTRIBUTION: 'attribution',
}

/** Formats regional environmental reading or returns null if incomplete. */
export function formatEnvironmentalReading(data) {
  if (!data) return null
  const value = data[ENVIRONMENTAL_FIELDS.VALUE]
  const unit = data[ENVIRONMENTAL_FIELDS.UNIT]
  const observedAt = data[ENVIRONMENTAL_FIELDS.OBSERVED_AT]
  const attribution = data[ENVIRONMENTAL_FIELDS.ATTRIBUTION]

  if (value === undefined || value === null || !unit || !observedAt || !attribution) {
    return null
  }

  const formattedDate = dateTimeIST(observedAt)
  if (formattedDate === 'Time not reported') return null

  const variable = data[ENVIRONMENTAL_FIELDS.VARIABLE] || 'Regional environment'

  return {
    variable,
    value,
    unit,
    dateIST: formattedDate,
    attribution,
  }
}
