import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { StatementImport } from './pages/StatementImport'
import { Layout } from './components/Layout'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout><Dashboard /></Layout>} />
        <Route path="/import" element={<StatementImport />} />
      </Routes>
    </Router>
  )
}

export default App