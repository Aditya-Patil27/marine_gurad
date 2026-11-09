import { Navigate, Route, Routes } from 'react-router-dom'
import Shell from './components/Shell'
import MapPage from './pages/MapPage'
import Overview from './pages/Overview'
import Operations from './pages/Operations'
import SpillPage from './pages/SpillPage'
import OceanPage from './pages/OceanPage'
import DetectionsPage from './pages/DetectionsPage'
import { AlertsPage, EvidencePage, InvestigationCasesPage, ReportsPage } from './pages/Cases'
import { ReplayWindowProvider } from './lib/replayWindow'

export default function App() {
  return (
    <ReplayWindowProvider>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="overview" element={<Overview />} />
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
          <Route path="reports/:id" element={<ReportsPage />} />
          <Route path="cases" element={<InvestigationCasesPage />} />
          <Route path="ocean" element={<OceanPage />} />
          <Route path="detections" element={<DetectionsPage />} />
          <Route path="spills" element={<SpillPage />} />
          <Route path="settings" element={<Operations />} />
          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Route>
      </Routes>
    </ReplayWindowProvider>
  )
}
