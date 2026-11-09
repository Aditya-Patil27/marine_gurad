import { act, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Overview from '@/pages/Overview'
import { alertsApi, casesApi, reportsApi, sourcesApi, vesselsApi } from '@/lib/api'
import { fleet } from './fixtures'

vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  vesselsApi: { list: vi.fn() },
  alertsApi: { stored: vi.fn() },
  casesApi: { list: vi.fn() },
  reportsApi: { list: vi.fn() },
  sourcesApi: { health: vi.fn() },
}))

const health = {
  sources: {
    local_vessel_records: { status: 'available' },
    copernicus_sst: { status: 'available', mode: 'historical' },
    global_fishing_watch: { status: 'configured', availability: 'not_checked' },
    aisstream: { status: 'not_configured', availability: 'not_checked' },
    open_meteo_marine: { status: 'not_checked', availability: 'not_checked' },
  },
}

async function open() {
  render(<MemoryRouter initialEntries={['/overview']}><Routes><Route path="/overview" element={<Overview />} /></Routes></MemoryRouter>)
  await act(async () => {})
}

beforeEach(() => {
  vi.resetAllMocks()
  vesselsApi.list.mockResolvedValue(fleet)
  alertsApi.stored.mockResolvedValue({ alerts: [], total: 2 })
  casesApi.list.mockResolvedValue([{ id: 'c1', title: 'Harbour review', status: 'open', mmsi: 123 }, { id: 'c2' }])
  reportsApi.list.mockResolvedValue([{ id: 1 }])
  sourcesApi.health.mockResolvedValue(health)
})

describe('Overview landing page', () => {
  it('shows operational status, recent investigations and source readiness', async () => {
    await open()
    for (const heading of ['Regional activity', 'Open alerts', 'Cases and reports', 'Recent investigations']) {
      expect(screen.getByRole('heading', { name: heading })).toBeTruthy()
    }
    expect(screen.getByRole('link', { name: /Start investigation/ }).getAttribute('href')).toBe('/map')
    const regional = screen.getByRole('link', { name: /Regional activity/ })
    expect(regional.getAttribute('href')).toBe('/map')
    expect(within(regional).getByText('4 vessels in the current view')).toBeTruthy()
    expect(within(regional).getByText(/Source not reported/)).toBeTruthy()
    expect(within(screen.getByRole('link', { name: /Open alerts/ })).getByText('2 open stored alerts')).toBeTruthy()
    expect(screen.getByText('Harbour review')).toBeTruthy()
    expect(screen.getByText('local vessel records')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/demo path|walkthrough|presenter/i)
  })

  it('shows honest unknown states instead of inventing zero when an endpoint fails', async () => {
    vesselsApi.list.mockRejectedValue(new Error('offline'))
    alertsApi.stored.mockRejectedValue(new Error('offline'))
    casesApi.list.mockRejectedValue(new Error('offline'))
    reportsApi.list.mockRejectedValue(new Error('offline'))
    sourcesApi.health.mockRejectedValue(new Error('offline'))
    await open()
    expect(within(screen.getByRole('link', { name: /Regional activity/ })).getByText('Count not loaded')).toBeTruthy()
    expect(within(screen.getByRole('link', { name: /Open alerts/ })).getByText('Count not loaded')).toBeTruthy()
    expect(within(screen.getByRole('link', { name: /Cases and reports/ })).getByText('Count not loaded')).toBeTruthy()
    expect(screen.getAllByText('Source status unavailable').length).toBeGreaterThan(0)
    expect(document.body.textContent).not.toMatch(/0 vessels|0 open stored alerts|0 cases/)
  })

  it('shows empty states, not fake activity, when endpoints return nothing', async () => {
    vesselsApi.list.mockResolvedValue({ ...fleet, vessels: [] })
    alertsApi.stored.mockResolvedValue({ alerts: [], total: 0 })
    casesApi.list.mockResolvedValue([])
    reportsApi.list.mockResolvedValue([])
    await open()
    expect(screen.getByText('No vessels in the current view')).toBeTruthy()
    expect(screen.getByText('No open stored alerts')).toBeTruthy()
    expect(screen.getByText(/No cases yet/)).toBeTruthy()
    expect(screen.getByText('No investigations have been opened.')).toBeTruthy()
  })

  it('shows loading states while counts are requested', async () => {
    vesselsApi.list.mockReturnValue(new Promise(() => {}))
    alertsApi.stored.mockReturnValue(new Promise(() => {}))
    casesApi.list.mockReturnValue(new Promise(() => {}))
    reportsApi.list.mockReturnValue(new Promise(() => {}))
    sourcesApi.health.mockReturnValue(new Promise(() => {}))
    await open()
    expect(screen.getAllByText(/Loading/).length).toBeGreaterThanOrEqual(4)
  })
})
