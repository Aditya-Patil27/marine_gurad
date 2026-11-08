import { useEffect } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '@/App'
import { environmentApi, mapApi, reportsApi, sarApi, vesselsApi, weatherApi } from '@/lib/api'
import { fleet, httpError, networkError, regionalEnvironment, seaPearlDetail } from './fixtures'

// MapLibre needs WebGL, which jsdom doesn't have; the map itself is checked in a browser
vi.mock('@/features/map/OceanMap', () => ({ default: () => null }))
vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  vesselsApi: { list: vi.fn(), get: vi.fn() },
  mapApi: { zones: vi.fn() },
  weatherApi: { vessel: vi.fn() },
  sarApi: { detections: vi.fn() },
  environmentApi: { regional: vi.fn() },
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
  weatherApi.vessel.mockReset().mockResolvedValue({ status: 'unavailable', reason: 'Weather service unavailable.' })
  sarApi.detections.mockReset().mockResolvedValue([])
  environmentApi.regional.mockReset().mockRejectedValue(new Error('Endpoint not available'))
})

afterEach(() => vi.useRealTimers())

describe('map page', () => {
  it('keeps the vessel open when its panel links to the regional value', async () => {
    environmentApi.regional.mockResolvedValue(regionalEnvironment)
    await open('/map?vessel=419007431')

    fireEvent.click(screen.getByRole('link', { name: /Regional ocean context/ }))
    await settle()

    expect(screen.getByRole('complementary', { name: /Sea Pearl II/ })).toBeTruthy()
  })

  it('does not carry a failed draft report over to the next vessel', async () => {
    const create = vi.spyOn(reportsApi, 'create').mockRejectedValue(httpError(500))
    vesselsApi.get.mockImplementation(async (mmsi) => ({ ...seaPearlDetail, mmsi }))
    await open('/map?vessel=419007431')

    fireEvent.click(screen.getByRole('button', { name: 'Draft report' }))
    await settle()
    expect(screen.getByRole('alert').textContent).toContain('Could not create an evidence snapshot')

    fireEvent.click(screen.getByText(/Lakshmi Matha jumped/))
    await settle()

    expect(screen.queryByText(/Could not create an evidence snapshot/)).toBeNull()
    create.mockRestore()
  })

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

    // Rolling view: no historical window bounds are sent
    expect(vesselsApi.get).toHaveBeenCalledWith(419007431, null)
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

    fireEvent.click(screen.getByRole('link', { name: 'View track on map' }))
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

  describe('data mode banner and status dot', () => {
    const dot = () => screen.getByRole('status').querySelector('[aria-hidden="true"]')
    const banner = () => screen.getByRole('region', { name: 'Data mode' })

    it('shows api error on banner when refresh fails after live load', async () => {
      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'live' })
      await open('/map')
      vesselsApi.list.mockRejectedValue(networkError())

      await settle(30000)

      const text = banner().textContent
      expect(text).toMatch(/^Can't reach the API · last sync 18:33 IST/)
      expect(text).not.toContain('Live data')
    })

    it('restores live banner when api answers again', async () => {
      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'live' })
      await open('/map')
      vesselsApi.list.mockRejectedValue(networkError())

      await settle(30000)
      expect(banner().textContent).not.toContain('Live data')

      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'live' })
      await settle(30000)
      expect(banner().textContent).toBe('Data mode: Live data')
    })

    it('renders faint dot when fleet has no data_mode', async () => {
      await open('/map')

      expect(dot().className).toContain('bg-faint')
      expect(dot().className).not.toContain('bg-risk-green')
    })

    it('renders green dot when fleet has data_mode live', async () => {
      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'live' })
      await open('/map')

      expect(dot().className).toContain('bg-risk-green')
    })

    it('renders red dot when fleet request rejects', async () => {
      vesselsApi.list.mockRejectedValue(networkError())
      await open('/map')

      expect(dot().className).toContain('bg-risk-red')
    })

    it('renders faint dot while connecting', async () => {
      vesselsApi.list.mockReturnValue(new Promise(() => {}))
      await open('/map')

      expect(dot().className).toContain('bg-faint')
      expect(dot().className).not.toContain('bg-risk-green')
    })

    it('renders green dot online with live data, grey dot offline with live data, and red dot offline with fleet.error (B-16b)', async () => {
      const liveFleet = { ...fleet, data_mode: 'live' }
      const onlineSpy = vi.spyOn(window.navigator, 'onLine', 'get').mockReturnValue(true)
      vesselsApi.list.mockResolvedValue(liveFleet)
      await open('/map')

      // 1. Online with live data: green
      expect(dot().className).toContain('bg-risk-green')
      expect(dot().className).not.toContain('bg-faint')

      // 2. Offline with live data: grey (bg-faint)
      onlineSpy.mockReturnValue(false)
      act(() => {
        window.dispatchEvent(new Event('offline'))
      })
      expect(dot().className).toContain('bg-faint')
      expect(dot().className).not.toContain('bg-risk-green')

      // 3. Offline with fleet.error: red (bg-risk-red)
      vesselsApi.list.mockRejectedValue(networkError())
      await settle(30000)
      expect(dot().className).toContain('bg-risk-red')
      expect(dot().className).not.toContain('bg-faint')
    })
  })

  describe('regional environmental value (B-07)', () => {
    it('shows environmental data not available when endpoint fails or has no data', async () => {
      environmentApi.regional.mockRejectedValue(new Error('404 Not Found'))
      await open('/map')

      const envBox = screen.getByRole('region', { name: 'Regional environmental conditions' })
      expect(envBox.textContent).toContain('Environmental data not available')
      expect(envBox.textContent).not.toContain('29.4')
    })

    it('shows value, unit, date with labelled timezone, and attribution from regional environment fixture', async () => {
      environmentApi.regional.mockResolvedValue(regionalEnvironment)
      await open('/map')

      const envBox = screen.getByRole('region', { name: 'Regional environmental conditions' })
      expect(envBox.textContent).toContain('29.4')
      expect(envBox.textContent).toContain('°C')
      expect(envBox.textContent).toContain('13 Oct 2026, 11:30 IST')
      expect(envBox.textContent).toContain('Copernicus Marine Service')
      expect(envBox.textContent).not.toContain('Environmental data not available')
    })
  })
})
