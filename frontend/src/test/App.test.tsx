import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../App'

describe('App', () => {
  it('renders the expense tracker title', () => {
    render(<App />)
    expect(screen.getByText('Expense Tracker')).toBeInTheDocument()
  })

  it('renders the dashboard', () => {
    render(<App />)
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Welcome to your expense tracker dashboard')).toBeInTheDocument()
  })
})