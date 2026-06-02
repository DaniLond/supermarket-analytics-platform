import { Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import ExecutiveSummary from './pages/ExecutiveSummary'
import AnalyticsExploration from './pages/AnalyticsExploration'
import AdvancedAnalysis from './pages/AdvancedAnalysis'
import Recommendations from './pages/Recommendations'
import DataManagement from './pages/DataManagement'

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <Routes>
          <Route path="/" element={<ExecutiveSummary />} />
          <Route path="/analytics" element={<AnalyticsExploration />} />
          <Route path="/advanced" element={<AdvancedAnalysis />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/data" element={<DataManagement />} />
        </Routes>
      </main>
    </div>
  )
}
