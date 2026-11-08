import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import api from '@/lib/api'
import { AlertsPage, InvestigationCasesPage } from '@/pages/Cases'
import { ReplayWindowProvider } from '@/lib/replayWindow'
import { fleet } from './fixtures'

// The real api.js runs; only the HTTP boundary is replaced, so the bodies below are what the API receives
const conflict = (detail) => Object.assign(new Error('409'), { response: { status: 409, data: { detail } } })

const storedAlert = (overrides = {}) => ({
  id: 'al-1', title: 'Entered Gulf of Mannar MPA', severity: 'HIGH', mmsi: 419007431, status: 'open', version: 3,
  last_observed_at: '2026-11-01T06:00:00Z', source_mode: 'synthetic', acknowledged_by: null, resolved_by: null, resolution_note: null,
  ...overrides,
})

const triage = {
  items: [{ id: 'asm-1', mmsi: 419007431, vessel_name: 'SEA PEARL II', score: 0.82, level: 'HIGH', evaluated_at: '2026-11-01T06:00:00Z',
    review_state: 'under_review', alerts: { total: 2, open: 1, acknowledged: 1, resolved: 0, high_active: 1 }, cases: { open: 1, closed: 0 } }],
  total: 1, weather: { reason: 'This read-only triage view does not fetch weather.' }, limitation: 'Triage is a deterministic review queue.',
}

const openCase = {
  id: 'case-1', title: 'Vessel investigation: Sea Pearl II', mmsi: 419007431, status: 'open', version: 2, created_by: 'analyst',
  revisions: [], events: [{ id: 1, event: 'opened', actor: 'analyst', note: null, created_at: '2026-11-01T06:00:00Z' }],
}

let get, post, alertResponses

async function open(url) {
  render(
    <ReplayWindowProvider>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/cases" element={<InvestigationCasesPage />} />
        </Routes>
      </MemoryRouter>
    </ReplayWindowProvider>,
  )
  await act(async () => {})
}

const calls = (spy, url) => spy.mock.calls.filter(([u]) => u === url)

beforeEach(() => {
  sessionStorage.clear()
  alertResponses = [[storedAlert()]]
  get = vi.spyOn(api, 'get').mockImplementation(async (url) => {
    if (url === '/vessels/') return { data: fleet }
    if (url === '/triage/assessments') return { data: triage }
    if (url === '/alerts/stored') {
      const alerts = alertResponses.length > 1 ? alertResponses.shift() : alertResponses[0]
      return { data: { alerts, total: alerts.length, limitation: 'Stored alerts are rule-based screening records.' } }
    }
    if (url === '/cases/') return { data: [openCase] }
    if (url === '/cases/case-1') return { data: openCase }
    throw new Error(`unavailable ${url}`)
  })
  post = vi.spyOn(api, 'post')
})

afterEach(() => vi.restoreAllMocks())

describe('stored alert lifecycle and triage', () => {
  it('shows the persisted review queue with its state and counts', async () => {
    await open('/alerts')
    const queue = screen.getByRole('region', { name: 'Review queue' })
    for (const text of ['Sea Pearl II', 'Under review (open case)', '0.82', 'Alerts: 1 open, 1 acknowledged, 0 resolved', 'Cases: 1 open, 0 closed', 'does not fetch weather']) {
      expect(queue.textContent).toContain(text)
    }
  })

  it('acknowledges with the version on screen, then resolves with the note', async () => {
    alertResponses = [[storedAlert()], [storedAlert({ status: 'acknowledged', version: 4, acknowledged_by: 'analyst' })], [storedAlert({ status: 'acknowledged', version: 4 })]]
    post.mockResolvedValue({ data: {} })
    await open('/alerts')
    expect(calls(get, '/alerts/stored')[0][1].params).toEqual({ limit: 100, status: 'open' })

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Acknowledge Entered Gulf of Mannar MPA (MMSI 419007431)' })) })
    expect(calls(post, '/alerts/stored/al-1/acknowledge')[0][1]).toEqual({ expected_version: 3 })
    expect(screen.getByRole('status').textContent).toBe('Entered Gulf of Mannar MPA (MMSI 419007431) acknowledged.')
    expect(screen.getByText(/Acknowledged by analyst/)).toBeTruthy()

    fireEvent.change(screen.getByLabelText('Resolution note for Entered Gulf of Mannar MPA (MMSI 419007431)'), { target: { value: ' Licensed transit ' } })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Resolve Entered Gulf of Mannar MPA (MMSI 419007431)' })) })
    expect(calls(post, '/alerts/stored/al-1/resolve')[0][1]).toEqual({ expected_version: 4, note: 'Licensed transit' })
  })

  it('shows the server 409 detail, says nothing changed and reloads the list', async () => {
    post.mockRejectedValue(conflict('Alert changed; reload before retrying'))
    await open('/alerts')
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Acknowledge Entered Gulf of Mannar MPA (MMSI 419007431)' })) })
    expect(screen.getByRole('status').textContent).toBe('Alert changed; reload before retrying Nothing was changed. The list was reloaded.')
    expect(calls(get, '/alerts/stored')).toHaveLength(2)
  })

  it('syncs stored alerts and reports the counts the server returned', async () => {
    post.mockResolvedValue({ data: { observed: 3, created: 1, updated: 1, unchanged: 0, skipped_resolved: 1 } })
    await open('/alerts')
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Sync stored alerts' })) })
    expect(calls(post, '/alerts/sync')).toHaveLength(1)
    expect(screen.getByRole('status').textContent).toBe('Synced 3 current alerts: 1 new, 1 updated, 0 unchanged, 1 left resolved.')
  })
})

describe('case lifecycle', () => {
  it('closes with the version and note, then shows the closed state and history', async () => {
    const closed = { ...openCase, status: 'closed', version: 3, events: [...openCase.events, { id: 2, event: 'closed', actor: 'analyst', note: 'No further action', created_at: '2026-11-02T06:00:00Z' }] }
    post.mockResolvedValue({ data: closed })
    await open('/cases?id=case-1')

    fireEvent.change(screen.getByLabelText('Note (optional)'), { target: { value: 'No further action' } })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Close case' })) })

    expect(calls(post, '/cases/case-1/close')[0][1]).toEqual({ expected_version: 2, note: 'No further action' })
    expect(screen.getByRole('status').textContent).toBe('Case closed.')
    expect(screen.getByRole('button', { name: 'Reopen case' })).toBeTruthy()
    expect(screen.getByText(/accepts no new report revisions/)).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Case history' }).textContent).toContain('closed by analyst')
  })

  it('reloads the case on a 409 instead of guessing its state', async () => {
    post.mockRejectedValue(conflict('Case changed; reload before retrying'))
    await open('/cases?id=case-1')
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Close case' })) })
    expect(screen.getByRole('status').textContent).toBe('Case changed; reload before retrying Nothing was changed; the case was reloaded.')
    expect(calls(get, '/cases/case-1')).toHaveLength(2)
    expect(calls(post, '/cases/case-1/close')[0][1]).toEqual({ expected_version: 2 })
  })
})
