import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatCard from '../../../src/components/dashboard/StatCard'

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="Offene Orders" value={3} />)
    expect(screen.getByText('Offene Orders')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders zero value', () => {
    render(<StatCard label="Pending" value={0} />)
    expect(screen.getByText('0')).toBeInTheDocument()
  })
})
