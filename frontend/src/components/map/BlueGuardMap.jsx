import React, { useState } from 'react'
import { MapContainer, TileLayer, LayersControl, ZoomControl } from 'react-leaflet'
import LayerControl from './LayerControl'
import VesselMarkers from './VesselMarkers'
import PollutionLayer from './PollutionLayer'
import MPALayer from './MPALayer'
import 'leaflet/dist/leaflet.css'

const { BaseLayer } = LayersControl

// Default center coordinates - can be overridden via environment variables
const DEFAULT_CENTER = [
  parseFloat(import.meta.env.VITE_MAP_CENTER_LAT) || 20.0,  // Default to global ocean view
  parseFloat(import.meta.env.VITE_MAP_CENTER_LNG) || 77.0   // Indian Ocean region
]
const DEFAULT_ZOOM = parseInt(import.meta.env.VITE_MAP_ZOOM) || 4

const BlueGuardMap = ({ selectedLayer, onLayerChange }) => {
  const [center] = useState(DEFAULT_CENTER)
  const [zoom] = useState(DEFAULT_ZOOM)
  const [layers, setLayers] = useState({
    vessels: true,
    pollution: true,
    mpas: true
  })

  const toggleLayer = (layerName) => {
    setLayers(prev => ({
      ...prev,
      [layerName]: !prev[layerName]
    }))
  }

  return (
    <div className="relative w-full h-full">
      <MapContainer
        center={center}
        zoom={zoom}
        className="w-full h-full"
        zoomControl={false}
      >
        <LayersControl position="topright">
          <BaseLayer checked name="Ocean Base">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </BaseLayer>
          <BaseLayer name="Satellite">
            <TileLayer
              attribution='&copy; <a href="https://www.esri.com/">Esri</a>'
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </BaseLayer>
        </LayersControl>

        <ZoomControl position="bottomright" />

        {layers.mpas && <MPALayer />}
        {layers.pollution && <PollutionLayer />}
        {layers.vessels && <VesselMarkers />}
      </MapContainer>

      <LayerControl layers={layers} onToggle={toggleLayer} />
    </div>
  )
}

export default BlueGuardMap
