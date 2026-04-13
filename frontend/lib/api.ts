// API client for the AI Platform backend

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080'

function getToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('ai_platform_token')
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  useApiKey = false
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  return res.json()
}

// ── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, full_name: string, team_name: string) =>
    request<{ access_token: string }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name, team_name }),
    }),

  me: () => request<any>('/auth/me'),
}

// ── API Keys ────────────────────────────────────────────────────────────────
export const keysApi = {
  list: () => request<any[]>('/v1/keys'),
  create: (name: string, expires_in_days?: number) =>
    request<any>('/v1/keys', {
      method: 'POST',
      body: JSON.stringify({ name, expires_in_days }),
    }),
  revoke: (id: string) => request<any>(`/v1/keys/${id}`, { method: 'DELETE' }),
}

// ── Usage ────────────────────────────────────────────────────────────────────
export const usageApi = {
  summary: (days = 30) => request<any>(`/v1/usage/summary?days=${days}`),
  logs: (page = 1, per_page = 50, service?: string) =>
    request<any>(`/v1/usage/logs?page=${page}&per_page=${per_page}${service ? `&service=${service}` : ''}`),
}

// ── Agents ────────────────────────────────────────────────────────────────────
export const agentsApi = {
  list: () => request<any[]>('/v1/agents'),
  create: (data: any) => request<any>('/v1/agents', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: any) => request<any>(`/v1/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  delete: (id: string) => request<any>(`/v1/agents/${id}`, { method: 'DELETE' }),
}

// ── RAG ────────────────────────────────────────────────────────────────────────
export const ragApi = {
  listCollections: () => request<any[]>('/v1/collections'),
  createCollection: (data: any) => request<any>('/v1/collections', { method: 'POST', body: JSON.stringify(data) }),
  getCollection: (id: string) => request<any>(`/v1/collections/${id}`),
  deleteCollection: (id: string) => request<any>(`/v1/collections/${id}`, { method: 'DELETE' }),

  uploadDocument: async (collection_id: string, file: File) => {
    const token = getToken()
    const formData = new FormData()
    formData.append('collection_id', collection_id)
    formData.append('file', file)
    const res = await fetch(`${API_URL}/v1/documents`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Upload failed')
    }
    return res.json()
  },

  deleteDocument: (id: string) => request<any>(`/v1/documents/${id}`, { method: 'DELETE' }),

  search: (collection_id: string, query: string, top_k = 5) =>
    request<any>(`/v1/collections/${collection_id}/search`, {
      method: 'POST',
      body: JSON.stringify({ query, top_k }),
    }),
}

// ── Billing ────────────────────────────────────────────────────────────────────
export const billingApi = {
  getQuota: () => request<any>('/v1/billing/quota'),
  upgrade: (plan: string) => request<any>('/v1/billing/upgrade', { method: 'POST', body: JSON.stringify({ plan }) }),
}

// ── Teams ────────────────────────────────────────────────────────────────────
export const teamsApi = {
  getCurrent: () => request<any>('/v1/teams/current'),
}

// ── Webhooks ────────────────────────────────────────────────────────────────────
export const webhooksApi = {
  list: () => request<any[]>('/v1/webhooks'),
  create: (data: any) => request<any>('/v1/webhooks', { method: 'POST', body: JSON.stringify(data) }),
  delete: (id: string) => request<any>(`/v1/webhooks/${id}`, { method: 'DELETE' }),
}
