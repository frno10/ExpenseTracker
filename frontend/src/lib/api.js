// JavaScript version of the API client for deployment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

console.log('🌐 API Configuration:')
console.log('VITE_API_URL from env:', import.meta.env.VITE_API_URL)
console.log('API_BASE_URL being used:', API_BASE_URL)

class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl
    this.token = localStorage.getItem('auth_token')
  }

  setToken(token) {
    this.token = token
    localStorage.setItem('auth_token', token)
  }

  clearToken() {
    this.token = null
    localStorage.removeItem('auth_token')
  }

  async login(email, password) {
    return { access_token: 'mock-token', user: { id: 'mock-id', email, full_name: 'Mock User' } }
  }

  async register(email, password, fullName) {
    return { access_token: 'mock-token', user: { id: 'mock-id', email, full_name: fullName } }
  }

  async logout() {
    return {}
  }

  async resendConfirmation(email) {
    return { message: 'Confirmation sent', email }
  }

  async getExpenses(params) {
    return { items: [] }
  }

  async createExpense(expenseData) {
    return { id: 'mock-id', ...expenseData }
  }

  async updateExpense(id, expenseData) {
    return { id, ...expenseData }
  }

  async deleteExpense(id) {
    return {}
  }

  async bulkDeleteExpenses(expenseIds) {
    return {}
  }

  async exportExpenses(params) {
    return new Blob(['mock,csv,data'], { type: 'text/csv' })
  }

  async getCategories() {
    return []
  }

  async getAccounts() {
    return []
  }

  async getPaymentMethods() {
    return []
  }

  async getDashboardStats() {
    return {
      total_expenses: 0,
      monthly_spending: 0,
      categories_count: 0,
      budget_usage: 0,
      monthly_trend: 0
    }
  }

  async getBudgetAlerts() {
    return []
  }
}

export const apiClient = new ApiClient()
export default apiClient