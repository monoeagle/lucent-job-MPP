import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Notifications from '../../src/pages/Notifications'

describe('Notifications', () => {
  it('renders the notifications heading', () => {
    render(<Notifications />)
    expect(screen.getByText('Benachrichtigungen')).toBeInTheDocument()
  })

  it('shows empty state message', () => {
    render(<Notifications />)
    expect(screen.getByText('Keine Benachrichtigungen vorhanden')).toBeInTheDocument()
  })
})
