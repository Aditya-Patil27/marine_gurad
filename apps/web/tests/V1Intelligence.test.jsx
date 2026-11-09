import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DetectionsPage from '@/pages/DetectionsPage'
import OceanPage from '@/pages/OceanPage'
import { boundariesApi, casesApi, oceanApi, sarApi } from '@/lib/api'

vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  oceanApi: { observations: vi.fn(), baseline: vi.fn(), scanPlan: vi.fn() },
  boundariesApi: { list: vi.fn() },
  sarApi: { detections: vi.fn(), create: vi.fn() },
  casesApi: { createFromSar: vi.fn() },
}))

beforeEach(() => {
  vi.resetAllMocks()
  oceanApi.observations.mockResolvedValue({ status: 'available', source: 'Copernicus', dataset: 'sst-v1', unit: '°C', values: [{ observed_at: '2026-10-20T00:00:00Z', value: 29.4 }] })
  oceanApi.baseline.mockResolvedValue({ status: 'available', evaluation: { status: 'descriptive_only' }, factors: [{ key: 'activity', label: 'Recent activity proxy' }], limitations: 'Not a crime classifier.' })
  sarApi.detections.mockResolvedValue([{ id: 'd1', scene_id: 'S1-001', source: 'Sentinel-1', observed_at: '2026-11-01T00:00:00Z', latitude: 8.7, longitude: 78.3, association_state: 'ambiguous', candidates: [{}, {}] }])
  boundariesApi.list.mockResolvedValue({ items: [{ id: 'b1', name: 'Marine National Park', publisher: 'Official source', citation: 'Gazette 1', restriction: { description: 'Activities require verification.', verification_status: 'source_cited' } }], limitations: 'Verify current legal applicability.' })
})

describe('v1 intelligence surfaces', () => {
  it('shows dated ocean data and prepares a bounded scan plan', async () => {
    oceanApi.scanPlan.mockResolvedValue({ status: 'planned', ranked_cells: [{ cell_id: '8.5:78.2', rank: 1, score: 0.8 }], reserve_fraction: 0.2, limitations: 'Does not task a satellite.' })
    render(<MemoryRouter><OceanPage /></MemoryRouter>)
    expect(await screen.findByText('Copernicus')).toBeTruthy()
    expect(screen.getByText('Not a crime classifier.')).toBeTruthy()
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Prepare plan' })) })
    expect(oceanApi.scanPlan).toHaveBeenCalledWith(8, 0.2)
    expect(screen.getByText('8.5:78.2')).toBeTruthy()
    expect(screen.getByText('Does not task a satellite.')).toBeTruthy()
  })

  it('keeps ambiguous SAR identity explicit and opens an unidentified-object case', async () => {
    casesApi.createFromSar.mockResolvedValue({ id: 'case-sar-1' })
    render(<MemoryRouter><DetectionsPage /></MemoryRouter>)
    expect(await screen.findByText('S1-001')).toBeTruthy()
    expect(screen.getByText(/2 plausible AIS candidates/)).toBeTruthy()
    expect(screen.getByText('Marine National Park')).toBeTruthy()
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Open unidentified-object case' })) })
    expect(casesApi.createFromSar).toHaveBeenCalledWith('d1', 'Unidentified SAR observation · S1-001')
    expect(screen.getByRole('link', { name: /Open case case-sar-1/ })).toBeTruthy()
  })
})
