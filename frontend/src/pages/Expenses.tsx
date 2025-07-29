import { useState, useEffect } from 'react'
import { 
  Search, 
  Filter, 
  Plus, 
  Download, 
  Edit, 
  Trash2, 
  Calendar,
  DollarSign,
  Tag,
  Building,
  ChevronDown,
  X
} from 'lucide-react'
import { apiClient } from '../lib/api'
import { ExpenseForm } from '../components/ExpenseForm'

interface Expense {
  id: string
  amount: number
  description: string
  category: string
  date: string
  account?: string
  payment_method?: string
  tags?: string[]
  notes?: string
}

interface FilterState {
  search: string
  category: string
  account: string
  dateFrom: string
  dateTo: string
  minAmount: string
  maxAmount: string
}

export function Expenses() {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(false)
  const [selectedExpenses, setSelectedExpenses] = useState<string[]>([])
  const [showExpenseForm, setShowExpenseForm] = useState(false)
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null)
  const [filters, setFilters] = useState<FilterState>({
    search: '',
    category: '',
    account: '',
    dateFrom: '',
    dateTo: '',
    minAmount: '',
    maxAmount: ''
  })
  const [categories, setCategories] = useState<string[]>([])
  const [accounts, setAccounts] = useState<string[]>([])

  useEffect(() => {
    loadExpenses()
    loadFilterOptions()
  }, [])

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      loadExpenses()
    }, 300)

    return () => clearTimeout(debounceTimer)
  }, [filters])

  const loadExpenses = async () => {
    try {
      setLoading(true)
      
      const params: any = {}
      if (filters.search) params.search = filters.search
      if (filters.category) params.category = filters.category
      if (filters.account) params.account = filters.account
      if (filters.dateFrom) params.date_from = filters.dateFrom
      if (filters.dateTo) params.date_to = filters.dateTo
      if (filters.minAmount) params.min_amount = parseFloat(filters.minAmount)
      if (filters.maxAmount) params.max_amount = parseFloat(filters.maxAmount)

      const data = await apiClient.getExpenses(params)
      setExpenses(data.items || [])
    } catch (error) {
      console.error('Error loading expenses:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadFilterOptions = async () => {
    try {
      const [categoriesData, accountsData] = await Promise.all([
        apiClient.getCategories().catch(() => []),
        apiClient.getAccounts().catch(() => [])
      ])
      
      setCategories(categoriesData.map((c: any) => c.name))
      setAccounts(accountsData.map((a: any) => a.name))
    } catch (error) {
      console.error('Error loading filter options:', error)
    }
  }

  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const clearFilters = () => {
    setFilters({
      search: '',
      category: '',
      account: '',
      dateFrom: '',
      dateTo: '',
      minAmount: '',
      maxAmount: ''
    })
  }

  const handleSelectExpense = (expenseId: string) => {
    setSelectedExpenses(prev => 
      prev.includes(expenseId) 
        ? prev.filter(id => id !== expenseId)
        : [...prev, expenseId]
    )
  }

  const handleSelectAll = () => {
    if (selectedExpenses.length === expenses.length) {
      setSelectedExpenses([])
    } else {
      setSelectedExpenses(expenses.map(e => e.id))
    }
  }

  const handleBulkDelete = async () => {
    if (selectedExpenses.length === 0) return
    
    if (confirm(`Delete ${selectedExpenses.length} selected expenses?`)) {
      try {
        await apiClient.bulkDeleteExpenses(selectedExpenses)
        setSelectedExpenses([])
        loadExpenses()
      } catch (error) {
        console.error('Error deleting expenses:', error)
      }
    }
  }

  const handleExport = async () => {
    try {
      const params: any = { format: 'csv' }
      if (filters.search) params.search = filters.search
      if (filters.category) params.category = filters.category
      if (filters.account) params.account = filters.account
      if (filters.dateFrom) params.date_from = filters.dateFrom
      if (filters.dateTo) params.date_to = filters.dateTo
      if (filters.minAmount) params.min_amount = parseFloat(filters.minAmount)
      if (filters.maxAmount) params.max_amount = parseFloat(filters.maxAmount)

      const blob = await apiClient.exportExpenses(params)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `expenses-${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error exporting expenses:', error)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const hasActiveFilters = Object.values(filters).some(value => value !== '')

  const handleAddExpense = () => {
    setEditingExpense(null)
    setShowExpenseForm(true)
  }

  const handleEditExpense = (expense: Expense) => {
    setEditingExpense(expense)
    setShowExpenseForm(true)
  }

  const handleDeleteExpense = async (expenseId: string) => {
    if (confirm('Delete this expense?')) {
      try {
        await apiClient.deleteExpense(expenseId)
        loadExpenses()
      } catch (error) {
        console.error('Error deleting expense:', error)
      }
    }
  }

  const handleSaveExpense = async (expenseData: any) => {
    try {
      if (editingExpense) {
        await apiClient.updateExpense(editingExpense.id, expenseData)
      } else {
        await apiClient.createExpense(expenseData)
      }
      loadExpenses()
      setShowExpenseForm(false)
      setEditingExpense(null)
    } catch (error) {
      console.error('Error saving expense:', error)
      throw error
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Expenses</h2>
          <p className="text-muted-foreground">
            Manage and track your expense transactions
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleExport}
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </button>
          <button 
            onClick={handleAddExpense}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Expense
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search expenses..."
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium transition-colors ${
              hasActiveFilters 
                ? 'border-primary bg-primary text-primary-foreground' 
                : 'border-input bg-background hover:bg-accent hover:text-accent-foreground'
            }`}
          >
            <Filter className="h-4 w-4 mr-2" />
            Filters
            {hasActiveFilters && (
              <span className="ml-2 bg-primary-foreground text-primary rounded-full px-2 py-0.5 text-xs">
                {Object.values(filters).filter(v => v !== '').length}
              </span>
            )}
          </button>
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <div className="border rounded-lg p-4 bg-muted/30">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="text-sm font-medium mb-1 block">Category</label>
                <select
                  value={filters.category}
                  onChange={(e) => handleFilterChange('category', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">All Categories</option>
                  {categories.map(category => (
                    <option key={category} value={category}>{category}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="text-sm font-medium mb-1 block">Account</label>
                <select
                  value={filters.account}
                  onChange={(e) => handleFilterChange('account', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">All Accounts</option>
                  {accounts.map(account => (
                    <option key={account} value={account}>{account}</option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="text-sm font-medium mb-1 block">Date From</label>
                <input
                  type="date"
                  value={filters.dateFrom}
                  onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              
              <div>
                <label className="text-sm font-medium mb-1 block">Date To</label>
                <input
                  type="date"
                  value={filters.dateTo}
                  onChange={(e) => handleFilterChange('dateTo', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              
              <div>
                <label className="text-sm font-medium mb-1 block">Min Amount</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={filters.minAmount}
                  onChange={(e) => handleFilterChange('minAmount', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              
              <div>
                <label className="text-sm font-medium mb-1 block">Max Amount</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={filters.maxAmount}
                  onChange={(e) => handleFilterChange('maxAmount', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
            
            {hasActiveFilters && (
              <div className="mt-4 flex justify-end">
                <button
                  onClick={clearFilters}
                  className="inline-flex items-center justify-center rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
                >
                  <X className="h-3 w-3 mr-1" />
                  Clear Filters
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bulk Actions */}
      {selectedExpenses.length > 0 && (
        <div className="flex items-center justify-between p-3 bg-primary/10 border border-primary/20 rounded-lg">
          <span className="text-sm font-medium">
            {selectedExpenses.length} expense{selectedExpenses.length > 1 ? 's' : ''} selected
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleBulkDelete}
              className="inline-flex items-center justify-center rounded-md bg-destructive px-3 py-1.5 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 transition-colors"
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Delete
            </button>
          </div>
        </div>
      )}

      {/* Expenses Table */}
      <div className="border rounded-lg">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : expenses.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b bg-muted/30">
                <tr>
                  <th className="text-left p-4">
                    <input
                      type="checkbox"
                      checked={selectedExpenses.length === expenses.length && expenses.length > 0}
                      onChange={handleSelectAll}
                      className="rounded border-input"
                    />
                  </th>
                  <th className="text-left p-4 font-medium">Date</th>
                  <th className="text-left p-4 font-medium">Description</th>
                  <th className="text-left p-4 font-medium">Category</th>
                  <th className="text-left p-4 font-medium">Account</th>
                  <th className="text-right p-4 font-medium">Amount</th>
                  <th className="text-right p-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {expenses.map((expense) => (
                  <tr key={expense.id} className="border-b hover:bg-muted/30">
                    <td className="p-4">
                      <input
                        type="checkbox"
                        checked={selectedExpenses.includes(expense.id)}
                        onChange={() => handleSelectExpense(expense.id)}
                        className="rounded border-input"
                      />
                    </td>
                    <td className="p-4 text-sm">
                      {new Date(expense.date).toLocaleDateString()}
                    </td>
                    <td className="p-4">
                      <div>
                        <p className="font-medium text-sm">{expense.description}</p>
                        {expense.notes && (
                          <p className="text-xs text-muted-foreground mt-1">{expense.notes}</p>
                        )}
                        {expense.tags && expense.tags.length > 0 && (
                          <div className="flex gap-1 mt-1">
                            {expense.tags.map(tag => (
                              <span key={tag} className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs bg-primary/10 text-primary">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="p-4 text-sm">{expense.category}</td>
                    <td className="p-4 text-sm">{expense.account || '-'}</td>
                    <td className="p-4 text-right font-medium">
                      {formatCurrency(expense.amount)}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button 
                          onClick={() => handleEditExpense(expense)}
                          className="p-1 hover:bg-muted rounded"
                        >
                          <Edit className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => handleDeleteExpense(expense.id)}
                          className="p-1 hover:bg-muted rounded text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <DollarSign className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No expenses found</h3>
            <p className="text-muted-foreground mb-4">
              {hasActiveFilters 
                ? 'Try adjusting your filters or search terms.'
                : 'Import a statement or add your first expense to get started.'
              }
            </p>
            {!hasActiveFilters && (
              <button 
                onClick={handleAddExpense}
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Expense
              </button>
            )}
          </div>
        )}
      </div>

      {/* Expense Form Modal */}
      <ExpenseForm
        expense={editingExpense}
        isOpen={showExpenseForm}
        onClose={() => {
          setShowExpenseForm(false)
          setEditingExpense(null)
        }}
        onSave={handleSaveExpense}
      />
    </div>
  )
}