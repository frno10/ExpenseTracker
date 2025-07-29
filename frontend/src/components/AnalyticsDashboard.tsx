import React, { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, DollarSign, Calendar, AlertTriangle, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { Progress } from './ui/progress'

interface DashboardSummary {
  period: {
    start_date: string
    end_date: string
    days: number
  }
  summary: {
    total_spending: number
    transaction_count: number
    average_transaction: number
    daily_average: number
  }
  trend: {
    direction: 'up' | 'down' | 'stable'
    change_amount: number
    change_percentage: number
  }
  category_breakdown: Array<{
    category: string
    amount: number
    count: number
    percentage: number
  }>
  merchant_breakdown: Array<{
    merchant: string
    amount: number
    count: number
  }>
  anomalies: Array<{
    date: string
    amount: number
    category: string
    merchant: string
    anomaly_type: string
    severity: string
    description: string
  }>
  insights: string[]
}

interface AnalyticsDashboardProps {
  periodDays?: number
}

export function AnalyticsDashboard({ periodDays = 30 }: AnalyticsDashboardProps) {
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDashboardData()
  }, [periodDays])

  const loadDashboardData = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`/api/analytics/dashboard?period_days=${periodDays}`, {
        headers: {
          // Add auth headers when authentication is implemented
        }
      })

      if (response.ok) {
        const data = await response.json()
        setDashboardData(data)
      } else {
        throw new Error('Failed to load dashboard data')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  const getTrendIcon = (direction: string) => {
    switch (direction) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-red-500" />
      case 'down':
        return <TrendingDown className="h-4 w-4 text-green-500" />
      default:
        return <DollarSign className="h-4 w-4 text-gray-500" />
    }
  }

  const getTrendColor = (direction: string) => {
    switch (direction) {
      case 'up':
        return 'text-red-600'
      case 'down':
        return 'text-green-600'
      default:
        return 'text-gray-600'
    }
  }

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'high':
        return <Badge variant="destructive" className="text-xs">High</Badge>
      case 'medium':
        return <Badge variant="outline" className="text-xs text-orange-600 border-orange-600">Medium</Badge>
      default:
        return <Badge variant="secondary" className="text-xs">Low</Badge>
    }
  }

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
            <AlertTriangle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Error Loading Analytics</h3>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={loadDashboardData}>Try Again</Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!dashboardData) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Analytics Dashboard</h2>
          <p className="text-muted-foreground">
            {formatDate(dashboardData.period.start_date)} - {formatDate(dashboardData.period.end_date)} ({dashboardData.period.days} days)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadDashboardData}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Spending</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(dashboardData.summary.total_spending)}
            </div>
            <div className={`flex items-center text-xs ${getTrendColor(dashboardData.trend.direction)}`}>
              {getTrendIcon(dashboardData.trend.direction)}
              <span className="ml-1">
                {dashboardData.trend.change_percentage > 0 ? '+' : ''}
                {dashboardData.trend.change_percentage.toFixed(1)}% from last period
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Transactions</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData.summary.transaction_count}
            </div>
            <p className="text-xs text-muted-foreground">
              {formatCurrency(dashboardData.summary.average_transaction)} average
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Daily Average</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(dashboardData.summary.daily_average)}
            </div>
            <p className="text-xs text-muted-foreground">
              Per day spending
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Anomalies</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {dashboardData.anomalies.length}
            </div>
            <p className="text-xs text-muted-foreground">
              Unusual transactions detected
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Category Breakdown */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Top Categories</CardTitle>
            <CardDescription>
              Spending breakdown by category
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {dashboardData.category_breakdown.slice(0, 5).map((category, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{category.category}</span>
                  <span>{formatCurrency(category.amount)}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{category.count} transactions</span>
                  <span>{category.percentage.toFixed(1)}%</span>
                </div>
                <Progress value={category.percentage} className="h-2" />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Merchants</CardTitle>
            <CardDescription>
              Most frequent spending locations
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {dashboardData.merchant_breakdown.slice(0, 5).map((merchant, index) => (
              <div key={index} className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">{merchant.merchant}</p>
                  <p className="text-xs text-muted-foreground">{merchant.count} transactions</p>
                </div>
                <div className="text-sm font-medium">
                  {formatCurrency(merchant.amount)}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Anomalies */}
      {dashboardData.anomalies.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              Spending Anomalies
            </CardTitle>
            <CardDescription>
              Unusual transactions that may need review
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {dashboardData.anomalies.map((anomaly, index) => (
                <div key={index} className="flex items-start justify-between p-3 bg-orange-50 rounded-lg border">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{anomaly.merchant}</span>
                      {getSeverityBadge(anomaly.severity)}
                    </div>
                    <p className="text-xs text-muted-foreground">{anomaly.description}</p>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span>{formatDate(anomaly.date)}</span>
                      <span>{anomaly.category}</span>
                    </div>
                  </div>
                  <div className="text-sm font-medium">
                    {formatCurrency(anomaly.amount)}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Insights */}
      {dashboardData.insights.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Insights</CardTitle>
            <CardDescription>
              AI-generated insights about your spending patterns
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {dashboardData.insights.map((insight, index) => (
                <div key={index} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                  <TrendingUp className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-blue-900">{insight}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}