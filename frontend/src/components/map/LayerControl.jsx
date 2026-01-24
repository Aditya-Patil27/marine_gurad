import React from 'react'
import { Ship, Droplet, Shield } from 'lucide-react'

const LayerControl = ({ layers, onToggle }) => {
  return (
    <div className="absolute top-4 left-4 z-[1000] bg-white rounded-lg shadow-lg p-4 space-y-3">
      <h3 className="font-semibold text-gray-800 text-sm mb-2">Map Layers</h3>
      
      <label className="flex items-center space-x-2 cursor-pointer">
        <input
          type="checkbox"
          checked={layers.vessels}
          onChange={() => onToggle('vessels')}
          className="w-4 h-4 text-ocean-600 rounded"
        />
        <Ship className="w-4 h-4 text-ocean-600" />
        <span className="text-sm text-gray-700">Vessels</span>
      </label>

      <label className="flex items-center space-x-2 cursor-pointer">
        <input
          type="checkbox"
          checked={layers.pollution}
          onChange={() => onToggle('pollution')}
          className="w-4 h-4 text-red-600 rounded"
        />
        <Droplet className="w-4 h-4 text-red-600" />
        <span className="text-sm text-gray-700">Pollution</span>
      </label>

      <label className="flex items-center space-x-2 cursor-pointer">
        <input
          type="checkbox"
          checked={layers.mpas}
          onChange={() => onToggle('mpas')}
          className="w-4 h-4 text-green-600 rounded"
        />
        <Shield className="w-4 h-4 text-green-600" />
        <span className="text-sm text-gray-700">Protected Areas</span>
      </label>
    </div>
  )
}

export default LayerControl
