import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import StepIndicator from '../../../src/components/orders/StepIndicator'

const steps = [
  { key: 'context', label: 'Kontext' },
  { key: 'network', label: 'Netzwerk' },
  { key: 'sizing', label: 'VM Sizing' },
  { key: 'summary', label: 'Zusammenfassung' },
]

describe('StepIndicator', () => {
  it('renders all step labels', () => {
    render(<StepIndicator steps={steps} currentStep={0} onStepClick={() => {}} />)
    expect(screen.getByText('Kontext')).toBeInTheDocument()
    expect(screen.getByText('Netzwerk')).toBeInTheDocument()
    expect(screen.getByText('VM Sizing')).toBeInTheDocument()
    expect(screen.getByText('Zusammenfassung')).toBeInTheDocument()
  })

  it('marks completed steps', () => {
    render(<StepIndicator steps={steps} currentStep={2} onStepClick={() => {}} />)
    const items = screen.getAllByTestId('step-item')
    expect(items[0]).toHaveAttribute('data-status', 'completed')
    expect(items[1]).toHaveAttribute('data-status', 'completed')
    expect(items[2]).toHaveAttribute('data-status', 'current')
    expect(items[3]).toHaveAttribute('data-status', 'pending')
  })

  it('calls onStepClick for completed steps', () => {
    const onClick = vi.fn()
    render(<StepIndicator steps={steps} currentStep={2} onStepClick={onClick} />)
    fireEvent.click(screen.getByText('✓ Kontext'))
    expect(onClick).toHaveBeenCalledWith(0)
  })

  it('does not call onStepClick for pending steps', () => {
    const onClick = vi.fn()
    render(<StepIndicator steps={steps} currentStep={1} onStepClick={onClick} />)
    fireEvent.click(screen.getByText('Zusammenfassung'))
    expect(onClick).not.toHaveBeenCalled()
  })
})
