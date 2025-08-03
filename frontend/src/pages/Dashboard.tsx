import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Upload, 
  Plus, 
  TrendingUp, 
  TrendingDown, 
  Target, 
  DollarSign, 
  Calendar,
  AlertTriangle,
  FileText,
  CreditCard,
  PieChart,
  Bell
} from 'lucide-react'
import { apiClient } from '../lib/api-simple'

interface DashboardStats {
  totalExpenses: number
  monthlySpending: number
  categoriesCount: number
  budgetUsage: number
  recentExpenses: Expense[]
  budgetAlerts: BudgetAlert[]
  monthlyTrend: number
}

interface Expense {
  id: string
  amount: number
  description: string
  category: string
  date: string
  account?: string
}

interface BudgetAlert {
  id: string
  budgetName: string
  message: string
  type: 'warning' | 'exceeded' | 'approaching'
  percentage: number
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalExpenses: 0,
    monthlySpending: 0,
    categoriesCount: 0,
    budgetUsage: 0,
    recentExpenses: [],
    budgetAlerts: [],
    monthlyTrend: 0
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      
      // Load dashboard statistics
      const [statsData, expensesData, alertsData] = await Promise.all([
        apiClient.getDashboardStats().catch(() => ({})),
        apiClient.getExpenses({ size: 5 }).catch(() => ({ items: [] })),
        apiClient.getBudgetAlerts().catch(() => [])
      ])
      
      setStats({
        totalExpenses: statsData.total_expenses || 0,
        monthlySpending: statsData.monthly_spending || 0,
        categoriesCount: statsData.categories_count || 0,
        budgetUsage: statsData.budget_usage || 0,
        recentExpenses: expensesData.items || [],
        budgetAlerts: alertsData || [],
        monthlyTrend: statsData.monthly_trend || 0
      })
      
    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const StatCard = ({ title, value, icon: Icon, trend, description, color = 'text-foreground' }: any) => (
    <div className="rounded-lg border bg-card p-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
          <p className={`text-2xl font-bold ${color}`}>{value}</p>
          {trend !== undefined && (
            <div className="flex items-center mt-1">
              {trend > 0 ? (
                <TrendingUp className="h-3 w-3 text-green-500 mr-1" />
              ) : trend < 0 ? (
                <TrendingDown className="h-3 w-3 text-red-500 mr-1" />
              ) : null}
              <span className={`text-xs ${trend > 0 ? 'text-green-500' : trend < 0 ? 'text-red-500' : 'text-muted-foreground'}`}>
                {trend !== 0 && `${Math.abs(trend)}% `}{description}
              </span>
            </div>
          )}
        </div>
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Welcome back! Here's your expense overview.
          </p>
        </div>
        <div className="flex gap-2">
          <Link 
            to="/analytics" 
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <PieChart className="h-4 w-4 mr-2" />
            Analytics
          </Link>
          <Link 
            to="/budgets" 
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <Target className="h-4 w-4 mr-2" />
            Budgets
          </Link>
          <Link 
            to="/import" 
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Upload className="h-4 w-4 mr-2" />
            Import
          </Link>
        </div>
      </div>

      {/* Budget Alerts */}
      {stats.budgetAlerts.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-center">
            <Bell className="h-5 w-5 text-amber-600 mr-2" />
            <h3 className="font-medium text-amber-800">Budget Alerts</h3>
          </div>
          <div className="mt-2 space-y-1">
            {stats.budgetAlerts.slice(0, 3).map((alert) => (
              <p key={alert.id} className="text-sm text-amber-700">
                <strong>{alert.budgetName}:</strong> {alert.message}
              </p>
            ))}
            {stats.budgetAlerts.length > 3 && (
              <Link to="/budgets" className="text-sm text-amber-600 hover:text-amber-800">
                View all {stats.budgetAlerts.length} alerts →
              </Link>
            )}
          </div>
        </div>
      )}
      
      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Expenses"
          value={stats.totalExpenses.toLocaleString()}
          icon={FileText}
          description="total transactions"
        />
        
        <StatCard
          title="This Month"
          value={formatCurrency(stats.monthlySpending)}
          icon={DollarSign}
          trend={stats.monthlyTrend}
          description="from last month"
        />
        
        <StatCard
          title="Categories"
          value={stats.categoriesCount}
          icon={Target}
          description="active categories"
        />
        
        <StatCard
          title="Budget Used"
          value={`${stats.budgetUsage}%`}
          icon={PieChart}
          color={stats.budgetUsage > 90 ? 'text-red-500' : stats.budgetUsage > 75 ? 'text-amber-500' : 'text-green-500'}
          description="of total budget"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Quick Actions */}
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <Link 
              to="/import" 
              className="flex items-center gap-3 p-3 rounded-md hover:bg-muted/50 transition-colors"
            >
              <Upload className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Import Bank Statement</p>
                <p className="text-sm text-muted-foreground">
                  Upload PDF, CSV, Excel, or other formats
                </p>
              </div>
            </Link>
            <Link 
              to="/budgets" 
              className="flex items-center gap-3 p-3 rounded-md hover:bg-muted/50 transition-colors"
            >
              <Target className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Manage Budgets</p>
                <p className="text-sm text-muted-foreground">
                  Set spending limits and track progress
                </p>
              </div>
            </Link>
            <div className="flex items-center gap-3 p-3 rounded-md hover:bg-muted/50 transition-colors cursor-pointer">
              <Plus className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Add Manual Expense</p>
                <p className="text-sm text-muted-foreground">
                  Quickly add a single expense
                </p>
              </div>
            </div>
            <Link 
              to="/analytics" 
              className="flex items-center gap-3 p-3 rounded-md hover:bg-muted/50 transition-colors"
            >
              <PieChart className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">View Analytics</p>
                <p className="text-sm text-muted-foreground">
                  Detailed spending insights and trends
                </p>
              </div>
            </Link>
          </div>
        </div>

        {/* Recent Expenses */}
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Recent Expenses</h3>
            <Link 
              to="/expenses" 
              className="text-sm text-primary hover:text-primary/80"
            >
              View all →
            </Link>
          </div>
          
          {stats.recentExpenses.length > 0 ? (
            <div className="space-y-3">
              {stats.recentExpenses.map((expense) => (
                <div key={expense.id} className="flex items-center justify-between p-3 rounded-md bg-muted/30">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{expense.description}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{expense.category}</span>
                      {expense.account && (
                        <>
                          <span>•</span>
                          <span>{expense.account}</span>
                        </>
                      )}
                      <span>•</span>
                      <span>{new Date(expense.date).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-sm">{formatCurrency(expense.amount)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="h-8 w-8 mx-auto mb-2" />
              <p>No expenses yet</p>
              <p className="text-sm mb-3">Import a statement or add expenses manually</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}