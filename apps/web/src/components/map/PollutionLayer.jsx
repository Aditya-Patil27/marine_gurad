import React, { useMemo } from 'react'
import { Polygon, Popup } from 'react-leaflet'
import { useMapData } from '../../hooks/useMapData'

// GeoJSON [lon, lat] rings -> Leaflet [lat, lon]; supports Polygon and MultiPolygon
const toLatLngs = (geometry) => {
  const ring = (coords) => coords.map(([lon, lat]) => [lat, lon])
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.map((poly) => poly.map(ring))
  return geometry.coordinates.map(ring)
}

const PollutionLayer = () => {
  const { data, loading, error } = useMapData('pollution')

  const polygons = useMemo(() => {
    if (!data || !data.features) return []

    const typeColors = {
      OIL: '#1a1a1a',
      PLASTIC: '#3b82f6',
      ALGAE: '#16a34a'
    }

    return data.features.map((feature) => {
      const { geometry, properties } = feature
      const positions = toLatLngs(geometry)
      const color = typeColors[properties.type] || '#6b7280'

      return (
        <Polygon
          key={properties.id}
          positions={positions}
          pathOptions={{
            color: color,
            fillColor: color,
            fillOpacity: 0.4,
            weight: 2
          }}
        >
          <Popup>
            <div className="text-sm">
              <h3 className="font-bold text-gray-800 mb-2">Pollution Event</h3>
              <div className="space-y-1">
                <p><span className="font-semibold">Type:</span> {properties.type}</p>
                <p><span className="font-semibold">Severity:</span> {(properties.severity * 100).toFixed(0)}%</p>
                <p><span className="font-semibold">Detected:</span> {new Date(properties.detected_at).toLocaleString()}</p>
                {properties.confidence != null && (
                  <p><span className="font-semibold">Confidence:</span> {(properties.confidence * 100).toFixed(0)}%</p>
                )}
              </div>
            </div>
          </Popup>
        </Polygon>
      )
    })
  }, [data])

  if (loading || error) return null

  return <>{polygons}</>
}

export default PollutionLayer
