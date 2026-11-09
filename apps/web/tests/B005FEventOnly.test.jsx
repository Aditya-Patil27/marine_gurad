import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/lib/api'
import { EvidencePage, ReportsPage } from '@/pages/Cases'
import { REPLAY_PRESET, ReplayWindowProvider } from '@/lib/replayWindow'
import { fleet, seaPearlDetail } from './fixtures'

// The real api.js runs; only the HTTP boundary is replaced, so the bodies below are what the API receives
const MMSI = '419007431'
const BOUNDS = { window_start: REPLAY_PRESET.start, window_end: REPLAY_PRESET.end }
const GFW_PAGE = { gfw_event_id: 'evt-404', gfw_start_date: '2026-10-01', gfw_end_date: '2026-10-08', gfw_offset: 20, gfw_limit: 20 }
const EVENT_URL = `/vessels/${MMSI}?${new URLSearchParams({ ...GFW_PAGE, gfw_offset: '20', gfw_limit: '20' })}`

const notFound = () => Object.assign(new Error('404'), { response: { status: 404, data: { detail: 'No vessel' } } })
const conflict = () => Object.assign(new Error('409'), { response: { status: 409, data: { detail: 'Report is not an event-only report' } } })

let get, post

function CasesStub() {
  return <p>at {useLocation().search}</p>
}

async function open(url) {
  render(
    <ReplayWindowProvider>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/vessels/:mmsi" element={<EvidencePage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/cases" element={<CasesStub />} />
        </Routes>
      </MemoryRouter>
    </ReplayWindowProvider>,
  )
  await act(async () => {})
}

const calls = (spy, url) => spy.mock.calls.filter(([u]) => u === url)

const evidence = {
  sha256: 'a'.repeat(64),
  integrity_note: 'Checksum detects changes only when compared with a separately trusted copy; not a digital signature.',
  snapshot: {
    source: 'Global Fishing Watch', dataset: 'public-global-fishing-events:latest',
    requested_start: '2026-10-01', requested_end_exclusive: '2026-10-08',
    limitations: 'Historical inferred apparent-fishing event locations, not live positions or vessel tracks.',
    event: { id: 'evt-404', type: 'fishing', start: '2026-10-02T03:00:00Z', end: '2026-10-02T07:00:00Z', position: { lat: 8.9, lon: 78.95 } },
  },
}

beforeEach(() => {
  sessionStorage.clear()
  sessionStorage.setItem('samudrasense.observation-window', 'historical')
  get = vi.spyOn(api, 'get').mockImplementation(async (url) => {
    if (url === '/vessels/') return { data: fleet }
    if (url === `/vessels/${MMSI}`) throw notFound()
    if (url === '/sar/detections') return { data: [] }
    if (url === '/weather/419007431') throw notFound()
    if (url === '/alerts/stored') return { data: { alerts: [], total: 0 } }
    if (url === '/triage/assessments') return { data: { items: [], total: 0 } }
    throw new Error(`unavailable ${url}`)
  })
  post = vi.spyOn(api, 'post')
})

afterEach(() => vi.restoreAllMocks())

describe('B-005F event-only review', () => {
  it('creates one event-only report and one case from it, then shows the missing AIS and event limits', async () => {
    post.mockImplementation(async (url) => {
      if (url === '/reports/') return { data: { id: 11 } }
      if (url === '/cases/') return { data: { id: 'evt-case' } }
      throw new Error(url)
    })

    await open(EVENT_URL)
    expect(screen.getByRole('alert').textContent).toContain(`No observations for MMSI ${MMSI}`)

    const button = screen.getByRole('button', { name: 'Create event-only review' })
    await act(async () => { fireEvent.click(button); fireEvent.click(button) })

    const reports = calls(post, '/reports/')
    expect(reports).toHaveLength(1)
    expect(reports[0][1]).toEqual({
      mmsi: Number(MMSI), event_only: true, ...GFW_PAGE, gfw_offset: 20, gfw_limit: 20, include_gfw_ocean_context: false,
    })
    // No assessment basis, replay window or weather field
    for (const key of ['assessment_id', 'window_start', 'window_end', 'lookback_hours', 'include_weather_context']) {
      expect(reports[0][1]).not.toHaveProperty(key)
    }
    const cases = calls(post, '/cases/')
    expect(cases).toHaveLength(1)
    expect(cases[0][1]).toEqual({ report_id: 11, title: `GFW event review: MMSI ${MMSI}` })
    expect(calls(post, '/alerts/assessments/sync')).toHaveLength(0)
    expect(post.mock.calls.some(([u]) => u.includes('/revisions'))).toBe(false)
    expect(screen.getByText('at ?id=evt-case')).toBeTruthy()
    cleanup()

    // The stored report keeps the absence explicit and never shows a score
    const snapshot = {
      mmsi: Number(MMSI), evidence_basis: 'gfw_event_only',
      ais_evidence: { status: 'unavailable', note: 'No AIS observation or vessel assessment is attached; neither is synthesized or inferred.', limitation: 'Missing AIS is a coverage gap, not evidence of absence or illegal activity.' },
      assessment: { status: 'unavailable', note: 'No persisted vessel assessment is attached and no risk score is copied.' },
      gfw_event_evidence: evidence,
      limitations: 'A GFW event is a historical, inferred event location. It is not a vessel track, live position, fishing proof or proof of illegality; no AIS observation or risk assessment supports this record.',
    }
    get.mockImplementation(async (url) => {
      if (url !== '/reports/') throw new Error(url)
      return { data: [{ id: 11, mmsi: Number(MMSI), integrity_ok: true, sha256: 'b'.repeat(64), signed_at: null, snapshot }] }
    })
    await open('/reports?id=11')

    expect(screen.queryByText('0.00')).toBeNull()
    expect(screen.queryByText(/Vessel investigation/)).toBeNull()
    const text = document.body.textContent
    for (const expected of [
      'AIS evidence: unavailable', 'Assessment: unavailable', snapshot.ais_evidence.note, snapshot.ais_evidence.limitation,
      snapshot.assessment.note, 'evt-404', '2026-10-02T03:00:00Z to 2026-10-02T07:00:00Z', snapshot.limitations,
      evidence.sha256, 'Global Fishing Watch', '2026-10-01 to 2026-10-08',
    ]) {
      expect(text).toContain(expected)
    }
  })

  it('offers no event-only action for a generic API failure or without a selected event', async () => {
    get.mockImplementation(async (url) => {
      if (url === '/sar/detections') return { data: [] }
      throw Object.assign(new Error('Network Error'), { code: 'ERR_NETWORK' })
    })
    await open(EVENT_URL)
    expect(screen.queryByRole('button', { name: 'Create event-only review' })).toBeNull()
    cleanup()

    get.mockImplementation(async (url) => {
      if (url === `/vessels/${MMSI}`) throw notFound()
      if (url === '/sar/detections') return { data: [] }
      throw new Error(url)
    })
    await open(`/vessels/${MMSI}`)
    expect(screen.queryByRole('button', { name: 'Create event-only review' })).toBeNull()
    expect(post).not.toHaveBeenCalled()
  })

  it('keeps the saved report when case creation fails and a retry calls only the case endpoint', async () => {
    let caseAttempts = 0
    post.mockImplementation(async (url) => {
      if (url === '/reports/') return { data: { id: 12 } }
      if (url === '/cases/') { caseAttempts += 1; if (caseAttempts === 1) throw conflict(); return { data: { id: 'case-12' } } }
      throw new Error(url)
    })

    await open(EVENT_URL)
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create event-only review' })) })

    const alerts = screen.getAllByRole('alert').map((node) => node.textContent).join(' ')
    expect(alerts).toContain('Report 12 is saved')
    expect(alerts).toContain('Check Cases before retrying')
    expect(calls(post, '/reports/')).toHaveLength(1)

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Retry case from saved report 12' })) })

    expect(calls(post, '/reports/')).toHaveLength(1)
    expect(calls(post, '/cases/')).toHaveLength(2)
    expect(calls(post, '/cases/')[1][1]).toEqual({ report_id: 12, title: `GFW event review: MMSI ${MMSI}` })
    expect(screen.getByText('at ?id=case-12')).toBeTruthy()
  })

  it('keeps the assessment-backed case path unchanged', async () => {
    get.mockImplementation(async (url) => {
      if (url === `/vessels/${MMSI}`) return { data: seaPearlDetail }
      if (url === '/sar/detections') return { data: [] }
      if (url === '/weather/419007431') return { data: { status: 'unavailable', reason: 'No recent positions' } }
      if (url === '/alerts/assessments') return { data: { assessments: [{ id: 'asm-1', window: { mode: 'historical', start: REPLAY_PRESET.start, end: REPLAY_PRESET.end } }] } }
      if (url === '/environment/regional') throw new Error('absent')
      throw new Error(url)
    })
    post.mockImplementation(async (url) => {
      if (url === '/alerts/assessments/sync') return { data: { synced: 1 } }
      if (url === '/cases/') return { data: { id: 'case-1' } }
      if (url === '/reports/') return { data: { id: 7 } }
      if (url === '/cases/case-1/revisions') return { data: {} }
      throw new Error(url)
    })

    await open(`/vessels/${MMSI}`)
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create investigation case' })) })

    expect(calls(post, '/cases/')[0][1]).toEqual({ assessment_id: 'asm-1', title: 'Vessel investigation: Sea Pearl II' })
    expect(calls(post, '/reports/')[0][1]).toMatchObject({ assessment_id: 'asm-1', ...BOUNDS })
    expect(calls(post, '/cases/case-1/revisions')[0][1]).toEqual({ report_id: 7, expected_version: 0 })
  })
})
