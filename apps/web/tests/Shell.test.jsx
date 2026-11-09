import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Shell from '@/components/Shell'
import { operationsApi, vesselsApi } from '@/lib/api'
import { fleet } from './fixtures'

vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  vesselsApi: { list: vi.fn(), get: vi.fn() },
  operationsApi: { status: vi.fn() },
}))

let healthy = false
function Flaky() {
  if (!healthy) throw new Error('This page cannot draw')
  return <p>Page drawn</p>
}

async function open(url) {
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route element={<Shell />}>
          <Route path="map" element={<Flaky />} />
          <Route path="alerts" element={<p>Alerts page</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
  await act(async () => {})
}

// React and jsdom both report an error a boundary catches; here it is thrown on purpose
const expected = (event) => event.preventDefault()

beforeEach(() => {
  healthy = false
  vesselsApi.list.mockReset().mockResolvedValue(fleet)
  operationsApi.status.mockReset().mockResolvedValue({ remote_fetch_paused: false, cache: {} })
  vi.spyOn(console, 'error').mockImplementation(() => {})
  window.addEventListener('error', expected)
})

afterEach(() => {
  window.removeEventListener('error', expected)
  vi.restoreAllMocks()
})

describe('shell', () => {
  it('says how many vessels are high risk on the Alerts link', async () => {
    await open('/alerts')

    expect(screen.getByRole('link', { name: 'Alerts, 1 high risk' })).toBeTruthy()
  })

  it('keeps the rail when a page fails to draw', async () => {
    await open('/map')

    expect(screen.getByRole('navigation', { name: 'Main' })).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toContain('This screen stopped working')
  })

  it('draws the page again when asked', async () => {
    await open('/map')
    healthy = true

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(screen.getByText('Page drawn')).toBeTruthy()
  })

  it('leaves the failure behind when another page is opened', async () => {
    await open('/map')

    fireEvent.click(screen.getByRole('link', { name: /Alerts/ }))

    expect(screen.getByText('Alerts page')).toBeTruthy()
  })

  describe('data mode banner', () => {
    const banner = () => screen.getByRole('region', { name: 'Data mode' })

    it('shows source not reported when fleet has no data_mode', async () => {
      await open('/alerts')

      expect(banner().textContent).toBe('Data mode: Source not reported')
    })

    it('shows live data when fleet has data_mode live', async () => {
      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'live' })
      await open('/alerts')

      expect(banner().textContent).toBe('Data mode: Live data')
    })

    it('shows synthetic data when fleet has data_mode synthetic', async () => {
      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'synthetic' })
      await open('/alerts')

      expect(banner().textContent).toBe('Data mode: Synthetic data')
    })

    it('shows offline warning when offline even if fleet is live', async () => {
      vi.spyOn(window.navigator, 'onLine', 'get').mockReturnValue(false)
      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'live' })
      await open('/alerts')

      const text = banner().textContent
      expect(text).toMatch(/^Offline · last sync/)
      expect(text).toContain('need a connection')
      expect(text).not.toContain('Live data')
    })

    it('shows nothing synced yet when offline and fleet never answered', async () => {
      vi.spyOn(window.navigator, 'onLine', 'get').mockReturnValue(false)
      vesselsApi.list.mockReturnValue(new Promise(() => {}))
      await open('/alerts')

      expect(banner().textContent).toMatch(/^Offline · nothing synced yet/)
    })

    it('shows no data loaded yet when fleet rejects with no data', async () => {
      vesselsApi.list.mockRejectedValue(new Error('Network error'))
      await open('/alerts')

      expect(banner().textContent).toBe("Can't reach the API · no data loaded yet")
    })

    it('shows checking data source when fleet never answered and online', async () => {
      vesselsApi.list.mockReturnValue(new Promise(() => {}))
      await open('/alerts')

      expect(banner().textContent).toBe('Checking the data source…')
    })

    it('reacts to online and offline events', async () => {
      const spy = vi.spyOn(window.navigator, 'onLine', 'get').mockReturnValue(true)
      await open('/alerts')
      expect(banner().textContent).toContain('Data mode:')

      spy.mockReturnValue(false)
      act(() => {
        window.dispatchEvent(new Event('offline'))
      })
      expect(banner().textContent).toContain('Offline ·')

      spy.mockReturnValue(true)
      act(() => {
        window.dispatchEvent(new Event('online'))
      })
      expect(banner().textContent).toContain('Data mode:')
    })

    it('keeps the banner when a page fails to draw', async () => {
      await open('/map')

      expect(banner()).toBeTruthy()
      expect(screen.getByRole('alert').textContent).toContain('This screen stopped working')
    })

    it('applies pill-amber warning class for rows that warn: offline with data, offline with no data, API error with no data (K)', async () => {
      // offline with data
      const onlineSpy = vi.spyOn(window.navigator, 'onLine', 'get').mockReturnValue(false)
      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'live' })
      await open('/alerts')
      expect(banner().className).toContain('pill-amber')
      cleanup()

      // offline with no data
      vesselsApi.list.mockReturnValue(new Promise(() => {}))
      await open('/alerts')
      expect(banner().className).toContain('pill-amber')
      cleanup()

      // API error with no data
      onlineSpy.mockReturnValue(true)
      vesselsApi.list.mockRejectedValue(new Error('Network error'))
      await open('/alerts')
      expect(banner().className).toContain('pill-amber')
      cleanup()
    })

    it('does not apply pill-amber class for rows that do not warn: checking data source and data mode shown (L)', async () => {
      // checking the data source
      vesselsApi.list.mockReturnValue(new Promise(() => {}))
      await open('/alerts')
      expect(banner().className).not.toContain('pill-amber')
      cleanup()

      // data mode shown
      vesselsApi.list.mockResolvedValue({ ...fleet, data_mode: 'live' })
      await open('/alerts')
      expect(banner().className).not.toContain('pill-amber')
      cleanup()
    })
  })
})
