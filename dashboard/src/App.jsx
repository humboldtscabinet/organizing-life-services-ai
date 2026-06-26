import React, { useState, useEffect, useCallback } from 'react'
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { RefreshCw, Zap, CheckCircle, AlertCircle, Eye, Clock, Bell } from 'lucide-react'
import {
  acknowledgeAlert,
  clearDevApiKey,
  dismissTask,
  dismissAlert,
  generateTasks,
  getAlertMetrics,
  getAlerts,
  getChannelMetrics,
  getDevApiKey,
  getMetrics,
  getTasks,
  isDevAuthRequired,
  refreshAllData,
  setDevApiKey,
  approveTask,
  delayTask,
} from './api'

const COLORS = {
  bg: '#1a1a2e',
  cardBg: '#16213e',
  accent: '#0f3460',
  text: '#e0e0e0',
  textDim: '#a0a0a0',
}

const TASK_TYPE_COLORS = {
  seo: '#3b82f6',
  ads: '#a855f7',
  shopify: '#10b981',
}

const PRIORITY_COLORS = {
  HIGH: '#ef4444',
  MEDIUM: '#eab308',
  LOW: '#10b981',
}

const ALERT_SEVERITY_COLORS = {
  CRITICAL: '#ef4444',
  WARNING: '#eab308',
  INFO: '#3b82f6',
}

const DEV_AUTH_REQUIRED = isDevAuthRequired()

const getErrorMessage = (error, fallback) => error?.detail || error?.message || fallback

const Toast = ({ message, type, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000)
    return () => clearTimeout(timer)
  }, [onClose])

  const bgColor = type === 'success'
    ? 'bg-green-600'
    : type === 'warning'
      ? 'bg-amber-500'
      : 'bg-red-600'

  return (
    <div className={`${bgColor} text-white px-4 py-3 rounded-lg shadow-lg animate-pulse`}>
      {message}
    </div>
  )
}

export default function App() {
  const [tasks, setTasks] = useState([])
  const [alerts, setAlerts] = useState([])
  const [alertMetrics, setAlertMetrics] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [channelMetrics, setChannelMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [typeFilter, setTypeFilter] = useState('all')
  const [toast, setToast] = useState(null)
  const [generatingTasks, setGeneratingTasks] = useState(false)
  const [refreshingAll, setRefreshingAll] = useState(false)
  const [sessionApiKey, setSessionApiKey] = useState(() => getDevApiKey())
  const [apiKeyInput, setApiKeyInput] = useState('')
  const hasRequiredApiKey = !DEV_AUTH_REQUIRED || Boolean(sessionApiKey)

  const fetchData = useCallback(async () => {
    if (!hasRequiredApiKey) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      const [tasksData, metricsData, channelsData, alertsData, alertMetricsData] = await Promise.all([
        getTasks({ limit: 50 }),
        getMetrics(),
        getChannelMetrics(),
        getAlerts({ status: 'open', limit: 20 }),
        getAlertMetrics(),
      ])
      setTasks(tasksData.tasks || [])
      setMetrics(metricsData.metrics || metricsData)
      setChannelMetrics(channelsData.metrics || channelsData)
      setAlerts(alertsData.alerts || [])
      setAlertMetrics(alertMetricsData.metrics || alertMetricsData)
    } catch (error) {
      console.error('Error fetching data:', error)
      setToast({ message: getErrorMessage(error, 'Failed to load dashboard data'), type: 'error' })
    } finally {
      setLoading(false)
    }
  }, [hasRequiredApiKey])

  useEffect(() => {
    if (!hasRequiredApiKey) {
      setTasks([])
      setAlerts([])
      setAlertMetrics(null)
      setMetrics(null)
      setChannelMetrics(null)
      setLoading(false)
      return undefined
    }

    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [fetchData, hasRequiredApiKey])

  const handleGenerateTasks = async () => {
    try {
      setGeneratingTasks(true)
      await generateTasks()
      setToast({ message: 'Tasks generated successfully', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error generating tasks:', error)
      setToast({ message: getErrorMessage(error, 'Failed to generate tasks'), type: 'error' })
    } finally {
      setGeneratingTasks(false)
    }
  }

  const handleApproveTask = async (id) => {
    try {
      await approveTask(id)
      setToast({ message: 'Task approved', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error approving task:', error)
      setToast({ message: getErrorMessage(error, 'Failed to approve task'), type: 'error' })
    }
  }

  const handleDismissTask = async (id) => {
    try {
      await dismissTask(id)
      setToast({ message: 'Task dismissed', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error dismissing task:', error)
      setToast({ message: getErrorMessage(error, 'Failed to dismiss task'), type: 'error' })
    }
  }

  const handleDelayTask = async (id) => {
    try {
      await delayTask(id, 24)
      setToast({ message: 'Task delayed 24 hours', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error delaying task:', error)
      setToast({ message: getErrorMessage(error, 'Failed to delay task'), type: 'error' })
    }
  }

  const handleAcknowledgeAlert = async (id) => {
    try {
      await acknowledgeAlert(id)
      setToast({ message: 'Alert acknowledged', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error acknowledging alert:', error)
      setToast({ message: getErrorMessage(error, 'Failed to acknowledge alert'), type: 'error' })
    }
  }

  const handleDismissAlert = async (id) => {
    try {
      await dismissAlert(id)
      setToast({ message: 'Alert dismissed', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error dismissing alert:', error)
      setToast({ message: getErrorMessage(error, 'Failed to dismiss alert'), type: 'error' })
    }
  }

  const handleRefreshAll = async () => {
    try {
      setRefreshingAll(true)
      const result = await refreshAllData()
      setToast({
        message: result.status === 'partial'
          ? 'Refresh completed with some follow-up needed'
          : 'Data refreshed and new tasks generated',
        type: result.status === 'partial' ? 'warning' : 'success',
      })
      await fetchData()
    } catch (error) {
      console.error('Error refreshing all data:', error)
      setToast({ message: getErrorMessage(error, 'Failed to refresh data'), type: 'error' })
    } finally {
      setRefreshingAll(false)
    }
  }

  const handleSaveApiKey = async () => {
    const normalized = apiKeyInput.trim()
    if (!normalized) {
      setToast({ message: 'Enter an API key before saving', type: 'error' })
      return
    }

    const storedApiKey = setDevApiKey(normalized)
    setSessionApiKey(storedApiKey)
    setApiKeyInput('')
    setToast({ message: 'API key saved for this browser session', type: 'success' })
    await fetchData()
  }

  const handleClearApiKey = () => {
    clearDevApiKey()
    setSessionApiKey('')
    setApiKeyInput('')
    setTasks([])
    setAlerts([])
    setAlertMetrics(null)
    setMetrics(null)
    setChannelMetrics(null)
    setToast({ message: 'Session API key cleared', type: 'warning' })
  }

  const filteredTasks = tasks.filter(task => {
    const statusMatch = statusFilter === 'all' || task.status === statusFilter
    const typeMatch = typeFilter === 'all' || task.task_type === typeFilter
    return statusMatch && typeMatch
  })

  const completedToday = metrics?.status_breakdown?.completed || 0
  const pendingCount = metrics?.status_breakdown?.pending || 0
  const highPriorityCount = metrics?.priority_breakdown?.HIGH || 0
  const activeChannels = channelMetrics ? Object.keys(channelMetrics).filter(k => k !== 'status').length : 0
  const openAlertCount = alertMetrics?.open_count || 0

  const taskTypeData = metrics?.type_breakdown ? Object.entries(metrics.type_breakdown).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  })) : []

  const taskPriorityData = metrics?.priority_breakdown ? Object.entries(metrics.priority_breakdown).map(([name, value]) => ({
    name,
    value,
  })) : []

  return (
    <div style={{ backgroundColor: COLORS.bg, minHeight: '100vh' }} className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold" style={{ color: COLORS.text }}>
          OLS Marketing Dashboard
        </h1>
        <div className="flex gap-3">
          <button
            onClick={handleRefreshAll}
            disabled={refreshingAll}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition"
            style={{
              backgroundColor: '#10b981',
              color: '#fff',
              opacity: refreshingAll ? 0.6 : 1,
            }}
          >
            <Zap size={18} className={refreshingAll ? 'animate-spin' : ''} />
            {refreshingAll ? 'Pulling Data...' : 'New Task Set'}
          </button>
          <button
            onClick={handleGenerateTasks}
            disabled={generatingTasks}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition"
            style={{
              backgroundColor: '#0f3460',
              color: COLORS.text,
              opacity: generatingTasks ? 0.6 : 1,
            }}
          >
            <Zap size={18} />
            {generatingTasks ? 'Generating...' : 'Generate Tasks'}
          </button>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition"
            style={{ backgroundColor: '#0f3460', color: COLORS.text }}
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {DEV_AUTH_REQUIRED && (
        <div
          style={{ backgroundColor: COLORS.cardBg, border: `1px solid ${COLORS.accent}` }}
          className="rounded-lg p-4 mb-8"
        >
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold mb-1" style={{ color: COLORS.text }}>
                Development API Access
              </h2>
              <p style={{ color: COLORS.textDim }}>
                The dev dashboard stores the API key in `sessionStorage` for this browser session only.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 sm:items-center">
              <input
                type="password"
                value={apiKeyInput}
                onChange={(event) => setApiKeyInput(event.target.value)}
                placeholder={sessionApiKey ? 'Update API key' : 'Enter API key'}
                className="px-4 py-2 rounded-lg"
                style={{
                  backgroundColor: COLORS.bg,
                  color: COLORS.text,
                  border: '1px solid #333',
                  minWidth: '280px',
                }}
              />
              <button
                onClick={handleSaveApiKey}
                className="px-4 py-2 rounded-lg font-semibold"
                style={{ backgroundColor: '#0f3460', color: COLORS.text }}
              >
                Save Key
              </button>
              <button
                onClick={handleClearApiKey}
                className="px-4 py-2 rounded-lg font-semibold"
                style={{ backgroundColor: '#666', color: '#fff' }}
              >
                Clear Key
              </button>
            </div>
          </div>
          <p className="mt-3 text-sm" style={{ color: sessionApiKey ? '#10b981' : '#eab308' }}>
            {sessionApiKey
              ? 'A session API key is loaded for this browser.'
              : 'Enter the current OLS API key to enable dashboard requests in dev mode.'}
          </p>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
        <KPICard
          title="Pending Tasks"
          value={pendingCount}
          color="#eab308"
          icon={<AlertCircle size={24} />}
        />
        <KPICard
          title="Completed Today"
          value={completedToday}
          color="#10b981"
          icon={<CheckCircle size={24} />}
        />
        <KPICard
          title="High Priority"
          value={highPriorityCount}
          color="#ef4444"
          icon={<Zap size={24} />}
        />
        <KPICard
          title="Active Channels"
          value={activeChannels}
          color="#3b82f6"
          icon={<Eye size={24} />}
        />
        <KPICard
          title="Open Alerts"
          value={openAlertCount}
          color={alertMetrics?.critical_open_count ? '#ef4444' : '#eab308'}
          icon={<Bell size={24} />}
        />
      </div>

      <AlertsPanel
        alerts={alerts}
        loading={loading}
        hasRequiredApiKey={hasRequiredApiKey}
        onAcknowledge={handleAcknowledgeAlert}
        onDismiss={handleDismissAlert}
      />

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Task Type Chart */}
        <div style={{ backgroundColor: COLORS.cardBg }} className="rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4" style={{ color: COLORS.text }}>
            Tasks by Type
          </h2>
          {taskTypeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={taskTypeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {taskTypeData.map((entry) => (
                    <Cell key={entry.name} fill={TASK_TYPE_COLORS[entry.name.toLowerCase()] || '#666'} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => value} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center" style={{ color: COLORS.textDim }}>
              No data available
            </div>
          )}
        </div>

        {/* Priority Chart */}
        <div style={{ backgroundColor: COLORS.cardBg }} className="rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4" style={{ color: COLORS.text }}>
            Tasks by Priority
          </h2>
          {taskPriorityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={taskPriorityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="name" stroke={COLORS.textDim} />
                <YAxis stroke={COLORS.textDim} />
                <Tooltip
                  contentStyle={{ backgroundColor: COLORS.cardBg, border: `1px solid ${COLORS.accent}` }}
                  formatter={(value) => value}
                />
                <Bar dataKey="value" fill="#0f3460" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center" style={{ color: COLORS.textDim }}>
              No data available
            </div>
          )}
        </div>
      </div>

      {/* Task Queue Section */}
      <div style={{ backgroundColor: COLORS.cardBg }} className="rounded-lg p-6 mb-8">
        <h2 className="text-2xl font-semibold mb-6" style={{ color: COLORS.text }}>
          Task Queue
        </h2>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex gap-2">
            {['pending', 'approved', 'completed', 'delayed', 'dismissed', 'all'].map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className="px-4 py-2 rounded-lg transition capitalize"
                style={{
                  backgroundColor: statusFilter === filter ? '#0f3460' : '#1a1a2e',
                  color: COLORS.text,
                  border: `1px solid ${statusFilter === filter ? '#0f3460' : '#333'}`,
                }}
              >
                {filter === 'all' ? 'All' : filter}
              </button>
            ))}
          </div>

          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-4 py-2 rounded-lg capitalize"
            style={{
              backgroundColor: '#1a1a2e',
              color: COLORS.text,
              border: `1px solid #333`,
            }}
          >
            <option value="all">All Types</option>
            <option value="seo">SEO</option>
            <option value="ads">Ads</option>
            <option value="shopify">Shopify</option>
          </select>
        </div>

        {/* Task Cards */}
        <div className="space-y-4">
          {!hasRequiredApiKey ? (
            <div className="text-center py-8" style={{ color: COLORS.textDim }}>
              Enter the API key above to load dashboard data.
            </div>
          ) : loading ? (
            <div className="text-center py-8" style={{ color: COLORS.textDim }}>
              Loading tasks...
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="text-center py-8" style={{ color: COLORS.textDim }}>
              No tasks found
            </div>
          ) : (
            filteredTasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onApprove={handleApproveTask}
                onDismiss={handleDismissTask}
                onDelay={handleDelayTask}
              />
            ))
          )}
        </div>
      </div>

      {/* Channel Status */}
      <div>
        <h2 className="text-2xl font-semibold mb-4" style={{ color: COLORS.text }}>
          Channel Status
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {!hasRequiredApiKey ? (
            <div style={{ color: COLORS.textDim }}>Enter the API key above to load channel data.</div>
          ) : channelMetrics ? (
            Object.entries(channelMetrics).map(([channel, data]) => (
              <div key={channel} style={{ backgroundColor: COLORS.cardBg }} className="rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-2" style={{ color: COLORS.text }}>
                  {channel.toUpperCase()}
                </h3>
                <div className="space-y-2" style={{ color: COLORS.textDim }}>
                  <p>Records: <span style={{ color: COLORS.text }}>{data.record_count || 0}</span></p>
                  <p className="text-sm">
                    Last sync: <span style={{ color: COLORS.text }}>
                      {data.last_date ? new Date(data.last_date).toLocaleDateString() : 'N/A'}
                    </span>
                  </p>
                </div>
              </div>
            ))
          ) : (
            <div style={{ color: COLORS.textDim }}>Loading channel data...</div>
          )}
        </div>
      </div>

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-50">
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        </div>
      )}
    </div>
  )
}

function KPICard({ title, value, color, icon }) {
  return (
    <div style={{ backgroundColor: COLORS.cardBg }} className="rounded-lg p-6 flex items-center justify-between">
      <div>
        <p style={{ color: COLORS.textDim }} className="text-sm font-semibold mb-2">
          {title}
        </p>
        <p className="text-4xl font-bold" style={{ color: COLORS.text }}>
          {value}
        </p>
      </div>
      <div style={{ color }}>
        {icon}
      </div>
    </div>
  )
}

function AlertsPanel({ alerts, loading, hasRequiredApiKey, onAcknowledge, onDismiss }) {
  return (
    <div style={{ backgroundColor: COLORS.cardBg }} className="rounded-lg p-6 mb-8">
      <div className="flex items-center gap-3 mb-4">
        <Bell size={22} style={{ color: '#eab308' }} />
        <h2 className="text-2xl font-semibold" style={{ color: COLORS.text }}>
          Alerts
        </h2>
      </div>

      {!hasRequiredApiKey ? (
        <div className="text-center py-6" style={{ color: COLORS.textDim }}>
          Enter the API key above to load alerts.
        </div>
      ) : loading ? (
        <div className="text-center py-6" style={{ color: COLORS.textDim }}>
          Loading alerts...
        </div>
      ) : alerts.length === 0 ? (
        <div className="flex items-center gap-3 rounded-lg p-4" style={{ backgroundColor: COLORS.bg }}>
          <CheckCircle size={20} style={{ color: '#10b981' }} />
          <span style={{ color: COLORS.textDim }}>No open operational alerts</span>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <AlertCard
              key={alert.id}
              alert={alert}
              onAcknowledge={onAcknowledge}
              onDismiss={onDismiss}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function AlertCard({ alert, onAcknowledge, onDismiss }) {
  const severityColor = ALERT_SEVERITY_COLORS[alert.severity] || '#64748b'
  const seenAt = alert.last_seen_at || alert.created_at

  return (
    <div
      style={{ backgroundColor: COLORS.bg, borderLeft: `4px solid ${severityColor}` }}
      className="rounded-lg p-4 flex flex-col md:flex-row md:items-start justify-between gap-4"
    >
      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <span
            className="px-2 py-1 rounded text-xs font-semibold text-white"
            style={{ backgroundColor: severityColor }}
          >
            {alert.severity}
          </span>
          <span className="px-2 py-1 rounded text-xs font-semibold text-white bg-gray-600">
            {alert.source}
          </span>
          {alert.occurrence_count > 1 && (
            <span className="px-2 py-1 rounded text-xs font-semibold text-white bg-slate-600">
              Seen {alert.occurrence_count}x
            </span>
          )}
        </div>
        <h3 className="font-bold mb-1" style={{ color: COLORS.text }}>
          {alert.title}
        </h3>
        {alert.message && (
          <p className="text-sm mb-2" style={{ color: COLORS.textDim }}>
            {alert.message}
          </p>
        )}
        <div className="flex flex-wrap gap-4 text-xs" style={{ color: COLORS.textDim }}>
          {alert.created_at && (
            <span>Created: {new Date(alert.created_at).toLocaleString()}</span>
          )}
          {seenAt && (
            <span>Last seen: {new Date(seenAt).toLocaleString()}</span>
          )}
        </div>
      </div>
      <div className="flex gap-2 shrink-0">
        <button
          onClick={() => onAcknowledge(alert.id)}
          className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80"
          style={{ backgroundColor: '#0f3460' }}
        >
          Acknowledge
        </button>
        <button
          onClick={() => onDismiss(alert.id)}
          className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80"
          style={{ backgroundColor: '#666' }}
        >
          Dismiss
        </button>
      </div>
    </div>
  )
}

function TaskCard({ task, onApprove, onDismiss, onDelay }) {
  const leadScore = task.action_payload?.lead_score
  const leadTier = task.action_payload?.lead_tier
  const leadReasons = task.action_payload?.lead_relevance_reasons || []

  return (
    <div style={{ backgroundColor: COLORS.bg, borderLeft: `4px solid ${PRIORITY_COLORS[task.priority] || '#666'}` }} className="rounded-lg p-4 flex justify-between items-start gap-4">
      <div className="flex-1">
        <div className="flex items-center gap-3 mb-2">
          <span
            className="px-2 py-1 rounded text-xs font-semibold text-white"
            style={{ backgroundColor: PRIORITY_COLORS[task.priority] || '#666' }}
          >
            {task.priority}
          </span>
          <span
            className="px-2 py-1 rounded text-xs font-semibold text-white"
            style={{ backgroundColor: TASK_TYPE_COLORS[task.task_type] || '#666' }}
          >
            {task.task_type.toUpperCase()}
          </span>
          {task.status !== 'pending' && (
            <span className="px-2 py-1 rounded text-xs font-semibold text-white bg-gray-600 capitalize">
              {task.status}
            </span>
          )}
          {typeof leadScore === 'number' && (
            <span
              className="px-2 py-1 rounded text-xs font-semibold text-white"
              style={{
                backgroundColor: leadTier === 'HIGH' ? '#10b981' : leadTier === 'MEDIUM' ? '#eab308' : '#64748b',
              }}
              title={leadReasons.join('; ')}
            >
              Lead {leadTier || 'LOW'} {leadScore}/100
            </span>
          )}
        </div>
        <h3 className="font-bold mb-1" style={{ color: COLORS.text }}>
          {task.title}
        </h3>
        <p className="text-sm mb-2" style={{ color: COLORS.textDim }}>
          {task.description}
        </p>
        {task.finding && (
          <p className="text-xs mb-3" style={{ color: COLORS.textDim }}>
            <span className="font-semibold">Finding:</span> {task.finding}
          </p>
        )}
        <div className="flex gap-4 text-xs" style={{ color: COLORS.textDim }}>
          {task.created_at && (
            <span>Created: {new Date(task.created_at).toLocaleDateString()}</span>
          )}
          {task.approved_at && (
            <span>Approved: {new Date(task.approved_at).toLocaleDateString()}</span>
          )}
          {task.completed_at && (
            <span>Completed: {new Date(task.completed_at).toLocaleDateString()}</span>
          )}
        </div>
      </div>
      {task.status === 'pending' && (
        <div className="flex gap-2">
          <button
            onClick={() => onApprove(task.id)}
            className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80"
            style={{ backgroundColor: '#10b981' }}
          >
            Approve
          </button>
          <button
            onClick={() => onDelay(task.id)}
            className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80 flex items-center gap-1"
            style={{ backgroundColor: '#eab308' }}
          >
            <Clock size={14} />
            Delay
          </button>
          <button
            onClick={() => onDismiss(task.id)}
            className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80"
            style={{ backgroundColor: '#666' }}
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  )
}
