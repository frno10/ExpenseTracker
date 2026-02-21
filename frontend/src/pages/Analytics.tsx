import { useState, useEffect, useMemo } from 'react'
import { Calendar, BarChart3, TrendingUp, TrendingDown, Filter, DollarSign, Lightbulb } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend,
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

const CHART_COLORS = ['#6366f1', '#f43f5e', '#10b981', '#f59e0b', '#3b82f6', '#8b5cf6', '#64748b']

export function Analytics() {
  const [selectedPeriod, setSelectedPeriod] = useState(30)
  const [activeView, setActiveView] = useState<'trends' | 'categories' | 'insights'>('trends')
  const [expenses, setExpenses] = useState<Expense[]>([])
  const [categories, setCategories] = useState<CategorySummary[]>([])
  const [loading, setLoading] = useState(true)

  const periodOptions = [
    { value: 7, label: '7 Days' },
    { value: 30, label: '30 Days' },
    { value: 90, label: '90 Days' },
    { value: 365, label: '1 Year' }
  ]

  const viewOptions = [
    { key: 'trends', label: 'Trends', icon: TrendingUp },
    { key: 'categories', label: 'Categories', icon: Filter },
    { key: 'insights', label: 'Insights', icon: Lightbulb }
  ]

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [expData, catData] = await Promise.all([
        apiClient.getExpenses().catch(() => ({ items: [] })),
        apiClient.getCategories().catch(() => [])
      ])
      setExpenses(expData.items || expData || [])
      setCategories(catData || [])
    } catch (err) {
      console.error('Error loading analytics data:', err)
    } finally {
      setLoading(false)
    }
  }

  // Filter expenses by selected period
  const filteredExpenses = useMemo(() => {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - selectedPeriod)
    return expenses.filter(e => new Date(e.date) >= cutoff)
  }, [expenses, selectedPeriod])

  // Daily spending trend data
  const dailyTrend = useMemo(() => {
    const map: Record<string, number> = {}
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - selectedPeriod)

    // Initialize all dates in range
    for (let d = new Date(cutoff); d <= new Date(); d.setDate(d.getDate() + 1)) {
      map[d.toISOString().slice(0, 10)] = 0
    }

    filteredExpenses.forEach(e => {
      const day = e.date.slice(0, 10)
      if (map[day] !== undefined) {
        map[day] += Number(e.amount)
      }
    })

    return Object.entries(map)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, amount]) => ({
        date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        amount: Math.round(amount * 100) / 100
      }))
  }, [filteredExpenses, selectedPeriod])

  // Category breakdown for chart
  const categoryChartData = useMemo(() => {
    return categories
      .filter(c => c.total_expenses > 0)
      .sort((a, b) => b.total_expenses - a.total_expenses)
  }, [categories])

  // Insights computed from expense data
  const insights = useMemo(() => {
    if (filteredExpenses.length === 0) return []

    const total = filteredExpenses.reduce((s, e) => s + Number(e.amount), 0)
    const avgPerDay = total / selectedPeriod
    const largest = filteredExpenses.reduce((max, e) => Number(e.amount) > Number(max.amount) ? e : max, filteredExpenses[0])

    // Category counts
    const catMap: Record<string, number> = {}
    filteredExpenses.forEach(e => { catMap[e.category] = (catMap[e.category] || 0) + Number(e.amount) })
    const topCategory = Object.entries(catMap).sort(([, a], [, b]) => b - a)[0]

    // Weekly comparison
    const oneWeekAgo = new Date()
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
    const twoWeeksAgo = new Date()
    twoWeeksAgo.setDate(twoWeeksAgo.getDate() - 14)
    const thisWeek = filteredExpenses
      .filter(e => new Date(e.date) >= oneWeekAgo)
      .reduce((s, e) => s + Number(e.amount), 0)
    const lastWeek = filteredExpenses
      .filter(e => new Date(e.date) >= twoWeeksAgo && new Date(e.date) < oneWeekAgo)
      .reduce((s, e) => s + Number(e.amount), 0)

    const result = []

    result.push({
      icon: 'dollar',
      title: 'Daily Average',
      text: `You spend an average of ${formatCurrency(avgPerDay)} per day over the last ${selectedPeriod} days.`
    })

    if (topCategory) {
      const pct = ((topCategory[1] / total) * 100).toFixed(0)
      result.push({
        icon: 'category',
        title: 'Top Category',
        text: `${topCategory[0]} accounts for ${pct}% of your spending (${formatCurrency(topCategory[1])}).`
      })
    }

    result.push({
      icon: 'expense',
      title: 'Largest Expense',
      text: `Your biggest expense was ${formatCurrency(Number(largest.amount))} for "${largest.description}" on ${new Date(largest.date).toLocaleDateString()}.`
    })

    if (lastWeek > 0) {
      const change = ((thisWeek - lastWeek) / lastWeek * 100).toFixed(0)
      const direction = thisWeek > lastWeek ? 'increased' : 'decreased'
      result.push({
        icon: 'trend',
        title: 'Weekly Trend',
        text: `This week's spending ${direction} by ${Math.abs(Number(change))}% compared to last week (${formatCurrency(thisWeek)} vs ${formatCurrency(lastWeek)}).`
      })
    }

    const activeCats = Object.keys(catMap).length
    result.push({
      icon: 'spread',
      title: 'Spending Spread',
      text: `You spent across ${activeCats} categories with ${filteredExpenses.length} total transactions.`
    })

    return result
  }, [filteredExpenses, selectedPeriod])

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Analytics</h2>
          <p className="text-muted-foreground">
            Analyze your spending patterns and financial insights
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {viewOptions.map((option) => {
            const Icon = option.icon
            return (
              <Button
                key={option.key}
                variant={activeView === option.key ? "default" : "outline"}
                size="sm"
                onClick={() => setActiveView(option.key as typeof activeView)}
                className="flex items-center gap-2"
              >
                <Icon className="h-4 w-4" />
                {option.label}
              </Button>
            )
          })}
        </div>

        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Period:</span>
          {periodOptions.map((option) => (
            <Button
              key={option.value}
              variant={selectedPeriod === option.value ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedPeriod(option.value)}
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="space-y-6">
        {/* Trends Tab */}
        {activeView === 'trends' && (
          <>
            {/* Summary stats */}
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Total Spending</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatCurrency(filteredExpenses.reduce((s, e) => s + Number(e.amount), 0))}
                  </div>
                  <p className="text-xs text-muted-foreground">{filteredExpenses.length} transactions</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Daily Average</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatCurrency(filteredExpenses.reduce((s, e) => s + Number(e.amount), 0) / Math.max(selectedPeriod, 1))}
                  </div>
                  <p className="text-xs text-muted-foreground">over {selectedPeriod} days</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Average Transaction</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatCurrency(filteredExpenses.length > 0
                      ? filteredExpenses.reduce((s, e) => s + Number(e.amount), 0) / filteredExpenses.length
                      : 0)}
                  </div>
                  <p className="text-xs text-muted-foreground">per expense</p>
                </CardContent>
              </Card>
            </div>

            {/* Daily spending line chart */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Daily Spending
                </CardTitle>
                <CardDescription>
                  Your spending pattern over the last {selectedPeriod} days
                </CardDescription>
              </CardHeader>
              <CardContent>
                {dailyTrend.length > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={dailyTrend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 12 }}
                        interval={Math.max(0, Math.floor(dailyTrend.length / 10))}
                      />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip
                        formatter={(value: number) => formatCurrency(value)}
                        contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                      />
                      <Line
                        type="monotone"
                        dataKey="amount"
                        stroke="#6366f1"
                        strokeWidth={2}
                        dot={selectedPeriod <= 30}
                        name="Daily Spending"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <p className="text-center py-12 text-muted-foreground">No expense data for this period.</p>
                )}
              </CardContent>
            </Card>
          </>
        )}

        {/* Categories Tab */}
        {activeView === 'categories' && (
          <>
            <div className="grid gap-6 md:grid-cols-2">
              {/* Pie Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Filter className="h-5 w-5" />
                    Category Distribution
                  </CardTitle>
                  <CardDescription>Proportional spending by category</CardDescription>
                </CardHeader>
                <CardContent>
                  {categoryChartData.length > 0 ? (
                    <div className="flex flex-col items-center">
                      <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                          <Pie
                            data={categoryChartData}
                            dataKey="total_expenses"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius={110}
                            innerRadius={60}
                            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                          >
                            {categoryChartData.map((_entry, index) => (
                              <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip
                            formatter={(value: number) => formatCurrency(value)}
                            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                          />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <p className="text-center py-12 text-muted-foreground">No category data available.</p>
                  )}
                </CardContent>
              </Card>

              {/* Bar Chart */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5" />
                    Spending by Category
                  </CardTitle>
                  <CardDescription>Amount and transaction count</CardDescription>
                </CardHeader>
                <CardContent>
                  {categoryChartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={categoryChartData} layout="vertical">
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" tick={{ fontSize: 12 }} />
                        <YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 12 }} />
                        <Tooltip
                          formatter={(value: number, name: string) => [
                            name === 'total_expenses' ? formatCurrency(value) : value,
                            name === 'total_expenses' ? 'Amount' : 'Transactions'
                          ]}
                          contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                        />
                        <Bar dataKey="total_expenses" fill="#6366f1" radius={[0, 4, 4, 0]} name="Amount" />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <p className="text-center py-12 text-muted-foreground">No category data available.</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Category detail table */}
            <Card>
              <CardHeader>
                <CardTitle>Category Details</CardTitle>
                <CardDescription>Full breakdown of spending per category</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="border-b bg-muted/30">
                      <tr>
                        <th className="text-left p-3 font-medium">Category</th>
                        <th className="text-right p-3 font-medium">Transactions</th>
                        <th className="text-right p-3 font-medium">Total</th>
                        <th className="text-right p-3 font-medium">Avg per Transaction</th>
                        <th className="text-right p-3 font-medium">% of Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {categoryChartData.map((cat, i) => {
                        const total = categoryChartData.reduce((s, c) => s + c.total_expenses, 0)
                        return (
                          <tr key={cat.name} className="border-b hover:bg-muted/30">
                            <td className="p-3">
                              <div className="flex items-center gap-2">
                                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                                {cat.name}
                              </div>
                            </td>
                            <td className="p-3 text-right">{cat.expense_count}</td>
                            <td className="p-3 text-right font-medium">{formatCurrency(cat.total_expenses)}</td>
                            <td className="p-3 text-right">
                              {formatCurrency(cat.expense_count > 0 ? cat.total_expenses / cat.expense_count : 0)}
                            </td>
                            <td className="p-3 text-right">
                              {total > 0 ? ((cat.total_expenses / total) * 100).toFixed(1) : 0}%
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {/* Insights Tab */}
        {activeView === 'insights' && (
          <div className="space-y-4">
            {insights.length > 0 ? (
              insights.map((insight, i) => (
                <Card key={i}>
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-4">
                      <div className="rounded-full bg-primary/10 p-2">
                        {insight.icon === 'dollar' && <DollarSign className="h-5 w-5 text-primary" />}
                        {insight.icon === 'category' && <Filter className="h-5 w-5 text-primary" />}
                        {insight.icon === 'expense' && <TrendingUp className="h-5 w-5 text-primary" />}
                        {insight.icon === 'trend' && <TrendingDown className="h-5 w-5 text-primary" />}
                        {insight.icon === 'spread' && <BarChart3 className="h-5 w-5 text-primary" />}
                      </div>
                      <div>
                        <h4 className="font-semibold">{insight.title}</h4>
                        <p className="text-sm text-muted-foreground mt-1">{insight.text}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            ) : (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-center py-8">
                    <Lightbulb className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h3 className="text-lg font-semibold mb-2">No Insights Yet</h3>
                    <p className="text-muted-foreground">
                      Add some expenses to see spending insights and recommendations.
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
