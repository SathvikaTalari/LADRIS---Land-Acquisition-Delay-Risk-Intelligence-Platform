/**
 * LADRIS — Common Utility Functions
 */
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { RiskLevel, ProjectStatus } from '@/types'

/** shadcn/ui-compatible className merger */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Map RiskLevel to CSS class suffix */
export function riskLevelClass(level: RiskLevel): string {
  const map: Record<RiskLevel, string> = {
    CRITICAL: 'critical',
    HIGH: 'high',
    MEDIUM: 'medium',
    LOW: 'low',
    UNKNOWN: 'unknown',
  }
  return map[level] ?? 'unknown'
}

/** Map ProjectStatus to badge class */
export function statusBadgeClass(status: ProjectStatus): string {
  const map: Record<ProjectStatus, string> = {
    ACTIVE: 'badge-green',
    COMPLETED: 'badge-gray',
    DELAYED: 'badge-red',
    APPROVED: 'badge-blue',
    UNDER_REVIEW: 'badge-yellow',
    DRAFT: 'badge-gray',
    CANCELLED: 'badge-red',
    ON_HOLD: 'badge-yellow',
  }
  return map[status] ?? 'badge-gray'
}

/** Format INR currency */
export function formatINR(amount: number | null): string {
  if (amount === null || amount === undefined) return '—'
  if (amount >= 1_00_00_00_000) return `₹${(amount / 1_00_00_00_000).toFixed(2)} Cr`
  if (amount >= 1_00_000) return `₹${(amount / 1_00_000).toFixed(2)} L`
  return `₹${amount.toLocaleString('en-IN')}`
}

/** Format area in hectares */
export function formatHa(ha: number | null): string {
  if (ha === null || ha === undefined) return '—'
  return `${ha.toLocaleString('en-IN')} ha`
}

/** Format a date string */
export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

/** Get human-readable role label */
export function roleLabel(role: string): string {
  const map: Record<string, string> = {
    SUPER_ADMIN: 'Super Admin',
    CENTRAL_ADMIN: 'Central Admin',
    STATE_ADMIN: 'State Admin',
    DISTRICT_OFFICER: 'District Officer',
    LA_OFFICER: 'LA Officer',
    PROJECT_OFFICER: 'LA Officer',
    PROJECT_AGENCY: 'Project Agency',
    POLICY_ANALYST: 'Policy Analyst',
    ANALYST: 'Policy Analyst',
    VIEWER: 'Viewer',
  }
  return map[role] ?? role
}


/** Get human-readable project type label */
export function projectTypeLabel(type: string): string {
  const map: Record<string, string> = {
    HIGHWAY: 'Highway',
    RAILWAY: 'Railway',
    METRO_RAIL: 'Metro Rail',
    AIRPORT: 'Airport',
    PORT: 'Port',
    POWER_TRANSMISSION: 'Power Transmission',
    PIPELINE: 'Pipeline',
    IRRIGATION: 'Irrigation',
    URBAN_DEVELOPMENT: 'Urban Development',
    INDUSTRIAL_CORRIDOR: 'Industrial Corridor',
    DEFENCE: 'Defence',
    OTHER: 'Other',
  }
  return map[type] ?? type
}
