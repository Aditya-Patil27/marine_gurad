import { useEffect } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '@/App'
import { mapApi, vesselsApi } from '@/lib/api'
import { fleet, httpError, networkError, seaPearlDetail } from './fixtures'

// MapLibre needs WebGL, which jsdom doesn't have; the map itself is checked in a browser
vi.mock('@/features/map/OceanMap', () => ({ default: () => null }))
vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  vesselsApi: { list: vi.fn(), get: vi.fn() },
  mapApi: { zones: vi.fn() },
}))

const ZONES = { type: 'FeatureCollection', features: [] }

/** Every history entry the app creates, in order. */
function Visits({ log }) {
  const location = useLocation()
  useEffect(() => {
    log.push(location.pathname + location.search)
  }, [location, log])
  return null
}

async function open(url) {
  const visits = []
  render(
    <MemoryRouter initialEntries={[url]}>
      <Visits log={visits} />
      <App />
    </MemoryRouter>,
  )
  await settle()
  return visits
}

/** Let pending requests answer and the screen catch up. */
const settle = (ms = 0) => act(() => vi.advanceTimersByTimeAsync(ms))

const pill = () => screen.getByRole('status').textContent

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-13T13:03:27Z')) // 18:33 IST
  vesselsApi.list.mockReset().mockResolvedValue(fleet)
  vesselsApi.get.mockReset().mockResolvedValue(seaPearlDetail)
  mapApi.zones.mockReset().mockResolvedValue(ZONES)
})

afterEach(() => vi.useRealTimers())

describe('map page', () => {
  it('lists the vessels that need attention', async () => {
    await open('/map')

    expect(screen.getByText('Sea Pearl II went dark for 6.4 h')).toBeTruthy()
    expect(screen.queryByText('Nila is behaving normally')).toBeNull()
  })

  it('shows when the fleet was last updated in India Standard Time', async () => {
    await open('/map')

    expect(pill()).toBe('4 vessels · updated 18:33')
  })

  it('does not give the all-clear when the API is down', async () => {
    vesselsApi.list.mockRejectedValue(networkError())
    await open('/map')

    expect(pill()).toBe("Can't reach the API")
    expect(screen.queryByText(/Nothing needs attention/)).toBeNull()
    expect(screen.getByText(/Can't load vessels/)).toBeTruthy()
  })

  it('says how old the fleet is when a refresh fails', async () => {
    await open('/map')
    vesselsApi.list.mockRejectedValue(networkError())

    await settle(30000)

    expect(pill()).toBe("Can't reach the API · last update 18:33")
    expect(screen.getByText('Sea Pearl II went dark for 6.4 h')).toBeTruthy()
  })

  it('loads the fleet again when asked', async () => {
    vesselsApi.list.mockRejectedValueOnce(networkError())
    await open('/map')

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await settle()

    expect(screen.getByText('Sea Pearl II went dark for 6.4 h')).toBeTruthy()
  })

  it('opens the vessel named in the address', async () => {
    await open('/map?vessel=419007431')

    expect(vesselsApi.get).toHaveBeenCalledWith(419007431)
    expect(screen.getByRole('heading', { name: 'Sea Pearl II' })).toBeTruthy()
  })

  it('adds one history entry when a vessel is selected', async () => {
    const visits = await open('/map')

    fireEvent.click(screen.getByRole('button', { name: /Sea Pearl II went dark/ }))
    await settle()

    expect(visits).toEqual(['/map', '/map?vessel=419007431'])
  })

  it('adds no history entry when the selected vessel is selected again', async () => {
    const visits = await open('/map?vessel=419007431')

    fireEvent.click(screen.getByRole('button', { name: /Sea Pearl II went dark/ }))
    await settle()

    expect(visits).toEqual(['/map?vessel=419007431'])
  })

  it.each(['1.5', 'abc', '-7', '0'])('ignores "%s" as the vessel in the address', async (value) => {
    await open(`/map?vessel=${value}`)

    expect(vesselsApi.get).not.toHaveBeenCalled()
    expect(screen.queryByLabelText('Vessel details')).toBeNull()
  })

  it('says a vessel has no positions when the API has none for it', async () => {
    vesselsApi.get.mockRejectedValue(httpError(404))
    await open('/map?vessel=999')

    expect(screen.getByText('No positions for MMSI 999 in the last 24 h.')).toBeTruthy()
  })

  it('loads the vessel again when asked', async () => {
    vesselsApi.get.mockRejectedValueOnce(networkError())
    await open('/map?vessel=419007431')

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await settle()

    expect(screen.getByRole('heading', { name: 'Sea Pearl II' })).toBeTruthy()
  })

  describe('vessel search', () => {
    const search = () => screen.getByRole('combobox', { name: 'Search vessels' })
    // Every vessel in the fixture has an "a" in its name, in fleet order
    const type = (text) => fireEvent.change(search(), { target: { value: text } })
    const press = (key) => fireEvent.keyDown(search(), { key })
    const onOption = () => document.getElementById(search().getAttribute('aria-activedescendant'))

    it('opens the first result on Enter', async () => {
      const visits = await open('/map')

      type('a')
      press('Enter')
      await settle()

      expect(visits.at(-1)).toBe('/map?vessel=419007431')
    })

    it('opens the result picked with the arrow keys', async () => {
      const visits = await open('/map')

      type('a')
      press('ArrowDown')
      press('Enter')
      await settle()

      expect(visits.at(-1)).toBe('/map?vessel=419001265')
    })

    it('says which result the arrow keys are on', async () => {
      await open('/map')

      type('a')
      press('ArrowDown')

      expect(onOption().textContent).toContain('Lakshmi Matha')
      expect(onOption().getAttribute('aria-selected')).toBe('true')
      expect(screen.getAllByRole('option')).toHaveLength(4)
    })

    it('goes from the first result up to the last', async () => {
      await open('/map')

      type('a')
      press('ArrowUp')

      expect(onOption().textContent).toContain('Nila')
    })

    it('starts again from the first result when the search changes', async () => {
      await open('/map')

      type('a')
      press('ArrowDown')
      type('la')

      expect(onOption().textContent).toContain('Lakshmi Matha')
    })

    it('clears the search on Escape', async () => {
      await open('/map')

      type('pearl')
      press('Escape')

      expect(search().value).toBe('')
      expect(screen.queryByRole('listbox')).toBeNull()
    })

    it('says when no vessel matches', async () => {
      await open('/map')

      type('zzz')

      expect(screen.getByText('No vessel matches “zzz”').getAttribute('role')).toBe('status')
      expect(search().getAttribute('aria-expanded')).toBe('false')
    })
  })

  it('comes back from the evidence screen to the same vessel', async () => {
    const visits = await open('/vessels/419007431')

    fireEvent.click(screen.getByRole('link', { name: 'Back to the map' }))
    await settle()

    expect(visits.at(-1)).toBe('/map?vessel=419007431')
    expect(screen.getByRole('heading', { name: 'Sea Pearl II' })).toBeTruthy()
  })

  it('says so when protected areas did not load, and loads them when asked', async () => {
    mapApi.zones.mockRejectedValueOnce(networkError())
    await open('/map')

    fireEvent.click(screen.getByRole('button', { name: "Protected areas didn't load. Try again" }))
    await settle()

    expect(screen.getByRole('button', { name: 'Protected areas' }).getAttribute('aria-pressed')).toBe('true')
  })
})
