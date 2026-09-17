import React, { useMemo } from 'react'
import { Polygon, Popup } from 'react-leaflet'
import { useMapData } from '../../hooks/useMapData'

// GeoJSON [lon, lat] rings -> Leaflet [lat, lon]; supports Polygon and MultiPolygon
const toLatLngs = (geometry) => {
  const ring = (coords) => coords.map(([lon, lat]) => [lat, lon])
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.map((poly) => poly.map(ring))
  return geometry.coordinates.map(ring)
}

const MPALayer = () => {
  const { data, loading, error } = useMapData('mpas')

  const polygons = useMemo(() => {
    if (!data || !data.features) return []

    return data.features.map((feature) => {
      const { geometry, properties } = feature
      const positions = toLatLngs(geometry)

      return (
        <Polygon
          key={properties.id}
          positions={positions}
          pathOptions={{
            color: '#10b981',
            fillColor: '#10b981',
            fillOpacity: 0.15,
            weight: 2,
            dashArray: '5, 10'
          }}
        >
          <Popup>
            <div className="text-sm">
              <h3 className="font-bold text-gray-800 mb-2">{properties.name}</h3>
              <div className="space-y-1">
                {properties.designation && (
                  <p><span className="font-semibold">Designation:</span> {properties.designation}</p>
                )}
                {properties.iucn_category && (
                  <p><span className="font-semibold">IUCN Category:</span> {properties.iucn_category}</p>
                )}
                {properties.country && (
                  <p><span className="font-semibold">Country:</span> {properties.country}</p>
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

export default MPALayer
