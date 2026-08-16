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

export const applyTask = async (id, { humanConfirmed, judgeVerdict } = {}) => {
  const params = new URLSearchParams({
    human_confirmed: humanConfirmed ? 'true' : 'false',
  })
  if (judgeVerdict) {
    params.append('judge_verdict', judgeVerdict)
  }
  return fetchAPI(`/dashboard/tasks/${id}/apply?${params.toString()}`, {
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

export const runPhase1Cycle = async (options = {}) => {
  const params = new URLSearchParams()
  if (options.daysBack) params.append('days_back', String(options.daysBack))
  if (options.scheduleContentCount !== undefined) {
    params.append('schedule_content_count', String(options.scheduleContentCount))
  }
  if (options.pushToSheets !== undefined) {
    params.append('push_to_sheets', String(options.pushToSheets))
  }

  const queryString = params.toString()
  const endpoint = queryString
    ? `/dashboard/phase1-cycle?${queryString}`
    : '/dashboard/phase1-cycle'

  return fetchAPI(endpoint, {
    method: 'POST',
  })
}

export const previewContentForTask = async (taskId) => {
  return fetchAPI(`/content/preview-for-task?task_id=${taskId}`, {
    method: 'POST',
  })
}

export const publishContentTask = async (taskId, { humanConfirmed, judgeVerdict }) => {
  const params = new URLSearchParams({
    task_id: String(taskId),
    human_confirmed: humanConfirmed ? 'true' : 'false',
  })
  if (judgeVerdict) {
    params.append('judge_verdict', judgeVerdict)
  }

  return fetchAPI(`/content/generate-and-publish?${params.toString()}`, {
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

export const getWorkflowLogs = async (filters = {}) => {
  const params = new URLSearchParams()
  if (filters.days) params.append('days', String(filters.days))
  if (filters.limit) params.append('limit', String(filters.limit))
  if (filters.workflowName) params.append('workflow_name', filters.workflowName)
  if (filters.status) params.append('status', filters.status)
  const queryString = params.toString()
  const endpoint = queryString ? `/dashboard/logs?${queryString}` : '/dashboard/logs'
  return fetchAPI(endpoint)
}

export const getLlmAudit = async (filters = {}) => {
  const params = new URLSearchParams()
  if (filters.days) params.append('days', String(filters.days))
  if (filters.limit) params.append('limit', String(filters.limit))
  if (filters.taskType) params.append('task_type', filters.taskType)
  if (filters.status) params.append('status', filters.status)
  if (filters.includeBodies) params.append('include_bodies', 'true')
  const queryString = params.toString()
  const endpoint = queryString ? `/llm/audit?${queryString}` : '/llm/audit'
  return fetchAPI(endpoint)
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
