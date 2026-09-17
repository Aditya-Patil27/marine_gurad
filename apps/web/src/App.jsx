import React, { useState } from 'react'
import OceanMap from './components/map/OceanMap'
import AlertFeed from './components/dashboard/AlertFeed'
import HealthCharts from './components/dashboard/HealthCharts'
import StatsPanel from './components/dashboard/StatsPanel'
import ChatBot from './components/chat/ChatBot'

function App() {
  const [selectedLayer, setSelectedLayer] = useState('vessels')

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-gray-900 via-blue-950 to-gray-900">
      {/* Header */}
      <header className="bg-gradient-premium text-white p-4 shadow-2xl border-b border-blue-800/30">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-cyan-500 rounded-lg flex items-center justify-center shadow-lg">
              <span className="text-2xl">🌊</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-200 to-cyan-200 bg-clip-text text-transparent">SamudraSense</h1>
              <p className="text-xs text-blue-200">AI Ocean Intelligence Platform</p>
            </div>
          </div>
          <StatsPanel />
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-80 bg-gradient-to-b from-gray-900 to-gray-950 overflow-y-auto border-r border-blue-900/30 shadow-xl">
          <div className="p-4">
            <AlertFeed />
          </div>
        </aside>

        {/* Map */}
        <main className="flex-1 relative">
          <OceanMap selectedLayer={selectedLayer} onLayerChange={setSelectedLayer} />
        </main>

        {/* Right Panel */}
        <aside className="w-96 bg-gradient-to-b from-gray-900 to-gray-950 overflow-y-auto border-l border-blue-900/30 shadow-xl">
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
