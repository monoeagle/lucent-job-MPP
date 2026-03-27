export interface User {
  username: string
  display_name: string
  email: string
  roles: string[]
}

export interface LoginResponse {
  token: string
  user: User
  expires_at: string
}

export interface ErrorResponse {
  error_code: string
  message: string
  details: Record<string, unknown> | null
  request_id: string
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    public details: Record<string, unknown> | null,
    public requestId: string,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function hasRole(user: User | null, role: string): boolean {
  return user?.roles.includes(role) ?? false
}

export function isAdmin(user: User | null): boolean {
  return hasRole(user, 'admin')
}

export function isApprover(user: User | null): boolean {
  return hasRole(user, 'approver')
}
