const API_URL = import.meta.env.VITE_API_URL || ''
const API_KEY_STORAGE_KEY = 'olsApiKey'

export const getStoredApiKey = () => {
  return window.localStorage.getItem(API_KEY_STORAGE_KEY) || ''
}

export const setStoredApiKey = (apiKey) => {
  const trimmed = apiKey.trim()
  if (trimmed) {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, trimmed)
  }
  return trimmed
}

export const clearStoredApiKey = () => {
  window.localStorage.removeItem(API_KEY_STORAGE_KEY)
}

const fetchAPI = async (endpoint, options = {}) => {
  const apiKey = options.apiKey || getStoredApiKey()
  if (!apiKey) {
    throw new Error('Missing API key')
  }

  const url = `${API_URL}/api${endpoint}`
  const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey,
    ...options.headers,
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`)
  }

  return response.json()
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
