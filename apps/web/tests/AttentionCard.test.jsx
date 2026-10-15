import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import AttentionCard from '@/features/map/AttentionCard'
import { fleet, networkError, nila, seaPearl } from './fixtures'

const LOADED_AT = new Date('2026-10-13T13:03:27Z') // 18:33 IST

function show(props) {
  const calls = { selected: [], retried: 0 }
  render(
    <MemoryRouter>
      <AttentionCard
        vessels={[]}
        allVessels={[]}
        selectedMmsi={null}
        onSelect={(mmsi) => calls.selected.push(mmsi)}
        loading={false}
        error={null}
        updatedAt={LOADED_AT}
        onRetry={() => (calls.retried += 1)}
        {...props}
      />
    </MemoryRouter>,
  )
  return calls
}

describe('AttentionCard', () => {
  it('says vessels are loading before the first answer', () => {
    show({ loading: true, updatedAt: null })

    expect(screen.getByText('Loading vessels…')).toBeTruthy()
  })

  it('says nothing needs attention when vessels are reporting and none is risky', () => {
    show({ allVessels: [nila] })

    expect(screen.getByText('Nothing needs attention in the last 24 h.')).toBeTruthy()
  })

  it('says no vessel has reported when the fleet is empty, not that nothing needs attention', () => {
    show({ allVessels: [] })

    expect(screen.getByText('No vessel has reported in the last 24 h.')).toBeTruthy()
    expect(screen.queryByText(/Nothing needs attention/)).toBeNull()
  })

  it('does not give the all-clear when the vessel list never loaded', () => {
    show({ error: networkError(), updatedAt: null })

    expect(screen.queryByText(/Nothing needs attention/)).toBeNull()
    expect(screen.getByRole('alert').textContent).toContain("Can't load vessels")
  })

  it('shows no count when the vessel list never loaded', () => {
    show({ error: networkError(), updatedAt: null })

    expect(screen.getByRole('heading', { name: 'Needs attention' }).parentElement.textContent).not.toMatch(/\d/)
  })

  it('offers to try again when the vessel list never loaded', () => {
    const calls = show({ error: networkError(), updatedAt: null })

    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

    expect(calls.retried).toBe(1)
  })

  it('keeps the last list and says when it is from, when a refresh fails', () => {
    show({ vessels: [seaPearl], allVessels: fleet.vessels, error: networkError() })

    expect(screen.getByText('Sea Pearl II went dark for 6.4 h')).toBeTruthy()
    expect(screen.getByRole('alert').textContent).toContain('Not updating. This list is from 18:33.')
  })

  it('does not give the all-clear from an out-of-date list', () => {
    show({ allVessels: [nila], error: networkError() })

    expect(screen.getByText('Nothing needed attention at 18:33.')).toBeTruthy()
    expect(screen.queryByText(/Nothing needs attention/)).toBeNull()
  })

  it('still lists a vessel whose level it does not know', () => {
    show({ vessels: [{ ...seaPearl, level: 'critical', reasons: [] }], allVessels: fleet.vessels })

    expect(screen.getByText('Sea Pearl II went dark for 6.4 h')).toBeTruthy()
  })

  it('selects the vessel that is clicked', () => {
    const calls = show({ vessels: [seaPearl], allVessels: fleet.vessels })

    fireEvent.click(screen.getByRole('button', { name: /Sea Pearl II/ }))

    expect(calls.selected).toEqual([419007431])
  })
})
