const BASE = '/api/v1'

function getToken() {
  return localStorage.getItem('pixora_token')
}

async function request(path, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, { headers, ...options })

  if (res.status === 401) {
    localStorage.removeItem('pixora_token')
    localStorage.removeItem('pixora_refresh')
    localStorage.removeItem('pixora_user')
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  if (res.status === 402) {
    const err = await res.json()
    throw new Error(err.detail?.message || 'Quota exceeded. Please upgrade your plan.')
  }

  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  health: () => request('/health'),

  // Auth
  me: () => request('/auth/me'),

  // Billing
  getPlan: () => request('/billing/plan'),
  getPlans: () => request('/billing/plans'),
  getUsage: () => request('/billing/usage'),
  upgradePlan: (plan) => request('/billing/upgrade', { method: 'POST', body: JSON.stringify({ plan }) }),

  // Parse
  createParse: (data) => request('/parse', { method: 'POST', body: JSON.stringify(data) }),
  getParse: (id) => request(`/parse/${id}`),
  listParses: () => request('/parse'),
  cancelParse: (id) => request(`/parse/${id}/cancel`, { method: 'POST' }),
  deleteParse: (id) => request(`/parse/${id}`, { method: 'DELETE' }),
  getJobFileUrl: (id) => `${BASE}/parse/${id}/file`,
  rerunJob: (id, tier = '') => {
    const form = new FormData()
    if (tier) form.append('tier', tier)
    const token = getToken()
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    return fetch(`${BASE}/parse/${id}/rerun`, { method: 'POST', body: form, headers }).then(r => {
      if (!r.ok) throw new Error(`Rerun failed: ${r.status}`)
      return r.json()
    })
  },

  // Extract
  createExtract: (data) => request('/extract', { method: 'POST', body: JSON.stringify(data) }),
  listExtracts: () => request('/extract'),

  // Classify
  createClassify: (data) => request('/classify', { method: 'POST', body: JSON.stringify(data) }),
  listClassifies: () => request('/classify'),

  // Quality
  getQuality: (jobId) => request(`/parse/${jobId}/quality`),
  getGrounding: (jobId) => request(`/parse/${jobId}/grounding`),
  getTrace: (jobId) => request(`/parse/${jobId}/trace`),
  getCost: (jobId) => request(`/parse/${jobId}/cost`),

  // Schemas
  listSchemas: () => request('/schemas'),
  createSchema: (data) => request('/schemas', { method: 'POST', body: JSON.stringify(data) }),
  deleteSchema: (id) => request(`/schemas/${id}`, { method: 'DELETE' }),

  // Review
  getReviewQueue: () => request('/review/queue'),
  submitReview: (docId, data) => request(`/review/${docId}`, { method: 'POST', body: JSON.stringify(data) }),

  // Evals
  runSuite: (data) => request('/evals/run', { method: 'POST', body: JSON.stringify(data) }),
  listReports: () => request('/evals/reports'),
  getDrift: () => request('/evals/drift'),

  // Webhooks
  listWebhooks: () => request('/webhooks'),
  createWebhook: (data) => request('/webhooks', { method: 'POST', body: JSON.stringify(data) }),
  deleteWebhook: (id) => request(`/webhooks/${id}`, { method: 'DELETE' }),

  // File upload
  uploadAndParse: async (file, tier = 'agentic', accuracyTier = 'standard') => {
    const form = new FormData()
    form.append('file', file)
    form.append('tier', tier)
    form.append('accuracy_tier', accuracyTier)
    const token = getToken()
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    const res = await fetch(`${BASE}/parse/upload`, { method: 'POST', body: form, headers })
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
    return res.json()
  },

  // Audit
  getAuditLog: (limit = 100) => request(`/audit/log?limit=${limit}`),
  getServiceCalls: (limit = 100) => request(`/audit/service-calls?limit=${limit}`),
  getCostSummary: () => request('/audit/costs'),
  getJobAudit: (jobId) => request(`/audit/jobs/${jobId}`),
  exportAudit: (jobId, format = 'json') => `${BASE}/audit/export/${jobId}?format=${format}`,

  // Billing - SLA
  getSLATiers: () => request('/billing/sla-tiers'),

  // Dashboard
  getDashboardStats: () => request('/dashboard/stats'),
  refreshDashboardStats: () => request('/dashboard/refresh', { method: 'POST' }),
  getBenchmarkResults: () => request('/dashboard/benchmark-results'),

  // Models
  listModels: () => request('/models'),
  getModel: (id) => request(`/models/${id}`),
}
