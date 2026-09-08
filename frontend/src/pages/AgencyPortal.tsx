/**
 * LADRIS — Project Implementing Agency Portal
 * Dedicated view for Land Requiring Bodies / Project Implementing Agencies (e.g. NHAI, RVNL).
 */
import { useState } from 'react'
import {
  MapPin,
  Layers,
  AlertTriangle,
  Lock,
  Edit3,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { formatINR } from '@/utils'

export default function AgencyPortal() {
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState<'status' | 'update_schedule' | 'bottlenecks'>('status')


  // Sample agency projects data
  const agencyProjects = [
    {
      id: 'p1',
      code: 'NHAI-TG-765',
      name: 'NH-765 Package 2 Expressway Extension',
      agency: user?.agency_name || 'National Highways Authority of India (NHAI)',
      requiredArea: 142.5,
      acquiredArea: 98.2,
      possessionArea: 72.0,
      currentStage: 'Objection Hearing & Award Preparation',
      riskLevel: 'CRITICAL',
      predictedDelayMonths: 4.5,
      requiredByDate: '2026-12-31',
      projectCost: 12500000000,
      constructionDependency: 'Bridge Foundation Construction in Ch. 42+100 to 48+300',
      criticalVillages: ['Sangareddy Khasra 401', 'Kandi Village', 'Rudraram Corridor'],
    },
    {
      id: 'p2',
      code: 'NHAI-MH-204',
      name: 'Pune-Solapur Expressway Widening Package 3',
      agency: user?.agency_name || 'National Highways Authority of India (NHAI)',
      requiredArea: 210.0,
      acquiredArea: 185.0,
      possessionArea: 160.0,
      currentStage: 'Compensation Disbursement',
      riskLevel: 'HIGH',
      predictedDelayMonths: 2.1,
      requiredByDate: '2026-11-15',
      projectCost: 18900000000,
      constructionDependency: 'Toll Plaza Land Handover',
      criticalVillages: ['Hadapsar Sector 9', 'Loni Kalbhor'],
    },
  ]

  const selectedProj = agencyProjects[0]

  return (
    <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* ── Page Banner ── */}
      <div style={{
        padding: '24px 28px',
        borderRadius: 'var(--radius-xl)',
        background: 'linear-gradient(135deg, rgba(244,119,33,0.12) 0%, rgba(0,51,102,0.08) 100%)',
        border: '1px solid rgba(244,119,33,0.25)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 20,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <span className="badge badge-yellow" style={{ fontSize: '0.75rem', fontWeight: 700 }}>
              PROJECT IMPLEMENTING AGENCY PORTAL
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              Agency: {user?.agency_name || 'National Highways Authority of India (NHAI)'}
            </span>
          </div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-text-primary)', margin: 0 }}>
            Land Availability & Acquisition Monitor
          </h1>
          <p style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', margin: '4px 0 0 0' }}>
            Track when required land will become available for your infrastructure civil works.
          </p>
        </div>

        <button
          onClick={() => setActiveTab('update_schedule')}
          className="btn btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px' }}
        >
          <Edit3 size={16} />
          <span>Update Schedule Requirements</span>
        </button>
      </div>

      {/* ── KPI Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
        {/* Land Required vs Acquired */}
        <div style={{
          padding: '20px',
          borderRadius: 'var(--radius-lg)',
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 8 }}>
            Land Required vs Acquired
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-text-primary)' }}>
            {selectedProj.acquiredArea} / {selectedProj.requiredArea} ha
          </div>
          <div style={{
            height: 6,
            width: '100%',
            background: 'var(--color-bg-elevated)',
            borderRadius: 3,
            marginTop: 10,
            overflow: 'hidden',
          }}>
            <div style={{
              height: '100%',
              width: `${(selectedProj.acquiredArea / selectedProj.requiredArea) * 100}%`,
              background: '#3b82f6',
              borderRadius: 3,
            }} />
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 6 }}>
            {((selectedProj.acquiredArea / selectedProj.requiredArea) * 100).toFixed(1)}% Acquired Officially
          </div>
        </div>

        {/* Land in Possession */}
        <div style={{
          padding: '20px',
          borderRadius: 'var(--radius-lg)',
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 8 }}>
            Available for Construction (Possession)
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#10b981' }}>
            {selectedProj.possessionArea} ha
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 12 }}>
            Ready for civil contractor mobilization
          </div>
        </div>

        {/* Predicted Delay */}
        <div style={{
          padding: '20px',
          borderRadius: 'var(--radius-lg)',
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 8 }}>
            AI Predicted Land Handover Delay
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#ef4444' }}>
            +{selectedProj.predictedDelayMonths} Months
          </div>
          <div style={{ fontSize: '0.75rem', color: '#ef4444', fontWeight: 600, marginTop: 12 }}>
            Risk Level: {selectedProj.riskLevel}
          </div>
        </div>

        {/* Required-By Date */}
        <div style={{
          padding: '20px',
          borderRadius: 'var(--radius-lg)',
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
          boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 8 }}>
            Required-By Date for Civil Works
          </div>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--color-accent-primary)' }}>
            {selectedProj.requiredByDate}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 12 }}>
            Construction Dependency: Bridge Foundation
          </div>
        </div>
      </div>

      {/* ── Notice Banner on Permissions ── */}
      <div style={{
        padding: '12px 18px',
        borderRadius: 'var(--radius-lg)',
        background: 'rgba(59, 130, 246, 0.08)',
        border: '1px solid rgba(59, 130, 246, 0.2)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        fontSize: '0.8125rem',
        color: 'var(--color-text-secondary)',
      }}>
        <Lock size={18} color="#3b82f6" style={{ flexShrink: 0 }} />
        <div>
          <strong style={{ color: 'var(--color-text-primary)' }}>Audit & Compliance Governance:</strong> Implementing Agencies can update project-side parameters (required-by date, project cost, construction dependencies). Official LA court records, compensation disbursement, and possession certificates are managed exclusively by Government LA Authorities for auditability.
        </div>
      </div>

      {/* ── Tabs Navigation ── */}
      <div style={{ display: 'flex', gap: 12, borderBottom: '1px solid var(--color-border-default)', paddingBottom: 12 }}>
        {[
          { id: 'status', label: 'Land Availability Overview', icon: Layers },
          { id: 'update_schedule', label: 'Project Schedule & Requirements', icon: Edit3 },
          { id: 'bottlenecks', label: 'Critical Village Bottlenecks', icon: AlertTriangle },
        ].map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 16px',
                borderRadius: 'var(--radius-md)',
                background: isActive ? 'rgba(244,119,33,0.12)' : 'transparent',
                border: isActive ? '1px solid rgba(244,119,33,0.3)' : '1px solid transparent',
                color: isActive ? 'var(--color-accent-primary)' : 'var(--color-text-secondary)',
                fontWeight: isActive ? 700 : 500,
                fontSize: '0.875rem',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              <Icon size={16} />
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {/* ── Tab Content ── */}
      {activeTab === 'status' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{
            padding: '24px',
            borderRadius: 'var(--radius-xl)',
            background: 'var(--color-bg-surface)',
            border: '1px solid var(--color-border-default)',
          }}>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0 0 16px 0', color: 'var(--color-text-primary)' }}>
              Project: {selectedProj.name} ({selectedProj.code})
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
              <div>
                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Executing / Requiring Agency</span>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: 2 }}>{selectedProj.agency}</div>
              </div>

              <div>
                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Current LA Lifecycle Stage</span>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#f59e0b', marginTop: 2 }}>{selectedProj.currentStage}</div>
              </div>

              <div>
                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Project Budget (INR)</span>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)', marginTop: 2 }}>{formatINR(selectedProj.projectCost)}</div>
              </div>

              <div>
                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Critical Civil Work Dependency</span>
                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-text-secondary)', marginTop: 2 }}>{selectedProj.constructionDependency}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'update_schedule' && (
        <div style={{
          padding: '24px',
          borderRadius: 'var(--radius-xl)',
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
        }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0 0 16px 0', color: 'var(--color-text-primary)' }}>
            Update Project-Side Requirements (Agency Input)
          </h3>

          <form onSubmit={(e) => { e.preventDefault(); alert('Agency requirements successfully saved!'); }} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Total Land Extent Required (Hectares)
              </label>
              <input type="number" step="0.1" className="input" defaultValue={selectedProj.requiredArea} />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Required-By Date (For Contractor Mobilization)
              </label>
              <input type="date" className="input" defaultValue={selectedProj.requiredByDate} />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Project Estimated Cost (INR)
              </label>
              <input type="number" className="input" defaultValue={selectedProj.projectCost} />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Project Priority Level
              </label>
              <select className="input" defaultValue="HIGH">
                <option value="CRITICAL">National Priority Corridor (Critical)</option>
                <option value="HIGH">High Priority Infrastructure</option>
                <option value="MEDIUM">Standard State/Central Project</option>
              </select>
            </div>

            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Construction Dependency Notes
              </label>
              <textarea className="input" rows={3} defaultValue={selectedProj.constructionDependency} />
            </div>

            <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
              <button type="button" onClick={() => setActiveTab('status')} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" style={{ padding: '10px 24px' }}>
                Save Agency Requirements
              </button>
            </div>
          </form>
        </div>
      )}

      {activeTab === 'bottlenecks' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
            Critical Villages Delaying Handover
          </h3>

          <div style={{ display: 'grid', gap: 10 }}>
            {selectedProj.criticalVillages.map((v, i) => (
              <div
                key={i}
                style={{
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-default)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <MapPin size={20} color="#ef4444" />
                  <div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{v}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>Status: Section 21 Objection hearings ongoing</div>
                  </div>
                </div>

                <span className="badge badge-red">DELAY RISK HIGH</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
