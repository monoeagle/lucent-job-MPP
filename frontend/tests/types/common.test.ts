import { describe, it, expect } from 'vitest'
import { hasRole, isAdmin, isApprover, ApiError } from '../../src/types/common'

describe('hasRole', () => {
  it('returns true when user has role', () => {
    const user = { username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'] }
    expect(hasRole(user, 'requester')).toBe(true)
  })

  it('returns false when user lacks role', () => {
    const user = { username: 'test', display_name: 'Test', email: 'test@test.local', roles: ['requester'] }
    expect(hasRole(user, 'admin')).toBe(false)
  })

  it('returns false for null user', () => {
    expect(hasRole(null, 'admin')).toBe(false)
  })
})

describe('isAdmin', () => {
  it('returns true for admin', () => {
    const user = { username: 'admin', display_name: 'Admin', email: 'a@test.local', roles: ['admin'] }
    expect(isAdmin(user)).toBe(true)
  })
})

describe('isApprover', () => {
  it('returns true for approver', () => {
    const user = { username: 'app', display_name: 'App', email: 'a@test.local', roles: ['approver'] }
    expect(isApprover(user)).toBe(true)
  })
})

describe('ApiError', () => {
  it('creates with all fields', () => {
    const err = new ApiError(400, 'VALIDATION_FAILED', { fields: [] }, 'req-1', 'Bad request')
    expect(err.status).toBe(400)
    expect(err.errorCode).toBe('VALIDATION_FAILED')
    expect(err.name).toBe('ApiError')
  })
})
