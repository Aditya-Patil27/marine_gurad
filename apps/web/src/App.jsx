import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import MapPage from './pages/MapPage'
import NotBuiltYet from './pages/NotBuiltYet'
import { AlertsPage, EvidencePage, ReportsPage } from './pages/Cases'

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Navigate to="/map" replace />} />
        <Route path="map" element={<MapPage />} />
        <Route
          path="alerts"
          element={<AlertsPage />}
        />
        <Route
          path="vessels/:mmsi?"
          element={<EvidencePage />}
        />
        <Route
          path="reports"
          element={<ReportsPage />}
        />
        <Route
          path="spills"
          element={<NotBuiltYet title="Spill simulator" what="Drop a pin to see where oil drifts in 6, 12 and 24 hours and what it reaches." />}
        />
        <Route
          path="settings"
          element={<NotBuiltYet title="Settings" what="Alert thresholds, data sources and who receives reports." />}
        />
        <Route path="*" element={<Navigate to="/map" replace />} />
      </Route>
    </Routes>
  )
}
