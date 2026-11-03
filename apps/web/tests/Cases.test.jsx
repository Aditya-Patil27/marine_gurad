import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EvidencePage, ReportsPage } from '@/pages/Cases'
import { reportsApi, sarApi, vesselsApi, weatherApi } from '@/lib/api'
import { httpError, networkError, seaPearlDetail } from './fixtures'

vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  vesselsApi: { list: vi.fn(), get: vi.fn() },
  reportsApi: { list: vi.fn(), create: vi.fn(), sign: vi.fn() },
  weatherApi: { vessel: vi.fn() },
  sarApi: { detections: vi.fn() },
}))

const sampleReport = {
  id: 1,
  mmsi: 419007431,
  integrity_ok: true,
  sha256: 'a1b2c3d4e5f6',
  signed_at: null,
  signed_by: null,
  snapshot: seaPearlDetail,
}

const sampleReport2 = {
  id: 2,
  mmsi: 419001265,
  integrity_ok: true,
  sha256: 'b2c3d4e5f6a1',
  signed_at: null,
  signed_by: null,
  snapshot: { ...seaPearlDetail, mmsi: 419001265, name: 'LAKSHMI MATHA' },
}

async function openEvidence(mmsi = '419007431') {
  render(
    <MemoryRouter initialEntries={[`/vessels/${mmsi}`]}>
      <Routes>
        <Route path="/vessels/:mmsi" element={<EvidencePage />} />
      </Routes>
    </MemoryRouter>,
  )
  await act(async () => {})
}

async function openReports(url = '/reports') {
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/reports" element={<ReportsPage />} />
      </Routes>
    </MemoryRouter>,
  )
  await act(async () => {})
}

beforeEach(() => {
  vi.clearAllMocks()
  weatherApi.vessel.mockResolvedValue({ status: 'unavailable', reason: 'Weather service unavailable.' })
  sarApi.detections.mockResolvedValue([])
})

describe('Cases / EvidencePage & ReportsPage', () => {
  it('shows failure when SAR request fails, repeats only SAR on retry, and shows data when retry succeeds', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    sarApi.detections.mockRejectedValueOnce(networkError())

    await openEvidence('419007431')

    expect(screen.getByText("SAR detections didn't load, so a match can't be ruled out.")).toBeTruthy()
    expect(screen.queryByText(/No candidate/)).toBeNull()

    const retryBtn = screen.getByRole('button', { name: 'Try again' })
    expect(retryBtn).toBeTruthy()
    expect(vesselsApi.get).toHaveBeenCalledTimes(1)
    expect(sarApi.detections).toHaveBeenCalledTimes(1)

    const matchDetection = {
      id: 'det-1',
      source: 'Sentinel-1',
      scene_id: 'S1A_IW_GRDH_1SDV',
      matched_mmsi: 419007431,
      match_distance_m: 450,
    }
    sarApi.detections.mockResolvedValueOnce([matchDetection])

    await act(async () => {
      fireEvent.click(retryBtn)
    })

    expect(sarApi.detections).toHaveBeenCalledTimes(2)
    expect(vesselsApi.get).toHaveBeenCalledTimes(1)
    expect(screen.getByText(/Sentinel-1 · S1A_IW_GRDH_1SDV · 450 m from AIS/)).toBeTruthy()
    expect(screen.queryByText("SAR detections didn't load, so a match can't be ruled out.")).toBeNull()
  })

  it('shows no candidate message when SAR request succeeds with no match for this vessel', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    sarApi.detections.mockResolvedValue([])

    await openEvidence('419007431')

    expect(screen.getByText('No candidate SAR detection recorded for this vessel.')).toBeTruthy()
    expect(screen.queryByText(/SAR detections didn't load/)).toBeNull()
  })

  it('shows no positions message and no try again button when vessel request returns 404', async () => {
    vesselsApi.get.mockRejectedValue(httpError(404))

    await openEvidence('999')

    expect(screen.getByRole('alert').textContent).toContain('No positions for MMSI 999 in the last 24 h.')
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
  })

  it('blames API and offers retry when vessel request fails any other way, and shows data when retry succeeds', async () => {
    vesselsApi.get.mockRejectedValueOnce(networkError())

    await openEvidence('419007431')

    expect(screen.getByRole('alert').textContent).toContain("Can't reach the API, so this vessel's evidence didn't load.")
    const retryBtn = screen.getByRole('button', { name: 'Try again' })
    expect(retryBtn).toBeTruthy()
    expect(vesselsApi.get).toHaveBeenCalledTimes(1)

    vesselsApi.get.mockResolvedValueOnce(seaPearlDetail)

    await act(async () => {
      fireEvent.click(retryBtn)
    })

    expect(vesselsApi.get).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('heading', { name: 'Sea Pearl II' })).toBeTruthy()
    expect(screen.queryByText(/Can't reach the API/)).toBeNull()
  })

  it('shows not found when report ID is not in the list while keeping report list visible', async () => {
    reportsApi.list.mockResolvedValue([sampleReport])

    await openReports('/reports?id=999')

    expect(screen.getByRole('alert').textContent).toContain('Report #999 was not found.')
    expect(screen.queryByText(/Vessel investigation:/)).toBeNull()
    expect(screen.queryByText('Officer name')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Record sign-off' })).toBeNull()
    expect(screen.getByRole('link', { name: /#1 · Sea Pearl II/ })).toBeTruthy()
  })

  it('shows the first report when visited with no report ID', async () => {
    reportsApi.list.mockResolvedValue([sampleReport, sampleReport2])

    await openReports('/reports')

    expect(screen.getByText('REPORT #1 · Awaiting review')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Vessel investigation: Sea Pearl II' })).toBeTruthy()
    expect(screen.getByText('Officer name')).toBeTruthy()
  })

  it('keeps report on screen with readable message when sign-off rejected with non-string detail, allowing correction and signing', async () => {
    reportsApi.list.mockResolvedValue([sampleReport])
    const validationError = Object.assign(new Error('Unprocessable Entity'), {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'officer'], msg: 'String should have at most 120 characters', type: 'string_too_long' },
          ],
        },
      },
    })
    reportsApi.sign.mockRejectedValueOnce(validationError)

    await openReports('/reports')

    const officerInput = screen.getByLabelText(/Officer name/)
    const checkbox = screen.getByLabelText(/I reviewed the evidence/)
    const signBtn = screen.getByRole('button', { name: 'Record sign-off' })

    fireEvent.change(officerInput, { target: { value: 'A'.repeat(121) } })
    fireEvent.click(checkbox)

    await act(async () => {
      fireEvent.click(signBtn)
    })

    expect(screen.getByRole('alert').textContent).toContain('The API rejected this sign-off. Check the officer name and try again.')
    expect(screen.getByRole('heading', { name: 'Vessel investigation: Sea Pearl II' })).toBeTruthy()

    reportsApi.sign.mockResolvedValueOnce({ ...sampleReport, signed_at: '2026-11-03T10:00:00Z', signed_by: 'Officer Rao' })
    reportsApi.list.mockResolvedValueOnce([{ ...sampleReport, signed_at: '2026-11-03T10:00:00Z', signed_by: 'Officer Rao' }])

    fireEvent.change(officerInput, { target: { value: 'Officer Rao' } })
    await act(async () => {
      fireEvent.click(signBtn)
    })

    expect(reportsApi.sign).toHaveBeenCalledWith(1, 'Officer Rao', true)
    expect(screen.queryByText(/The API rejected this sign-off/)).toBeNull()
  })

  it('shows string error message when sign-off is rejected and detail is a string', async () => {
    reportsApi.list.mockResolvedValue([sampleReport])
    const stringError = Object.assign(new Error('Bad Request'), {
      response: {
        status: 400,
        data: {
          detail: 'Sign-off blocked: hash mismatch',
        },
      },
    })
    reportsApi.sign.mockRejectedValueOnce(stringError)

    await openReports('/reports')

    const officerInput = screen.getByLabelText(/Officer name/)
    const checkbox = screen.getByLabelText(/I reviewed the evidence/)
    const signBtn = screen.getByRole('button', { name: 'Record sign-off' })

    fireEvent.change(officerInput, { target: { value: 'Officer Rao' } })
    fireEvent.click(checkbox)

    await act(async () => {
      fireEvent.click(signBtn)
    })

    expect(screen.getByRole('alert').textContent).toContain('Sign-off blocked: hash mismatch')
    expect(screen.getByRole('heading', { name: 'Vessel investigation: Sea Pearl II' })).toBeTruthy()
  })
})
