import { useState, useEffect } from 'react'
import { alertsApi } from '../lib/api'

export const useAlerts = (limit = 50) => {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true

    const fetchAlerts = async () => {
      try {
        const response = await alertsApi.getAlerts(limit)
        
        if (mounted) {
          setAlerts(response.data)
          setError(null)
        }
      } catch (err) {
        if (mounted) {
          setError(err.message)
          console.error('Error fetching alerts:', err)
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    fetchAlerts()
    
    // Refresh every 15 seconds
    const interval = setInterval(fetchAlerts, 15000)

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [limit])

  return { alerts, loading, error }
}
