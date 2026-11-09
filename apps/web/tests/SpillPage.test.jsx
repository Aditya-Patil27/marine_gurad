import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SpillPage from '@/pages/SpillPage'
import { spillApi } from '@/lib/api'

vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  spillApi: { capabilities: vi.fn(), jobs: vi.fn(), create: vi.fn() },
}))

const unavailable = {
  status: 'unavailable', engine: 'PyGNOME', engine_version: null,
  forcing: { wind: 'not_configured', current: 'not_configured' }, supported_modes: [],
  reason: 'PyGNOME and compatible wind/current forcing are not installed.',
  limitations: 'No fallback trajectory is generated; missing current data is never treated as zero flow.',
}

async function open() {
  render(<MemoryRouter><SpillPage /></MemoryRouter>)
  await act(async () => {})
}

beforeEach(() => {
  vi.resetAllMocks()
  spillApi.capabilities.mockResolvedValue(unavailable)
  spillApi.jobs.mockResolvedValue({ items: [], capability: unavailable })
})

describe('spill scenario jobs', () => {
  it('shows real capability and disables submission without an engine or forcing', async () => {
    await open()
    expect(screen.getByRole('heading', { name: 'Spill scenarios' })).toBeTruthy()
    expect(screen.getByText('Scenario engine unavailable')).toBeTruthy()
    expect(screen.getByText(/No fallback trajectory is generated/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Run scenario' }).disabled).toBe(true)
    expect(document.body.textContent).not.toMatch(/training simulator|illustrative drift path/i)
  })

  it('submits the bounded job contract when the engine is available', async () => {
    spillApi.capabilities.mockResolvedValue({ status: 'available', engine: 'PyGNOME', engine_version: '1.0', forcing: { wind: 'available', current: 'cached' }, supported_modes: ['real', 'cached'] })
    spillApi.create.mockResolvedValue({ id: 'spill-1', state: 'queued' })
    await open()
    fireEvent.change(screen.getByLabelText('Release time (UTC)'), { target: { value: '2026-11-09T06:00' } })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Run scenario' })) })
    expect(spillApi.create).toHaveBeenCalledWith({ longitude: 78.35, latitude: 8.75, release_at: '2026-11-09T06:00:00.000Z', duration_hours: 24, particle_count: 500, mode: 'real' })
    expect(screen.getByText('Scenario job spill-1 queued.')).toBeTruthy()
  })
})
