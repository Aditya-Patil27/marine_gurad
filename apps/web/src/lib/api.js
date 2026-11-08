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
  return error?.message || ''
}

export const reportsApi = {
  list: () => api.get('/reports/').then((r) => r.data),
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
  sign: (id, officer, reviewed) => api.post(`/reports/${id}/sign`, { officer, reviewed }).then((r) => r.data),
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
  addRevision: (id, report_id, expected_version) => api.post(`/cases/${id}/revisions`, { report_id, expected_version }).then(r => r.data),
  /** `action` is 'close' or 'reopen'; the server answers 409 when the case changed since `expected_version`. */
  transition: (id, action, expected_version, note) =>
    api.post(`/cases/${id}/${action}`, { expected_version, ...(note ? { note } : {}) }).then(r => r.data),
}

/** Stored alert records with an analyst lifecycle; not limited to the selected observation window. */
export const alertsApi = {
  stored: (status) => api.get('/alerts/stored', { params: { limit: 100, ...(status ? { status } : {}) } }).then(r => r.data),
  sync: () => api.post('/alerts/sync').then(r => r.data),
  /** `action` is 'acknowledge', 'resolve' or 'reopen'; only resolve keeps a note. */
  transition: (id, action, expected_version, note) =>
    api.post(`/alerts/stored/${id}/${action}`, { expected_version, ...(note ? { note } : {}) }).then(r => r.data),
}

export const triageApi = {
  queue: () => api.get('/triage/assessments', { params: { limit: 50 } }).then(r => r.data),
}

export const weatherApi = {
  vessel: (mmsi) => api.get(`/weather/${mmsi}`).then((r) => r.data),
}

export const sarApi = {
  detections: () => api.get('/sar/detections').then((r) => r.data),
}

export const environmentApi = {
  regional: () => api.get('/environment/regional').then((r) => r.data),
}

export default api
