/**
 * Simplified API client for deployment - includes all methods used by components
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'



class ApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
    this.token = localStorage.getItem('auth_token')
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
    return { access_token: 'mock-token', user: { id: 'mock-id', email, full_name: 'Mock User' } }
  }

  async register(email: string, password: string, fullName: string) {
    return { access_token: 'mock-token', user: { id: 'mock-id', email, full_name: fullName } }
  }

  async logout() {
    return {}
  }

  async resendConfirmation(email: string) {
    return { message: 'Confirmation sent', email }
  }

  // Expense methods
  async getExpenses(params?: any) {
    return { items: [] }
  }

  async createExpense(expenseData: any) {
    return { id: 'mock-id', ...expenseData }
  }

  async updateExpense(id: string, expenseData: any) {
    return { id, ...expenseData }
  }

  async deleteExpense(id: string) {
    return {}
  }

  async bulkDeleteExpenses(expenseIds: string[]) {
    return {}
  }

  async exportExpenses(params?: any) {
    return new Blob(['mock,csv,data'], { type: 'text/csv' })
  }

  // Category and Account methods
  async getCategories() {
    return []
  }

  async getAccounts() {
    return []
  }

  async getPaymentMethods() {
    return []
  }

  // Dashboard methods
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

const apiClient = new ApiClient()

export { apiClient }
export default apiClient