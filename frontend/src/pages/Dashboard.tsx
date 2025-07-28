import { Link } from 'react-router-dom'
import { Upload, Plus } from 'lucide-react'

export function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
          <p className="text-muted-foreground">
            Welcome to your expense tracker dashboard
          </p>
        </div>
        <div className="flex gap-2">
          <Link 
            to="/import" 
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            <Upload className="h-4 w-4 mr-2" />
            Import Statement
          </Link>
        </div>
      </div>
      
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-sm font-medium text-muted-foreground">
            Total Expenses
          </h3>
          <p className="text-2xl font-bold">$0.00</p>
        </div>
        
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-sm font-medium text-muted-foreground">
            This Month
          </h3>
          <p className="text-2xl font-bold">$0.00</p>
        </div>
        
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-sm font-medium text-muted-foreground">
            Categories
          </h3>
          <p className="text-2xl font-bold">0</p>
        </div>
        
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-sm font-medium text-muted-foreground">
            Budget Used
          </h3>
          <p className="text-2xl font-bold">0%</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
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
            <div className="flex items-center gap-3 p-3 rounded-md hover:bg-muted/50 transition-colors cursor-pointer">
              <Plus className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Add Manual Expense</p>
                <p className="text-sm text-muted-foreground">
                  Quickly add a single expense
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
          <div className="text-center py-8 text-muted-foreground">
            <p>No recent activity</p>
            <p className="text-sm">Import your first statement to get started</p>
          </div>
        </div>
      </div>
    </div>
  )
}