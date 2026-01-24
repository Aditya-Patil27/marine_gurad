import React, { useState, useEffect } from 'react'
import { Ship, Droplet, Shield, Activity } from 'lucide-react'
import { analyticsApi } from '../../lib/api'

const StatsPanel = () => {
  const [stats, setStats] = useState({
    active_vessels: 0,
    pollution_events_week: 0,
    high_risk_vessels: 0,
    mpas_monitored: 0
  })

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await analyticsApi.getStatistics()
        setStats(response.data)
      } catch (err) {
        console.error('Error fetching statistics:', err)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 30000) // Refresh every 30 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center space-x-6">
      <div className="flex items-center space-x-2">
        <Ship className="w-5 h-5 text-ocean-300" />
        <div>
          <p className="text-xs text-ocean-200">Active Vessels</p>
          <p className="text-lg font-bold text-white">{stats.active_vessels}</p>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Droplet className="w-5 h-5 text-red-400" />
        <div>
          <p className="text-xs text-ocean-200">Pollution Events</p>
          <p className="text-lg font-bold text-white">{stats.pollution_events_week}</p>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Activity className="w-5 h-5 text-yellow-400" />
        <div>
          <p className="text-xs text-ocean-200">High Risk</p>
          <p className="text-lg font-bold text-white">{stats.high_risk_vessels}</p>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Shield className="w-5 h-5 text-green-400" />
        <div>
          <p className="text-xs text-ocean-200">MPAs</p>
          <p className="text-lg font-bold text-white">{stats.mpas_monitored}</p>
        </div>
      </div>
    </div>
  )
}

export default StatsPanel
