import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Operations from '@/pages/Operations'
import { adminApi, authApi, operationsApi, sourcesApi } from '@/lib/api'

vi.mock('@/lib/api', async (original) => ({
  ...(await original()),
  authApi: { me: vi.fn() },
  sourcesApi: { health: vi.fn(), jobs: vi.fn(), run: vi.fn(), cancelJob: vi.fn() },
  operationsApi: { status: vi.fn() },
  adminApi: {
    settings: vi.fn(),
    updateSettings: vi.fn(),
    users: vi.fn(),
    createUser: vi.fn(),
    setUserActive: vi.fn(),
  },
}))

const sourceHealth = {
  checked_at: '2026-11-09T06:00:00Z',
  external_calls: false,
  writes: false,
  sources: {
    local_vessel_records: {
      source: 'local vessel records', status: 'available', positions: 678, vessels: 14,
      source_mode: 'unknown', last_run: null,
      limitations: 'Replay rows have no verified provider provenance.',
    },
    copernicus_sst: {
      source: 'Copernicus Marine Service', status: 'available', mode: 'historical',
      latest_observed_at: '2026-10-20T00:00:00Z', value: 29.72, unit: '°C',
      limitations: 'One prepared regional cell, not a forecast.',
    },
    global_fishing_watch: {
      provider: 'Global Fishing Watch', status: 'configured', availability: 'not_checked',
      last_run: { status: 'succeeded', finished_at: '2026-11-09T05:00:00Z' },
      last_run_note: 'Historical checkpoint only.', limitations: 'Events are inferred points, not tracks.',
    },
    aisstream: {
      source: 'AISStream', status: 'not_configured', availability: 'not_checked', coverage: 'unknown',
      last_run: null, limitations: 'No coverage is claimed.',
    },
    open_meteo_marine: {
      source: 'Open-Meteo Marine', status: 'not_checked', availability: 'not_checked',
      kind: 'modelled_marine_data', limitations: 'Model output, not an observation.',
    },
  },
}

const settings = {
  organization: 'Gulf Marine Authority',
  aoi_name: 'Gulf of Mannar',
  aoi_bbox: [[78.0, 8.0], [79.5, 9.5]],
  display_timezone: 'Asia/Kolkata',
  alert_threshold: 0.6,
  report_recipients: ['watch@example.org'],
  retention_days: 365,
  updated_at: '2026-11-09T05:30:00Z',
  updated_by: 'a1',
}

const admin = { id: 'a1', username: 'admin', roles: ['ADMINISTRATOR'], is_active: true }
const viewer = { id: 'v1', username: 'viewer', roles: ['VIEWER'], is_active: true }

async function open() {
  render(<MemoryRouter><Operations /></MemoryRouter>)
  await act(async () => {})
}

beforeEach(() => {
  vi.resetAllMocks()
  authApi.me.mockResolvedValue(viewer)
  sourcesApi.health.mockResolvedValue(sourceHealth)
  sourcesApi.jobs.mockResolvedValue({ items: [] })
  operationsApi.status.mockResolvedValue({ remote_fetch_paused: false, cache: {}, queue: { active_jobs: 0, worker_status: 'not_verified' }, disk: { status: 'available', free_bytes: 21474836480 }, backup: { status: 'not_verified' } })
})

describe('Operations page', () => {
  it('shows all five source-health cards with mode, last-run and limitations to a Viewer', async () => {
    await open()

    for (const name of ['Local replay', 'Copernicus SST', 'GFW', 'AISStream', 'Open-Meteo']) {
      expect(screen.getByRole('heading', { name })).toBeTruthy()
    }
    expect(screen.getByText('Replay rows have no verified provider provenance.')).toBeTruthy()
    expect(screen.getByText('One prepared regional cell, not a forecast.')).toBeTruthy()
    expect(screen.getByText(/Succeeded/)).toBeTruthy()
    expect(screen.getByText('No persisted run', { exact: false })).toBeTruthy()
    expect(screen.getByText(/Configured or not checked does not mean reachable/)).toBeTruthy()
    expect(screen.getByText(/Administrator access is required to change deployment settings/)).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Save deployment settings' })).toBeNull()
  })

  it('lets an Administrator read and save deployment settings', async () => {
    authApi.me.mockResolvedValue(admin)
    adminApi.settings.mockResolvedValue(settings)
    adminApi.users.mockResolvedValue([admin, viewer])
    adminApi.updateSettings.mockImplementation(async (payload) => ({ ...settings, ...payload }))

    await open()

    expect(screen.getByLabelText('Organisation').value).toBe('Gulf Marine Authority')
    expect(screen.getByLabelText('Area of interest').value).toBe('Gulf of Mannar')
    expect(screen.getByLabelText('West').value).toBe('78')
    expect(screen.getByLabelText('Display timezone').value).toBe('Asia/Kolkata')
    expect(screen.getByLabelText('Report recipients').value).toBe('watch@example.org')

    fireEvent.change(screen.getByLabelText('Organisation'), { target: { value: 'New Organisation' } })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Save deployment settings' })) })

    expect(adminApi.updateSettings).toHaveBeenCalledWith({
      organization: 'New Organisation',
      aoi_name: 'Gulf of Mannar',
      aoi_bbox: [[78, 8], [79.5, 9.5]],
      display_timezone: 'Asia/Kolkata',
      alert_threshold: 0.6,
      report_recipients: ['watch@example.org'],
      retention_days: 365,
    })
    expect(screen.getByRole('status').textContent).toContain('Deployment settings saved')
  })

  it('creates a user without showing the password afterwards and blocks self-deactivation', async () => {
    authApi.me.mockResolvedValue(admin)
    adminApi.settings.mockResolvedValue(settings)
    adminApi.users.mockResolvedValue([admin, viewer])
    adminApi.createUser.mockImplementation(async (payload) => ({
      id: 'v2', username: payload.username, roles: payload.roles, is_active: true,
    }))

    await open()

    expect(screen.getByRole('button', { name: 'Disable admin' }).disabled).toBe(true)
    expect(screen.getByText(/You cannot deactivate your own account/)).toBeTruthy()
    for (const role of ['VIEWER', 'ANALYST', 'APPROVER', 'ADMINISTRATOR']) {
      expect(screen.getByLabelText(role)).toBeTruthy()
    }

    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'analyst2' } })
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'not-shown-after' } })
    fireEvent.click(screen.getByLabelText('ANALYST'))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Create local user' })) })

    expect(adminApi.createUser).toHaveBeenCalledWith({
      username: 'analyst2', password: 'not-shown-after', roles: ['ANALYST'],
    })
    expect(screen.getByLabelText('Password').value).toBe('')
    expect(document.body.textContent).not.toContain('not-shown-after')
    expect(screen.getByText(/has been created/)).toBeTruthy()
  })

  it('activates and deactivates another local account', async () => {
    authApi.me.mockResolvedValue(admin)
    adminApi.settings.mockResolvedValue(settings)
    adminApi.users.mockResolvedValue([admin, viewer])
    adminApi.setUserActive.mockResolvedValue({ ...viewer, is_active: false })

    await open()

    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Disable viewer' })) })

    expect(adminApi.setUserActive).toHaveBeenCalledWith('v1', false)
    expect(screen.getByRole('button', { name: 'Enable viewer' })).toBeTruthy()
    expect(screen.getByText(/viewer is now disabled/)).toBeTruthy()
  })

  it('explains a signed-out or forbidden state instead of drawing a broken form', async () => {
    authApi.me.mockRejectedValue(Object.assign(new Error('401'), { response: { status: 401 } }))
    sourcesApi.health.mockRejectedValue(Object.assign(new Error('401'), { response: { status: 401 } }))
    await open()

    expect(screen.getByRole('alert').textContent).toContain('Sign in to view operations')
    expect(screen.queryByRole('button', { name: 'Save deployment settings' })).toBeNull()
  })

  it('names a forbidden source-health read and still renders the page', async () => {
    sourcesApi.health.mockRejectedValue(Object.assign(new Error('403'), { response: { status: 403 } }))
    await open()

    expect(screen.getByRole('alert').textContent).toContain('You do not have permission to view source health')
    expect(screen.getByRole('heading', { name: 'Operations' })).toBeTruthy()
  })

  it('says source health is not reported when the API returns no sources', async () => {
    sourcesApi.health.mockResolvedValue({ sources: {} })
    await open()

    expect(screen.getByText('Source health not reported.')).toBeTruthy()
  })

  it('shows the server validation message and keeps the editable settings', async () => {
    authApi.me.mockResolvedValue(admin)
    adminApi.settings.mockResolvedValue(settings)
    adminApi.users.mockResolvedValue([admin])
    adminApi.updateSettings.mockRejectedValue(Object.assign(new Error('422'), {
      response: { status: 422, data: { detail: [{ msg: 'alert_threshold must be between 0 and 1' }] } },
    }))

    await open()
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Save deployment settings' })) })

    expect(screen.getByRole('alert').textContent).toContain('alert_threshold must be between 0 and 1')
    expect(screen.getByLabelText('Organisation').value).toBe('Gulf Marine Authority')
  })
})
