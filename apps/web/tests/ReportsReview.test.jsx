import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ReportsPage } from '@/pages/Cases'
import { reportsApi } from '@/lib/api'
import { seaPearlDetail } from './fixtures'

vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  reportsApi: {
    list: vi.fn(),
    listText: vi.fn(),
    get: vi.fn(),
    manifest: vi.fn(),
    exportPdf: vi.fn(),
    sign: vi.fn(),
    deliveries: vi.fn(),
    deliver: vi.fn(),
    submitDelivery: vi.fn(),
    create: vi.fn(),
    createEventOnly: vi.fn(),
  },
}))

const SHA = 'a'.repeat(64)

const report = {
  id: 7,
  mmsi: 419007431,
  sha256: SHA,
  integrity_ok: true,
  created_at: '2026-11-09T05:00:00Z',
  signed_at: null,
  signed_by: null,
  snapshot: {
    ...seaPearlDetail,
    evidence_basis: 'vessel_assessment',
    persisted_assessment: { id: 'assessment-1' },
  },
}

const approved = {
  ...report,
  signed_at: '2026-11-09T06:00:00Z',
  signed_by: 'Officer Rao',
}

const eventOnly = {
  id: 8,
  mmsi: 419001265,
  sha256: SHA,
  integrity_ok: true,
  created_at: '2026-11-09T05:00:00Z',
  signed_at: null,
  signed_by: null,
  snapshot: {
    evidence_basis: 'gfw_event_only',
    mmsi: 419001265,
    name: 'LAKSHMI MATHA',
    ais_evidence: { note: 'AIS evidence unavailable for this event.', limitation: 'No AIS track is claimed.' },
    assessment: { note: 'No assessment is attached.' },
    gfw_event_evidence: {
      sha256: SHA,
      snapshot: {
        source: 'Global Fishing Watch',
        dataset: 'public-global-fishing-events',
        event: { id: 'event-1', type: 'fishing', start: '2026-09-01T00:00:00Z', end: '2026-09-01T05:00:00Z', position: { lat: 8.8, lon: 78.9 }, vessel: { ssvid: '419001265' } },
        limitations: 'A historical inferred event point, not a track.',
      },
    },
    limitations: 'Event-only evidence does not prove illegal activity.',
  },
}

async function open(url = '/reports/7') {
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/reports/:id" element={<ReportsPage />} />
      </Routes>
    </MemoryRouter>,
  )
  await act(async () => {})
}

beforeEach(() => {
  vi.resetAllMocks()
  reportsApi.list.mockResolvedValue([report])
  reportsApi.get.mockResolvedValue(report)
  reportsApi.deliveries.mockResolvedValue({ items: [] })
})

describe('Reports review and export', () => {
  it('loads the report detail endpoint and shows basis, source, draft state and checksum', async () => {
    await open()

    expect(reportsApi.get).toHaveBeenCalledWith(7)
    expect(screen.getByRole('heading', { name: 'Vessel investigation: Sea Pearl II' })).toBeTruthy()
    expect(screen.getByText('Evidence basis: Vessel and assessment evidence')).toBeTruthy()
    expect(screen.getByText(/Persisted assessment: assessment-1/)).toBeTruthy()
    expect(screen.getByText(/Draft — awaiting approval/)).toBeTruthy()
    expect(screen.getByText(`SHA-256 ${SHA}`)).toBeTruthy()
    expect(screen.getByText(/integrity checksum, not a digital signature/)).toBeTruthy()
  })

  it('approves with reviewed true and the displayed checksum', async () => {
    reportsApi.sign.mockResolvedValue(approved)
    reportsApi.list.mockResolvedValue([approved])

    await open()

    fireEvent.click(screen.getByLabelText(/I reviewed the evidence/))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Record sign-off' })) })

    expect(reportsApi.sign).toHaveBeenCalledWith(7, 'Authenticated reviewer', true, SHA)
    expect(screen.getByText(/Signed by Officer Rao/)).toBeTruthy()
    expect(screen.getByText(/Approved/)).toBeTruthy()
  })

  it('keeps the draft and offers a reload when approval conflicts with a changed revision', async () => {
    reportsApi.sign.mockRejectedValue(Object.assign(new Error('Conflict'), {
      response: { status: 409, data: { detail: 'Report changed; reload before approving' } },
    }))
    reportsApi.get.mockResolvedValueOnce(report).mockResolvedValueOnce({ ...report, sha256: 'b'.repeat(64) })

    await open()

    fireEvent.click(screen.getByLabelText(/I reviewed the evidence/))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Record sign-off' })) })

    expect(screen.getByRole('alert').textContent).toContain('Report changed; reload before approving')
    expect(screen.getByRole('heading', { name: 'Vessel investigation: Sea Pearl II' })).toBeTruthy()
    expect(screen.getByText(/Draft — awaiting approval/)).toBeTruthy()

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Reload report' })) })
    expect(reportsApi.get).toHaveBeenCalledTimes(2)
  })

  it('offers the PDF only after approval and downloads the returned bytes', async () => {
    await open()
    expect(screen.queryByRole('button', { name: 'Export approved PDF' })).toBeNull()

    reportsApi.list.mockResolvedValue([approved])
    reportsApi.get.mockResolvedValue(approved)
    await open('/reports/7')

    let blob
    URL.createObjectURL = vi.fn((value) => { blob = value; return 'blob:pdf' })
    URL.revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      expect(this.download).toBe('samudrasense-report-7.pdf')
    })

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Export approved PDF' })) })

    expect(reportsApi.exportPdf).toHaveBeenCalledWith(7)
    expect(blob).toBeTruthy()
    expect(click).toHaveBeenCalledTimes(1)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:pdf')
    click.mockRestore()
  })

  it('queues the exact approved hash and explicitly submits it to the local sink', async () => {
    const queued = { id: 'delivery-1', state: 'queued', attempts: 0, created_at: '2026-11-09T07:00:00Z' }
    const submitted = { ...queued, state: 'submitted', attempts: 1 }
    reportsApi.list.mockResolvedValue([approved])
    reportsApi.get.mockResolvedValue(approved)
    reportsApi.deliveries.mockResolvedValueOnce({ items: [] }).mockResolvedValueOnce({ items: [queued] }).mockResolvedValueOnce({ items: [submitted] })
    reportsApi.deliver.mockResolvedValue(queued)
    reportsApi.submitDelivery.mockResolvedValue(submitted)
    await open()

    fireEvent.change(screen.getByLabelText('Local sink recipients'), { target: { value: 'watch@example.test' } })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Queue approved version' })) })
    expect(reportsApi.deliver).toHaveBeenCalledWith(7, SHA, ['watch@example.test'], expect.any(String))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Submit to local sink' })) })
    expect(reportsApi.submitDelivery).toHaveBeenCalledWith('delivery-1')
    expect(screen.getByRole('status').textContent).toContain('not received or read')
  })

  it('downloads the manifest canonical JSON unchanged', async () => {
    const canonical = '{"mmsi":419007431,"score":0.9}'
    reportsApi.manifest.mockResolvedValue({
      report_id: 7,
      canonical_json: canonical,
      canonical_sha256: SHA,
      checksum_note: 'SHA-256 is an integrity checksum.',
      evidence_references: [],
    })
    let blob
    URL.createObjectURL = vi.fn((value) => { blob = value; return 'blob:manifest' })
    URL.revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      expect(this.download).toBe('samudrasense-report-7-manifest.json')
    })

    await open()
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Download manifest (canonical JSON)' })) })

    expect(reportsApi.manifest).toHaveBeenCalledWith(7)
    expect(await blob.text()).toBe(canonical)
    click.mockRestore()
  })

  it('renders an event-only report with its basis and GFW source', async () => {
    reportsApi.list.mockResolvedValue([eventOnly])
    reportsApi.get.mockResolvedValue(eventOnly)

    await open('/reports/8')

    expect(screen.getByRole('heading', { name: /GFW event review/ })).toBeTruthy()
    expect(screen.getByText('Evidence basis: Selected GFW event only')).toBeTruthy()
    expect(screen.getAllByText(/Global Fishing Watch/).length).toBeGreaterThan(0)
    expect(screen.getByText('A historical inferred event point, not a track and not proof of illegality. AIS coverage is unknown.')).toBeTruthy()
  })
})
