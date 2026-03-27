import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ParameterForm from '../../src/components/ParameterForm/ParameterForm'
import type { ParameterDefinition } from '../../src/types/catalog'

const mockParams: ParameterDefinition[] = [
  { key: 'cpu', label: 'CPU-Kerne', type: 'integer', required: true,
    tofu_variable_name: 'cpu', display_order: 1, group: 'Compute',
    constraints: { min: 1, max: 64 }, depends_on: [], affects_options_of: [],
    description: null, default_value: 2 },
  { key: 'os', label: 'Betriebssystem', type: 'enum', required: true,
    tofu_variable_name: 'os', display_order: 2, group: 'System',
    constraints: { options: [
      { value: 'ubuntu', label: 'Ubuntu', enabled: true },
      { value: 'rhel', label: 'RHEL', enabled: true },
    ] }, depends_on: [], affects_options_of: [],
    description: null, default_value: null },
  { key: 'backup', label: 'Backup', type: 'boolean', required: false,
    tofu_variable_name: 'backup', display_order: 3, group: 'Compute',
    constraints: {}, depends_on: [], affects_options_of: [],
    description: 'Backup aktivieren', default_value: false },
]

describe('ParameterForm', () => {
  it('renders all visible parameters', () => {
    render(<ParameterForm parameters={mockParams} values={{}} onChange={vi.fn()} />)
    expect(screen.getByLabelText(/CPU-Kerne/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Betriebssystem/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Backup/)).toBeInTheDocument()
  })

  it('renders group headers', () => {
    render(<ParameterForm parameters={mockParams} values={{}} onChange={vi.fn()} />)
    expect(screen.getByText('Compute')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
  })

  it('shows required indicator', () => {
    render(<ParameterForm parameters={mockParams} values={{}} onChange={vi.fn()} />)
    const cpuLabel = screen.getByText('CPU-Kerne')
    expect(cpuLabel.parentElement?.textContent).toContain('*')
  })
})
