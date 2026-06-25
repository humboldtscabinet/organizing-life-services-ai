const API_URL = import.meta.env.VITE_API_URL || ''
const DEV_API_KEY_STORAGE = 'ols-dashboard-api-key'
const DEV_AUTH_REQUIRED = import.meta.env.DEV

export class APIRequestError extends Error {
  constructor(message, { status, code, detail, payload } = {}) {
    super(message)
    this.name = 'APIRequestError'
    this.status = status
    this.code = code
    this.detail = detail || message
    this.payload = payload
  }
}

export const isDevAuthRequired = () => DEV_AUTH_REQUIRED

export const getDevApiKey = () => {
  if (!DEV_AUTH_REQUIRED) {
    return ''
  }

  return sessionStorage.getItem(DEV_API_KEY_STORAGE)?.trim() || ''
}

export const setDevApiKey = (apiKey) => {
  if (!DEV_AUTH_REQUIRED) {
    return ''
  }

  const normalized = apiKey.trim()
  if (normalized) {
    sessionStorage.setItem(DEV_API_KEY_STORAGE, normalized)
  } else {
    sessionStorage.removeItem(DEV_API_KEY_STORAGE)
  }

  return normalized
}

export const clearDevApiKey = () => {
  if (DEV_AUTH_REQUIRED) {
    sessionStorage.removeItem(DEV_API_KEY_STORAGE)
  }
}

const buildHeaders = (headers = {}) => {
  const mergedHeaders = {
    'Content-Type': 'application/json',
    ...headers,
  }

  if (DEV_AUTH_REQUIRED) {
    const apiKey = getDevApiKey()
    if (apiKey) {
      mergedHeaders['X-API-Key'] = apiKey
    }
  }

  return mergedHeaders
}

const toAPIError = (response, payload) => {
  const detail = typeof payload === 'object' && payload !== null
    ? payload.detail || payload.message || `API request failed with status ${response.status}`
    : `API request failed with status ${response.status}`

  return new APIRequestError(detail, {
    status: response.status,
    code: payload?.code,
    detail,
    payload,
  })
}

const parseResponse = async (response) => {
  const contentType = response.headers.get('content-type') || ''
  const isJSON = contentType.includes('application/json')
  const payload = isJSON ? await response.json() : await response.text()

  if (!response.ok) {
    throw toAPIError(response, payload)
  }

  return payload
}

const fetchAPI = async (endpoint, options = {}) => {
  if (DEV_AUTH_REQUIRED && !getDevApiKey()) {
    throw new APIRequestError(
      'Enter the API key for this dev session before loading dashboard data.',
      {
        status: 401,
        code: 'missing_api_key',
      }
    )
  }

  const url = `${API_URL}/api${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers: buildHeaders(options.headers),
  })

  return parseResponse(response)
}

export const generateTasks = async () => {
  return fetchAPI('/dashboard/generate-tasks', {
    method: 'POST',
  })
}

export const getTasks = async (filters = {}) => {
  const params = new URLSearchParams()
  if (filters.status) params.append('status', filters.status)
  if (filters.task_type) params.append('task_type', filters.task_type)
  if (filters.limit) params.append('limit', filters.limit)

  const queryString = params.toString()
  const endpoint = queryString ? `/dashboard/tasks?${queryString}` : '/dashboard/tasks'
  return fetchAPI(endpoint)
}

export const approveTask = async (id) => {
  return fetchAPI(`/dashboard/tasks/${id}/approve`, {
    method: 'POST',
  })
}

export const dismissTask = async (id) => {
  return fetchAPI(`/dashboard/tasks/${id}/dismiss`, {
    method: 'POST',
  })
}

export const delayTask = async (id, hours = 24) => {
  return fetchAPI(`/dashboard/tasks/${id}/delay?hours=${hours}`, {
    method: 'POST',
  })
}

export const refreshAllData = async () => {
  return fetchAPI('/dashboard/refresh', {
    method: 'POST',
  })
}

export const getMetrics = async () => {
  return fetchAPI('/dashboard/metrics')
}

export const getChannelMetrics = async () => {
  return fetchAPI('/dashboard/metrics/channels')
}

export const getAlerts = async (filters = {}) => {
  const params = new URLSearchParams()
  if (filters.status) params.append('status', filters.status)
  if (filters.severity) params.append('severity', filters.severity)
  if (filters.source) params.append('source', filters.source)
  if (filters.limit) params.append('limit', filters.limit)

  const queryString = params.toString()
  const endpoint = queryString ? `/dashboard/alerts?${queryString}` : '/dashboard/alerts'
  return fetchAPI(endpoint)
}

export const getAlertMetrics = async () => {
  return fetchAPI('/dashboard/alerts/metrics')
}

export const acknowledgeAlert = async (id) => {
  return fetchAPI(`/dashboard/alerts/${id}/acknowledge`, {
    method: 'POST',
  })
}

export const dismissAlert = async (id) => {
  return fetchAPI(`/dashboard/alerts/${id}/dismiss`, {
    method: 'POST',
  })
}

export const resolveAlert = async (id) => {
  return fetchAPI(`/dashboard/alerts/${id}/resolve`, {
    method: 'POST',
  })
}
