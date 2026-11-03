import { describe, expect, it } from 'vitest'
import { dateTimeIST, modeLabel, sourceLabel } from '@/lib/format'

describe('sourceLabel', () => {
  it('returns Live data for live data_mode', () => {
    expect(sourceLabel({ data_mode: 'live' })).toBe('Live data')
  })

  it('returns Historical data for historical data_mode', () => {
    expect(sourceLabel({ data_mode: 'historical' })).toBe('Historical data')
  })

  it('returns Cached data for cached data_mode', () => {
    expect(sourceLabel({ data_mode: 'cached' })).toBe('Cached data')
  })

  it('returns Synthetic data for synthetic data_mode', () => {
    expect(sourceLabel({ data_mode: 'synthetic' })).toBe('Synthetic data')
  })

  it('returns Source not reported for empty object, null, undefined, or null data_mode', () => {
    expect(sourceLabel({})).toBe('Source not reported')
    expect(sourceLabel(null)).toBe('Source not reported')
    expect(sourceLabel(undefined)).toBe('Source not reported')
    expect(sourceLabel({ data_mode: null })).toBe('Source not reported')
  })

  it('returns Source not reported for unknown modes including uppercase, non-standard, or prototype properties', () => {
    expect(sourceLabel({ data_mode: 'LIVE' })).toBe('Source not reported')
    expect(sourceLabel({ data_mode: 'realtime' })).toBe('Source not reported')
    expect(sourceLabel({ data_mode: 'constructor' })).toBe('Source not reported')
  })
})

describe('dateTimeIST', () => {
  it('formats UTC ISO timestamp with Z ending to IST', () => {
    expect(dateTimeIST('2026-10-13T06:40:48Z')).toBe('13 Oct 2026, 12:10 IST')
  })

  it('formats ISO timestamp with +00:00 offset to IST', () => {
    expect(dateTimeIST('2026-10-13T06:40:48+00:00')).toBe('13 Oct 2026, 12:10 IST')
  })

  it('formats timestamp where the date moves to IST on midnight', () => {
    expect(dateTimeIST('2026-11-03T18:30:00Z')).toBe('4 Nov 2026, 00:00 IST')
  })

  it('returns Time not reported for null, undefined, or empty string', () => {
    expect(dateTimeIST(null)).toBe('Time not reported')
    expect(dateTimeIST(undefined)).toBe('Time not reported')
    expect(dateTimeIST('')).toBe('Time not reported')
  })

  it('returns Time not reported with no exception for invalid date string', () => {
    expect(dateTimeIST('not a date')).toBe('Time not reported')
  })

  it('returns Time not reported when ISO string has no Z and no offset', () => {
    expect(dateTimeIST('2026-10-13T06:40:48')).toBe('Time not reported')
  })

  it('returns Time not reported with no exception for out-of-range ISO timestamp (O)', () => {
    expect(dateTimeIST('2026-13-45T00:00:00Z')).toBe('Time not reported')
  })
})

describe('modeLabel', () => {
  it('returns Live data for live data_mode', () => {
    expect(modeLabel({ data_mode: 'live' })).toBe('Live data')
  })

  it('returns Historical data for historical data_mode', () => {
    expect(modeLabel({ data_mode: 'historical' })).toBe('Historical data')
  })

  it('returns Cached data for cached data_mode', () => {
    expect(modeLabel({ data_mode: 'cached' })).toBe('Cached data')
  })

  it('returns Synthetic data for synthetic data_mode', () => {
    expect(modeLabel({ data_mode: 'synthetic' })).toBe('Synthetic data')
  })

  it('returns Mode not reported for {}, null, undefined, or null data_mode', () => {
    expect(modeLabel({})).toBe('Mode not reported')
    expect(modeLabel(null)).toBe('Mode not reported')
    expect(modeLabel(undefined)).toBe('Mode not reported')
    expect(modeLabel({ data_mode: null })).toBe('Mode not reported')
  })

  it('returns Mode not reported for realtime and constructor', () => {
    expect(modeLabel({ data_mode: 'realtime' })).toBe('Mode not reported')
    expect(modeLabel({ data_mode: 'constructor' })).toBe('Mode not reported')
  })
})
