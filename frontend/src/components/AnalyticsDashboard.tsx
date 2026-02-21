import { useState, useEffect, useMemo } from 'react'
import { TrendingUp, TrendingDown, DollarSign, Calendar, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Progress } from './ui/progress'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { apiClient } from '../lib/api'

interface Expense {
  id: string
  amount: number
  description: string
  category: string
  date: string
}

interface CategorySummary {
  name: string
  total_expenses: number
  expense_count: number
}

interface AnalyticsDashboardProps {
  periodDays?: number
}

const CHART_COLORS = ['#6366f1', '#f43f5e', '#10b981', '#f59e0b', '#3b82f6', '#8b5cf6', '#64748b']

export function AnalyticsDashboard({ periodDays = 30 }: AnalyticsDashboardProps) {
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [categories, setCategories] = useState<CategorySummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDashboardData()
  }, [periodDays])

  const loadDashboardData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [expData, catData] = await Promise.all([
        apiClient.getExpenses().catch(() => ({ items: [] })),
        apiClient.getCategories().catch(() => [])
      ])
      setExpenses(expData.items || expData || [])
      setCategories(catData || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const filteredExpenses = useMemo(() => {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - periodDays)
    return expenses.filter(e => new Date(e.date) >= cutoff)
  }, [expenses, periodDays])

  const totalSpending = useMemo(
    () => filteredExpenses.reduce((s, e) => s + Number(e.amount), 0),
    [filteredExpenses]
  )

  const trend = useMemo(() => {
    const now = new Date()
    const periodStart = new Date(now)
    periodStart.setDate(periodStart.getDate() - periodDays)
    const prevStart = new Date(periodStart)
    prevStart.setDate(prevStart.getDate() - periodDays)

    const prevTotal = expenses
      .filter(e => {
        const d = new Date(e.date)
        return d >= prevStart && d < periodStart
      })
      .reduce((s, e) => s + Number(e.amount), 0)

    if (prevTotal === 0) return { direction: 'stable' as const, pct: 0 }
    const pct = ((totalSpending - prevTotal) / prevTotal) * 100
    return {
      direction: pct > 2 ? 'up' as const : pct < -2 ? 'down' as const : 'stable' as const,
      pct: Math.round(pct)
    }
  }, [expenses, totalSpending, periodDays])

  const categoryChartData = useMemo(
    () => categories.filter(c => c.total_expenses > 0).sort((a, b) => b.total_expenses - a.total_expenses),
    [categories]
  )

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <div className="animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-8 bg-gray-200 rounded w-1/2"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center">
            <h3 className="text-lg font-semibold mb-2">Error Loading Analytics</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadDashboardData}>Try Again</Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Spending</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalSpending)}</div>
            <div className={`flex items-center text-xs ${trend.direction === 'up' ? 'text-red-600' : trend.direction === 'down' ? 'text-green-600' : 'text-gray-600'}`}>
              {trend.direction === 'up' && <TrendingUp className="h-3 w-3 mr-1" />}
              {trend.direction === 'down' && <TrendingDown className="h-3 w-3 mr-1" />}
              <span>{trend.pct > 0 ? '+' : ''}{trend.pct}% from last period</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transactions</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredExpenses.length}</div>
            <p className="text-xs text-muted-foreground">
              {filteredExpenses.length > 0
                ? `${formatCurrency(totalSpending / filteredExpenses.length)} average`
                : 'No transactions'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Daily Average</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalSpending / Math.max(periodDays, 1))}</div>
            <p className="text-xs text-muted-foreground">Per day spending</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Categories</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{categoryChartData.length}</div>
            <p className="text-xs text-muted-foreground">Active categories</p>
          </CardContent>
        </Card>
      </div>

      {/* Category Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top Categories</CardTitle>
            <CardDescription>Spending breakdown by category</CardDescription>
          </CardHeader>
          <CardContent>
            {categoryChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={categoryChartData.slice(0, 7)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    formatter={(value: number) => formatCurrency(value)}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                  />
                  <Bar dataKey="total_expenses" name="Spending" radius={[4, 4, 0, 0]}>
                    {categoryChartData.slice(0, 7).map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center py-12 text-muted-foreground">No category data yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Category Breakdown</CardTitle>
            <CardDescription>Percentage of total spending</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {categoryChartData.slice(0, 7).map((category, index) => {
              const pct = totalSpending > 0 ? (category.total_expenses / totalSpending) * 100 : 0
              return (
                <div key={category.name} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }} />
                      <span className="font-medium">{category.name}</span>
                    </div>
                    <span>{formatCurrency(category.total_expenses)}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>{category.expense_count} transactions</span>
                    <span>{pct.toFixed(1)}%</span>
                  </div>
                  <Progress value={pct} className="h-2" />
                </div>
              )
            })}
            {categoryChartData.length === 0 && (
              <p className="text-center py-8 text-muted-foreground">No categories with expenses.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
