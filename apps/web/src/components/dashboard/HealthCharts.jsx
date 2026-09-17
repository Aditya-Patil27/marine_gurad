import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { analyticsApi } from '../../lib/api'

const HealthCharts = () => {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await analyticsApi.getOHI(1, 30)
        
        const chartData = response.data.dates.map((date, index) => ({
          date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          ohi: response.data.ohi_scores[index],
          temperature: response.data.temperatures[index],
          ph: response.data.ph_values[index] ? response.data.ph_values[index] * 10 : null, // Scale for visibility
          forecast: response.data.forecasts[index]
        }))
        
        setData(chartData)
        setError(null)
      } catch (err) {
        setError(err.message)
        console.error('Error fetching OHI data:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 60000) // Refresh every minute

    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className="text-white text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
        <p className="mt-2 text-sm text-gray-400">Loading health data...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gradient-to-r from-red-900/50 to-red-800/50 backdrop-blur-sm text-red-200 p-4 rounded-lg border border-red-700/30">
        <p className="text-sm">Error loading health data: {error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold bg-gradient-to-r from-blue-200 to-cyan-200 bg-clip-text text-transparent">Ocean Health Trends</h2>

      <div className="bg-gradient-to-br from-gray-800/80 to-blue-950/40 backdrop-blur-sm rounded-xl p-4 border border-blue-800/30 shadow-xl">
        <h3 className="text-sm font-semibold text-blue-200 mb-4">Ocean Health Index</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: '10px' }} />
            <YAxis stroke="#9ca3af" style={{ fontSize: '10px' }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #3b82f6', borderRadius: '0.5rem' }}
              labelStyle={{ color: '#f3f4f6' }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Line type="monotone" dataKey="ohi" stroke="#3b82f6" strokeWidth={2} dot={false} name="OHI Score" />
            {data.some(d => d.forecast) && (
              <Line type="monotone" dataKey="forecast" stroke="#8b5cf6" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Forecast" />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-gradient-to-br from-gray-800/80 to-blue-950/40 backdrop-blur-sm rounded-xl p-4 border border-blue-800/30 shadow-xl">
        <h3 className="text-sm font-semibold text-blue-200 mb-4">Temperature & pH</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: '10px' }} />
            <YAxis stroke="#9ca3af" style={{ fontSize: '10px' }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #3b82f6', borderRadius: '0.5rem' }}
              labelStyle={{ color: '#f3f4f6' }}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <Line type="monotone" dataKey="temperature" stroke="#f59e0b" strokeWidth={2} dot={false} name="Temp (°C)" />
            <Line type="monotone" dataKey="ph" stroke="#10b981" strokeWidth={2} dot={false} name="pH (×10)" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default HealthCharts
