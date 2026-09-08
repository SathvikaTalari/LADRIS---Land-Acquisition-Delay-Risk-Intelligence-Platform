/**
 * LADRIS — LA Officer Workbench
 * Specialized operational dashboard for Land Acquisition Officers / Competent Authorities.
 */
import { useState } from 'react'
import {
  FolderCheck,
  AlertTriangle,
  Clock,
  Bell,
  PlusCircle,
  FileCheck2,
  Sparkles,
  ChevronRight,
  ShieldAlert,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'


export default function LAWorkbench() {
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState<'my_projects' | 'actions_due' | 'alerts' | 'data_entry'>('my_projects')
  const [selectedProject, setSelectedProject] = useState<string>('NH-765 Package 2')

  // Sample operational state for LA Officer
  const assignedProjects = [
    { id: '1', code: 'NH-765-P2', name: 'NH-765 Package 2 Expressway Acquisition', risk: 'CRITICAL', area: '142.5 ha', pendingComp: '₹14.2 Cr', status: 'SECTION_21_OBJECTIONS' },
    { id: '2', code: 'RR-BLR-04', name: 'Bengaluru Outer Ring Rail Corridor', risk: 'CRITICAL', area: '88.0 ha', pendingComp: '₹8.6 Cr', status: 'AWARD_PREPARATION' },
    { id: '3', code: 'TG-IND-01', name: 'Sangareddy Industrial Zone Expansion', risk: 'HIGH', area: '210.0 ha', pendingComp: '₹22.1 Cr', status: 'COMPENSATION_DISBURSEMENT' },
    { id: '4', code: 'HYD-MET-03', name: 'Hyderabad Metro Phase 2 Extension', risk: 'MEDIUM', area: '45.2 ha', pendingComp: '₹5.4 Cr', status: 'POSSESSION' },
    { id: '5', code: 'MH-HW-109', name: 'Nagpur Bypass Highway Section 4', risk: 'MEDIUM', area: '96.8 ha', pendingComp: '₹11.0 Cr', status: 'PRELIMINARY_NOTIFICATION' },
  ]

  const actionsDue = [
    { id: 'a1', project: 'NH-765 Package 2', task: 'Issue Section 19 Declaration Notice', deadline: 'Today, 5:00 PM', priority: 'HIGH', category: 'Notification' },
    { id: 'a2', project: 'Sangareddy Industrial Zone', task: 'Verify 42 Disbursed Solatium Claims', deadline: 'Today, 6:00 PM', priority: 'CRITICAL', category: 'Compensation' },
    { id: 'a3', project: 'Bengaluru Outer Ring Rail', task: 'Upload Hearing Minutes for Khasra #402', deadline: 'Today', priority: 'HIGH', category: 'Objection Hearing' },
    { id: 'a4', project: 'NH-765 Package 2', task: 'Acknowledge Stay Order from District Court', deadline: 'Tomorrow', priority: 'CRITICAL', category: 'Legal' },
    { id: 'a5', project: 'Hyderabad Metro Phase 2', task: 'Sign Possession Certificate for Parcel 12B', deadline: 'Sep 6, 2026', priority: 'MEDIUM', category: 'Possession' },
    { id: 'a6', project: 'Nagpur Bypass Highway', task: 'Submit R&R Family Entitlement Report', deadline: 'Sep 7, 2026', priority: 'MEDIUM', category: 'R&R' },
    { id: 'a7', project: 'Sangareddy Industrial Zone', task: 'Resolve Grievance #GRV-2026-892', deadline: 'Sep 8, 2026', priority: 'LOW', category: 'Grievance' },
  ]

  const unresolvedAlerts = [
    { id: 'al1', project: 'NH-765 Package 2', title: 'Possession Blocked by Landowners', time: '2 hours ago', severity: 'CRITICAL' },
    { id: 'al2', project: 'Sangareddy Industrial Zone', title: 'Compensation Overdue for 18 Parcels', time: '5 hours ago', severity: 'HIGH' },
    { id: 'al3', project: 'Bengaluru Outer Ring Rail', title: 'Legal Case Filed in High Court (Writ #4401)', time: '1 day ago', severity: 'CRITICAL' },
  ]

  return (
    <div style={{ padding: '24px 32px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* ── Page Banner ── */}
      <div style={{
        padding: '24px 28px',
        borderRadius: 'var(--radius-xl)',
        background: 'linear-gradient(135deg, rgba(64,128,255,0.12) 0%, rgba(124,92,252,0.08) 100%)',
        border: '1px solid rgba(64,128,255,0.2)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 20,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <span className="badge badge-blue" style={{ fontSize: '0.75rem', fontWeight: 700 }}>
              OPERATIONAL WORKBENCH
            </span>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              Jurisdiction: {user?.district_code || 'Sangareddy (TG-SR)'}
            </span>
          </div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--color-text-primary)', margin: 0 }}>
            Welcome back, {user?.full_name || 'Land Acquisition Officer'}
          </h1>
          <p style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', margin: '4px 0 0 0' }}>
            Manage assigned land acquisition packages, track daily action items, and record official proceedings.
          </p>
        </div>

        {/* Action Button */}
        <button
          onClick={() => setActiveTab('data_entry')}
          className="btn btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px' }}
        >
          <PlusCircle size={16} />
          <span>New Acquisition Record</span>
        </button>
      </div>

      {/* ── Summary KPI Cards ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
        {/* Card 1: Assigned Projects */}
        <div
          onClick={() => setActiveTab('my_projects')}
          style={{
            padding: '20px',
            borderRadius: 'var(--radius-lg)',
            background: 'var(--color-bg-surface)',
            border: activeTab === 'my_projects' ? '1.5px solid var(--color-accent-primary)' : '1px solid var(--color-border-default)',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-sm)',
            transition: 'all 0.2s',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>My Assigned Projects</span>
            <FolderCheck size={20} color="#4080ff" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--color-text-primary)', lineHeight: 1.1 }}>5</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 8, display: 'flex', gap: 8 }}>
            <span style={{ color: '#ef4444', fontWeight: 700 }}>2 Critical</span>
            <span>•</span>
            <span style={{ color: '#f59e0b', fontWeight: 700 }}>1 High</span>
            <span>•</span>
            <span style={{ color: '#3b82f6', fontWeight: 700 }}>2 Medium</span>
          </div>
        </div>

        {/* Card 2: Actions Due Today */}
        <div
          onClick={() => setActiveTab('actions_due')}
          style={{
            padding: '20px',
            borderRadius: 'var(--radius-lg)',
            background: 'var(--color-bg-surface)',
            border: activeTab === 'actions_due' ? '1.5px solid var(--color-accent-primary)' : '1px solid var(--color-border-default)',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-sm)',
            transition: 'all 0.2s',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Actions Due Today</span>
            <Clock size={20} color="#f59e0b" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#f59e0b', lineHeight: 1.1 }}>7</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 8 }}>
            3 Section notifications pending signature
          </div>
        </div>

        {/* Card 3: Unresolved Alerts */}
        <div
          onClick={() => setActiveTab('alerts')}
          style={{
            padding: '20px',
            borderRadius: 'var(--radius-lg)',
            background: 'var(--color-bg-surface)',
            border: activeTab === 'alerts' ? '1.5px solid var(--color-accent-primary)' : '1px solid var(--color-border-default)',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-sm)',
            transition: 'all 0.2s',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--color-text-secondary)' }}>Unresolved Alerts</span>
            <Bell size={20} color="#ef4444" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: '#ef4444', lineHeight: 1.1 }}>3</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 8 }}>
            2 High Court stay notices requiring response
          </div>
        </div>

        {/* Card 4: AI Decision Assist */}
        <div style={{
          padding: '20px',
          borderRadius: 'var(--radius-lg)',
          background: 'linear-gradient(135deg, rgba(124,92,252,0.1) 0%, rgba(64,128,255,0.05) 100%)',
          border: '1px solid rgba(124,92,252,0.25)',
          boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#a78bfa' }}>AI Recommended Action</span>
            <Sparkles size={20} color="#a78bfa" />
          </div>
          <div style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
            Fast-track Section 23 Award Disbursement
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
            Predicted to reduce package delay by 24 days.
          </div>
        </div>
      </div>

      {/* ── Tabs Navigation ── */}
      <div style={{ display: 'flex', gap: 12, borderBottom: '1px solid var(--color-border-default)', paddingBottom: 12 }}>
        {[
          { id: 'my_projects', label: 'Assigned Packages (5)', icon: FolderCheck },
          { id: 'actions_due', label: 'Actions Due Today (7)', icon: Clock },
          { id: 'alerts', label: 'Critical Alerts (3)', icon: AlertTriangle },
          { id: 'data_entry', label: 'Update Land Record', icon: FileCheck2 },
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
                background: isActive ? 'rgba(64,128,255,0.12)' : 'transparent',
                border: isActive ? '1px solid rgba(64,128,255,0.3)' : '1px solid transparent',
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

      {/* ── Content View ── */}
      {activeTab === 'my_projects' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
              Assigned Land Acquisition Packages
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Scoped to: LA Officer A</span>
          </div>

          <div style={{ display: 'grid', gap: 12 }}>
            {assignedProjects.map((p) => (
              <div
                key={p.id}
                style={{
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-default)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 16,
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ flex: 1, minWidth: 260 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                    <span className="badge badge-gray" style={{ fontSize: '0.7rem', fontWeight: 700 }}>{p.code}</span>
                    <span className={`badge badge-${p.risk === 'CRITICAL' ? 'red' : p.risk === 'HIGH' ? 'yellow' : 'blue'}`}>
                      {p.risk} RISK
                    </span>
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{p.name}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Extent: {p.area} • Current Stage: <strong style={{ color: 'var(--color-text-secondary)' }}>{p.status}</strong>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Pending Compensation</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--color-accent-primary)' }}>{p.pendingComp}</div>
                </div>

                <button
                  onClick={() => {
                    setSelectedProject(p.name)
                    setActiveTab('data_entry')
                  }}
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', fontSize: '0.8125rem' }}
                >
                  <span>Update Package</span>
                  <ChevronRight size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'actions_due' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
            Actions Due Today ({actionsDue.length})
          </h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {actionsDue.map((a) => (
              <div
                key={a.id}
                style={{
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'var(--color-bg-surface)',
                  border: '1px solid var(--color-border-default)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 16,
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>{a.category}</span>
                    <span style={{ fontSize: '0.78rem', color: '#ef4444', fontWeight: 700 }}>Deadline: {a.deadline}</span>
                  </div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{a.task}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 2 }}>{a.project}</div>
                </div>

                <button className="btn btn-primary" style={{ padding: '6px 14px', fontSize: '0.8rem' }}>
                  Complete Action
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'alerts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0, color: 'var(--color-text-primary)' }}>
            Unresolved Package Alerts
          </h3>
          <div style={{ display: 'grid', gap: 10 }}>
            {unresolvedAlerts.map((al) => (
              <div
                key={al.id}
                style={{
                  padding: '16px 20px',
                  borderRadius: 'var(--radius-lg)',
                  background: 'rgba(239, 68, 68, 0.05)',
                  border: '1px solid rgba(239, 68, 68, 0.2)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <ShieldAlert size={22} color="#ef4444" />
                  <div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{al.title}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>{al.project} • {al.time}</div>
                  </div>
                </div>
                <button className="btn btn-secondary" style={{ padding: '6px 14px', fontSize: '0.8rem' }}>
                  Acknowledge Alert
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'data_entry' && (
        <div style={{
          padding: '24px',
          borderRadius: 'var(--radius-xl)',
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-border-default)',
        }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0 0 16px 0', color: 'var(--color-text-primary)' }}>
            Operational Data Entry — {selectedProject}
          </h3>

          <form onSubmit={(e) => { e.preventDefault(); alert('Acquisition record successfully updated!'); }} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Acquisition Milestone / Stage
              </label>
              <select className="input" defaultValue="SECTION_21_OBJECTIONS">
                <option value="PRELIMINARY_NOTIFICATION">Section 11 Preliminary Notification</option>
                <option value="SOCIAL_IMPACT_ASSESSMENT">Social Impact Assessment (SIA)</option>
                <option value="SECTION_19_DECLARATION">Section 19 Declaration of Acquisition</option>
                <option value="SECTION_21_OBJECTIONS">Section 21 Objection Hearings</option>
                <option value="AWARD_PREPARATION">Section 23 Award Preparation</option>
                <option value="COMPENSATION_DISBURSEMENT">Compensation Disbursement</option>
                <option value="POSSESSION">Possession Taken</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Official Notification Date
              </label>
              <input type="date" className="input" defaultValue="2026-08-15" />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Objections Received / Resolved
              </label>
              <input type="text" className="input" defaultValue="14 Objections / 11 Resolved" />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Disbursed Compensation Amount (INR)
              </label>
              <input type="number" className="input" defaultValue={142000000} />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Pending Court Case Reference (if any)
              </label>
              <input type="text" className="input" placeholder="e.g. Writ Petition #4401/2026 High Court" />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-secondary)', display: 'block', marginBottom: 6 }}>
                Possession Certificate Reference
              </label>
              <input type="text" className="input" placeholder="e.g. POS-CERT-2026-901" />
            </div>

            <div style={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
              <button type="button" onClick={() => setActiveTab('my_projects')} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" style={{ padding: '10px 24px' }}>
                Save Official Record
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
