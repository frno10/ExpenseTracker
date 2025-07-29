import React, { useState } from 'react'
import { Calendar, BarChart3, TrendingUp, Filter } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { AnalyticsDashboard } from '../components/AnalyticsDashboard'

export function Analytics() {
  const [selectedPeriod, setSelectedPeriod] = useState(30)
  const [activeView, setActiveView] = useState<'dashboard' | 'trends' | 'categories' | 'insights'>('dashboard')

  const periodOptions = [
    { value: 7, label: '7 Days' },
    { value: 30, label: '30 Days' },
    { value: 90, label: '90 Days' },
    { value: 365, label: '1 Year' }
  ]

  const viewOptions = [
    { key: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { key: 'trends', label: 'Trends', icon: TrendingUp },
    { key: 'categories', label: 'Categories', icon: Filter },
    { key: 'insights', label: 'Insights', icon: Calendar }
  ]

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
        {/* View Selector */}
        <div className="flex items-center gap-2">
          {viewOptions.map((option) => {
            const Icon = option.icon
            return (
              <Button
                key={option.key}
                variant={activeView === option.key ? "default" : "outline"}
                size="sm"
                onClick={() => setActiveView(option.key as any)}
                className="flex items-center gap-2"
              >
                <Icon className="h-4 w-4" />
                {option.label}
              </Button>
            )
          })}
        </div>

        {/* Period Selector */}
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
        {activeView === 'dashboard' && (
          <AnalyticsDashboard periodDays={selectedPeriod} />
        )}

        {activeView === 'trends' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Spending Trends
              </CardTitle>
              <CardDescription>
                Analyze spending patterns over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <TrendingUp className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Trends Analysis</h3>
                <p className="text-muted-foreground mb-4">
                  Advanced trend analysis and time-series charts coming soon.
                </p>
                <Badge variant="secondary">Coming Soon</Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {activeView === 'categories' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Filter className="h-5 w-5" />
                Category Analysis
              </CardTitle>
              <CardDescription>
                Deep dive into spending by category
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <Filter className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Category Breakdown</h3>
                <p className="text-muted-foreground mb-4">
                  Detailed category analysis with drill-down capabilities coming soon.
                </p>
                <Badge variant="secondary">Coming Soon</Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {activeView === 'insights' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                AI Insights
              </CardTitle>
              <CardDescription>
                Personalized financial insights and recommendations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Smart Insights</h3>
                <p className="text-muted-foreground mb-4">
                  AI-powered spending insights and personalized recommendations coming soon.
                </p>
                <Badge variant="secondary">Coming Soon</Badge>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}