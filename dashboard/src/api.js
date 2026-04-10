const API_KEY = '2xkosINFyLDgo1KBDc2xIIT_eQYSgPAFVpaq_Iixa8o'
const API_URL = import.meta.env.VITE_API_URL || ''

const fetchAPI = async (endpoint, options = {}) => {
  const url = `${API_URL}/api${endpoint}`
  const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
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
