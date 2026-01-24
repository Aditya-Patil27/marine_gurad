import React, { useState } from 'react'
import BlueGuardMap from './components/map/BlueGuardMap'
import AlertFeed from './components/dashboard/AlertFeed'
import HealthCharts from './components/dashboard/HealthCharts'
import StatsPanel from './components/dashboard/StatsPanel'
import ChatBot from './components/chat/ChatBot'

function App() {
  const [selectedLayer, setSelectedLayer] = useState('vessels')

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Header */}
      <header className="bg-ocean-800 text-white p-4 shadow-lg">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-ocean-500 rounded-lg flex items-center justify-center">
              <span className="text-2xl">🌊</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold">BlueGuard</h1>
              <p className="text-xs text-ocean-200">AI Ocean Intelligence Platform</p>
            </div>
          </div>
          <StatsPanel />
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-80 bg-gray-800 overflow-y-auto border-r border-gray-700">
          <div className="p-4">
            <AlertFeed />
          </div>
        </aside>

        {/* Map */}
        <main className="flex-1 relative">
          <BlueGuardMap selectedLayer={selectedLayer} onLayerChange={setSelectedLayer} />
        </main>

        {/* Right Panel */}
        <aside className="w-96 bg-gray-800 overflow-y-auto border-l border-gray-700">
          <div className="p-4">
            <HealthCharts />
          </div>
        </aside>
      </div>

      {/* Marine Intelligence Assistant (MIA) Chatbot */}
      <ChatBot />
    </div>
  )
}

export default App
