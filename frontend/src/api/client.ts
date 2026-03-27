import { ApiError } from '../types/common'

async function handleResponse(response: Response): Promise<unknown> {
  const data = await response.json()

  if (!response.ok) {
    throw new ApiError(
      response.status,
      data.error_code ?? 'UNKNOWN_ERROR',
      data.details ?? null,
      data.request_id ?? '',
      data.message ?? 'An error occurred',
    )
  }

  return data
}

function buildHeaders(token?: string): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

export const apiClient = {
  async get(url: string, token?: string): Promise<unknown> {
    const response = await fetch(url, {
      method: 'GET',
      headers: buildHeaders(token),
    })
    return handleResponse(response)
  },

  async post(url: string, body?: unknown, token?: string): Promise<unknown> {
    const response = await fetch(url, {
      method: 'POST',
      headers: buildHeaders(token),
      body: body ? JSON.stringify(body) : undefined,
    })
    return handleResponse(response)
  },

  async patch(url: string, body: unknown, token?: string): Promise<unknown> {
    const response = await fetch(url, {
      method: 'PATCH',
      headers: buildHeaders(token),
      body: JSON.stringify(body),
    })
    return handleResponse(response)
  },

  async put(url: string, body: unknown, token?: string): Promise<unknown> {
    const response = await fetch(url, {
      method: 'PUT',
      headers: buildHeaders(token),
      body: JSON.stringify(body),
    })
    return handleResponse(response)
  },

  async del(url: string, token?: string): Promise<void> {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: buildHeaders(token),
    })
    if (!response.ok) {
      const data = await response.json()
      throw new ApiError(
        response.status,
        data.error_code ?? 'UNKNOWN_ERROR',
        data.details ?? null,
        data.request_id ?? '',
        data.message ?? 'An error occurred',
      )
    }
  },
}
