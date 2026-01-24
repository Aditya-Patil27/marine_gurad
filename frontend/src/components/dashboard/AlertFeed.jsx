import React from 'react'
import { AlertTriangle, Droplet, Ship, Shield } from 'lucide-react'
import { useAlerts } from '../../hooks/useAlerts'

const AlertFeed = () => {
  const { alerts, loading, error } = useAlerts(20)

  const getAlertIcon = (type) => {
    switch (type) {
      case 'POLLUTION':
        return <Droplet className="w-5 h-5 text-red-500" />
      case 'IUU_FISHING':
        return <Ship className="w-5 h-5 text-yellow-500" />
      case 'MPA_VIOLATION':
        return <Shield className="w-5 h-5 text-orange-500" />
      default:
        return <AlertTriangle className="w-5 h-5 text-gray-500" />
    }
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'HIGH':
        return 'border-l-red-500 bg-red-50'
      case 'MEDIUM':
        return 'border-l-yellow-500 bg-yellow-50'
      case 'LOW':
        return 'border-l-green-500 bg-green-50'
      default:
        return 'border-l-gray-500 bg-gray-50'
    }
  }

  if (loading) {
    return (
      <div className="text-white text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ocean-500 mx-auto"></div>
        <p className="mt-2 text-sm text-gray-400">Loading alerts...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900 text-red-200 p-4 rounded-lg">
        <p className="text-sm">Error loading alerts: {error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Alert Feed</h2>
        <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
          {alerts.length}
        </span>
      </div>

      <div className="space-y-2 max-h-[calc(100vh-200px)] overflow-y-auto">
        {alerts.length === 0 ? (
          <div className="text-gray-400 text-sm text-center py-8">
            No active alerts
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              className={`border-l-4 p-3 rounded ${getSeverityColor(alert.severity)}`}
            >
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 mt-0.5">
                  {getAlertIcon(alert.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900">
                    {alert.title}
                  </p>
                  <p className="text-xs text-gray-700 mt-1">
                    {alert.description}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    {new Date(alert.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default AlertFeed
