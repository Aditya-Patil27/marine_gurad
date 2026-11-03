import { describe, expect, it } from 'vitest'
import { sourceLabel } from '@/lib/format'

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
