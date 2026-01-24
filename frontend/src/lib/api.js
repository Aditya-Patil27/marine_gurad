import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const mapApi = {
  getLayers: (layerType, bbox) => {
    const params = { layer_type: layerType }
    if (bbox) params.bbox = bbox
    return api.get('/map/layers', { params })
  },
}

export const analyticsApi = {
  getOHI: (regionId = 1, days = 30) => {
    return api.get('/analytics/ohi', { params: { region_id: regionId, days } })
  },
  getStatistics: () => {
    return api.get('/analytics/statistics')
  },
}

export const alertsApi = {
  getAlerts: (limit = 50, severity = null) => {
    const params = { limit }
    if (severity) params.severity = severity
    return api.get('/alerts', { params })
  },
}

export const ingestApi = {
  ingestAIS: (records) => {
    return api.post('/ingest/ais', { records })
  },
  processSatelliteImage: (imageUrl) => {
    return api.post('/ingest/satellite-image', { image_url: imageUrl })
  },
}

export default api
