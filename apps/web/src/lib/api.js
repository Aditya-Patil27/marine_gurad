import axios from 'axios'

// Empty by default: requests go to /api on the same origin and the Vite dev server
// proxies them to the backend (no CORS). Set VITE_API_URL when hosting the API elsewhere.
export const API_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 30000,
})

export const vesselsApi = {
  list: (hours = 24) => api.get('/vessels/', { params: { hours } }).then((r) => r.data),
  get: (mmsi, hours = 24) => api.get(`/vessels/${mmsi}`, { params: { hours } }).then((r) => r.data),
}

export const mapApi = {
  zones: () => api.get('/map/zones').then((r) => r.data),
}

export default api
