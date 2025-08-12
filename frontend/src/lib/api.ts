/**
 * Real API client that connects to the FastAPI backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

console.log('🌐 API Configuration:')
console.log('  Base URL:', API_BASE_URL)
console.log('  Environment:', import.meta.env.MODE)

class ApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
    this.token = localStorage.getItem('auth_token')
  }

  // Helper method for making requests
  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseUrl}${endpoint}`
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    console.log(`🔗 API Request: ${options.method || 'GET'} ${url}`)

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      })

      console.log(`📡 API Response: ${response.status} ${response.statusText}`)

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ API Error:', errorText)
        throw new Error(`API Error: ${response.status} ${response.statusText}`)
      }

      // Check if response has content
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json()
        console.log('✅ API Success:', data)
        return data
      } else {
        // Return empty object for non-JSON responses
        return {}
      }
    } catch (error) {
      console.error('🚨 API Request Failed:', error)
      throw error
    }
  }

  // Token management
  setToken(token: string) {
    this.token = token
    localStorage.setItem('auth_token', token)
  }

  clearToken() {
    this.token = null
    localStorage.removeItem('auth_token')
  }

  // Auth methods
  async login(email: string, password: string) {
    try {
      const response = await this.request('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      
      if (response.access_token) {
        this.setToken(response.access_token)
      }
      
      return response
    } catch (error) {
      // In development mode, try the dev login as fallback
      if (import.meta.env.MODE === 'development') {
        console.log('🔧 Trying development login fallback...')
        try {
          const devResponse = await this.request('/auth/dev-login', {
            method: 'POST',
          })
          
          if (devResponse.access_token) {
            this.setToken(devResponse.access_token)
          }
          
          return devResponse
        } catch (devError) {
          console.error('❌ Development login also failed:', devError)
        }
      }
      
      throw error
    }
  }

  async register(email: string, password: string, fullName: string) {
    const response = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ 
        email, 
        password, 
        full_name: fullName 
      }),
    })
    
    if (response.access_token) {
      this.setToken(response.access_token)
    }
    
    return response
  }

  async logout() {
    this.clearToken()
    return {}
  }

  async resendConfirmation(email: string) {
    return await this.request('/auth/resend-confirmation', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  async getCurrentUser() {
    return await this.request('/auth/me')
  }

  // Expense methods
  async getExpenses(params?: any) {
    const expenses = await this.request('/expenses')
    return { items: expenses || [] }
  }

  async createExpense(expenseData: any) {
    return await this.request('/expenses', {
      method: 'POST',
      body: JSON.stringify(expenseData),
    })
  }

  async updateExpense(id: string, expenseData: any) {
    return await this.request(`/expenses/${id}`, {
      method: 'PUT',
      body: JSON.stringify(expenseData),
    })
  }

  async deleteExpense(id: string) {
    return await this.request(`/expenses/${id}`, {
      method: 'DELETE',
    })
  }

  async bulkDeleteExpenses(expenseIds: string[]) {
    // Backend doesn't support bulk delete yet, delete one by one
    for (const id of expenseIds) {
      await this.deleteExpense(id)
    }
    return {}
  }

  async exportExpenses(params?: any) {
    // Backend doesn't support export yet, return empty CSV
    return new Blob(['Date,Description,Amount,Category\n'], { type: 'text/csv' })
  }

  // Category and Account methods
  async getCategories() {
    try {
      return await this.request('/categories')
    } catch (error) {
      console.warn('Categories endpoint not available, returning defaults')
      return [
        { id: '1', name: 'Food & Dining', color: '#FF6B6B' },
        { id: '2', name: 'Transportation', color: '#4ECDC4' },
        { id: '3', name: 'Shopping', color: '#45B7D1' },
        { id: '4', name: 'Entertainment', color: '#96CEB4' },
        { id: '5', name: 'Bills & Utilities', color: '#FFEAA7' },
        { id: '6', name: 'Healthcare', color: '#DDA0DD' },
        { id: '7', name: 'Other', color: '#95A5A6' }
      ]
    }
  }

  async getAccounts() {
    // Backend doesn't have accounts yet, return defaults
    return [
      { id: '1', name: 'Checking Account', type: 'checking' },
      { id: '2', name: 'Savings Account', type: 'savings' },
      { id: '3', name: 'Credit Card', type: 'credit' }
    ]
  }

  async getPaymentMethods() {
    // Backend doesn't have payment methods yet, return defaults
    return [
      { id: '1', name: 'Cash', type: 'cash' },
      { id: '2', name: 'Credit Card', type: 'credit' },
      { id: '3', name: 'Debit Card', type: 'debit' },
      { id: '4', name: 'Bank Transfer', type: 'transfer' }
    ]
  }

  // Dashboard methods
  async getDashboardStats() {
    try {
      return await this.request('/summary')
    } catch (error) {
      console.warn('Summary endpoint not available, returning defaults')
      return {
        total_expenses: 0,
        monthly_spending: 0,
        categories_count: 7,
        budget_usage: 0,
        monthly_trend: 0
      }
    }
  }

  async getBudgetAlerts() {
    // Backend doesn't have budgets yet, return empty
    return []
  }
}

const apiClient = new ApiClient()

export { apiClient }
export default apiClient