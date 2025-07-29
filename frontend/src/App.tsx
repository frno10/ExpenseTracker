import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Expenses } from './pages/Expenses'
import { Budgets } from './pages/Budgets'
import { Analytics } from './pages/Analytics'
import { RecurringExpensesPage } from './pages/RecurringExpensesPage'
import { StatementImport } from './pages/StatementImport'
import { Layout } from './components/Layout'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout><Dashboard /></Layout>} />
        <Route path="/expenses" element={<Layout><Expenses /></Layout>} />
        <Route path="/budgets" element={<Layout><Budgets /></Layout>} />
        <Route path="/recurring" element={<Layout><RecurringExpensesPage /></Layout>} />
        <Route path="/analytics" element={<Layout><Analytics /></Layout>} />
        <Route path="/import" element={<StatementImport />} />
      </Routes>
    </Router>
  )
}

export default App