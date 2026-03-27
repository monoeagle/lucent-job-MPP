import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RequestSummary from '../../../src/components/orders/RequestSummary'

const template = {
  display_name: 'Linux VM',
  version: '1.0.0',
  estimated_cost_eur_per_month: 85,
}

const params = { cpu_cores: 8, ram_gb: 32, os_type: 'ubuntu-22.04' }

const parameterDefs = [
  { key: 'cpu_cores', label: 'CPU-Kerne', group: 'Compute' },
  { key: 'ram_gb', label: 'RAM', group: 'Compute' },
  { key: 'os_type', label: 'Betriebssystem', group: 'System' },
]

describe('RequestSummary', () => {
  it('renders template name and version', () => {
    render(
      <RequestSummary template={template} parameters={params}
        parameterDefs={parameterDefs} quantity={1} onQuantityChange={() => {}} />
    )
    expect(screen.getByText('Linux VM')).toBeInTheDocument()
    expect(screen.getByText('v1.0.0')).toBeInTheDocument()
  })

  it('renders parameter values', () => {
    render(
      <RequestSummary template={template} parameters={params}
        parameterDefs={parameterDefs} quantity={1} onQuantityChange={() => {}} />
    )
    expect(screen.getByText('CPU-Kerne')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
  })

  it('shows cost estimate for quantity', () => {
    render(
      <RequestSummary template={template} parameters={params}
        parameterDefs={parameterDefs} quantity={3} onQuantityChange={() => {}} />
    )
    expect(screen.getByText(/255/)).toBeInTheDocument()
  })
})
