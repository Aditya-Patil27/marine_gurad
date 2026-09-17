import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import MapPage from './pages/MapPage'
import NotBuiltYet from './pages/NotBuiltYet'

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Navigate to="/map" replace />} />
        <Route path="map" element={<MapPage />} />
        <Route
          path="alerts"
          element={<NotBuiltYet title="Alert triage" what="Sort alerts into New, Explained by weather, In review, Awaiting sign-off and Sent." />}
        />
        <Route
          path="vessels/:mmsi?"
          element={<NotBuiltYet title="Vessel evidence" what="The full case for one vessel: track, radar crop, speed profile and who it met." />}
        />
        <Route
          path="reports"
          element={<NotBuiltYet title="Incident reports" what="Draft reports where every figure links to its source, ready for an officer to sign." />}
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
