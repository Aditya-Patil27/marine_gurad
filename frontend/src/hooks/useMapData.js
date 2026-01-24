import { useState, useEffect } from 'react'
import { mapApi } from '../lib/api'

export const useMapData = (layerType, bbox = null) => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let mounted = true

    const fetchData = async () => {
      try {
        setLoading(true)
        const response = await mapApi.getLayers(layerType, bbox)
        
        if (mounted) {
          setData(response.data)
          setError(null)
        }
      } catch (err) {
        if (mounted) {
          setError(err.message)
          console.error('Error fetching map data:', err)
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    fetchData()
    
    // Refresh every 30 seconds for real-time updates
    const interval = setInterval(fetchData, 30000)

    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [layerType, bbox])

  return { data, loading, error }
}
