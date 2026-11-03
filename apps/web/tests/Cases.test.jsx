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
  vi.resetAllMocks()
  weatherApi.vessel.mockResolvedValue({ status: 'unavailable', reason: 'Weather service unavailable.' })
  sarApi.detections.mockResolvedValue([])
})

describe('Cases / EvidencePage & ReportsPage', () => {
  it('shows failure when SAR request fails, repeats only SAR on retry, and shows data when retry succeeds', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    sarApi.detections.mockRejectedValueOnce(networkError())

    await openEvidence('419007431')

    expect(screen.getByRole('alert').textContent).toContain("SAR detections didn't load, so a match can't be ruled out.")
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

  it('shows the box unticked on report 2 and disables sign-off when officer ticked report 1 then opened report 2', async () => {
    reportsApi.list.mockResolvedValue([sampleReport, sampleReport2])

    await openReports('/reports')

    const officerInput = screen.getByLabelText(/Officer name/)
    const checkbox = screen.getByLabelText(/I reviewed the evidence/)
    const signBtn = screen.getByRole('button', { name: 'Record sign-off' })

    fireEvent.change(officerInput, { target: { value: 'Officer Rao' } })
    fireEvent.click(checkbox)
    expect(checkbox.checked).toBe(true)
    expect(signBtn.disabled).toBe(false)

    const report2Link = screen.getByRole('link', { name: /#2/ })
    await act(async () => {
      fireEvent.click(report2Link)
    })

    const checkboxReport2 = screen.getByLabelText(/I reviewed the evidence/)
    const signBtnReport2 = screen.getByRole('button', { name: 'Record sign-off' })

    expect(checkboxReport2.checked).toBe(false)
    expect(signBtnReport2.disabled).toBe(true)
  })

  it('shows the box unticked on report 1 when officer ticked report 1, opened report 2, then returned to report 1', async () => {
    reportsApi.list.mockResolvedValue([sampleReport, sampleReport2])

    await openReports('/reports')

    const checkbox = screen.getByLabelText(/I reviewed the evidence/)
    fireEvent.click(checkbox)
    expect(checkbox.checked).toBe(true)

    const report2Link = screen.getByRole('link', { name: /#2/ })
    await act(async () => {
      fireEvent.click(report2Link)
    })

    const report1Link = screen.getByRole('link', { name: /#1/ })
    await act(async () => {
      fireEvent.click(report1Link)
    })

    const checkboxReport1Again = screen.getByLabelText(/I reviewed the evidence/)
    expect(checkboxReport1Again.checked).toBe(false)
  })

  it('does not show the rejection message on report 2 after sign-off on report 1 is rejected', async () => {
    reportsApi.list.mockResolvedValue([sampleReport, sampleReport2])
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

    const report2Link = screen.getByRole('link', { name: /#2/ })
    await act(async () => {
      fireEvent.click(report2Link)
    })

    expect(screen.queryByText(/The API rejected this sign-off/)).toBeNull()
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('keeps the officer name when officer types on report 1 then opens report 2', async () => {
    reportsApi.list.mockResolvedValue([sampleReport, sampleReport2])

    await openReports('/reports')

    const officerInput = screen.getByLabelText(/Officer name/)
    fireEvent.change(officerInput, { target: { value: 'Officer Rao' } })

    const report2Link = screen.getByRole('link', { name: /#2/ })
    await act(async () => {
      fireEvent.click(report2Link)
    })

    const officerInputReport2 = screen.getByLabelText(/Officer name/)
    expect(officerInputReport2.value).toBe('Officer Rao')
  })

  it('keeps message, name and tick when sign-off is rejected and officer stays on that report', async () => {
    reportsApi.list.mockResolvedValue([sampleReport, sampleReport2])
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

    fireEvent.change(officerInput, { target: { value: 'Officer Rao' } })
    fireEvent.click(checkbox)

    await act(async () => {
      fireEvent.click(signBtn)
    })

    expect(screen.getByRole('alert').textContent).toContain('The API rejected this sign-off. Check the officer name and try again.')
    expect(screen.getByLabelText(/Officer name/).value).toBe('Officer Rao')
    expect(screen.getByLabelText(/I reviewed the evidence/).checked).toBe(true)
  })

  it('shows report 2 and calls sign with id 2 when visited at /reports?id=2', async () => {
    reportsApi.list.mockResolvedValue([sampleReport, sampleReport2])

    await openReports('/reports?id=2')

    expect(screen.getByText('REPORT #2 · Awaiting review')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Vessel investigation: Lakshmi Matha' })).toBeTruthy()

    const officerInput = screen.getByLabelText(/Officer name/)
    const checkbox = screen.getByLabelText(/I reviewed the evidence/)
    const signBtn = screen.getByRole('button', { name: 'Record sign-off' })

    reportsApi.sign.mockResolvedValueOnce({ ...sampleReport2, signed_at: '2026-11-03T10:00:00Z', signed_by: 'Officer Rao' })
    reportsApi.list.mockResolvedValueOnce([sampleReport, { ...sampleReport2, signed_at: '2026-11-03T10:00:00Z', signed_by: 'Officer Rao' }])

    fireEvent.change(officerInput, { target: { value: 'Officer Rao' } })
    fireEvent.click(checkbox)

    await act(async () => {
      fireEvent.click(signBtn)
    })

    expect(reportsApi.sign).toHaveBeenCalledWith(2, 'Officer Rao', true)
  })

  it('shows AIS data source not reported for vessel with no data_mode in evidence', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)

    await openEvidence('419007431')

    expect(screen.getByText('AIS data: Source not reported')).toBeTruthy()
  })

  it('shows weather source, note, and historical data mode when weather is available', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    const weatherData = {
      status: 'available',
      wind_kn: 14,
      wave_m: 1.8,
      time_utc: '2026-10-13T06:40:48Z',
      source: 'INCOIS WRF-Chem',
      note: 'Nearshore wave buoy reading.',
      data_mode: 'historical',
    }
    weatherApi.vessel.mockResolvedValue(weatherData)

    await openEvidence('419007431')

    expect(screen.getByText(/INCOIS WRF-Chem/)).toBeTruthy()
    expect(screen.getByText(/Nearshore wave buoy reading\./)).toBeTruthy()
    expect(screen.getByText(/Weather data: Historical data/)).toBeTruthy()
  })

  it('shows source not reported and weather data source not reported with no undefined when fields are missing', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    const weatherData = {
      status: 'available',
      wind_kn: 12,
      wave_m: 1.2,
      time_utc: '2026-10-13T06:40:48Z',
    }
    weatherApi.vessel.mockResolvedValue(weatherData)

    await openEvidence('419007431')

    expect(screen.getByText(/Source: Source not reported/)).toBeTruthy()
    expect(screen.getByText(/Weather data: Source not reported/)).toBeTruthy()
    expect(screen.queryByText(/undefined/)).toBeNull()
  })

  it('shows the reason and no weather data label when weather is unavailable', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    weatherApi.vessel.mockResolvedValue({
      status: 'unavailable',
      reason: 'Weather service connection timed out.',
    })

    await openEvidence('419007431')

    expect(screen.getByText(/Weather service connection timed out\./)).toBeTruthy()
    expect(screen.queryByText(/Weather data:/)).toBeNull()
  })

  it('shows synthetic SAR data label and candidate match text on evidence page', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    sarApi.detections.mockResolvedValue([
      {
        id: 'det-synth-1',
        source: 'Sentinel-1 Simulated',
        scene_id: 'S1A_SIM_2026',
        matched_mmsi: 419007431,
        match_distance_m: 350,
        data_mode: 'synthetic',
      },
    ])

    await openEvidence('419007431')

    expect(screen.getByText(/SAR data: Synthetic data/)).toBeTruthy()
    expect(screen.getByText(/Candidate match, not confirmed identity\./)).toBeTruthy()
  })

  it('shows cached AIS data label in report for snapshot with cached data_mode', async () => {
    const reportWithCachedSnapshot = {
      ...sampleReport,
      snapshot: {
        ...seaPearlDetail,
        data_mode: 'cached',
      },
    }
    reportsApi.list.mockResolvedValue([reportWithCachedSnapshot])

    await openReports('/reports')

    expect(screen.getByText('AIS data: Cached data')).toBeTruthy()
  })

  it('shows source not reported for SAR candidate in report with no data_mode', async () => {
    const reportWithSar = {
      ...sampleReport,
      snapshot: {
        ...seaPearlDetail,
        sar_candidates: [
          {
            id: 'sar-1',
            source: 'Sentinel-1',
            scene_id: 'S1A_IW_GRDH_1SDV',
            observed_at: '2026-10-13T06:40:48Z',
            match_distance_m: 520,
          },
        ],
      },
    }
    reportsApi.list.mockResolvedValue([reportWithSar])

    await openReports('/reports')

    expect(screen.getByText(/SAR data: Source not reported/)).toBeTruthy()
    expect(screen.getByText(/Identity not confirmed\./)).toBeTruthy()
  })

  it('shows formatted date and timezone for last observed when evidence opens (A)', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    await openEvidence('419007431')
    expect(screen.getByText(/Last observed 13 Oct 2026, 12:10 IST/)).toBeTruthy()
  })

  it('formats weather observation time and omits raw time_utc string (B)', async () => {
    vesselsApi.get.mockResolvedValue(seaPearlDetail)
    weatherApi.vessel.mockResolvedValue({
      status: 'available',
      wind_kn: 14,
      wave_m: 1.8,
      time_utc: '2026-10-13T06:40:48Z',
      source: 'INCOIS WRF-Chem',
      data_mode: 'historical',
    })
    await openEvidence('419007431')
    expect(screen.getByText(/at 13 Oct 2026, 12:10 IST/)).toBeTruthy()
    expect(screen.queryByText(/2026-10-13T06:40:48Z/)).toBeNull()
  })

  it('formats last observed on report and shows no raw last_seen string outside source snapshot (C)', async () => {
    reportsApi.list.mockResolvedValue([sampleReport])
    await openReports('/reports')
    expect(screen.getByText(/Last observed 13 Oct 2026, 12:10 IST/)).toBeTruthy()
    const article = screen.getByRole('article')
    const details = article.querySelector('details')
    const textWithoutDetails = Array.from(article.childNodes)
      .filter((n) => n !== details)
      .map((n) => n.textContent)
      .join(' ')
    expect(textWithoutDetails).not.toContain('2026-10-13T06:40:48Z')
  })

  it('formats SAR candidate observed_at and omits raw timezone offset (D)', async () => {
    const reportWithSar = {
      ...sampleReport,
      snapshot: {
        ...seaPearlDetail,
        sar_candidates: [
          {
            id: 'sar-1',
            source: 'Sentinel-1',
            scene_id: 'S1A_IW_GRDH_1SDV',
            observed_at: '2026-10-13T06:40:48+00:00',
            match_distance_m: 520,
          },
        ],
      },
    }
    reportsApi.list.mockResolvedValue([reportWithSar])
    await openReports('/reports')
    const sarLine = screen.getByText(/SAR candidate:/).closest('div')
    expect(sarLine.textContent).toContain('13 Oct 2026, 12:10 IST')
    expect(sarLine.textContent).not.toContain('+00:00')
  })

  it('formats signed_at timestamp on signed report (E)', async () => {
    const signedReport = {
      ...sampleReport,
      signed_at: '2026-11-03T10:00:00Z',
      signed_by: 'Officer Rao',
    }
    reportsApi.list.mockResolvedValue([signedReport])
    await openReports('/reports')
    expect(screen.getByText('Signed by Officer Rao at 3 Nov 2026, 15:30 IST')).toBeTruthy()
  })

  it('shows different dates in report list links for two reports of one vessel (F)', async () => {
    const report1 = {
      ...sampleReport,
      id: 1,
      created_at: '2026-10-13T06:40:48Z',
    }
    const report2 = {
      ...sampleReport,
      id: 2,
      created_at: '2026-10-14T06:40:48Z',
    }
    reportsApi.list.mockResolvedValue([report1, report2])
    await openReports('/reports')
    const link1 = screen.getByRole('link', { name: /#1/ })
    const link2 = screen.getByRole('link', { name: /#2/ })
    expect(link1.textContent).toContain('13 Oct 2026')
    expect(link2.textContent).toContain('14 Oct 2026')
    expect(link1.textContent).not.toEqual(link2.textContent)
  })

  it('shows date and awaiting review status on unsigned report list link (G)', async () => {
    const unsignedReport = {
      ...sampleReport,
      created_at: '2026-10-13T06:40:48Z',
      signed_at: null,
    }
    reportsApi.list.mockResolvedValue([unsignedReport])
    await openReports('/reports')
    const link = screen.getByRole('link', { name: /#1/ })
    expect(link.textContent).toContain('13 Oct 2026, 12:10 IST · Awaiting review')
  })

  it('shows signed status on signed report list link (H)', async () => {
    const signedReport = {
      ...sampleReport,
      created_at: '2026-10-13T06:40:48Z',
      signed_at: '2026-11-03T10:00:00Z',
      signed_by: 'Officer Rao',
    }
    reportsApi.list.mockResolvedValue([signedReport])
    await openReports('/reports')
    const link = screen.getByRole('link', { name: /#1/ })
    expect(link.textContent).toContain('· Signed')
  })

  it('shows Time not reported · Awaiting review and draws page when report has no created_at (I)', async () => {
    const noCreatedReport = {
      ...sampleReport,
      created_at: null,
      signed_at: null,
    }
    reportsApi.list.mockResolvedValue([noCreatedReport])
    await openReports('/reports')
    const link = screen.getByRole('link', { name: /#1/ })
    expect(link.textContent).toContain('Time not reported · Awaiting review')
    expect(screen.getByRole('heading', { name: 'Incident reports' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Vessel investigation: Sea Pearl II' })).toBeTruthy()
  })
})
