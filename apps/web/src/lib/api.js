import axios from 'axios'

// Empty by default: requests go to /api on the same origin and the Vite dev server
// proxies them to the backend (no CORS). Set VITE_API_URL when hosting the API elsewhere.
export const API_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 30000,
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'samudra_csrf',
  xsrfHeaderName: 'X-CSRF-Token',
})

export const authApi = {
  me: () => api.get('/auth/me').then((r) => r.data),
  login: (username, password) => api.post('/auth/login', { username, password }).then((r) => r.data),
  logout: () => api.post('/auth/logout').then((r) => r.data),
}

export const gfwApi = {
  events: (start_date, end_date, offset = 0, limit = 50) => api.get('/gfw/events/regional/geojson', { params: { start_date, end_date, offset, limit } }).then((r) => r.data),
}

/** Historical callers send both bounds; rolling callers send neither and keep `hours`. */
const windowQuery = (window) =>
  window?.start && window?.end ? { window_start: window.start, window_end: window.end } : {}

const windowHours = (window) => {
  if (!window?.start || !window?.end) return 168
  return Math.max(1, Math.ceil((new Date(window.end) - new Date(window.start)) / 36e5))
}

export const vesselsApi = {
  list: (hours = 168, window = null) =>
    api.get('/vessels/', { params: { hours, ...windowQuery(window) } }).then((r) => r.data),
  get: (mmsi, window = null, hours = 168) =>
    api.get(`/vessels/${mmsi}`, { params: { hours, ...windowQuery(window) } }).then((r) => r.data),
}

export const mapApi = {
  zones: () => api.get('/map/zones').then((r) => r.data),
}

/** The API answered and has no such record, as opposed to not answering at all. */
export const isNotFound = (error) => error?.response?.status === 404

/** The selected assessment no longer matches the report window; nothing was inserted. */
export const isConflict = (error) => error?.response?.status === 409

/** The API's own message, including the 409 safe-retry detail, without guessing a cause. */
export const serverDetail = (error) => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg ?? String(item)).join(' ')
  if (detail && typeof detail === 'object') return detail.reason ?? detail.message ?? ''
  return error?.message || ''
}

export const reportsApi = {
  list: () => api.get('/reports/').then((r) => r.data),
  /** The list body as text, unparsed: parsing turns 59.0 into 59 and the snapshot no longer matches its SHA-256. */
  listText: () => api.get('/reports/', { transformResponse: [(d) => d] }).then((r) => r.data),
  /**
   * `gfwEvent` is the selected page identity {gfw_event_id, gfw_start_date, gfw_end_date, gfw_offset, gfw_limit}, or null.
   * `oceanContext` asks the server to add the prepared regional SST subset; the server answers 503 when that subset is missing.
   */
  create: (mmsi, assessment_id = null, window = null, gfwEvent = null, oceanContext = false) =>
    api
      .post('/reports/', {
        mmsi,
        lookback_hours: windowHours(window),
        ...windowQuery(window),
        ...(assessment_id ? { assessment_id } : {}),
        // Without a selected event no GFW field is sent, not even a default page
        ...(gfwEvent ? { ...gfwEvent, include_gfw_ocean_context: oceanContext } : {}),
      })
      .then((r) => r.data),
  /** Explicit A-004F basis: one selected GFW event, no assessment/window/weather fields. */
  createEventOnly: (mmsi, gfwEvent, oceanContext = false) =>
    api
      .post('/reports/', {
        mmsi,
        event_only: true,
        ...gfwEvent,
        include_gfw_ocean_context: oceanContext,
      })
      .then((r) => r.data),
  /** One report by id; the review page must not depend on the bounded list page. */
  get: (id) => api.get(`/reports/${id}`).then((r) => r.data),
  /** Verified canonical bytes and source references; 409 means the saved evidence no longer verifies. */
  manifest: (id) => api.get(`/reports/${id}/manifest`).then((r) => r.data),
  /** Approved-only deterministic PDF, returned as bytes. */
  exportPdf: (id) => api.get(`/reports/${id}/export.pdf`, { responseType: 'blob' }).then((r) => r.data),
  /** `expected_sha256` guards approval against a revision that changed after it was displayed. */
  sign: (id, officer, reviewed, expected_sha256) =>
    api
      .post(`/reports/${id}/sign`, { officer, reviewed, ...(expected_sha256 ? { expected_sha256 } : {}) })
      .then((r) => r.data),
  deliveries: (id) => api.get(`/reports/${id}/deliveries`).then((r) => r.data),
  deliver: (id, expected_sha256, recipients, idempotency_key) =>
    api.post(`/reports/${id}/deliveries`, { expected_sha256, recipients, idempotency_key }).then((r) => r.data),
  submitDelivery: (deliveryId) => api.post(`/reports/deliveries/${deliveryId}/submit`).then((r) => r.data),
}

/** Operational source state; read-only, never a live-provider or coverage claim. */
export const sourcesApi = {
  health: () => api.get('/sources/health').then((r) => r.data),
  run: (payload) => api.post('/sources/runs', payload).then((r) => r.data),
  jobs: () => api.get('/sources/jobs').then((r) => r.data),
  job: (id) => api.get(`/sources/jobs/${id}`).then((r) => r.data),
  cancelJob: (id, expected_version) => api.post(`/sources/jobs/${id}/cancel`, { expected_version }).then((r) => r.data),
}

/** Administrator-only local accounts and deployment settings. */
export const adminApi = {
  settings: () => api.get('/admin/settings').then((r) => r.data),
  updateSettings: (payload) => api.put('/admin/settings', payload).then((r) => r.data),
  users: () => api.get('/admin/users').then((r) => r.data),
  createUser: (payload) => api.post('/admin/users', payload).then((r) => r.data),
  setUserActive: (id, is_active) => api.patch(`/admin/users/${id}/active`, { is_active }).then((r) => r.data),
}

export const assessmentsApi = {
  sync: (mmsi, window = null) =>
    api
      .post('/alerts/assessments/sync', {
        lookback_hours: windowHours(window),
        ...(mmsi ? { mmsi } : {}),
        ...windowQuery(window),
      })
      .then(r => r.data),
  vessel: (mmsi) => api.get('/alerts/assessments', { params: { mmsi, limit: 100 } }).then(r => r.data),
}

export const casesApi = {
  list: () => api.get('/cases/').then(r => r.data),
  get: (id) => api.get(`/cases/${id}`).then(r => r.data),
  create: (assessment_id, title) => api.post('/cases/', { assessment_id, title }).then(r => r.data),
  /** Event-only case: the server creates revision 1 from the saved report in the same transaction. */
  createFromReport: (report_id, title) => api.post('/cases/', { report_id, title }).then(r => r.data),
  createFromSar: (sar_detection_id, title) => api.post('/cases/', { sar_detection_id, title }).then(r => r.data),
  addRevision: (id, report_id, expected_version) => api.post(`/cases/${id}/revisions`, { report_id, expected_version }).then(r => r.data),
  /** `action` is 'close' or 'reopen'; the server answers 409 when the case changed since `expected_version`. */
  transition: (id, action, expected_version, note) =>
    api.post(`/cases/${id}/${action}`, { expected_version, ...(note ? { note } : {}) }).then(r => r.data),
}

/** Stored alert records with an analyst lifecycle; not limited to the selected observation window. */
export const alertsApi = {
  stored: (status) => api.get('/alerts/stored', { params: { limit: 100, ...(status ? { status } : {}) } }).then(r => r.data),
  sync: (window = null) => api.post('/alerts/sync', {
    lookback_hours: windowHours(window),
    ...windowQuery(window),
  }).then(r => r.data),
  /** `action` is 'acknowledge', 'resolve' or 'reopen'; only resolve keeps a note. */
  transition: (id, action, expected_version, note) =>
    api.post(`/alerts/stored/${id}/${action}`, { expected_version, ...(note ? { note } : {}) }).then(r => r.data),
  review: (id, expected_version, state, assigned_to, reason) =>
    api.post(`/alerts/stored/${id}/review`, {
      expected_version, state,
      ...(assigned_to ? { assigned_to } : {}),
      ...(reason ? { reason } : {}),
    }).then(r => r.data),
  addNote: (id, expected_version, note) => api.post(`/alerts/stored/${id}/notes`, { expected_version, note }).then(r => r.data),
}

export const triageApi = {
  queue: () => api.get('/triage/assessments', { params: { limit: 50 } }).then(r => r.data),
  evidence: (mmsi, hours = 48) => api.get(`/triage/evidence/${mmsi}`, { params: { hours } }).then(r => r.data),
}

export const weatherApi = {
  vessel: (mmsi) => api.get(`/weather/${mmsi}`).then((r) => r.data),
}

export const sarApi = {
  detections: () => api.get('/sar/detections').then((r) => r.data),
  detection: (id) => api.get(`/sar/detections/${id}`).then((r) => r.data),
  create: (payload) => api.post('/sar/detections', payload).then((r) => r.data),
}

export const environmentApi = {
  regional: () => api.get('/environment/regional').then((r) => r.data),
}

export const boundariesApi = {
  list: () => api.get('/boundaries').then((r) => r.data),
}

export const encountersApi = {
  graph: (mmsi, hours = 48) => api.get(`/vessels/${mmsi}/encounters`, { params: { hours, hops: 2, max_nodes: 40, max_edges: 80 } }).then((r) => r.data),
}

export const oceanApi = {
  observations: () => api.get('/ocean/observations').then((r) => r.data),
  temperature: (latitude, longitude) => api.get('/ocean/temperature', { params: { latitude, longitude } }).then((r) => r.data),
  baseline: () => api.get('/ocean/baseline').then((r) => r.data),
  scanPlan: (budget, reserve_fraction = 0.2) => api.post('/ocean/scan-plans', { budget, reserve_fraction }).then((r) => r.data),
}

export const spillApi = {
  capabilities: () => api.get('/spill/capabilities').then((r) => r.data),
  jobs: () => api.get('/spill/jobs').then((r) => r.data),
  create: (payload) => api.post('/spill/jobs', payload).then((r) => r.data),
  get: (id) => api.get(`/spill/jobs/${id}`).then((r) => r.data),
  cancel: (id, expected_version) => api.post(`/spill/jobs/${id}/cancel`, { expected_version }).then((r) => r.data),
}

export const operationsApi = {
  status: () => api.get('/operations/status').then((r) => r.data),
}

export default api
