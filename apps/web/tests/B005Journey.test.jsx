import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/lib/api'
import { AlertsPage, EvidencePage, ReportsPage } from '@/pages/Cases'
import { REPLAY_PRESET, ReplayWindowProvider, useReplayWindow } from '@/lib/replayWindow'
import { fleet, seaPearlDetail } from './fixtures'

// The real api.js runs; only the HTTP boundary is replaced, so the payloads below are what the API would receive
const MMSI = '419007431'
const BOUNDS = { window_start: REPLAY_PRESET.start, window_end: REPLAY_PRESET.end }
const HISTORICAL = { mode: 'historical', start: REPLAY_PRESET.start, end: REPLAY_PRESET.end }
const GFW_PAGE = { gfw_event_id: 'evt-1', gfw_start_date: '2026-10-01', gfw_end_date: '2026-10-08', gfw_offset: 20, gfw_limit: 20 }
const GFW_KEYS = ['gfw_event_id', 'gfw_start_date', 'gfw_end_date', 'gfw_offset', 'gfw_limit', 'include_gfw_ocean_context']
const conflict = () => Object.assign(new Error('409'), { response: { status: 409, data: { detail: 'Assessment window does not match the report window; re-sync and retry.' } } })

let get, post

function Toggle() {
  const { selectRolling } = useReplayWindow()
  return <button type="button" onClick={selectRolling}>use rolling</button>
}

function CasesStub() {
  return <p>at {useLocation().search}</p>
}

async function open(url) {
  render(
    <ReplayWindowProvider>
      <MemoryRouter initialEntries={[url]}>
        <Toggle />
        <Routes>
          <Route path="/alerts" element={<AlertsPage />} />
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

beforeEach(() => {
  sessionStorage.clear()
  get = vi.spyOn(api, 'get').mockImplementation(async (url) => {
    if (url === '/vessels/') return { data: fleet }
    if (url === `/vessels/${MMSI}`) return { data: seaPearlDetail }
    if (url === '/alerts/assessments') return { data: { assessments: [{ id: 'asm-1', window: HISTORICAL }] } }
    if (url === '/sar/detections') return { data: [] }
    throw new Error(`unavailable ${url}`)
  })
  post = vi.spyOn(api, 'post')
})

afterEach(() => vi.restoreAllMocks())

describe('B-005 replay journey', () => {
  it('sends the same bounds to list, detail, sync and report, recovers a 409 with the same case, and passes the GFW page unchanged', async () => {
    sessionStorage.setItem('samudrasense.observation-window', 'historical')
    let reportAttempts = 0
    post.mockImplementation(async (url) => {
      if (url === '/alerts/assessments/sync') return { data: { synced: 1 } }
      if (url === '/cases/') return { data: { id: 'case-1' } }
      if (url === '/reports/') { reportAttempts += 1; if (reportAttempts === 1) throw conflict(); return { data: { id: 7 } } }
      if (url === '/cases/case-1/revisions') return { data: {} }
      throw new Error(url)
    })

    await open('/alerts')
    expect(calls(get, '/vessels/')[0][1].params).toMatchObject(BOUNDS)
    cleanup()

    await open(`/vessels/${MMSI}?${new URLSearchParams({ ...GFW_PAGE, gfw_offset: '20', gfw_limit: '20' })}`)
    expect(calls(get, `/vessels/${MMSI}`)[0][1].params).toMatchObject(BOUNDS)
    expect(screen.getByText(/GFW event/).textContent).toContain('evt-1')

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create investigation case' })) })
    const caseConflict = screen.getByText(/Assessment window does not match the report window/)
    expect(caseConflict.textContent).toContain('Case case-1 was created')

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Re-sync with the same window and retry' })) })

    const syncs = calls(post, '/alerts/assessments/sync')
    expect(syncs).toHaveLength(2)
    syncs.forEach(([, body]) => expect(body).toMatchObject({ mmsi: Number(MMSI), ...BOUNDS }))
    expect(calls(get, '/alerts/assessments')).toHaveLength(2)
    expect(calls(post, '/cases/')).toHaveLength(1)
    const reports = calls(post, '/reports/')
    expect(reports).toHaveLength(2)
    reports.forEach(([, body]) => expect(body).toEqual({
      // The regional SST subset is unavailable here, so the event is attached without asking for it
      mmsi: Number(MMSI), lookback_hours: 72, ...BOUNDS, assessment_id: 'asm-1', ...GFW_PAGE, include_gfw_ocean_context: false,
    }))
    expect(calls(post, '/cases/case-1/revisions')[0][1]).toEqual({ report_id: 7, expected_version: 0 })
    expect(screen.getByText('at ?id=case-1')).toBeTruthy()
  })

  it('asks for SST context with the event only when the regional subset loaded', async () => {
    const base = get.getMockImplementation()
    get.mockImplementation(async (url, config) => (url === '/environment/regional'
      ? { data: { variable: 'Sea surface temperature', value: 29.1, unit: '°C', observed_at: '2026-10-19T00:00:00Z', attribution: 'Copernicus Marine Service' } }
      : base(url, config)))
    post.mockImplementation(async () => ({ data: { id: 4 } }))
    await open(`/vessels/${MMSI}?${new URLSearchParams({ ...GFW_PAGE, gfw_offset: '20', gfw_limit: '20' })}`)

    expect(screen.getByText('Regional historical SST context will be included.')).toBeTruthy()
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create report snapshot' })) })
    expect(calls(post, '/reports/')[0][1]).toMatchObject({ ...GFW_PAGE, include_gfw_ocean_context: true })
  })

  it('rolling mode omits both bounds and, without an event, every GFW field', async () => {
    post.mockImplementation(async (url) => (url === '/reports/' ? { data: { id: 3 } } : { data: { synced: 1 } }))
    await open(`/vessels/${MMSI}`)
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create report snapshot' })) })

    const detailParams = calls(get, `/vessels/${MMSI}`)[0][1].params
    const [, body] = calls(post, '/reports/')[0]
    for (const key of ['window_start', 'window_end']) {
      expect(detailParams).not.toHaveProperty(key)
      expect(body).not.toHaveProperty(key)
    }
    GFW_KEYS.forEach((key) => expect(body).not.toHaveProperty(key))
  })

  it('ignores a late historical vessel answer after the selection changed', async () => {
    sessionStorage.setItem('samudrasense.observation-window', 'historical')
    let lateHistorical
    get.mockImplementation((url, config) => {
      if (url !== `/vessels/${MMSI}`) return Promise.reject(new Error(url))
      if (config.params.window_start) return new Promise((resolve) => { lateHistorical = resolve })
      return Promise.resolve({ data: { ...seaPearlDetail, name: 'ROLLING ANSWER' } })
    })
    await open(`/vessels/${MMSI}`)
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'use rolling' })) })
    await act(async () => { lateHistorical({ data: { ...seaPearlDetail, name: 'STALE HISTORICAL' } }) })

    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Rolling Answer')
    expect(screen.queryByText(/stale historical/i)).toBeNull()
  })

  it('renders persisted GFW evidence with its limitations and independently dated SST', async () => {
    const evidence = {
      sha256: 'f'.repeat(64),
      integrity_note: 'Checksum detects changes only when compared with a separately trusted copy; not a digital signature.',
      snapshot: {
        source: 'Global Fishing Watch', dataset: 'public-global-fishing-events:latest',
        requested_start: '2026-10-01', requested_end_exclusive: '2026-10-08',
        limitations: 'Historical inferred apparent-fishing event locations, not live positions or vessel tracks.',
        event: { id: 'evt-1', type: 'fishing', start: '2026-10-02T03:00:00Z', end: '2026-10-02T07:00:00Z', position: { lat: 8.9, lon: 78.95 } },
        regional_ocean_context: {
          source: 'Copernicus Marine Service', dataset: 'sst-l4', unit: '°C', mode: 'historical_subset',
          values: [{ observed_at: '2026-10-18T00:00:00Z', temperature_c: 29.1 }, { observed_at: '2026-10-20T00:00:00Z', temperature_c: 29.3 }],
          association: 'Regional historical context only; not necessarily concurrent with or at the event position.',
        },
      },
    }
    get.mockImplementation(async (url) => {
      if (url === '/reports/') return { data: [{ id: 7, mmsi: Number(MMSI), integrity_ok: true, sha256: 'a', signed_at: null, snapshot: { ...seaPearlDetail, window: HISTORICAL, gfw_event_evidence: evidence } }] }
      throw new Error(url)
    })
    await open('/reports?id=7')

    const section = screen.getByRole('region', { name: 'GFW event evidence' })
    for (const text of ['not a vessel track', 'not a live vessel position', 'not proof of fishing', 'not proof of illegality', 'Global Fishing Watch',
      'public-global-fishing-events:latest', 'evt-1', '2026-10-02T03:00:00Z to 2026-10-02T07:00:00Z', '8.9, 78.95', '2026-10-01 to 2026-10-08',
      'f'.repeat(64), evidence.integrity_note, evidence.snapshot.limitations, '2026-10-18T00:00:00Z to 2026-10-20T00:00:00Z', 'not necessarily concurrent']) {
      expect(section.textContent).toContain(text)
    }
    expect(screen.getByRole('note', { name: 'Historical observation window' }).textContent).toContain(`UTC ${REPLAY_PRESET.start} to ${REPLAY_PRESET.end}`)
  })
})
