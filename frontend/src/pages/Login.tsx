/**
 * LADRIS — Premium Login Page
 */
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, EyeOff, AlertCircle, Lock, Mail, Shield, Zap, Sun, Moon, UserCheck } from 'lucide-react'
import { useAuthStore, getRoleDefaultPath } from '@/store/authStore'
import { useThemeStore } from '@/store/themeStore'

export const ROLE_OPTIONS = [
  { key: 'CENTRAL_ADMIN', label: 'Central Admin (MoRTH / Central Ministry)', email: 'central.admin@ladris.gov.in', pass: 'Password123!', scope: 'India-wide National Jurisdiction', target: 'National Dashboard' },
  { key: 'STATE_ADMIN', label: 'State Admin (Telangana State Nodal Auth)', email: 'state.admin.tg@ladris.gov.in', pass: 'Password123!', scope: 'Telangana State Scope', target: 'State Dashboard' },
  { key: 'DISTRICT_OFFICER', label: 'District Officer (Collector / LA Admin)', email: 'district.officer.sangareddy@ladris.gov.in', pass: 'Password123!', scope: 'Sangareddy District Scope', target: 'District Dashboard' },
  { key: 'LA_OFFICER', label: 'LA Officer (Competent Authority)', email: 'la.officer@ladris.gov.in', pass: 'Password123!', scope: 'Assigned Packages Only', target: 'LA Workbench' },
  { key: 'PROJECT_AGENCY', label: 'Project Agency (Implementing Body / NHAI)', email: 'project.agency@nhai.gov.in', pass: 'Password123!', scope: 'NHAI Project Scope', target: 'Agency Portal' },
  { key: 'POLICY_ANALYST', label: 'Policy Analyst (NITI Aayog / Researcher)', email: 'policy.analyst@niti.gov.in', pass: 'Password123!', scope: 'Analytics & Simulations', target: 'Decision Hub' },
  { key: 'VIEWER', label: 'Viewer (Senior Audit Observer)', email: 'viewer@ladris.gov.in', pass: 'Password123!', scope: 'Scoped Read-Only Observer', target: 'Read-Only View' },
  { key: 'SUPER_ADMIN', label: 'Super Admin (Technical Admin)', email: 'admin@ladris.gov.in', pass: 'admin123', scope: 'Full Platform Technical Admin', target: 'Admin Panel' },
]

export default function Login() {
  const navigate = useNavigate()
  const { login, isLoading, isAuthenticated, error, clearError } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const isDark = theme === 'dark'

  const [selectedRoleKey, setSelectedRoleKey] = useState<string>('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const handleRoleDropdownChange = (key: string) => {
    setSelectedRoleKey(key)
    const found = ROLE_OPTIONS.find((r) => r.key === key)
    if (found) {
      setEmail(found.email)
      setPassword(found.pass)
    }
  }

  useEffect(() => {
    if (isAuthenticated && localStorage.getItem('access_token')) {
      navigate('/dashboard')
    }
  }, [isAuthenticated, navigate])

  // Animated particle canvas
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }
    resize()
    window.addEventListener('resize', resize)

    const particles: Array<{
      x: number; y: number; vx: number; vy: number;
      radius: number; opacity: number; pulseOffset: number
    }> = []

    for (let i = 0; i < 70; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        radius: Math.random() * 1.5 + 0.5,
        opacity: Math.random() * 0.4 + 0.1,
        pulseOffset: Math.random() * Math.PI * 2,
      })
    }

    let animId: number
    let t = 0
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      t += 0.01

      particles.forEach((p, i) => {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1

        const pulse = Math.sin(t * 0.8 + p.pulseOffset) * 0.2 + 0.8
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(64, 128, 255, ${p.opacity * pulse})`
        ctx.fill()

        // Draw connections
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[j].x - p.x
          const dy = particles[j].y - p.y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 100) {
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.strokeStyle = `rgba(64, 128, 255, ${(1 - dist / 100) * 0.12})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        }
      })

      animId = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    try {
      await login(email.trim(), password.trim())
      const currentUser = useAuthStore.getState().user
      const dest = getRoleDefaultPath(currentUser?.role)
      navigate(dest)
    } catch {
      // Error handled in store
    }
  }


  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      background: isDark ? '#060b14' : 'var(--color-bg-primary)',
      position: 'relative',
      overflow: 'hidden',
      transition: 'background-color 0.3s ease',
    }}>
      {/* ── Top-Right Theme Toggle Floating Button ── */}
      <div style={{
        position: 'absolute',
        top: 24,
        right: 24,
        zIndex: 50,
      }}>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={toggleTheme}
          title={isDark ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '8px 16px',
            borderRadius: 'var(--radius-full)',
            background: isDark ? 'rgba(14,22,40,0.85)' : 'rgba(255,255,255,0.92)',
            border: `1px solid ${isDark ? 'rgba(64,128,255,0.3)' : 'rgba(0,51,102,0.2)'}`,
            color: isDark ? '#f0f6fc' : '#0a1d37',
            cursor: 'pointer',
            backdropFilter: 'blur(12px)',
            fontSize: '0.8125rem',
            fontWeight: 600,
            boxShadow: isDark
              ? '0 4px 20px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)'
              : '0 4px 16px rgba(0,51,102,0.12), inset 0 1px 0 rgba(255,255,255,0.8)',
            transition: 'all 0.25s ease',
          }}
        >
          {isDark ? (
            <>
              <Sun size={16} color="#facc15" strokeWidth={2.2} />
              <span>Light Mode</span>
            </>
          ) : (
            <>
              <Moon size={16} color="#003366" strokeWidth={2.2} />
              <span>Dark Mode</span>
            </>
          )}
        </motion.button>
      </div>

      {/* ── Left Panel: Branded Showcase (Rich & High-Visibility Video) ── */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '52px 72px',
        position: 'relative',
        overflow: 'hidden',
        background: '#060b14',
      }}>

        {/* Particle Canvas */}
        <canvas
          ref={canvasRef}
          style={{
            position: 'absolute', inset: 0,
            width: '100%', height: '100%',
          }}
        />

        {/* Background glow orbs */}
        <div style={{
          position: 'absolute', top: '15%', left: '20%',
          width: 500, height: 500,
          background: 'radial-gradient(circle, rgba(64,128,255,0.08) 0%, transparent 65%)',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', bottom: '10%', right: '10%',
          width: 400, height: 400,
          background: 'radial-gradient(circle, rgba(124,92,252,0.06) 0%, transparent 65%)',
          pointerEvents: 'none',
        }} />

        {/* Background Video (Full visibility in both light & dark mode) */}
        <video
          autoPlay
          loop
          muted
          playsInline
          style={{
            position: 'absolute', top: 0, left: 0,
            width: '100%', height: '100%',
            objectFit: 'cover',
            zIndex: 0,
            opacity: 0.55,
            filter: 'brightness(1.1) contrast(1.05)',
          }}
        >
          <source src="/LandAcquisition_video.mp4" type="video/mp4" />
        </video>

        {/* Gradient overlay */}
        <div style={{
          position: 'absolute', inset: 0,
          background: 'linear-gradient(90deg, rgba(6,11,20,0.45) 0%, rgba(6,11,20,0.2) 60%, rgba(6,11,20,0.1) 100%), linear-gradient(180deg, rgba(6,11,20,0.3) 0%, transparent 40%, rgba(6,11,20,0.45) 100%)',
          zIndex: 1,
        }} />

        {/* Grid overlay */}
        <div style={{
          position: 'absolute', inset: 0, zIndex: 1,
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)
          `,
          backgroundSize: '60px 60px',
        }} />

        {/* Brand Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          style={{ position: 'relative', zIndex: 2 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{
              width: 56, height: 56,
              borderRadius: 14,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
              background: 'rgba(14,22,40,0.85)',
              border: '1px solid rgba(64,128,255,0.3)',
              boxShadow: '0 4px 24px rgba(64,128,255,0.4)',
              padding: 3,
            }}>
              <img
                src="/logo.png"
                alt="LADRIS Logo"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
            <div>
              <div style={{
                fontSize: '1.6rem',
                fontWeight: 900,
                color: '#ffffff',
                letterSpacing: '-0.03em',
                lineHeight: 1.1,
                textShadow: '0 2px 8px rgba(0,0,0,0.7)',
              }}>
                LADRIS<span style={{ color: '#60a5fa' }}>·</span>AI
              </div>
              <div style={{
                fontSize: '0.65rem',
                fontWeight: 700,
                color: 'rgba(255,255,255,0.9)',
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                marginTop: 2,
                textShadow: '0 1px 4px rgba(0,0,0,0.6)',
              }}>
                Intelligence Platform
              </div>
            </div>
          </div>
        </motion.div>

        {/* Hero Content */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: 'easeOut' }}
          style={{ position: 'relative', zIndex: 2 }}
        >
          <div style={{
            fontSize: '0.72rem',
            fontWeight: 800,
            color: '#ffffff',
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            textShadow: '0 1px 4px rgba(0,0,0,0.7)',
          }}>
            <div style={{
              width: 24, height: 2,
              background: '#ffffff',
              boxShadow: '0 0 8px rgba(255,255,255,0.8)',
            }} />
            Government Intelligence
          </div>
          <h1 style={{
            fontSize: '3.4rem',
            fontWeight: 900,
            lineHeight: 1.08,
            letterSpacing: '-0.04em',
            color: '#ffffff',
            marginBottom: 20,
            textShadow: '0 2px 16px rgba(0,0,0,0.6), 0 1px 3px rgba(0,0,0,0.8)',
          }}>
            Land Intelligence
          </h1>
          <p style={{
            fontSize: '1.05rem',
            color: '#f8fafc',
            lineHeight: 1.7,
            maxWidth: 460,
            marginBottom: 40,
            fontWeight: 500,
            textShadow: '0 1px 8px rgba(0,0,0,0.7), 0 2px 4px rgba(0,0,0,0.8)',
          }}>
            AI-powered land acquisition command center for
            national infrastructure decision makers. Real-time
            risk monitoring across all project corridors.
          </p>

          {/* Feature Pills */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {[
              { icon: '⚡', label: 'Real-time Risk Scoring' },
              { icon: '🗺️', label: 'GIS Spatial Analytics' },
              { icon: '🧠', label: 'AI Decision Intelligence' },
              { icon: '🔐', label: 'Secure Government Access' },
            ].map((pill) => (
              <div
                key={pill.label}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 16px',
                  background: 'rgba(8, 15, 28, 0.75)',
                  border: '1px solid rgba(255,255,255,0.25)',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  color: '#ffffff',
                  backdropFilter: 'blur(10px)',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
                  textShadow: '0 1px 3px rgba(0,0,0,0.6)',
                }}
              >
                <span style={{ fontSize: '0.95rem' }}>{pill.icon}</span>
                {pill.label}
              </div>
            ))}
          </div>
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          style={{
            position: 'relative', zIndex: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 20,
            fontSize: '0.75rem',
            fontWeight: 600,
            color: '#ffffff',
            textShadow: '0 1px 6px rgba(0,0,0,0.8)',
          }}
        >
          <span>© 2026 LADRIS</span>
          <span style={{ opacity: 0.7 }}>•</span>
          <span>Ministry of Rural Development</span>
          <span style={{ opacity: 0.7 }}>•</span>
          <span>Secure Government Platform</span>
        </motion.div>
      </div>

      {/* Right Border Separator */}
      <div style={{
        width: 1,
        background: isDark
          ? 'linear-gradient(180deg, transparent, rgba(64,128,255,0.2), rgba(64,128,255,0.1), transparent)'
          : 'linear-gradient(180deg, transparent, rgba(0,51,102,0.15), rgba(0,51,102,0.08), transparent)',
        flexShrink: 0,
      }} />

      {/* ── Right Panel: Login Form ── */}
      <div style={{
        width: 480,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px 44px',
        background: isDark ? 'rgba(8,15,28,0.95)' : '#ffffff',
        position: 'relative',
        flexShrink: 0,
        boxShadow: isDark ? 'none' : '-10px 0 30px rgba(0,51,102,0.05)',
        transition: 'background 0.3s ease',
      }}>
        {/* Subtle top glow */}
        <div style={{
          position: 'absolute',
          top: 0, left: '20%', right: '20%',
          height: 1,
          background: isDark
            ? 'linear-gradient(90deg, transparent, rgba(64,128,255,0.4), transparent)'
            : 'linear-gradient(90deg, transparent, rgba(244,119,33,0.4), transparent)',
        }} />

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.25, ease: [0.4, 0, 0.2, 1] }}
          style={{ width: '100%', maxWidth: 360 }}
        >
          {/* Form Header */}
          <div style={{ marginBottom: 36 }}>
            <div style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '5px 12px',
              background: isDark ? 'rgba(46,213,115,0.06)' : 'rgba(19,136,8,0.08)',
              border: `1px solid ${isDark ? 'rgba(46,213,115,0.18)' : 'rgba(19,136,8,0.25)'}`,
              borderRadius: 'var(--radius-full)',
              fontSize: '0.72rem',
              fontWeight: 700,
              color: isDark ? '#2ed573' : '#138808',
              letterSpacing: '0.04em',
              marginBottom: 20,
            }}>
              <span style={{
                width: 5, height: 5,
                borderRadius: '50%',
                background: isDark ? '#2ed573' : '#138808',
                animation: 'pulse-glow 2s ease-in-out infinite',
              }} />
              SECURE ACCESS PORTAL
            </div>
            <h2 style={{
              fontSize: '1.6rem',
              fontWeight: 800,
              color: isDark ? '#eef2ff' : '#0a1d37',
              letterSpacing: '-0.025em',
              lineHeight: 1.2,
              marginBottom: 10,
            }}>
              Sign in to your<br />account
            </h2>
            <p style={{ color: isDark ? '#4a5880' : '#5a7194', fontSize: '0.875rem', lineHeight: 1.6 }}>
              Authorized personnel only. All access is monitored and logged.
            </p>
          </div>

          {/* Error Banner */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -8, height: 0 }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '12px 14px',
                  background: isDark ? 'rgba(255,71,87,0.06)' : 'rgba(255,71,87,0.08)',
                  border: `1px solid ${isDark ? 'rgba(255,71,87,0.2)' : 'rgba(255,71,87,0.3)'}`,
                  borderRadius: 'var(--radius-lg)',
                  marginBottom: 20,
                  fontSize: '0.875rem',
                  color: isDark ? '#ff8090' : '#dc2626',
                }}
              >
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Form Fields */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {/* Role Selection Dropdown */}
            <div>
              <label
                htmlFor="role-select"
                style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  fontWeight: 700,
                  color: isDark ? '#7daaff' : '#003366',
                  marginBottom: 8,
                  letterSpacing: '0.02em',
                }}
              >
                Select User Role
              </label>
              <div style={{ position: 'relative' }}>
                <UserCheck
                  size={16}
                  style={{
                    position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
                    color: selectedRoleKey
                      ? (isDark ? '#4080ff' : '#003366')
                      : (isDark ? '#4a5880' : '#94a3b8'),
                    pointerEvents: 'none',
                  }}
                />
                <select
                  id="role-select"
                  className="input"
                  value={selectedRoleKey}
                  onChange={(e) => handleRoleDropdownChange(e.target.value)}
                  style={{
                    paddingLeft: 40,
                    height: 46,
                    cursor: 'pointer',
                    fontWeight: selectedRoleKey ? 700 : 400,
                    color: isDark ? '#eef2ff' : '#0a1d37',
                    background: isDark ? '#0e1628' : '#f8fafc',
                    borderColor: selectedRoleKey
                      ? (isDark ? 'rgba(64,128,255,0.5)' : 'rgba(0,51,102,0.5)')
                      : undefined,
                  }}
                >
                  <option value="">-- Select Role to Auto-Fill Credentials --</option>
                  {ROLE_OPTIONS.map((r) => (
                    <option key={r.key} value={r.key}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Selected Role Scope Preview Badge */}
              {selectedRoleKey && (
                <div style={{
                  marginTop: 8,
                  padding: '8px 12px',
                  borderRadius: 8,
                  background: isDark ? 'rgba(64,128,255,0.08)' : 'rgba(0,51,102,0.05)',
                  border: `1px solid ${isDark ? 'rgba(64,128,255,0.2)' : 'rgba(0,51,102,0.15)'}`,
                  fontSize: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}>
                  <span style={{ color: isDark ? '#8898b8' : '#2b4263' }}>
                    Scope: <strong style={{ color: isDark ? '#7daaff' : '#003366' }}>{ROLE_OPTIONS.find(r => r.key === selectedRoleKey)?.scope}</strong>
                  </span>
                  <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>
                    ➜ {ROLE_OPTIONS.find(r => r.key === selectedRoleKey)?.target}
                  </span>
                </div>
              )}
            </div>

            {/* Email Field */}

            <div>
              <label
                htmlFor="email"
                style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: isDark ? '#8898b8' : '#2b4263',
                  marginBottom: 8,
                  letterSpacing: '0.02em',
                }}
              >
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail
                  size={15}
                  style={{
                    position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
                    color: focusedField === 'email'
                      ? (isDark ? '#4080ff' : '#003366')
                      : (isDark ? '#4a5880' : '#94a3b8'),
                    transition: 'color 0.15s',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  id="email"
                  type="email"
                  className="input"
                  style={{
                    paddingLeft: 40,
                    height: 46,
                    borderColor: focusedField === 'email'
                      ? (isDark ? 'rgba(64,128,255,0.5)' : 'rgba(0,51,102,0.5)')
                      : undefined,
                    boxShadow: focusedField === 'email'
                      ? (isDark
                          ? '0 0 0 3px rgba(64,128,255,0.1), inset 0 2px 6px rgba(0,0,0,0.2)'
                          : '0 0 0 3px rgba(0,51,102,0.1), inset 0 1px 3px rgba(0,0,0,0.05)')
                      : (isDark ? 'inset 0 2px 6px rgba(0,0,0,0.3)' : 'var(--shadow-sm)'),
                  }}
                  placeholder="officer@department.gov.in"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField(null)}
                  required
                  autoComplete="email"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label
                htmlFor="password"
                style={{
                  display: 'block',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  color: isDark ? '#8898b8' : '#2b4263',
                  marginBottom: 8,
                  letterSpacing: '0.02em',
                }}
              >
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={15}
                  style={{
                    position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
                    color: focusedField === 'password'
                      ? (isDark ? '#4080ff' : '#003366')
                      : (isDark ? '#4a5880' : '#94a3b8'),
                    transition: 'color 0.15s',
                    pointerEvents: 'none',
                  }}
                />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="input"
                  style={{
                    paddingLeft: 40,
                    paddingRight: 46,
                    height: 46,
                    borderColor: focusedField === 'password'
                      ? (isDark ? 'rgba(64,128,255,0.5)' : 'rgba(0,51,102,0.5)')
                      : undefined,
                    boxShadow: focusedField === 'password'
                      ? (isDark
                          ? '0 0 0 3px rgba(64,128,255,0.1), inset 0 2px 6px rgba(0,0,0,0.2)'
                          : '0 0 0 3px rgba(0,51,102,0.1), inset 0 1px 3px rgba(0,0,0,0.05)')
                      : (isDark ? 'inset 0 2px 6px rgba(0,0,0,0.3)' : 'var(--shadow-sm)'),
                  }}
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusedField('password')}
                  onBlur={() => setFocusedField(null)}
                  required
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute', right: 13, top: '50%', transform: 'translateY(-50%)',
                    background: 'transparent', border: 'none', cursor: 'pointer',
                    color: isDark ? '#4a5880' : '#64748b',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    padding: 4,
                    transition: 'color 0.15s',
                    borderRadius: 4,
                  }}
                  onMouseEnter={e => (e.currentTarget.style.color = isDark ? '#7daaff' : '#003366')}
                  onMouseLeave={e => (e.currentTarget.style.color = isDark ? '#4a5880' : '#64748b')}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: 1.01 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={isLoading}
              style={{
                width: '100%',
                height: 48,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 10,
                background: isLoading
                  ? (isDark ? 'rgba(64,128,255,0.5)' : 'rgba(0,51,102,0.5)')
                  : (isDark
                      ? 'linear-gradient(135deg, #4080ff 0%, #7c5cfc 100%)'
                      : 'linear-gradient(135deg, #003366 0%, #f47721 100%)'),
                border: 'none',
                borderRadius: 'var(--radius-lg)',
                color: 'white',
                fontSize: '0.9375rem',
                fontWeight: 700,
                cursor: isLoading ? 'not-allowed' : 'pointer',
                fontFamily: 'var(--font-sans)',
                letterSpacing: '-0.01em',
                boxShadow: isLoading
                  ? 'none'
                  : (isDark
                      ? '0 4px 20px rgba(64,128,255,0.35), inset 0 1px 0 rgba(255,255,255,0.15)'
                      : '0 4px 16px rgba(0,51,102,0.25), inset 0 1px 0 rgba(255,255,255,0.2)'),
                transition: 'all 0.2s',
                marginTop: 4,
              }}
            >
              {isLoading ? (
                <>
                  <div style={{
                    width: 18, height: 18,
                    border: '2px solid rgba(255,255,255,0.3)',
                    borderTopColor: 'white',
                    borderRadius: '50%',
                    animation: 'spin 0.7s linear infinite',
                  }} />
                  Authenticating...
                </>
              ) : (
                <>
                  <Zap size={17} strokeWidth={2.5} />
                  Sign In to Command Center
                </>
              )}
            </motion.button>
          </form>

          {/* Security Notice */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            style={{
              marginTop: 24,
              padding: '14px 16px',
              background: isDark ? 'rgba(14,22,40,0.8)' : 'rgba(240,244,249,0.8)',
              border: `1px solid ${isDark ? 'rgba(64,128,255,0.1)' : 'rgba(0,51,102,0.12)'}`,
              borderRadius: 'var(--radius-lg)',
              display: 'flex',
              gap: 12,
              alignItems: 'flex-start',
            }}
          >
            <Shield size={15} color={isDark ? 'rgba(64,128,255,0.6)' : '#003366'} style={{ flexShrink: 0, marginTop: 1 }} />
            <p style={{
              fontSize: '0.75rem',
              color: isDark ? '#4a5880' : '#5a7194',
              margin: 0,
              lineHeight: 1.6,
            }}>
              <strong style={{ color: isDark ? '#8898b8' : '#0a1d37', fontWeight: 600 }}>Secure Access</strong> — Authorized government personnel only. All access is logged.
            </p>
          </motion.div>

        </motion.div>
      </div>
    </div>
  )
}


