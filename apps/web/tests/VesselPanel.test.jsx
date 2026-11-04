import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import VesselPanel from '@/features/map/VesselPanel'
import { reportsApi } from '@/lib/api'
import { fleet, httpError, networkError, regionalEnvironment, seaPearlDetail } from './fixtures'

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    reportsApi: {
      ...actual.reportsApi,
      create: vi.fn(),
    },
  }
})

function show(props, initialEntries = ['/']) {
  const calls = { closed: 0, retried: 0 }
  let currentPath = ''
  function PathWatcher() {
    const loc = useLocation()
    currentPath = loc.pathname + loc.search
    return null
  }
  render(
    <MemoryRouter initialEntries={initialEntries}>
      <PathWatcher />
      <Routes>
        <Route path="/reports" element={<div data-testid="reports-page">Reports page</div>} />
        <Route path="/vessels/:mmsi" element={<div data-testid="evidence-page">Evidence page</div>} />
        <Route
          path="*"
          element={
            <VesselPanel
              detail={null}
              mmsi={419007431}
              error={null}
              loading={false}
              onClose={() => (calls.closed += 1)}
              onRetry={() => (calls.retried += 1)}
              names={fleet.vessels}
              {...props}
            />
          }
        />
      </Routes>
    </MemoryRouter>,
  )
  calls.getPath = () => currentPath
  return calls
}

describe('VesselPanel', () => {
  it('explains the score of a loaded vessel', () => {
    show({ detail: seaPearlDetail })

    expect(screen.getByRole('heading', { name: 'Sea Pearl II' })).toBeTruthy()
    expect(screen.getByText('Met Hai Feng 818')).toBeTruthy()
    expect(screen.getByText('What would clear it').parentElement.textContent).toContain('Score drops to 0.32, below the alert line, if AIS comes back on.')
  })

  it('says the vessel has no positions when the API answers 404', () => {
    show({ mmsi: 999, error: httpError(404) })

    expect(screen.getByRole('alert').textContent).toContain('No positions for MMSI 999 in the last 24 h.')
  })

  it('blames the connection, not the vessel, when the API cannot be reached', () => {
    show({ error: networkError() })

    expect(screen.getByRole('alert').textContent).toContain("Can't reach the API")
    expect(screen.queryByText(/No positions/)).toBeNull()
  })

  it('blames the connection when the API answers with a server error', () => {
    show({ error: httpError(500) })

    expect(screen.getByRole('alert').textContent).toContain("Can't reach the API")
  })

  it('offers to try again when the API cannot be reached', () => {
    const calls = show({ error: networkError() })

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(calls.retried).toBe(1)
  })

  it('shows loading, not the old error, while a retry is in flight', () => {
    show({ error: networkError(), loading: true })

    expect(screen.getByText('Loading vessel…')).toBeTruthy()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('can be closed from the error state', () => {
    const calls = show({ error: httpError(404) })

    fireEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect(calls.closed).toBe(1)
  })

  it('still lists a check whose status it does not know', () => {
    const checks = [{ key: 'weather', label: 'Bad weather', status: 'downgraded', detail: 'Cyclone warning in force' }]
    show({ detail: { ...seaPearlDetail, checks } })

    expect(screen.getByText('Bad weather')).toBeTruthy()
    expect(screen.getByLabelText('Unknown result')).toBeTruthy()
  })

  it('still shows a vessel whose level it does not know', () => {
    show({ detail: { ...seaPearlDetail, level: 'critical' } })

    expect(screen.getByRole('heading', { name: 'Sea Pearl II' })).toBeTruthy()
    expect(screen.getAllByText('critical').length).toBeGreaterThan(0)
  })

  it('shows source not reported when vessel has no data_mode', () => {
    show({ detail: seaPearlDetail })

    expect(screen.getByText('AIS data: Source not reported')).toBeTruthy()
  })

  it('shows cached data and no live data when vessel has cached data_mode', () => {
    show({ detail: { ...seaPearlDetail, data_mode: 'cached' } })

    expect(screen.getByText('AIS data: Cached data')).toBeTruthy()
    expect(screen.queryByText(/Live data/)).toBeNull()
  })

  it('shows formatted date and timezone on last position and does not duplicate IST (J)', () => {
    show({ detail: seaPearlDetail })

    const panel = screen.getByRole('complementary')
    expect(panel.textContent).toContain('Last position 13 Oct 2026, 12:10 IST')
    expect(panel.textContent).not.toContain('IST IST')
  })

  it('calls create once on a double click and navigates to the new ID', async () => {
    let resolveCreate
    reportsApi.create.mockReturnValue(
      new Promise((resolve) => {
        resolveCreate = resolve
      }),
    )
    const { getPath } = show({ detail: seaPearlDetail })

    const draftBtn = screen.getByRole('button', { name: 'Draft report' })
    fireEvent.click(draftBtn)
    fireEvent.click(draftBtn)

    expect(reportsApi.create).toHaveBeenCalledTimes(1)
    expect(reportsApi.create).toHaveBeenCalledWith(419007431)
    expect(draftBtn.disabled).toBe(true)

    await act(async () => {
      resolveCreate({ id: 88 })
    })

    expect(getPath()).toBe('/reports?id=88')
    expect(screen.getByTestId('reports-page')).toBeTruthy()
  })

  it('shows error on report creation failure and does not navigate', async () => {
    reportsApi.create.mockRejectedValue(new Error('Network failure'))
    const { getPath } = show({ detail: seaPearlDetail })

    const draftBtn = screen.getByRole('button', { name: 'Draft report' })
    await act(async () => {
      fireEvent.click(draftBtn)
    })

    expect(reportsApi.create).toHaveBeenCalledTimes(1)
    expect(getPath()).toBe('/')
    expect(screen.queryByTestId('reports-page')).toBeNull()
    expect(screen.getByRole('alert').textContent).toContain('Could not create an evidence snapshot')
    expect(screen.getByRole('link', { name: 'Open evidence' })).toBeTruthy()
  })

  it('links to environmental value with date and context-only wording (B-08)', () => {
    show({ detail: seaPearlDetail, environmental: regionalEnvironment })

    const link = screen.getByRole('link', { name: /Regional ocean context \(13 Oct 2026, 11:30 IST\)/ })
    expect(link).toBeTruthy()
    expect(link.getAttribute('href')).toBe('/map#environmental-context')
    expect(link.textContent).not.toMatch(/caused by|because of/i)
  })

  it('shows fallback link when environmental data is unavailable (B-08)', () => {
    show({ detail: seaPearlDetail, environmental: null })

    const link = screen.getByRole('link', { name: /Regional ocean context \(Environmental data not available\)/ })
    expect(link).toBeTruthy()
    expect(link.getAttribute('href')).toBe('/map#environmental-context')
  })
})
