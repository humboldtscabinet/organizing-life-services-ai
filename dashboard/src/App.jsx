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
  getLlmAudit,
  getMetrics,
  getTasks,
  getWorkflowLogs,
  isDevAuthRequired,
  previewContentForTask,
  publishContentTask,
  refreshAllData,
  runPhase1Cycle,
  setDevApiKey,
  approveTask,
  applyTask,
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
  content: '#f97316',
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
  const [workflowLogs, setWorkflowLogs] = useState([])
  const [llmAudits, setLlmAudits] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('pending')
  const [typeFilter, setTypeFilter] = useState('all')
  const [toast, setToast] = useState(null)
  const [generatingTasks, setGeneratingTasks] = useState(false)
  const [refreshingAll, setRefreshingAll] = useState(false)
  const [runningPhase1Cycle, setRunningPhase1Cycle] = useState(false)
  const [contentPreview, setContentPreview] = useState(null)
  const [publishTarget, setPublishTarget] = useState(null)
  const [applyTarget, setApplyTarget] = useState(null)
  const [previewLoadingTaskId, setPreviewLoadingTaskId] = useState(null)
  const [publishLoading, setPublishLoading] = useState(false)
  const [applyLoading, setApplyLoading] = useState(false)
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
      const [tasksData, metricsData, channelsData, alertsData, alertMetricsData, logsData, auditData] = await Promise.all([
        getTasks({ limit: 50 }),
        getMetrics(),
        getChannelMetrics(),
        getAlerts({ status: 'open', limit: 20 }),
        getAlertMetrics(),
        getWorkflowLogs({ days: 7, limit: 20 }),
        getLlmAudit({ days: 7, limit: 20 }),
      ])
      setTasks(tasksData.tasks || [])
      setMetrics(metricsData.metrics || metricsData)
      setChannelMetrics(channelsData.metrics || channelsData)
      setAlerts(alertsData.alerts || [])
      setAlertMetrics(alertMetricsData.metrics || alertMetricsData)
      setWorkflowLogs(logsData.logs || [])
      setLlmAudits(auditData.audits || [])
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
      setWorkflowLogs([])
      setLlmAudits([])
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

  const handleOpenApplyModal = (task) => {
    setApplyTarget(task)
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

  const handleApplyTask = async ({ humanConfirmed }) => {
    if (!applyTarget) {
      return
    }

    try {
      setApplyLoading(true)
      const result = await applyTask(applyTarget.id, { humanConfirmed })
      setApplyTarget(null)
      const childId = result?.result?.publish_task_id
      setToast({
        message: childId
          ? `Applied. Publish task #${childId} is waiting for a separate Apply.`
          : 'Task applied',
        type: 'success',
      })
      await fetchData()
    } catch (error) {
      console.error('Error applying task:', error)
      setToast({ message: getErrorMessage(error, 'Failed to apply task'), type: 'error' })
    } finally {
      setApplyLoading(false)
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

  const handleRunPhase1Cycle = async () => {
    try {
      setRunningPhase1Cycle(true)
      const result = await runPhase1Cycle({ scheduleContentCount: 1 })
      setToast({
        message: result.status === 'partial'
          ? 'Phase 1 cycle completed with follow-up needed'
          : 'Phase 1 cycle completed — review pending tasks',
        type: result.status === 'partial' ? 'warning' : 'success',
      })
      await fetchData()
    } catch (error) {
      console.error('Error running Phase 1 cycle:', error)
      setToast({ message: getErrorMessage(error, 'Failed to run Phase 1 cycle'), type: 'error' })
    } finally {
      setRunningPhase1Cycle(false)
    }
  }

  const handlePreviewContent = async (task) => {
    try {
      setPreviewLoadingTaskId(task.id)
      const preview = await previewContentForTask(task.id)
      setContentPreview({ task, preview })
    } catch (error) {
      console.error('Error generating preview:', error)
      setToast({ message: getErrorMessage(error, 'Failed to generate preview'), type: 'error' })
    } finally {
      setPreviewLoadingTaskId(null)
    }
  }

  const handleOpenPublishModal = (task) => {
    setPublishTarget(task)
  }

  const handlePublishContent = async ({ humanConfirmed, judgeVerdict }) => {
    if (!publishTarget) {
      return
    }

    try {
      setPublishLoading(true)
      const result = await publishContentTask(publishTarget.id, {
        humanConfirmed,
        judgeVerdict,
      })
      setPublishTarget(null)
      setContentPreview(null)
      setToast({
        message: result.article_url
          ? `Published: ${result.article_url}`
          : 'Content published successfully',
        type: 'success',
      })
      await fetchData()
    } catch (error) {
      console.error('Error publishing content:', error)
      setToast({ message: getErrorMessage(error, 'Failed to publish content'), type: 'error' })
    } finally {
      setPublishLoading(false)
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
    setWorkflowLogs([])
    setLlmAudits([])
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
  const weeklyLeads = channelMetrics?.leads?.total_leads
    ?? channelMetrics?.leads?.record_count
    ?? 0
  const channelCards = channelMetrics
    ? ['gsc', 'ga4', 'google_ads', 'leads']
        .filter((key) => channelMetrics[key] && typeof channelMetrics[key] === 'object')
        .map((key) => [key, channelMetrics[key]])
    : []
  const activeChannels = channelCards.filter(([key]) => key !== 'leads').length
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
            onClick={handleRunPhase1Cycle}
            disabled={runningPhase1Cycle || !hasRequiredApiKey}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition disabled:opacity-50"
            style={{ backgroundColor: '#f97316', color: '#fff' }}
          >
            <Zap size={18} />
            {runningPhase1Cycle ? 'Running Phase 1...' : 'Run Phase 1 Cycle'}
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
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
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
        <KPICard
          title="Weekly Leads"
          value={weeklyLeads}
          color="#10b981"
          icon={<CheckCircle size={24} />}
        />
      </div>

      <AlertsPanel
        alerts={alerts}
        loading={loading}
        hasRequiredApiKey={hasRequiredApiKey}
        onAcknowledge={handleAcknowledgeAlert}
        onDismiss={handleDismissAlert}
      />

      <LogsPanel
        workflowLogs={workflowLogs}
        llmAudits={llmAudits}
        loading={loading}
        hasRequiredApiKey={hasRequiredApiKey}
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
            <option value="content">Content</option>
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
                onApply={handleOpenApplyModal}
                onDismiss={handleDismissTask}
                onDelay={handleDelayTask}
                onPreviewContent={handlePreviewContent}
                onPublishContent={handleOpenPublishModal}
                previewLoadingTaskId={previewLoadingTaskId}
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
          ) : channelCards.length > 0 ? (
            channelCards.map(([channel, data]) => (
              <div key={channel} style={{ backgroundColor: COLORS.cardBg }} className="rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-2" style={{ color: COLORS.text }}>
                  {channel === 'leads' ? 'WEEKLY LEADS' : channel.toUpperCase()}
                </h3>
                <div className="space-y-2" style={{ color: COLORS.textDim }}>
                  {channel === 'leads' ? (
                    <>
                      <p>Total: <span style={{ color: COLORS.text }}>{data.total_leads || data.record_count || 0}</span></p>
                      <p className="text-sm">form_submit: <span style={{ color: COLORS.text }}>{data.form_submit || 0}</span></p>
                      <p className="text-sm">phone_call_clicks: <span style={{ color: COLORS.text }}>{data.phone_call_clicks || 0}</span></p>
                      <p className="text-xs">{data.kpi || 'form_submit + phone_call_clicks (never page_view)'}</p>
                    </>
                  ) : (
                    <p>Records: <span style={{ color: COLORS.text }}>{data.record_count || 0}</span></p>
                  )}
                  <p className="text-sm">
                    Last metric date: <span style={{ color: COLORS.text }}>
                      {data.last_date ? new Date(data.last_date).toLocaleDateString() : 'N/A'}
                    </span>
                  </p>
                  {data.last_ingested_at && (
                    <p className="text-sm">
                      Last ingest: <span style={{ color: COLORS.text }}>
                        {new Date(data.last_ingested_at).toLocaleString()}
                      </span>
                    </p>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div style={{ color: COLORS.textDim }}>Loading channel data...</div>
          )}
        </div>
      </div>

      {/* Toast Notification */}
      {contentPreview && (
        <ContentPreviewModal
          data={contentPreview}
          onClose={() => setContentPreview(null)}
          onPublish={() => {
            setPublishTarget(contentPreview.task)
            setContentPreview(null)
          }}
        />
      )}

      {publishTarget && (
        <ContentPublishModal
          task={publishTarget}
          loading={publishLoading}
          onClose={() => setPublishTarget(null)}
          onPublish={handlePublishContent}
        />
      )}

      {applyTarget && (
        <ApplyTaskModal
          task={applyTarget}
          loading={applyLoading}
          onClose={() => setApplyTarget(null)}
          onApply={handleApplyTask}
        />
      )}

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

function LogsPanel({ workflowLogs, llmAudits, loading, hasRequiredApiKey }) {
  return (
    <div style={{ backgroundColor: COLORS.cardBg }} className="rounded-lg p-6 mb-8">
      <h2 className="text-2xl font-semibold mb-4" style={{ color: COLORS.text }}>
        Recent logs (7 days)
      </h2>
      {!hasRequiredApiKey ? (
        <div className="text-center py-6" style={{ color: COLORS.textDim }}>
          Enter the API key above to load logs.
        </div>
      ) : loading ? (
        <div className="text-center py-6" style={{ color: COLORS.textDim }}>
          Loading logs...
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h3 className="text-lg font-semibold mb-3" style={{ color: COLORS.text }}>
              WorkflowLog
            </h3>
            {workflowLogs.length === 0 ? (
              <p style={{ color: COLORS.textDim }}>No workflow rows in the last 7 days.</p>
            ) : (
              <div className="space-y-2">
                {workflowLogs.map((row) => (
                  <div key={`wf-${row.id}`} className="rounded-lg p-3" style={{ backgroundColor: COLORS.bg }}>
                    <div className="flex justify-between gap-2 text-sm">
                      <span style={{ color: COLORS.text }}>{row.workflow_name}</span>
                      <span style={{ color: COLORS.textDim }}>{row.status}</span>
                    </div>
                    {row.created_at && (
                      <p className="text-xs mt-1" style={{ color: COLORS.textDim }}>
                        {new Date(row.created_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div>
            <h3 className="text-lg font-semibold mb-3" style={{ color: COLORS.text }}>
              LLMAudit
            </h3>
            {llmAudits.length === 0 ? (
              <p style={{ color: COLORS.textDim }}>No LLM audit rows in the last 7 days.</p>
            ) : (
              <div className="space-y-2">
                {llmAudits.map((row) => (
                  <div key={`llm-${row.id}`} className="rounded-lg p-3" style={{ backgroundColor: COLORS.bg }}>
                    <div className="flex justify-between gap-2 text-sm">
                      <span style={{ color: COLORS.text }}>{row.task_type} / {row.model_role}</span>
                      <span style={{ color: COLORS.textDim }}>{row.status}{row.verdict ? ` · ${row.verdict}` : ''}</span>
                    </div>
                    <p className="text-xs mt-1" style={{ color: COLORS.textDim }}>
                      {row.provider} {row.model}
                      {row.request || row.response ? ' (bodies present)' : ''}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
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

function TaskCard({
  task,
  onApprove,
  onApply,
  onDismiss,
  onDelay,
  onPreviewContent,
  onPublishContent,
  previewLoadingTaskId,
}) {
  const leadScore = task.action_payload?.lead_score
  const leadTier = task.action_payload?.lead_tier
  const leadReasons = task.action_payload?.lead_relevance_reasons || []
  const isContent = task.task_type === 'content'
  const showApply = Boolean(task.applyable) && !isContent
  const preview = task.action_payload?.preview

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
          {task.action_kind && (
            <span className="px-2 py-1 rounded text-xs font-semibold text-white bg-slate-700">
              {task.action_kind}
            </span>
          )}
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
        {preview && (
          <p className="text-xs mb-3" style={{ color: COLORS.textDim }}>
            <span className="font-semibold">Frozen apply:</span>{' '}
            {Object.entries(preview)
              .map(([key, value]) => `${key}=${value}`)
              .join(' · ')}
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
          {showApply ? (
            <button
              onClick={() => onApply(task)}
              className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80"
              style={{ backgroundColor: '#f97316' }}
            >
              Apply
            </button>
          ) : (
            <button
              onClick={() => onApprove(task.id)}
              className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80"
              style={{ backgroundColor: '#10b981' }}
            >
              Approve
            </button>
          )}
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
      {showApply && task.status === 'approved' && (
        <div className="flex gap-2">
          <button
            onClick={() => onApply(task)}
            className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80"
            style={{ backgroundColor: '#f97316' }}
          >
            Apply
          </button>
        </div>
      )}
      {isContent && task.status === 'approved' && (
        <div className="flex gap-2">
          <button
            onClick={() => onPreviewContent(task)}
            disabled={previewLoadingTaskId === task.id}
            className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80 disabled:opacity-50"
            style={{ backgroundColor: '#3b82f6' }}
          >
            {previewLoadingTaskId === task.id ? 'Generating...' : 'Preview Draft'}
          </button>
          <button
            onClick={() => onPublishContent(task)}
            className="px-4 py-2 rounded-lg text-white font-semibold transition hover:opacity-80"
            style={{ backgroundColor: '#f97316' }}
          >
            Publish
          </button>
        </div>
      )}
    </div>
  )
}

function ContentPreviewModal({ data, onClose, onPublish }) {
  const { task, preview } = data

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div
        className="max-w-4xl w-full max-h-[90vh] overflow-y-auto rounded-lg p-6"
        style={{ backgroundColor: COLORS.cardBg, color: COLORS.text }}
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h3 className="text-2xl font-bold">{preview.title}</h3>
            <p className="text-sm mt-2" style={{ color: COLORS.textDim }}>
              Task #{task.id} · {preview.word_count} words · /{preview.handle}
            </p>
          </div>
          <button onClick={onClose} className="text-sm px-3 py-1 rounded" style={{ backgroundColor: '#666' }}>
            Close
          </button>
        </div>
        <p className="text-sm mb-4" style={{ color: COLORS.textDim }}>
          {preview.meta_description}
        </p>
        <div
          className="prose prose-invert max-w-none text-sm mb-6"
          dangerouslySetInnerHTML={{ __html: preview.body_html }}
        />
        <div className="flex gap-3">
          <button
            onClick={onPublish}
            className="px-4 py-2 rounded-lg text-white font-semibold"
            style={{ backgroundColor: '#f97316' }}
          >
            Continue to Publish
          </button>
          <button onClick={onClose} className="px-4 py-2 rounded-lg" style={{ backgroundColor: '#666', color: '#fff' }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

function ContentPublishModal({ task, loading, onClose, onPublish }) {
  const [humanConfirmed, setHumanConfirmed] = useState(false)
  const [judgeVerdict, setJudgeVerdict] = useState('PASS')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div
        className="max-w-lg w-full rounded-lg p-6"
        style={{ backgroundColor: COLORS.cardBg, color: COLORS.text }}
      >
        <h3 className="text-xl font-bold mb-2">Publish Content Task</h3>
        <p className="text-sm mb-4" style={{ color: COLORS.textDim }}>
          {task.title}
        </p>
        <p className="text-sm mb-4" style={{ color: COLORS.textDim }}>
          Publishing requires explicit human confirmation and an independent judge verdict of PASS.
        </p>
        <label className="flex items-center gap-2 mb-3 text-sm">
          <input
            type="checkbox"
            checked={humanConfirmed}
            onChange={(event) => setHumanConfirmed(event.target.checked)}
          />
          I have reviewed the draft and approve publishing to Shopify.
        </label>
        <label className="block text-sm mb-2" style={{ color: COLORS.textDim }}>
          Judge verdict
        </label>
        <select
          value={judgeVerdict}
          onChange={(event) => setJudgeVerdict(event.target.value)}
          className="w-full px-3 py-2 rounded-lg mb-6"
          style={{ backgroundColor: COLORS.bg, color: COLORS.text, border: '1px solid #333' }}
        >
          <option value="PASS">PASS</option>
          <option value="FAIL">FAIL</option>
        </select>
        <div className="flex gap-3">
          <button
            onClick={() => onPublish({ humanConfirmed, judgeVerdict })}
            disabled={!humanConfirmed || judgeVerdict !== 'PASS' || loading}
            className="px-4 py-2 rounded-lg text-white font-semibold disabled:opacity-50"
            style={{ backgroundColor: '#f97316' }}
          >
            {loading ? 'Publishing...' : 'Publish to Shopify'}
          </button>
          <button onClick={onClose} className="px-4 py-2 rounded-lg" style={{ backgroundColor: '#666', color: '#fff' }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

function ApplyTaskModal({ task, loading, onClose, onApply }) {
  const [humanConfirmed, setHumanConfirmed] = useState(false)
  const preview = task.action_payload?.preview || {}
  const previewRows = Object.entries(preview)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div
        className="max-w-lg w-full rounded-lg p-6"
        style={{ backgroundColor: COLORS.cardBg, color: COLORS.text }}
      >
        <h3 className="text-xl font-bold mb-2">Apply frozen task</h3>
        <p className="text-sm mb-2" style={{ color: COLORS.textDim }}>
          {task.title}
        </p>
        <p className="text-xs mb-4" style={{ color: COLORS.textDim }}>
          Kind: {task.action_kind}. This uses the payload stored on the task.
          n8n must never call Apply. GTM publish is a separate task after ensure.
        </p>
        {previewRows.length > 0 && (
          <div className="mb-4 text-sm" style={{ color: COLORS.textDim }}>
            {previewRows.map(([key, value]) => (
              <p key={key}>
                <span className="font-semibold">{key}:</span> {String(value)}
              </p>
            ))}
          </div>
        )}
        {task.finding && (
          <p className="text-sm mb-4" style={{ color: COLORS.textDim }}>
            {task.finding}
          </p>
        )}
        <label className="flex items-center gap-2 mb-6 text-sm">
          <input
            type="checkbox"
            checked={humanConfirmed}
            onChange={(event) => setHumanConfirmed(event.target.checked)}
          />
          I reviewed this frozen change and confirm Apply.
        </label>
        <div className="flex gap-3">
          <button
            onClick={() => onApply({ humanConfirmed })}
            disabled={!humanConfirmed || loading}
            className="px-4 py-2 rounded-lg text-white font-semibold disabled:opacity-50"
            style={{ backgroundColor: '#f97316' }}
          >
            {loading ? 'Applying...' : 'Apply'}
          </button>
          <button onClick={onClose} className="px-4 py-2 rounded-lg" style={{ backgroundColor: '#666', color: '#fff' }}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
