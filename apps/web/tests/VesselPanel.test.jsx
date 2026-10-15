import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import VesselPanel from '@/features/map/VesselPanel'
import { fleet, httpError, networkError, seaPearlDetail } from './fixtures'

function show(props) {
  const calls = { closed: 0, retried: 0 }
  render(
    <MemoryRouter>
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
    </MemoryRouter>,
  )
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
})
