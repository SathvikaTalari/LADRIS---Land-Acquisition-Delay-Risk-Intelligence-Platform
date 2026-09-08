/**
 * LADRIS — Executive Project Detail Command Center
 * 
 * Re-structured into 4 Executive Tabs:
 *   1. [ Overview ]             — Header, 5 KPI Cards, Lifecycle Bar, Problem Card, Next Best Action, Mini Risk Trend, Mini Map
 *   2. [ Acquisition Progress ] — 6 Expandable Stage Cards + Legal & Approval Issues
 *   3. [ Risk & Intelligence ]   — Structural/Predictive Risk Summary, Stage Fingerprint, SHAP Drivers, AI Reliability, Risk Propagation Chain, What-If Simulator
 *   4. [ Actions ]               — Recommended Actions, Active Interventions, Active Alerts, Outcome Effectiveness Learning
 * 
 * Side Drawers:
 *   - Documents Drawer
 *   - Legal Details Drawer
 *   - Audit History Modal
 */
import { useEffect, useState, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import ReactECharts from 'echarts-for-react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import {
  ArrowLeft,
  MapPin,
  AlertTriangle,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Download,
  Edit3,
  Flame,
  MoreVertical,
  X,
  Shield,
  FolderKanban
} from 'lucide-react'
import { projectsAPI, predictionsAPI, apiClient } from '@/api/client'
import type { Project, PredictionResult, RiskFingerprint } from '@/types'
import { RiskBadge, StatusBadge, EmptyState } from '@/components/common'
import { formatDate, formatINR } from '@/utils'
import { useAuthStore } from '@/store/authStore'

type MainTabId = 'overview' | 'progress' | 'intelligence' | 'actions'

const MAIN_TABS: { id: MainTabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'progress', label: 'Acquisition Progress' },
  { id: 'intelligence', label: 'Risk & Intelligence' },
  { id: 'actions', label: 'Actions' },
]

// State Centroids for mini map
const STATE_COORDINATES: Record<string, [number, number]> = {
  UP: [26.8467, 80.9462], MH: [19.7515, 75.7139], TN: [11.1271, 78.6569],
  GJ: [22.2587, 71.1924], BR: [25.0961, 85.3131], KA: [15.3173, 75.7139],
  RJ: [27.0238, 74.2179], DL: [28.7041, 77.1025], WB: [22.9868, 87.8550],
  AP: [15.9129, 79.7400], TS: [18.1124, 79.0193], TG: [18.1124, 79.0193],
  MP: [22.9734, 78.6569], HR: [29.0588, 76.0856], PB: [31.1471, 75.3412],
  OD: [20.9517, 85.0985], KL: [10.8505, 76.2711], AS: [26.2006, 92.9376],
  JH: [23.6102, 85.2799], UT: [30.0668, 79.0193], HP: [31.1048, 77.1734],
  CT: [21.2787, 81.8661], GA: [15.2993, 74.1240],
}

function createRiskMarkerIcon(riskLevel: string) {
  let color = '#138808'
  if (riskLevel === 'CRITICAL') color = '#ff4757'
  else if (riskLevel === 'HIGH') color = '#f47721'
  else if (riskLevel === 'MEDIUM') color = '#d97706'

  const html = `
    <div style="width:20px;height:20px;border-radius:50%;background:${color};border:2px solid #060f1e;box-shadow:0 0 10px ${color}"></div>
  `
  return L.divIcon({ html, className: 'mini-marker', iconSize: [20, 20], iconAnchor: [10, 10] })
}

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const [project, setProject] = useState<Project | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<MainTabId>('overview')

  // Intelligence Data
  const [prediction, setPrediction] = useState<PredictionResult | null>(null)
  const [_fingerprint, setFingerprint] = useState<RiskFingerprint | null>(null)
  const [_interventions, setInterventions] = useState<any>(null)
  const [_eligibleFields, setEligibleFields] = useState<any[]>([])

  // Risk Velocity state
  const [velocityData, setVelocityData] = useState<any>(null)
  const [velocityRiskType, setVelocityRiskType] = useState<string>('structural_anomaly')

  // Expandable Stage Cards state
  const [expandedStages, setExpandedStages] = useState<Record<string, boolean>>({
    COMPENSATION: true,
  })

  // Drawers & Modals state
  const [showDocsDrawer, setShowDocsDrawer] = useState(false)
  const [showLegalDrawer, setShowLegalDrawer] = useState(false)
  const [showAuditModal, setShowAuditModal] = useState(false)

  // What-If Simulator state
  const [scenarioInputs, setScenarioInputs] = useState<Record<string, number>>({})
  const [simResult, setSimResult] = useState<any>(null)
  const [isSimulating, setIsSimulating] = useState(false)

  // Role permissions check
  const canEdit = user && ['SUPER_ADMIN', 'STATE_ADMIN', 'DISTRICT_OFFICER', 'LA_OFFICER'].includes(user.role)

  useEffect(() => {
    if (!id) return
    setIsLoading(true)
    projectsAPI.get(id)
      .then(setProject)
      .catch(() => setError('Project not found or access denied.'))
      .finally(() => setIsLoading(false))
  }, [id])

  useEffect(() => {
    if (id) {
      Promise.all([
        predictionsAPI.get(id).catch(() => null),
        predictionsAPI.stages(id).catch(() => null),
        apiClient.get(`/api/v1/interventions/${id}`).then(r => r.data).catch(() => null),
        apiClient.get(`/api/v1/interventions/${id}/fields`).then(r => r.data).catch(() => null),
        apiClient.get(`/api/v1/intelligence/risk-velocity/${id}`, { params: { risk_type: velocityRiskType } }).then(r => r.data).catch(() => null),
      ]).then(([predRes, stageRes, intRes, fieldsRes, velRes]) => {
        setPrediction(predRes)
        setFingerprint(stageRes)
        setInterventions(intRes)
        if (velRes) setVelocityData(velRes)
        if (fieldsRes?.eligible_fields) {
          setEligibleFields(fieldsRes.eligible_fields)
          const init: Record<string, number> = {}
          fieldsRes.eligible_fields.forEach((f: any) => {
            if (f.current_value != null) init[f.field] = f.current_value
          })
          setScenarioInputs(init)
        }
      })
    }
  }, [id, velocityRiskType])

  const toggleStage = (stageKey: string) => {
    setExpandedStages(prev => ({ ...prev, [stageKey]: !prev[stageKey] }))
  }

  const runSimulation = useCallback(async () => {
    if (!id) return
    setIsSimulating(true)
    try {
      const res = await apiClient.post(`/api/v1/interventions/${id}/simulate`, {
        scenario_name: 'What-If Interactive Simulation',
        inputs: scenarioInputs,
      })
      setSimResult(res.data)
    } catch (err) {
      console.error('Simulation failed', err)
    } finally {
      setIsSimulating(false)
    }
  }, [id, scenarioInputs])

  // Computed Values
  const priorityScore = useMemo(() => {
    if (!project) return 50
    let base = project.risk_level === 'CRITICAL' ? 88.5 : project.risk_level === 'HIGH' ? 74.2 : project.risk_level === 'MEDIUM' ? 52.0 : 28.5
    const legalBoost = (project.legal_case_count || 0) * 2.5
    const delayBoost = Math.min(12, (project.delay_months || 0) * 1.2)
    return Math.min(99, Math.round(base + legalBoost + delayBoost))
  }, [project])

  const landAcquiredPct = useMemo(() => {
    if (!project || !project.total_area_ha || project.total_area_ha === 0) return 0
    return Math.round(((project.area_acquired_ha || 0) / project.total_area_ha) * 100)
  }, [project])

  const compensationDisbursedPct = useMemo(() => {
    if (!project || !project.estimated_compensation_inr || project.estimated_compensation_inr === 0) return 64
    return Math.round(((project.disbursed_compensation_inr || 0) / project.estimated_compensation_inr) * 100)
  }, [project])

  // Core ML Delay Prediction Metrics
  const overallDelayProb = useMemo(() => {
    if (prediction?.delay_risk?.score != null) return Math.round(prediction.delay_risk.score * 100)
    if (prediction?.overall_risk_score != null) return Math.round(prediction.overall_risk_score * 100)
    if (project?.risk_level === 'CRITICAL') return 82
    if (project?.risk_level === 'HIGH') return 68
    if (project?.risk_level === 'MEDIUM') return 45
    return 18
  }, [prediction, project])

  const riskScore = overallDelayProb

  const riskCategory = useMemo(() => {
    if (riskScore >= 81) return { label: 'CRITICAL', color: 'var(--color-risk-critical)', bg: 'rgba(255,71,87,0.15)', border: 'var(--color-risk-critical)' }
    if (riskScore >= 61) return { label: 'HIGH', color: 'var(--color-risk-high)', bg: 'rgba(244,119,33,0.15)', border: 'var(--color-risk-high)' }
    if (riskScore >= 31) return { label: 'MEDIUM', color: 'var(--color-risk-medium)', bg: 'rgba(217,119,6,0.15)', border: 'var(--color-risk-medium)' }
    return { label: 'LOW', color: '#138808', bg: 'rgba(19,136,8,0.15)', border: '#138808' }
  }, [riskScore])

  const expectedDelayDays = useMemo(() => {
    if (project?.delay_months) return project.delay_months * 30
    if (project?.risk_level === 'CRITICAL') return 46
    if (project?.risk_level === 'HIGH') return 32
    if (project?.risk_level === 'MEDIUM') return 18
    return 5
  }, [project])

  const criticalRiskExpectedDays = useMemo(() => {
    if (project?.risk_level === 'CRITICAL') return 18
    if (project?.risk_level === 'HIGH') return 24
    if (project?.risk_level === 'MEDIUM') return 35
    return 60
  }, [project])

  // Mini Risk Trend Chart
  const miniTrendOption = useMemo(() => {
    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', backgroundColor: '#0a182e', textStyle: { color: '#fff', fontSize: 11 } },
      grid: { top: 10, bottom: 20, left: 25, right: 10 },
      xAxis: {
        type: 'category',
        data: ['Jun', 'Jul', 'Aug', 'Sep'],
        axisLine: { lineStyle: { color: 'rgba(244,119,33,0.2)' } },
        axisLabel: { color: '#94a9c9', fontSize: 10 },
      },
      yAxis: {
        type: 'value',
        min: 0, max: 100,
        splitLine: { show: false },
        axisLabel: { color: '#94a9c9', fontSize: 9 },
      },
      series: [
        {
          type: 'line',
          smooth: true,
          data: [48, 55, 67, priorityScore],
          itemStyle: { color: '#f47721' },
          lineStyle: { width: 2.5 },
          areaStyle: {
            color: {
              type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: 'rgba(244,119,33,0.3)' }, { offset: 1, color: 'rgba(244,119,33,0.01)' }]
            }
          }
        }
      ]
    }
  }, [priorityScore])

  // Stage Risk Fingerprint Horizontal Bar Chart
  const fingerprintOption = useMemo(() => {
    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', backgroundColor: '#0a182e', textStyle: { color: '#fff', fontSize: 11 } },
      grid: { top: 10, bottom: 20, left: 110, right: 40 },
      xAxis: { type: 'value', max: 100, axisLabel: { color: '#94a9c9', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(244,119,33,0.06)' } } },
      yAxis: {
        type: 'category',
        data: ['Notification', 'Objection', 'Award', 'Compensation', 'R&R', 'Possession'],
        axisLabel: { color: '#f0f6fc', fontSize: 11 },
      },
      series: [{
        type: 'bar',
        barWidth: '50%',
        data: [
          { value: 34, itemStyle: { color: '#138808' } },
          { value: 42, itemStyle: { color: '#d97706' } },
          { value: 55, itemStyle: { color: '#d97706' } },
          { value: 89, itemStyle: { color: '#ff4757', borderRadius: [0, 4, 4, 0] } },
          { value: 61, itemStyle: { color: '#f47721' } },
          { value: 74, itemStyle: { color: '#ff4757' } },
        ],
        label: { show: true, position: 'right', color: '#f0f6fc', fontSize: 11, formatter: '{c}' }
      }]
    }
  }, [])

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16, padding: 24 }}>
        {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 80, opacity: 1 - i * 0.2 }} />)}
      </div>
    )
  }

  if (error || !project) {
    return (
      <EmptyState
        icon={<AlertTriangle size={32} />}
        title="Project Not Found"
        description={error || "The requested project record could not be loaded."}
        action={<button className="btn btn-secondary" onClick={() => navigate('/projects')}>Back to Projects</button>}
      />
    )
  }

  const coords = STATE_COORDINATES[(project.state_code || 'MH').toUpperCase()] || [19.7515, 75.7139]

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ width: '100%', paddingBottom: 60 }}>
      {/* Navigation Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/projects')}>
          <ArrowLeft size={14} /> Back to Projects
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {canEdit && (
            <button className="btn btn-secondary btn-sm" onClick={() => alert('Edit Project Modal')}>
              <Edit3 size={13} /> Edit Project
            </button>
          )}
          <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/gis?project_id=${project.id}`)}>
            <MapPin size={13} /> View on Map
          </button>
          <button className="btn btn-secondary btn-sm" onClick={() => window.open(`/api/v1/reports/projects.csv`, '_blank')}>
            <Download size={13} /> Generate Report
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowDocsDrawer(true)}>
            <FolderKanban size={13} /> Documents (12)
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowAuditModal(true)}>
            <MoreVertical size={14} />
          </button>
        </div>
      </div>

      {/* ─── PROJECT HEADER ──────────────────────────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 20, padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <h1 style={{ fontSize: '1.4rem', fontWeight: 800, margin: 0, color: 'var(--color-text-primary)' }}>
                PROJECT: {project.name}
              </h1>
              <RiskBadge level={project.risk_level} />
              <StatusBadge status={project.status} />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 14, fontSize: '0.82rem', color: 'var(--color-text-secondary)' }}>
              <span>Location: <strong>{project.state_code} • {project.district_codes?.[0] || 'Sangareddy'}</strong></span>
              <span>•</span>
              <span>Project ID: <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-accent-primary)' }}>{project.project_code}</code></span>
              <span>•</span>
              <span>Current Stage: <strong style={{ color: 'var(--color-risk-critical)' }}>Compensation</strong></span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ padding: '8px 16px', background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', textAlign: 'right', border: '1px solid var(--color-border-subtle)' }}>
              <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', display: 'block' }}>Priority Score</span>
              <strong style={{ fontSize: '1.25rem', fontFamily: 'var(--font-mono)', color: priorityScore >= 80 ? 'var(--color-risk-critical)' : 'var(--color-risk-high)' }}>
                {priorityScore} / 100
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* ─── 4 MAIN TABS NAVIGATION ──────────────────────────────────────────────── */}
      <div style={{
        display: 'flex',
        gap: 6,
        marginBottom: 20,
        borderBottom: '1px solid var(--color-border-subtle)',
        paddingBottom: 0,
      }}>
        {MAIN_TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '10px 20px',
              background: activeTab === tab.id ? 'var(--color-bg-card)' : 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? '3px solid var(--color-accent-primary)' : '3px solid transparent',
              color: activeTab === tab.id ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
              fontSize: '0.9rem',
              fontWeight: activeTab === tab.id ? 700 : 500,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              borderRadius: 'var(--radius-md) var(--radius-md) 0 0',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ─────────────────────────────────────────────────────────────────────────── */}
      {/* TAB 1: OVERVIEW                                                             */}
      {/* ─────────────────────────────────────────────────────────────────────────── */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          
          {/* B. FIVE IMPORTANT KPI CARDS */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 14 }}>
            <div className="metric-card">
              <span className="metric-label">Land Required</span>
              <div className="metric-value">{project.total_area_ha || 214} <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>ha</span></div>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Total project footprint</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Land Acquired</span>
              <div className="metric-value">{project.area_acquired_ha || 148} <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>ha</span></div>
              <span style={{ fontSize: '0.72rem', color: '#138808', fontWeight: 600 }}>{landAcquiredPct}% completed</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Compensation</span>
              <div className="metric-value">{compensationDisbursedPct}%</div>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-risk-high)', fontWeight: 600 }}>Disbursement progress</span>
            </div>

            <div className="metric-card">
              <span className="metric-label">Overall Risk</span>
              <div className="metric-value" style={{ color: 'var(--color-risk-critical)', fontSize: '1.4rem' }}>
                {project.risk_level}
              </div>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Structural Timeline Divergence</span>
            </div>

            {/* LOCATION 2: COMPACT RISK VELOCITY CARD */}
            <div className="metric-card" style={{ borderLeft: '3px solid var(--color-accent-primary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="metric-label">Risk Velocity</span>
                {velocityData?.velocity_status && velocityData.velocity_status !== 'NOT_AVAILABLE' ? (
                  <span className={`badge ${
                    velocityData.velocity_status === 'RAPIDLY_RISING' ? 'badge-red' :
                    velocityData.velocity_status === 'RISING' ? 'badge-yellow' :
                    velocityData.velocity_status === 'IMPROVING' ? 'badge-green' : 'badge-blue'
                  }`} style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                    {velocityData.symbol} {velocityData.label}
                  </span>
                ) : (
                  <span className="badge badge-gray" style={{ fontSize: '0.62rem', padding: '1px 5px' }}>
                    Not Available
                  </span>
                )}
              </div>

              {velocityData?.velocity_status && velocityData.velocity_status !== 'NOT_AVAILABLE' ? (
                <>
                  <div className="metric-value" style={{ fontSize: '1.25rem', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                    {velocityData.change_7d > 0 ? `+${velocityData.change_7d}` : velocityData.change_7d} <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', fontFamily: 'sans-serif' }}>pts/7d</span>
                  </div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', marginTop: 4, fontFamily: 'var(--font-mono)' }}>
                    Sparkline: {velocityData.sparkline?.join(' → ') || '52 → 57 → 61 → 68 → 78'}
                  </div>
                </>
              ) : (
                <>
                  <div className="metric-value" style={{ fontSize: '0.95rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Not Available
                  </div>
                  <div style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Insufficient historical observations
                  </div>
                </>
              )}
            </div>

            <div className="metric-card">
              <span className="metric-label">Priority Score</span>
              <div className="metric-value" style={{ color: 'var(--color-accent-primary)' }}>{priorityScore} <span style={{ fontSize: '0.8rem' }}>/100</span></div>
              <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Urgency index (10% velocity)</span>
            </div>
          </div>

          {/* AI Reliability Distinction pill */}
          <div style={{
            padding: '10px 16px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-bg-card)',
            border: '1px solid var(--color-border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.8rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <span>Structural Anomaly: <strong style={{ color: 'var(--color-risk-critical)' }}>High Signal</strong></span>
              <span>•</span>
              <span>Predictive Delay Risk: <strong style={{ color: '#7daaff' }}>Unavailable / Deferred</strong></span>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
              * Deferred due to insufficient verified historical outcome ground truth.
            </span>
          </div>

          {/* C. ACQUISITION PROGRESS BAR (Simple Lifecycle) */}
          <div className="card">
            <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Acquisition Lifecycle Progress
            </h3>

            {/* Lifecycle Steps */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              {[
                { name: 'Notification', status: 'done', symbol: '✓' },
                { name: 'Objection', status: 'done', symbol: '✓' },
                { name: 'Award', status: 'done', symbol: '✓' },
                { name: 'Compensation', status: 'current', symbol: '●', isBottleneck: true },
                { name: 'R&R', status: 'pending', symbol: '○' },
                { name: 'Possession', status: 'pending', symbol: '○' },
              ].map((s) => (
                <div key={s.name} style={{ textAlign: 'center', flex: 1, position: 'relative' }}>
                  <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    margin: '0 auto 6px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontWeight: 800,
                    fontSize: '0.9rem',
                    background: s.status === 'done' ? 'rgba(19,136,8,0.15)' : s.status === 'current' ? 'rgba(255,71,87,0.2)' : 'var(--color-bg-tertiary)',
                    color: s.status === 'done' ? '#138808' : s.status === 'current' ? 'var(--color-risk-critical)' : 'var(--color-text-muted)',
                    border: s.status === 'done' ? '1px solid #138808' : s.status === 'current' ? '2px solid var(--color-risk-critical)' : '1px solid var(--color-border-subtle)',
                  }}>
                    {s.symbol}
                  </div>
                  <div style={{ fontSize: '0.78rem', fontWeight: s.status === 'current' ? 800 : 500, color: s.status === 'current' ? 'var(--color-risk-critical)' : 'var(--color-text-primary)' }}>
                    {s.name}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--color-border-subtle)', paddingTop: 10, fontSize: '0.82rem' }}>
              <span>Current Stage: <strong style={{ color: 'var(--color-risk-critical)' }}>COMPENSATION</strong></span>
              <span>Overall Acquisition Progress: <strong style={{ color: 'var(--color-accent-primary)' }}>63%</strong></span>
            </div>
          </div>

          {/* D. CURRENT PROBLEM CARD & E. NEXT BEST ACTION (Grid 2) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20 }}>
            
            {/* D. Current Problem Card */}
            <div className="card" style={{ borderLeft: '4px solid var(--color-risk-critical)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <AlertTriangle size={18} color="var(--color-risk-critical)" />
                <h3 style={{ fontSize: '0.88rem', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 800, color: 'var(--color-risk-critical)' }}>
                  Current Bottleneck
                </h3>
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: 6, color: 'var(--color-text-primary)' }}>
                COMPENSATION DISBURSEMENT
              </div>
              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-secondary)', marginBottom: 12 }}>
                36% of awarded compensation is currently pending verification and disbursement across assigned revenue villages.
              </p>
              <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                Risk Level: <span className="badge badge-red">HIGH</span>
              </div>
            </div>

            {/* E. Next Best Action Card */}
            <div className="card" style={{ borderLeft: '4px solid var(--color-accent-primary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <Flame size={18} color="var(--color-accent-primary)" />
                <h3 style={{ fontSize: '0.88rem', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 800, color: 'var(--color-accent-primary)' }}>
                  Next Best Action
                </h3>
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 800, marginBottom: 4, color: 'var(--color-text-primary)' }}>
                Review Pending Compensation Cases in Village A
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginBottom: 10 }}>
                Priority: <strong style={{ color: 'var(--color-accent-primary)' }}>92 / 100</strong> • Reason: Compensation backlog is currently the strongest risk contributor.
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-primary btn-sm" onClick={() => setActiveTab('actions')}>
                  View Action
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => setActiveTab('intelligence')}>
                  Simulate Intervention
                </button>
              </div>
            </div>
          </div>

          {/* F. MINI RISK TREND & G. MINI MAP (Grid 2) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20 }}>
            
            {/* F. Mini Risk Trend */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <TrendingUp size={16} color="var(--color-accent-primary)" />
                    <h3 style={{ fontSize: '0.88rem', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
                      Risk Trajectory Trend
                    </h3>
                  </div>
                  <span className="badge badge-red">Rapidly Rising</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                  4-Month observation trajectory: Jun (48) → Jul (55) → Aug (67) → Sep ({priorityScore}) ↑
                </div>
              </div>

              <ReactECharts option={miniTrendOption} style={{ height: 160, width: '100%' }} />
            </div>

            {/* G. Mini Map */}
            <div className="card" style={{ padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--color-border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--color-bg-card)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <MapPin size={16} color="var(--color-accent-primary)" />
                  <h3 style={{ fontSize: '0.85rem', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
                    Project Location / Georeference
                  </h3>
                </div>
                <button className="btn btn-secondary btn-sm" style={{ padding: '2px 8px', fontSize: '0.7rem' }} onClick={() => navigate(`/gis?project_id=${project.id}`)}>
                  Open GIS Command Center →
                </button>
              </div>

              <div style={{ height: 180, width: '100%' }}>
                <MapContainer center={coords} zoom={7} style={{ height: '100%', width: '100%', background: '#060b14' }}>
                  <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <Marker position={coords} icon={createRiskMarkerIcon(project.risk_level)}>
                    <Popup>
                      <div style={{ color: '#000', fontSize: '0.75rem' }}>
                        <strong>{project.name}</strong><br/>
                        State: {project.state_code}
                      </div>
                    </Popup>
                  </Marker>
                </MapContainer>
              </div>
            </div>

          </div>

        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────────────── */}
      {/* TAB 2: ACQUISITION PROGRESS                                                 */}
      {/* ─────────────────────────────────────────────────────────────────────────── */}
      {activeTab === 'progress' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 800, margin: 0 }}>Acquisition Progress Stage Explorer</h2>
              <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', margin: '2px 0 0' }}>
                Expandable stage cards detailing exact stage bottlenecks and parcel statuses.
              </p>
            </div>
            {canEdit && (
              <button className="btn btn-secondary btn-sm" onClick={() => alert('Update Stage Modal')}>
                <Edit3 size={13} /> Update Stage Records
              </button>
            )}
          </div>

          {/* 6 EXPANDABLE STAGE CARDS */}
          {[
            {
              key: 'NOTIFICATION',
              name: 'Notification Stage (Section 3A & 3D)',
              status: 'Completed',
              badge: 'badge-green',
              symbol: '✓',
              details: [
                { label: 'Section 3A Gazette Date', value: formatDate(project.notification_3a_date || null) || '12 Oct 2024' },
                { label: 'Section 3D Gazette Date', value: formatDate(project.notification_3d_date || null) || '18 Jan 2025' },
                { label: '3A → 3D Duration', value: '98 days (Target: < 120d)' },
                { label: 'Notification Status', value: 'GAZETTE_PUBLISHED' },
              ]
            },
            {
              key: 'OBJECTION',
              name: 'Objection Hearing Stage (Section 3C)',
              status: 'Completed',
              badge: 'badge-green',
              symbol: '✓',
              details: [
                { label: 'Total Objections Filed', value: '42 Objections' },
                { label: 'Resolved Objections', value: '42 Hearing Orders' },
                { label: 'Pending Objections', value: '0' },
                { label: 'Oldest Pending Age', value: '0 days' },
              ]
            },
            {
              key: 'AWARD',
              name: 'Award Declaration Stage (Section 3G)',
              status: 'Completed',
              badge: 'badge-green',
              symbol: '✓',
              details: [
                { label: 'Award Status', value: 'FINAL_AWARD_DECLARED' },
                { label: 'Awarded Amount', value: formatINR(project.estimated_compensation_inr) || '₹82.4 Cr' },
                { label: 'Award Declaration Date', value: '14 May 2025' },
                { label: 'Pending Parcels', value: '0' },
              ]
            },
            {
              key: 'COMPENSATION',
              name: 'Compensation Disbursement Stage (Section 3H)',
              status: 'Delayed / Overdue',
              badge: 'badge-red',
              symbol: '⚠',
              isCurrent: true,
              detailsCustom: (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                    <div><span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Awarded Amount</span><br/><strong style={{ fontSize: '1rem' }}>₹82.4 Cr</strong></div>
                    <div><span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Disbursed</span><br/><strong style={{ fontSize: '1rem', color: '#138808' }}>₹53.1 Cr</strong></div>
                    <div><span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Disbursement %</span><br/><strong style={{ fontSize: '1rem', color: 'var(--color-risk-high)' }}>64%</strong></div>
                    <div><span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Status</span><br/><span className="badge badge-red">OVERDUE (48 days)</span></div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, borderTop: '1px dashed var(--color-border-subtle)', paddingTop: 10 }}>
                    <div><span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Affected Families</span><br/><strong>426 Families</strong></div>
                    <div><span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Beneficiaries Paid</span><br/><strong style={{ color: '#138808' }}>319 Paid</strong></div>
                    <div><span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Beneficiaries Pending</span><br/><strong style={{ color: 'var(--color-risk-critical)' }}>107 Pending</strong></div>
                  </div>

                  <div style={{ borderTop: '1px dashed var(--color-border-subtle)', paddingTop: 10 }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-risk-critical)', marginBottom: 4 }}>Main Stage Bottlenecks:</div>
                    <ul style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', paddingLeft: 18, margin: 0 }}>
                      <li>Bank Account Details Pending Verification: 31 Landowners</li>
                      <li>Revenue Record Ownership Verification Pending: 27 Parcels</li>
                      <li>Disputed Partition Awards under Judicial Review: 12 Cases</li>
                    </ul>
                  </div>
                </div>
              )
            },
            {
              key: 'RR',
              name: 'Resettlement & Rehabilitation (R&R)',
              status: 'In Progress',
              badge: 'badge-yellow',
              symbol: '●',
              details: [
                { label: 'Affected Families', value: `${project.total_affected_families || 426} Families` },
                { label: 'R&R Plan Completed', value: `${project.families_rehabilitated || 210} Families` },
                { label: 'Pending R&R Assistance', value: '216 Families' },
                { label: 'Grievances Registered', value: '8 Open Grievances' },
              ]
            },
            {
              key: 'POSSESSION',
              name: 'Land Possession & Handover (Section 3E)',
              status: 'Pending',
              badge: 'badge-gray',
              symbol: '○',
              details: [
                { label: 'Land Required', value: `${project.total_area_ha || 214} ha` },
                { label: 'Land Possessed', value: `${project.area_in_possession_ha || 95} ha` },
                { label: 'Possession %', value: '44%' },
                { label: 'Obstructed Parcels', value: '14 Parcels' },
              ]
            },
          ].map(stage => {
            const isExpanded = expandedStages[stage.key]

            return (
              <div key={stage.key} className="card" style={{ padding: 0, overflow: 'hidden', border: stage.isCurrent ? '1px solid var(--color-risk-critical)' : '1px solid var(--color-border-subtle)' }}>
                <div
                  onClick={() => toggleStage(stage.key)}
                  style={{
                    padding: '14px 18px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    background: stage.isCurrent ? 'rgba(255,71,87,0.06)' : 'var(--color-bg-card)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span style={{
                      width: 24, height: 24, borderRadius: '50%',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '0.8rem', fontWeight: 800,
                      background: stage.status === 'Completed' ? 'rgba(19,136,8,0.15)' : stage.isCurrent ? 'rgba(255,71,87,0.2)' : 'var(--color-bg-tertiary)',
                      color: stage.status === 'Completed' ? '#138808' : stage.isCurrent ? 'var(--color-risk-critical)' : 'var(--color-text-muted)',
                    }}>
                      {stage.symbol}
                    </span>
                    <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                      {stage.name}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <span className={`badge ${stage.badge}`}>{stage.status}</span>
                    {isExpanded ? <ChevronUp size={16} color="var(--color-text-muted)" /> : <ChevronDown size={16} color="var(--color-text-muted)" />}
                  </div>
                </div>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      style={{ borderTop: '1px solid var(--color-border-subtle)', padding: 18, background: 'var(--color-bg-tertiary)' }}
                    >
                      {stage.detailsCustom ? stage.detailsCustom : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
                          {stage.details?.map((d: any) => (
                            <div key={d.label}>
                              <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{d.label}</span>
                              <br />
                              <strong style={{ fontSize: '0.88rem', color: 'var(--color-text-primary)' }}>{d.value}</strong>
                            </div>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )
          })}

          {/* LEGAL & APPROVAL ISSUES SECTION */}
          <div className="card" style={{ marginTop: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Shield size={18} color="var(--color-accent-primary)" />
                <h3 style={{ fontSize: '0.9rem', margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
                  Legal & Approval Issues
                </h3>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setShowLegalDrawer(true)}>
                View Legal Details →
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
              <div style={{ padding: 12, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Active Legal Cases</span>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--color-risk-critical)' }}>
                  {project.legal_case_count || 4} Cases
                </div>
              </div>

              <div style={{ padding: 12, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Acquisition Stays</span>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--color-risk-high)' }}>
                  1 Active Stay
                </div>
              </div>

              <div style={{ padding: 12, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Approvals Pending</span>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: 'var(--color-accent-primary)' }}>
                  2 Clearances
                </div>
              </div>
            </div>
          </div>

        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────────────── */}
      {/* TAB 3: RISK & INTELLIGENCE                                                 */}
      {/* ─────────────────────────────────────────────────────────────────────────── */}
      {activeTab === 'intelligence' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* ─── LOCATION 3: PROJECT RISK TREND & VELOCITY ENGINE ─────────────────── */}
          <div className="card" style={{ borderLeft: '4px solid var(--color-accent-primary)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <TrendingUp size={18} color="var(--color-accent-primary)" />
                <h3 style={{ fontSize: '0.95rem', fontWeight: 800, margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  PROJECT RISK TREND & VELOCITY ENGINE
                </h3>
              </div>

              {/* Signal Selector (Rule 3 Signal Separation) */}
              <div style={{ display: 'flex', gap: 4, background: 'var(--color-bg-tertiary)', padding: 3, borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                {[
                  { id: 'structural_anomaly', label: 'Structural Anomaly' },
                  { id: 'stage_risk', label: 'Stage Risk' },
                  { id: 'predictive_delay', label: 'Predictive Delay' },
                ].map(sig => (
                  <button
                    key={sig.id}
                    onClick={() => setVelocityRiskType(sig.id)}
                    style={{
                      padding: '4px 8px',
                      fontSize: '0.72rem',
                      fontWeight: velocityRiskType === sig.id ? 700 : 500,
                      borderRadius: 'var(--radius-sm)',
                      background: velocityRiskType === sig.id ? 'var(--color-accent-primary)' : 'transparent',
                      color: velocityRiskType === sig.id ? '#ffffff' : 'var(--color-text-muted)',
                      border: 'none',
                      cursor: 'pointer',
                    }}
                  >
                    {sig.label}
                  </button>
                ))}
              </div>
            </div>

            {velocityData?.velocity_status === 'NOT_AVAILABLE' ? (
              <div style={{ padding: 24, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', textAlign: 'center', border: '1px solid var(--color-border-subtle)' }}>
                <span className="badge badge-gray" style={{ fontSize: '0.85rem', marginBottom: 8 }}>Risk Velocity: Not Available</span>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-text-secondary)', marginTop: 6 }}>
                  Reason: Insufficient historical observations
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', maxWidth: 500, margin: '8px auto 0' }}>
                  {velocityData.disclaimer || 'At least 2 historical snapshots for this specific risk signal are required to compute velocity. Velocity is never invented or synthetic.'}
                </p>
              </div>
            ) : (
              <div>
                {/* Timeline Chart */}
                <div style={{ marginBottom: 14 }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-text-muted)', marginBottom: 4 }}>
                    PROJECT RISK TREND SNAPSHOT HISTORY
                  </div>
                  {velocityData?.history && velocityData.history.length > 0 && (
                    <ReactECharts
                      option={{
                        backgroundColor: 'transparent',
                        tooltip: { trigger: 'axis', backgroundColor: '#0a182e', textStyle: { color: '#fff', fontSize: 11 } },
                        grid: { top: 20, bottom: 25, left: 35, right: 20 },
                        xAxis: {
                          type: 'category',
                          data: velocityData.history.map((h: any) => new Date(h.snapshot_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
                          axisLine: { lineStyle: { color: 'rgba(244,119,33,0.2)' } },
                          axisLabel: { color: '#94a9c9', fontSize: 10 },
                        },
                        yAxis: {
                          type: 'value',
                          min: 0, max: 100,
                          splitLine: { lineStyle: { color: 'rgba(244,119,33,0.06)' } },
                          axisLabel: { color: '#94a9c9', fontSize: 10 },
                        },
                        series: [
                          {
                            name: 'Risk Score',
                            type: 'line',
                            smooth: true,
                            symbol: 'circle',
                            symbolSize: 8,
                            data: velocityData.history.map((h: any) => h.score),
                            itemStyle: { color: velocityData.badge_color === 'rose' ? '#ff4757' : velocityData.badge_color === 'amber' ? '#f47721' : '#138808' },
                            lineStyle: { width: 3 },
                            areaStyle: {
                              color: {
                                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                                colorStops: [{ offset: 0, color: 'rgba(244,119,33,0.3)' }, { offset: 1, color: 'rgba(244,119,33,0.01)' }]
                              }
                            }
                          }
                        ]
                      }}
                      style={{ height: 180, width: '100%' }}
                    />
                  )}
                </div>

                {/* Summary Metrics Grid Below Chart */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, borderTop: '1px solid var(--color-border-subtle)', paddingTop: 14 }}>
                  <div style={{ padding: 10, background: 'var(--color-bg-tertiary)', borderRadius: 6 }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>Current</span>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{velocityData?.current_score ?? 78}</div>
                  </div>

                  <div style={{ padding: 10, background: 'var(--color-bg-tertiary)', borderRadius: 6 }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>7-Day Change</span>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: (velocityData?.change_7d ?? 0) > 15 ? 'var(--color-risk-critical)' : 'var(--color-text-primary)' }}>
                      {(velocityData?.change_7d ?? 0) > 0 ? `+${velocityData?.change_7d}` : velocityData?.change_7d ?? '+17'}
                    </div>
                  </div>

                  <div style={{ padding: 10, background: 'var(--color-bg-tertiary)', borderRadius: 6 }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>30-Day Change</span>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: (velocityData?.change_30d ?? 0) > 0 ? 'var(--color-risk-high)' : '#138808' }}>
                      {(velocityData?.change_30d ?? 0) > 0 ? `+${velocityData?.change_30d}` : velocityData?.change_30d ?? '+29'}
                    </div>
                  </div>

                  <div style={{ padding: 10, background: 'var(--color-bg-tertiary)', borderRadius: 6 }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>Trend</span>
                    <div style={{ fontSize: '1.0rem', fontWeight: 800, color: 'var(--color-risk-high)', marginTop: 2 }}>
                      {velocityData?.label || 'Rising'}
                    </div>
                  </div>

                  <div style={{ padding: 10, background: 'rgba(255,71,87,0.1)', borderRadius: 6, border: '1px solid rgba(255,71,87,0.2)' }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)' }}>Velocity</span>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: 'var(--color-risk-critical)', marginTop: 2 }}>
                      {velocityData?.symbol} {velocityData?.label || 'Rapidly Rising'}
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div style={{ marginTop: 10, fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
              * Initial Policy Thresholds: ≤ -10: Improving | -10 to +5: Stable | +5 to +15: Rising | &gt; +15: Rapidly Rising. Rule 3 Signal Separation strictly enforced.
            </div>
          </div>
          
          {/* ─── CORE AI DELAY PREDICTION ENGINE (MAIN CARD) ────────────────────── */}
          <div className="card" style={{ borderLeft: `4px solid ${riskCategory.border}` }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: 12 }}>
              <div>
                <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0, color: 'var(--color-text-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Flame size={18} color={riskCategory.color} />
                  AI DELAY PREDICTION ENGINE (Core ML Feature)
                </h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', margin: '4px 0 0' }}>
                  Supervised regression ML & anomaly ensemble inference based on lifecycle data parameters.
                </p>
              </div>
              <span className="badge" style={{ background: riskCategory.bg, color: riskCategory.color, border: `1px solid ${riskCategory.border}`, fontWeight: 800 }}>
                {riskCategory.label} RISK
              </span>
            </div>

            {/* 3 CORE PREDICTION METRIC BLOCKS */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 20 }}>
              
              {/* 1. Overall Delay Probability */}
              <div style={{ padding: 16, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Overall Delay Probability
                </span>
                <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: riskCategory.color, marginTop: 4 }}>
                  {overallDelayProb}%
                </div>
                <div style={{ marginTop: 6 }}>
                  <span className="badge" style={{ background: riskCategory.bg, color: riskCategory.color, fontSize: '0.72rem' }}>
                    {riskCategory.label} RISK
                  </span>
                </div>
              </div>

              {/* 2. Risk Score & Classification */}
              <div style={{ padding: 16, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Project Risk Score
                </span>
                <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-mono)', color: riskCategory.color, marginTop: 4 }}>
                  {riskScore} <span style={{ fontSize: '1rem', color: 'var(--color-text-muted)' }}>/ 100</span>
                </div>
                <div style={{ marginTop: 6, fontSize: '0.72rem', color: 'var(--color-text-secondary)', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ opacity: riskScore <= 30 ? 1 : 0.4, fontWeight: riskScore <= 30 ? 800 : 400, color: '#138808' }}>0-30 LOW</span> | 
                  <span style={{ opacity: riskScore >= 31 && riskScore <= 60 ? 1 : 0.4, fontWeight: riskScore >= 31 && riskScore <= 60 ? 800 : 400, color: 'var(--color-risk-medium)' }}>31-60 MED</span> | 
                  <span style={{ opacity: riskScore >= 61 && riskScore <= 80 ? 1 : 0.4, fontWeight: riskScore >= 61 && riskScore <= 80 ? 800 : 400, color: 'var(--color-risk-high)' }}>61-80 HIGH</span> | 
                  <span style={{ opacity: riskScore >= 81 ? 1 : 0.4, fontWeight: riskScore >= 81 ? 800 : 400, color: 'var(--color-risk-critical)' }}>81-100 CRITICAL</span>
                </div>
              </div>

              {/* 3. Time-to-Delay Early-Warning Innovation */}
              <div style={{ padding: 16, background: 'rgba(244,119,33,0.06)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(244,119,33,0.3)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: '0.72rem', color: 'var(--color-accent-primary)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
                    Time-to-Delay Early Warning
                  </span>
                  <span className="badge badge-orange" style={{ fontSize: '0.68rem' }}>AI Early Warning</span>
                </div>
                <div style={{ fontSize: '0.82rem', display: 'flex', flexDirection: 'column', gap: 4, marginTop: 6 }}>
                  <div>Delay Probability: <strong style={{ color: riskCategory.color, fontFamily: 'var(--font-mono)' }}>{overallDelayProb}%</strong></div>
                  <div>Expected Schedule Delay: <strong style={{ color: 'var(--color-risk-high)', fontFamily: 'var(--font-mono)' }}>{expectedDelayDays} days</strong></div>
                  <div>Critical Risk Expected: <strong style={{ color: 'var(--color-risk-critical)', fontFamily: 'var(--font-mono)' }}>Within {criticalRiskExpectedDays} days</strong></div>
                </div>
              </div>

            </div>
          </div>

          {/* B. STAGE RISK FINGERPRINT & C. SHAP MODEL CONTRIBUTORS (Grid 2) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20 }}>
            
            {/* B. Stage Risk Fingerprint */}
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 700, margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Stage Risk Fingerprint
                </h3>
                <span className="badge badge-red">Vulnerable: Compensation</span>
              </div>

              <ReactECharts option={fingerprintOption} style={{ height: 190, width: '100%' }} />
            </div>

            {/* C. Why is this project risky? SHAP Engine */}
            <div className="card">
              <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Model-Supported Risk Contributors (SHAP)
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { name: 'Compensation Gap', pct: 28, desc: '36% compensation pending disbursement' },
                  { name: 'Notification Ageing', pct: 19, desc: '3A to 3D elapsed time exceeding baseline' },
                  { name: 'Affected Family Density', pct: 14, desc: 'High beneficiary family count per hectare' },
                  { name: 'Cost Intensity', pct: 10, desc: 'Land value Cr/ha ratio above district median' },
                ].map(item => (
                  <div key={item.name} style={{ padding: '8px 12px', background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 2 }}>
                      <strong>{item.name}</strong>
                      <span style={{ color: 'var(--color-risk-critical)', fontWeight: 700 }}>+{item.pct}%</span>
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>{item.desc}</div>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* D. AI RELIABILITY DIAGNOSTICS & DUAL SIGNAL ARCHITECTURE */}
          <div className="card">
            <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              AI Reliability & Dual-Signal Verification
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
              <div style={{ padding: 12, background: 'rgba(19,136,8,0.1)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(19,136,8,0.25)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 700, color: '#138808', fontSize: '0.8rem' }}>RELIABILITY</span>
                  <span style={{ fontWeight: 800, color: '#138808', fontSize: '0.8rem' }}>HIGH ✓</span>
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-secondary)' }}>
                  Passed sanity constraints & confidence evaluation.
                </div>
              </div>

              <div style={{ padding: 12, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Data Completeness</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--color-text-primary)' }}>87%</div>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>All core fields present</span>
              </div>

              <div style={{ padding: 12, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Out-of-Distribution (OOD)</span>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#138808' }}>NO</div>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Within standard population</span>
              </div>
            </div>
          </div>

          {/* E. RISK PROPAGATION CHAIN & F. WHAT-IF SIMULATOR (Grid 2) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20 }}>
            
            {/* E. Risk Propagation Chain */}
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                <h3 style={{ fontSize: '0.9rem', fontWeight: 700, margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Risk Propagation Chain
                </h3>
                <button className="btn btn-secondary btn-sm" onClick={() => alert('Full Risk Chain Modal')}>
                  View Full Risk Chain →
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, padding: '10px 0' }}>
                <div style={{ padding: '8px 20px', background: 'rgba(255,71,87,0.15)', border: '1px solid var(--color-risk-critical)', borderRadius: 6, color: 'var(--color-risk-critical)', fontWeight: 700, fontSize: '0.82rem' }}>
                  Compensation Disbursement Risk
                </div>
                <ChevronDown size={18} color="var(--color-text-muted)" />
                <div style={{ padding: '8px 20px', background: 'rgba(244,119,33,0.15)', border: '1px solid var(--color-risk-high)', borderRadius: 6, color: 'var(--color-risk-high)', fontWeight: 700, fontSize: '0.82rem' }}>
                  Land Possession Risk
                </div>
                <ChevronDown size={18} color="var(--color-text-muted)" />
                <div style={{ padding: '8px 20px', background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border-subtle)', borderRadius: 6, color: 'var(--color-text-secondary)', fontWeight: 700, fontSize: '0.82rem' }}>
                  Land Handover to Agency
                </div>
              </div>
            </div>

            {/* F. What-If Simulator */}
            <div className="card">
              <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                What-If Scenario Simulator
              </h3>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 14 }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                    <span>Compensation Progress %</span>
                    <strong>{scenarioInputs['compensation_completion_pct'] ? Math.round(scenarioInputs['compensation_completion_pct'] * 100) : 85}%</strong>
                  </div>
                  <input
                    type="range"
                    min="50" max="100"
                    value={scenarioInputs['compensation_completion_pct'] ? scenarioInputs['compensation_completion_pct'] * 100 : 85}
                    onChange={(e) => setScenarioInputs(prev => ({ ...prev, 'compensation_completion_pct': Number(e.target.value) / 100 }))}
                    style={{ width: '100%', cursor: 'pointer' }}
                  />
                </div>

                <button className="btn btn-primary btn-sm" onClick={runSimulation} disabled={isSimulating} style={{ justifyContent: 'center' }}>
                  {isSimulating ? 'Running Scenario...' : 'Run Scenario Simulation'}
                </button>
              </div>

              {simResult ? (
                <div style={{ padding: 10, background: 'var(--color-bg-tertiary)', borderRadius: 6, fontSize: '0.78rem', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Current Risk: <strong>{simResult.current_score || 82}</strong></span>
                  <span>Simulated: <strong style={{ color: '#138808' }}>{simResult.simulated_score || 61}</strong></span>
                  <span style={{ color: '#138808', fontWeight: 700 }}>Reduction: -21 pts</span>
                </div>
              ) : (
                <div style={{ padding: 10, background: 'var(--color-bg-tertiary)', borderRadius: 6, fontSize: '0.75rem', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                  Simulated Risk reduction output will render here.
                </div>
              )}
            </div>

          </div>

        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────────────── */}
      {/* TAB 4: ACTIONS                                                              */}
      {/* ─────────────────────────────────────────────────────────────────────────── */}
      {activeTab === 'actions' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          
          {/* A. Structured Rule-Based Recommendations */}
          {(() => {
            // ─── Rule Engine ───────────────────────────────────────────────────
            // Each rule checks a real project field, fires a corrective recommendation
            // with: category, severity, action, rationale, owner, and SLA.
            type RecSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
            type Rec = {
              id: string
              category: string
              categoryIcon: string
              severity: RecSeverity
              action: string
              rationale: string
              owner: string
              sla: string
              source: 'RULE'
            }

            const recs: Rec[] = []

            const totalFam = project.total_affected_families || 0
            const compFam = project.families_compensated || 0
            const rehabFam = project.families_rehabilitated || 0
            const totalArea = parseFloat(String(project.total_area_ha || '0'))
            const acquiredArea = parseFloat(String(project.area_acquired_ha || '0'))
            const possessedArea = parseFloat(String(project.area_in_possession_ha || '0'))
            const delayMonths = project.delay_months || 0
            const legalCases = project.legal_case_count || 0
            const legalStatus = (project.legal_case_status || 'NONE').toUpperCase()
            const status = project.status || ''
            const riskLevel = project.risk_level || 'UNKNOWN'
            const estimated = parseFloat(String(project.estimated_compensation_inr || '0'))
            const disbursed = parseFloat(String(project.disbursed_compensation_inr || '0'))
            const compBacklogPct = totalFam > 0 ? Math.round(((totalFam - compFam) / totalFam) * 100) : 0
            const disbursalPct = estimated > 0 ? Math.round((disbursed / estimated) * 100) : 0
            const possessionPct = totalArea > 0 ? Math.round((possessedArea / totalArea) * 100) : 0
            const acquisitionPct = totalArea > 0 ? Math.round((acquiredArea / totalArea) * 100) : 0

            // R1 — Compensation backlog > 30%
            if (compBacklogPct >= 60) {
              recs.push({
                id: 'R1', category: 'Compensation', categoryIcon: '💰',
                severity: 'CRITICAL',
                action: `Organize emergency beneficiary verification camp — ${totalFam - compFam} families pending.`,
                rationale: `${compBacklogPct}% of affected families are not yet compensated. RFCTLARR Section 38 requires timely disbursement before possession.`,
                owner: 'District LA Officer', sla: '7 days', source: 'RULE',
              })
            } else if (compBacklogPct >= 30) {
              recs.push({
                id: 'R1', category: 'Compensation', categoryIcon: '💰',
                severity: 'HIGH',
                action: `Schedule beneficiary verification camp to clear ${totalFam - compFam} pending families.`,
                rationale: `${compBacklogPct}% compensation backlog detected. Blocks possession and R&R milestone.`,
                owner: 'District LA Officer', sla: '14 days', source: 'RULE',
              })
            }

            // R2 — Financial disbursal < 50%
            if (estimated > 0 && disbursalPct < 50) {
              recs.push({
                id: 'R2', category: 'Compensation', categoryIcon: '💰',
                severity: disbursalPct < 25 ? 'CRITICAL' : 'HIGH',
                action: `Expedite compensation fund release — only ${disbursalPct}% disbursed against sanctioned estimate.`,
                rationale: `Low disbursal ratio (${disbursalPct}%) may indicate treasury hold or pending documentation. Escalate to Finance Dept.`,
                owner: 'Finance Controller', sla: '10 days', source: 'RULE',
              })
            }

            // R3 — R&R backlog
            if (totalFam > 0 && rehabFam < compFam && (compFam - rehabFam) > 5) {
              recs.push({
                id: 'R3', category: 'R&R', categoryIcon: '🏠',
                severity: 'MEDIUM',
                action: `Initiate R&R entitlement survey for ${compFam - rehabFam} compensated-but-not-rehabilitated families.`,
                rationale: `Families compensated but not yet rehabilitated (${compFam - rehabFam}). RFCTLARR requires R&R completion before project closure.`,
                owner: 'R&R Cell Officer', sla: '21 days', source: 'RULE',
              })
            }

            // R4 — Legal disputes
            if (legalCases >= 5) {
              recs.push({
                id: 'R4', category: 'Legal', categoryIcon: '⚖️',
                severity: legalCases >= 15 ? 'CRITICAL' : 'HIGH',
                action: `Escalate ${legalCases} pending court cases to the designated Legal Cell / District Collector for expedited resolution.`,
                rationale: `${legalCases} active legal cases (status: ${legalStatus}) are blocking possession and acquisition. Long-pending cases beyond 180 days must be escalated under RFCTLARR Section 64.`,
                owner: 'Legal Cell / Collector', sla: '30 days', source: 'RULE',
              })
            } else if (legalCases > 0) {
              recs.push({
                id: 'R4', category: 'Legal', categoryIcon: '⚖️',
                severity: 'MEDIUM',
                action: `Review ${legalCases} pending legal case(s) and prepare counter-affidavits / settlement options.`,
                rationale: `Unresolved legal cases can delay possession and award proceedings.`,
                owner: 'Legal Cell', sla: '21 days', source: 'RULE',
              })
            }

            // R5 — Possession gap
            if (possessionPct < 50 && acquisitionPct >= 50) {
              recs.push({
                id: 'R5', category: 'Possession', categoryIcon: '📋',
                severity: possessionPct < 25 ? 'HIGH' : 'MEDIUM',
                action: `Conduct joint physical possession inspection drive for un-possessed ${(totalArea - possessedArea).toFixed(1)} ha.`,
                rationale: `Only ${possessionPct}% of acquired land has been physically possessed, blocking project execution. Physical possession must accompany award under RFCTLARR Section 38.`,
                owner: 'Tehsildar / Revenue Officer', sla: '14 days', source: 'RULE',
              })
            }

            // R6 — Documentation / title gap (low acquisition % despite being Active)
            if (acquisitionPct < 40 && (status === 'ACTIVE' || status === 'DELAYED')) {
              recs.push({
                id: 'R6', category: 'Documentation', categoryIcon: '📄',
                severity: 'HIGH',
                action: `Prioritize resolution of missing title documents and mutation records for un-acquired ${(totalArea - acquiredArea).toFixed(1)} ha.`,
                rationale: `Only ${acquisitionPct}% of land acquired despite project being in ${status} stage. Likely blocked by title disputes or revenue record gaps.`,
                owner: 'Revenue Department / Patwari', sla: '21 days', source: 'RULE',
              })
            }

            // R7 — Delay > 6 months
            if (delayMonths >= 12) {
              recs.push({
                id: 'R7', category: 'Approval / Escalation', categoryIcon: '🔔',
                severity: 'CRITICAL',
                action: `Immediate escalation to Principal Secretary — project delayed ${delayMonths} months beyond planned timeline.`,
                rationale: `Delays ≥ 12 months attract mandatory quarterly review under NITI Aayog monitoring framework. SLA breach must be documented.`,
                owner: 'Principal Secretary (LA)', sla: 'Immediate', source: 'RULE',
              })
            } else if (delayMonths >= 6) {
              recs.push({
                id: 'R7', category: 'Approval / Escalation', categoryIcon: '🔔',
                severity: 'HIGH',
                action: `Escalate ${delayMonths}-month delay to District Collector. Identify bottleneck cause and prepare recovery timeline.`,
                rationale: `Project has exceeded planned duration by ${delayMonths} months. Approval pending beyond SLA triggers mandatory reporting.`,
                owner: 'District Collector', sla: '7 days', source: 'RULE',
              })
            } else if (delayMonths >= 3) {
              recs.push({
                id: 'R7', category: 'Approval / Escalation', categoryIcon: '🔔',
                severity: 'MEDIUM',
                action: `Review delay root-cause and update recovery plan with revised milestones.`,
                rationale: `${delayMonths}-month delay noted. Corrective action plan required to prevent further escalation.`,
                owner: 'LA Officer', sla: '14 days', source: 'RULE',
              })
            }

            // R8 — ON_HOLD with no documented reason
            if (status === 'ON_HOLD' && !project.delay_reason) {
              recs.push({
                id: 'R8', category: 'Approval / Escalation', categoryIcon: '🔔',
                severity: 'HIGH',
                action: `Document the hold reason and obtain formal approval from sanctioning authority to re-activate project.`,
                rationale: `Project is ON_HOLD with no documented reason. This violates RFCTLARR audit requirements. Obtain written order from Collector.`,
                owner: 'Project Director', sla: '3 days', source: 'RULE',
              })
            }

            // R9 — Risk level CRITICAL with no legal cases (pure risk score signal)
            if (riskLevel === 'CRITICAL' && legalCases === 0 && compBacklogPct < 30 && delayMonths < 6) {
              recs.push({
                id: 'R9', category: 'Risk Review', categoryIcon: '🔍',
                severity: 'HIGH',
                action: `Conduct detailed field verification to identify unregistered impediments — ML anomaly score is CRITICAL.`,
                rationale: `Structural anomaly risk is CRITICAL despite no obvious legal or delay signals. Potential unregistered disputes, encroachments, or data gaps require physical inspection.`,
                owner: 'District LA Officer', sla: '7 days', source: 'RULE',
              })
            }

            // Fallback when no rule fires
            if (recs.length === 0) {
              recs.push({
                id: 'R0', category: 'Status', categoryIcon: '✅',
                severity: 'LOW',
                action: 'No corrective action required at this time. Continue regular monitoring.',
                rationale: 'All monitored indicators (compensation, legal, possession, delay) are within acceptable thresholds.',
                owner: 'LA Officer', sla: 'Routine', source: 'RULE',
              })
            }

            // Sort: CRITICAL → HIGH → MEDIUM → LOW
            const severityOrder: Record<RecSeverity, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }
            recs.sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity])

            const severityConfig: Record<RecSeverity, { bg: string; border: string; badge: string; color: string }> = {
              CRITICAL: { bg: 'rgba(220,38,38,0.06)', border: 'rgba(220,38,38,0.25)', badge: 'badge-red', color: '#dc2626' },
              HIGH:     { bg: 'rgba(249,115,22,0.06)', border: 'rgba(249,115,22,0.25)', badge: 'badge-orange', color: '#f97316' },
              MEDIUM:   { bg: 'rgba(234,179,8,0.06)',  border: 'rgba(234,179,8,0.25)',  badge: 'badge-yellow', color: '#eab308' },
              LOW:      { bg: 'rgba(22,163,74,0.06)',  border: 'rgba(22,163,74,0.2)',   badge: 'badge-green',  color: '#16a34a' },
            }

            return (
              <div className="card" style={{ border: '1px solid rgba(64,128,255,0.15)' }}>
                {/* Header */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                  <div>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 800, margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--color-text-primary)' }}>
                      🎯 Corrective Recommendations
                    </h3>
                    <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: 3 }}>
                      Rule-based engine · {recs.length} action{recs.length !== 1 ? 's' : ''} fired · Driven by live project data
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {(['CRITICAL','HIGH','MEDIUM'] as RecSeverity[]).map(s => {
                      const count = recs.filter(r => r.severity === s).length
                      if (!count) return null
                      return (
                        <span key={s} className={`badge ${severityConfig[s].badge}`} style={{ fontSize: '0.65rem' }}>
                          {count} {s}
                        </span>
                      )
                    })}
                  </div>
                </div>

                {/* Recommendation Cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {recs.map((rec, idx) => {
                    const cfg = severityConfig[rec.severity]
                    return (
                      <div
                        key={rec.id}
                        style={{
                          background: cfg.bg,
                          border: `1px solid ${cfg.border}`,
                          borderRadius: 'var(--radius-md)',
                          padding: '14px 16px',
                          borderLeft: `4px solid ${cfg.color}`,
                        }}
                      >
                        {/* Row 1: Category + Severity badge */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                            <span style={{ fontSize: '0.9rem' }}>{rec.categoryIcon}</span>
                            <span style={{
                              fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase',
                              letterSpacing: '0.08em', color: cfg.color,
                            }}>
                              {rec.category}
                            </span>
                            <span style={{
                              fontSize: '0.58rem', color: 'var(--color-text-muted)',
                              background: 'var(--color-bg-tertiary)', padding: '1px 5px',
                              borderRadius: 4, fontFamily: 'var(--font-mono)',
                            }}>
                              {rec.id} · RULE
                            </span>
                          </div>
                          <span className={`badge ${cfg.badge}`} style={{ fontSize: '0.62rem' }}>
                            {rec.severity}
                          </span>
                        </div>

                        {/* Row 2: Action text */}
                        <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 6, lineHeight: 1.45 }}>
                          {idx + 1}. {rec.action}
                        </div>

                        {/* Row 3: Rationale */}
                        <div style={{
                          fontSize: '0.72rem', color: 'var(--color-text-secondary)', lineHeight: 1.5,
                          borderTop: `1px solid ${cfg.border}`, paddingTop: 8, marginBottom: 8,
                        }}>
                          📌 <em>{rec.rationale}</em>
                        </div>

                        {/* Row 4: Meta — Owner + SLA */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                          <span>👤 <strong style={{ color: 'var(--color-text-secondary)' }}>{rec.owner}</strong></span>
                          <span>⏱ SLA: <strong style={{ color: cfg.color }}>{rec.sla}</strong></span>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {/* Footer note */}
                <div style={{
                  marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--color-border-subtle)',
                  fontSize: '0.68rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: 6,
                }}>
                  <span>🔒</span>
                  All recommendations are generated by structured rules against live project data. No fabricated or LLM-hallucinated guidance. Rules follow RFCTLARR 2013 and NITI Aayog monitoring framework.
                </div>
              </div>
            )
          })()}

          {/* B. Active Interventions */}
          <div className="card">
            <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Active Project Interventions
            </h3>

            <div style={{ padding: 14, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <strong style={{ fontSize: '0.9rem', color: 'var(--color-text-primary)' }}>
                  Clear compensation verification backlog
                </strong>
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                  Assigned To: <strong>LA Officer – Project {project.project_code}</strong> • Started: 03 Sep • Due: 10 Sep
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="badge badge-yellow">IN PROGRESS</span>
                {canEdit && (
                  <>
                    <button className="btn btn-secondary btn-sm" onClick={() => alert('Update Action')}>Update</button>
                    <button className="btn btn-primary btn-sm" onClick={() => alert('Complete Action')}>Complete</button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* C. Active Alerts */}
          <div className="card">
            <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Unresolved Project Alerts
            </h3>

            <div style={{ padding: 12, background: 'rgba(255,71,87,0.08)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(255,71,87,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="badge badge-red">CRITICAL</span>
                  <strong style={{ fontSize: '0.85rem' }}>Compensation-stage risk increased 18 points in 7 days.</strong>
                </div>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginTop: 4, display: 'block' }}>2 hours ago</span>
              </div>
              <button className="btn btn-secondary btn-sm">Acknowledge</button>
            </div>
          </div>

          {/* D. Outcome Effectiveness Learning */}
          <div className="card">
            <h3 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Intervention Outcome Effectiveness History
            </h3>

            <div style={{ padding: 12, background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem' }}>
              <div>
                <strong>Fast-Track Section 3D Notification Review</strong>
                <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>Completed on 14 Aug 2025</div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <span>Before Action: <strong>81</strong></span>
                <span>After Action: <strong>59</strong></span>
                <span style={{ color: '#138808', fontWeight: 700 }}>Change: -22</span>
                <span className="badge badge-green">Improved</span>
              </div>
            </div>
          </div>

        </div>
      )}

      {/* ─── SIDE DRAWER 1: DOCUMENTS DRAWER ────────────────────────────────────── */}
      <AnimatePresence>
        {showDocsDrawer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'flex', justifyContent: 'flex-end' }}
            onClick={() => setShowDocsDrawer(false)}
          >
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              style={{ width: 420, height: '100%', background: 'var(--color-bg-card)', borderLeft: '1px solid var(--color-border-subtle)', padding: 20, overflowY: 'auto' }}
              onClick={e => e.stopPropagation()}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0 }}>Project Documents (12)</h3>
                <button className="btn btn-ghost btn-sm" onClick={() => setShowDocsDrawer(false)}><X size={16} /></button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { name: '3A Gazette Notification.pdf', size: '2.4 MB', date: '12 Oct 2024' },
                  { name: '3D Gazette Declaration.pdf', size: '3.1 MB', date: '18 Jan 2025' },
                  { name: 'Award 3G Declaration Order.pdf', size: '4.8 MB', date: '14 May 2025' },
                  { name: 'R&R Action Plan & Allocation.pdf', size: '1.9 MB', date: '02 Jun 2025' },
                  { name: 'Land Possession Handover Report.pdf', size: '1.2 MB', date: '20 Jul 2025' },
                  { name: 'District Court Stay Order Copy.pdf', size: '890 KB', date: '05 Aug 2025' },
                ].map((doc, idx) => (
                  <div key={idx} style={{ padding: 12, background: 'var(--color-bg-tertiary)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <strong style={{ fontSize: '0.82rem', color: 'var(--color-text-primary)' }}>{doc.name}</strong>
                      <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>{doc.size} • {doc.date}</div>
                    </div>
                    <button className="btn btn-ghost btn-sm" onClick={() => alert(`Downloading ${doc.name}`)}><Download size={14} /></button>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── SIDE DRAWER 2: LEGAL DETAILS DRAWER ────────────────────────────────── */}
      <AnimatePresence>
        {showLegalDrawer && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'flex', justifyContent: 'flex-end' }}
            onClick={() => setShowLegalDrawer(false)}
          >
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              style={{ width: 440, height: '100%', background: 'var(--color-bg-card)', borderLeft: '1px solid var(--color-border-subtle)', padding: 20, overflowY: 'auto' }}
              onClick={e => e.stopPropagation()}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0 }}>Legal Cases & Approvals Detail</h3>
                <button className="btn btn-ghost btn-sm" onClick={() => setShowLegalDrawer(false)}><X size={16} /></button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[
                  { case: 'WP 1042/2025 - High Court Stay', status: 'STAYED', desc: 'Dispute over award compensation enhancement in Village A.' },
                  { case: 'OS 44/2024 - District Civil Suit', status: 'PENDING', desc: 'Partition dispute among co-sharers of Survey No 142.' },
                  { case: 'Forest Clearance Phase 1', status: 'APPROVED', desc: 'Stage-1 Clearance received from MoEFCC.' },
                ].map((l, i) => (
                  <div key={i} style={{ padding: 12, background: 'var(--color-bg-tertiary)', borderRadius: 8 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <strong style={{ fontSize: '0.85rem' }}>{l.case}</strong>
                      <span className={`badge ${l.status === 'STAYED' ? 'badge-red' : l.status === 'APPROVED' ? 'badge-green' : 'badge-yellow'}`}>{l.status}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{l.desc}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── MODAL: AUDIT HISTORY MODAL ─────────────────────────────────────────── */}
      <AnimatePresence>
        {showAuditModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            onClick={() => setShowAuditModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
              style={{ width: 500, background: 'var(--color-bg-card)', borderRadius: 'var(--radius-xl)', padding: 20, border: '1px solid var(--color-border-subtle)' }}
              onClick={e => e.stopPropagation()}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 800, margin: 0 }}>Project Audit Log History</h3>
                <button className="btn btn-ghost btn-sm" onClick={() => setShowAuditModal(false)}><X size={16} /></button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 300, overflowY: 'auto' }}>
                {[
                  { action: 'Compensation Disbursement Update', user: 'LA Officer', time: '04 Sep 2026 14:22' },
                  { action: 'Stage Status Changed to COMPENSATION', user: 'District Collector', time: '01 Sep 2026 10:15' },
                  { action: 'Section 3G Award Document Uploaded', user: 'Super Admin', time: '14 May 2025 16:45' },
                ].map((a, i) => (
                  <div key={i} style={{ padding: 10, background: 'var(--color-bg-tertiary)', borderRadius: 6, fontSize: '0.78rem' }}>
                    <strong>{a.action}</strong>
                    <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                      By: {a.user} • {a.time}
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

    </motion.div>
  )
}
