import React, { useState, useEffect, useCallback } from 'react'
import {
  BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'
import { RefreshCw, Zap, CheckCircle, AlertCircle, Eye, X, Clock, KeyRound, LogOut } from 'lucide-react'
import {
  generateTasks,
  getTasks,
  approveTask,
  dismissTask,
  delayTask,
  refreshAllData,
  getMetrics,
  getChannelMetrics,
  getStoredApiKey,
  setStoredApiKey,
  clearStoredApiKey,
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

const Toast = ({ message, type, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000)
    return () => clearTimeout(timer)
  }, [onClose])

  const bgColor = type === 'success' ? 'bg-green-600' : 'bg-red-600'

  return (
    <div className={`${bgColor} text-white px-4 py-3 rounded-lg shadow-lg animate-pulse`}>
      {message}
    </div>
  )
}

export default function App() {
  const [apiKey, setApiKey] = useState(() => getStoredApiKey())
  const [apiKeyInput, setApiKeyInput] = useState('')
  const [tasks, setTasks] = useState([])
  const [metrics, setMetrics] = useState(null)
  const [channelMetrics, setChannelMetrics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [typeFilter, setTypeFilter] = useState('all')
  const [toast, setToast] = useState(null)
  const [generatingTasks, setGeneratingTasks] = useState(false)
  const [refreshingAll, setRefreshingAll] = useState(false)

  const fetchData = useCallback(async () => {
    if (!apiKey) {
      setLoading(false)
      return
    }

    try {
      setLoading(true)
      const [tasksData, metricsData, channelsData] = await Promise.all([
        getTasks({ limit: 50 }),
        getMetrics(),
        getChannelMetrics(),
      ])
      setTasks(tasksData.tasks || [])
      setMetrics(metricsData.metrics || metricsData)
      setChannelMetrics(channelsData.metrics || channelsData)
    } catch (error) {
      console.error('Error fetching data:', error)
      setToast({ message: 'Failed to load dashboard data', type: 'error' })
    } finally {
      setLoading(false)
    }
  }, [apiKey])

  useEffect(() => {
    if (!apiKey) {
      setLoading(false)
      return undefined
    }

    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [apiKey, fetchData])

  const handleSaveApiKey = async (event) => {
    event.preventDefault()
    const storedKey = setStoredApiKey(apiKeyInput)
    if (!storedKey) {
      setToast({ message: 'Enter an API key', type: 'error' })
      return
    }
    setApiKey(storedKey)
    setApiKeyInput('')
    setToast({ message: 'API key saved for this browser', type: 'success' })
  }

  const handleClearApiKey = () => {
    clearStoredApiKey()
    setApiKey('')
    setTasks([])
    setMetrics(null)
    setChannelMetrics(null)
  }

  const handleGenerateTasks = async () => {
    try {
      setGeneratingTasks(true)
      await generateTasks()
      setToast({ message: 'Tasks generated successfully', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error generating tasks:', error)
      setToast({ message: 'Failed to generate tasks', type: 'error' })
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
      setToast({ message: 'Failed to approve task', type: 'error' })
    }
  }

  const handleDismissTask = async (id) => {
    try {
      await dismissTask(id)
      setToast({ message: 'Task dismissed', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error dismissing task:', error)
      setToast({ message: 'Failed to dismiss task', type: 'error' })
    }
  }

  const handleDelayTask = async (id) => {
    try {
      await delayTask(id, 24)
      setToast({ message: 'Task delayed 24 hours', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error delaying task:', error)
      setToast({ message: 'Failed to delay task', type: 'error' })
    }
  }

  const handleRefreshAll = async () => {
    try {
      setRefreshingAll(true)
      await refreshAllData()
      setToast({ message: 'Data refreshed & new tasks generated', type: 'success' })
      await fetchData()
    } catch (error) {
      console.error('Error refreshing all data:', error)
      setToast({ message: 'Failed to refresh data', type: 'error' })
    } finally {
      setRefreshingAll(false)
    }
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

  const taskTypeData = metrics?.type_breakdown ? Object.entries(metrics.type_breakdown).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value,
  })) : []

  const taskPriorityData = metrics?.priority_breakdown ? Object.entries(metrics.priority_breakdown).map(([name, value]) => ({
    name,
    value,
  })) : []

  if (!apiKey) {
    return (
      <div style={{ backgroundColor: COLORS.bg, minHeight: '100vh' }} className="p-6 flex items-center justify-center">
        <form
          onSubmit={handleSaveApiKey}
          style={{ backgroundColor: COLORS.cardBg }}
          className="w-full max-w-md rounded-lg p-6 shadow-xl"
        >
          <div className="flex items-center gap-3 mb-4">
            <KeyRound size={24} style={{ color: '#10b981' }} />
            <h1 className="text-2xl font-bold" style={{ color: COLORS.text }}>
              OLS Marketing Dashboard
            </h1>
          </div>
          <label className="block text-sm font-semibold mb-2" style={{ color: COLORS.textDim }}>
            API key
          </label>
          <input
            type="password"
            value={apiKeyInput}
            onChange={(event) => setApiKeyInput(event.target.value)}
            className="w-full px-4 py-3 rounded-lg mb-4"
            style={{
              backgroundColor: '#1a1a2e',
              color: COLORS.text,
              border: '1px solid #333',
            }}
            autoComplete="off"
            autoFocus
          />
          <button
            type="submit"
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg transition"
            style={{ backgroundColor: '#10b981', color: '#fff' }}
          >
            <KeyRound size={18} />
            Unlock Dashboard
          </button>
          {toast && (
            <div className="fixed bottom-4 right-4 z-50">
              <Toast
                message={toast.message}
                type={toast.type}
                onClose={() => setToast(null)}
              />
            </div>
          )}
        </form>
      </div>
    )
  }

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
          <button
            onClick={handleClearApiKey}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition"
            style={{ backgroundColor: '#2a2a3e', color: COLORS.text }}
          >
            <LogOut size={18} />
            Lock
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
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
      </div>

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
          {loading ? (
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
          {channelMetrics ? (
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

function TaskCard({ task, onApprove, onDismiss, onDelay }) {
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
