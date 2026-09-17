import React, { useMemo } from 'react'
import { Marker, Popup, CircleMarker } from 'react-leaflet'
import { useMapData } from '../../hooks/useMapData'
import L from 'leaflet'

// Fix for default marker icon
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
})

const VesselMarkers = () => {
  const { data, loading, error } = useMapData('vessels')

  const markers = useMemo(() => {
    if (!data || !data.features) return []

    return data.features.map((feature) => {
      const { geometry, properties } = feature
      const [lon, lat] = geometry.coordinates
      const riskLevel = properties.risk_score > 0.7 ? 'high' : properties.risk_score > 0.4 ? 'medium' : 'low'
      
      const colors = {
        high: '#ef4444',
        medium: '#f59e0b',
        low: '#10b981'
      }

      return (
        <CircleMarker
          key={properties.mmsi}
          center={[lat, lon]}
          radius={6}
          pathOptions={{
            fillColor: colors[riskLevel],
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
          }}
        >
          <Popup>
            <div className="text-sm">
              <h3 className="font-bold text-gray-800 mb-2">Vessel {properties.mmsi}</h3>
              <div className="space-y-1">
                <p><span className="font-semibold">Type:</span> {properties.vessel_type || 'Unknown'}</p>
                <p><span className="font-semibold">Flag:</span> {properties.flag || 'N/A'}</p>
                <p><span className="font-semibold">Speed:</span> {properties.speed != null ? `${properties.speed.toFixed(1)} kn` : 'N/A'}</p>
                <p><span className="font-semibold">Course:</span> {properties.course != null ? `${properties.course.toFixed(0)}°` : 'N/A'}</p>
                <p>
                  <span className="font-semibold">Risk:</span> 
                  <span className={`ml-1 px-2 py-0.5 rounded text-xs text-white ${
                    riskLevel === 'high' ? 'bg-red-500' : riskLevel === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`}>
                    {(properties.risk_score * 100).toFixed(0)}%
                  </span>
                </p>
                {properties.is_dark && (
                  <p className="text-red-600 font-semibold">⚠️ Dark Vessel</p>
                )}
              </div>
            </div>
          </Popup>
        </CircleMarker>
      )
    })
  }, [data])

  if (loading) {
    return (
      <div className="absolute top-20 left-4 z-[1000] bg-white rounded px-3 py-2 shadow text-sm">
        Loading vessels...
      </div>
    )
  }

  if (error) {
    return (
      <div className="absolute top-20 left-4 z-[1000] bg-red-100 rounded px-3 py-2 shadow text-sm text-red-700">
        Error loading vessels: {error}
      </div>
    )
  }

  return <>{markers}</>
}

export default VesselMarkers
