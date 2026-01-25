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
      <div className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/20 shadow-lg">
        <Ship className="w-5 h-5 text-cyan-300" />
        <div>
          <p className="text-xs text-blue-200">Active Vessels</p>
          <p className="text-lg font-bold bg-gradient-to-r from-white to-blue-100 bg-clip-text text-transparent">{stats.active_vessels}</p>
        </div>
      </div>

      <div className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/20 shadow-lg">
        <Droplet className="w-5 h-5 text-red-400" />
        <div>
          <p className="text-xs text-blue-200">Pollution Events</p>
          <p className="text-lg font-bold bg-gradient-to-r from-white to-blue-100 bg-clip-text text-transparent">{stats.pollution_events_week}</p>
        </div>
      </div>

      <div className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/20 shadow-lg">
        <Activity className="w-5 h-5 text-yellow-400" />
        <div>
          <p className="text-xs text-blue-200">High Risk</p>
          <p className="text-lg font-bold bg-gradient-to-r from-white to-blue-100 bg-clip-text text-transparent">{stats.high_risk_vessels}</p>
        </div>
      </div>

      <div className="flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-lg px-3 py-2 border border-white/20 shadow-lg">
        <Shield className="w-5 h-5 text-green-400" />
        <div>
          <p className="text-xs text-blue-200">MPAs</p>
          <p className="text-lg font-bold bg-gradient-to-r from-white to-blue-100 bg-clip-text text-transparent">{stats.mpas_monitored}</p>
        </div>
      </div>
    </div>
  )
}

export default StatsPanel
