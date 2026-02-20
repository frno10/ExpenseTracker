import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value }),
    removeItem: vi.fn((key: string) => { delete store[key] }),
    clear: vi.fn(() => { store = {} }),
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends auth token in Authorization header when available', async () => {
    localStorageMock.setItem('auth_token', 'test-token-123')

    mockFetch.mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ([]),
    })

    // Import fresh to pick up token
    const { apiClient } = await import('../lib/api')
    apiClient.setToken('test-token-123')
    await apiClient.getExpenses()

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [, options] = mockFetch.mock.calls[0]
    expect(options.headers['Authorization']).toBe('Bearer test-token-123')
  })

  it('throws on non-OK response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      text: async () => 'Invalid token',
    })

    const { apiClient } = await import('../lib/api')
    await expect(apiClient.getExpenses()).rejects.toThrow('API Error: 401')
  })

  it('login sends correct credentials', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        user: { id: '1', email: 'test@example.com', full_name: 'Test', created_at: '2024-01-01' },
        access_token: 'jwt-token',
        token_type: 'bearer',
      }),
    })

    const { apiClient } = await import('../lib/api')
    const result = await apiClient.login('test@example.com', 'password123')

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/auth/login')
    expect(options.method).toBe('POST')
    const body = JSON.parse(options.body)
    expect(body.email).toBe('test@example.com')
    expect(body.password).toBe('password123')
    expect(result.access_token).toBe('jwt-token')
  })

  it('register sends user data', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        user: { id: '1', email: 'new@example.com', full_name: 'New User', created_at: '2024-01-01' },
        access_token: 'jwt-token',
        token_type: 'bearer',
      }),
    })

    const { apiClient } = await import('../lib/api')
    const result = await apiClient.register('new@example.com', 'password123', 'New User')

    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/auth/register')
    expect(options.method).toBe('POST')
    const body = JSON.parse(options.body)
    expect(body.email).toBe('new@example.com')
    expect(body.full_name).toBe('New User')
  })

  it('createExpense sends expense data', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        id: 'exp-1', amount: 25.50, description: 'Lunch',
        category: 'Food', date: '2024-01-15', created_at: '2024-01-15', user_id: '1',
      }),
    })

    const { apiClient } = await import('../lib/api')
    const result = await apiClient.createExpense({
      amount: 25.50,
      description: 'Lunch',
      category: 'Food',
      date: '2024-01-15',
    })

    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/expenses')
    expect(options.method).toBe('POST')
    expect(result.amount).toBe(25.50)
  })

  it('deleteExpense calls correct endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ message: 'Expense deleted successfully' }),
    })

    const { apiClient } = await import('../lib/api')
    await apiClient.deleteExpense('exp-123')

    const [url, options] = mockFetch.mock.calls[0]
    expect(url).toContain('/expenses/exp-123')
    expect(options.method).toBe('DELETE')
  })

  it('getDashboardStats returns data or defaults', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({
        total_expenses: 42,
        total_amount: 1234.56,
        categories_used: 5,
        recent_expenses: [],
      }),
    })

    const { apiClient } = await import('../lib/api')
    const stats = await apiClient.getDashboardStats()

    expect(stats.total_expenses).toBe(42)
    expect(stats.total_amount).toBe(1234.56)
  })
})
