'use client'

import { FormEvent, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { authClient } from '@/lib/auth-client'
import { ArrowLeft, Sparkles, ShieldCheck, CheckCircle2, AlertCircle, AlertTriangle } from 'lucide-react'

function CompanionMark() {
  return (
    <div className="companion-mark" aria-hidden="true">
      <span /><span /><span />
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24Z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15Z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98Z"
      />
    </svg>
  )
}

export function AuthForm({
  mode: initialMode,
  onContinueGuest,
  onSuccess,
}: {
  mode: 'sign-in' | 'sign-up'
  onContinueGuest?: () => void
  onSuccess?: () => void
}) {
  const router = useRouter()
  const [mode, setMode] = useState<'sign-in' | 'sign-up'>(initialMode)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [pending, setPending] = useState(false)

  const isSecretKeyConfigured = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.startsWith('sb_secret_')

  async function handleGoogleSignIn() {
    setPending(true)
    setError('')
    setSuccess('')
    try {
      const result = await authClient.signIn.google()
      if (result?.error) {
        setError(result.error.message || 'Google OAuth is not configured yet. Please provide GOOGLE_CLIENT_ID in .env.local.')
        setPending(false)
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to initiate Google sign-in.')
      setPending(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setPending(true)
    setError('')
    setSuccess('')

    const formData = new FormData(event.currentTarget)
    const email = String(formData.get('email') || '').trim()
    const password = String(formData.get('password') || '')
    const name = String(formData.get('name') || '').trim()

    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      setPending(false)
      return
    }

    if (mode === 'sign-in') {
      const result = await authClient.signIn.email({ email, password })
      setPending(false)
      if (result.error) {
        setError(result.error.message || 'Invalid email or password. Please try again.')
        return
      }
      setSuccess('Welcome back! Opening your space...')
      setTimeout(() => {
        if (onSuccess) {
          onSuccess()
        } else {
          router.push('/')
          router.refresh()
        }
      }, 700)
    } else {
      const result = await authClient.signUp.email({ email, password, name })
      setPending(false)
      if (result.error) {
        setError(result.error.message || 'Unable to create account. Please check your details.')
        return
      }
      setSuccess('Account created! Opening your space...')
      setTimeout(() => {
        if (onSuccess) {
          onSuccess()
        } else {
          router.push('/')
          router.refresh()
        }
      }, 900)
    }
  }

  return (
    <div className="auth-card" style={{ position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CompanionMark />
          <strong style={{ color: '#2d5957', fontSize: '14px' }}>BhaavaBot</strong>
        </div>
        {onContinueGuest ? (
          <button
            type="button"
            onClick={onContinueGuest}
            style={{
              border: 0,
              background: 'transparent',
              color: '#338f8c',
              fontSize: '12px',
              fontWeight: 650,
              cursor: 'pointer',
            }}
          >
            Continue as guest →
          </button>
        ) : (
          <Link
            href="/"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              color: '#6e8985',
              fontSize: '12px',
              textDecoration: 'none',
            }}
          >
            <ArrowLeft style={{ width: '13px', height: '13px' }} />
            <span>Companion home</span>
          </Link>
        )}
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '6px',
          padding: '4px',
          borderRadius: '14px',
          background: '#eef5f2',
          marginBottom: '28px',
        }}
      >
        <button
          type="button"
          onClick={() => {
            setMode('sign-in')
            setError('')
            setSuccess('')
          }}
          style={{
            padding: '9px 12px',
            border: 0,
            borderRadius: '10px',
            background: mode === 'sign-in' ? '#fff' : 'transparent',
            color: mode === 'sign-in' ? '#2d5957' : '#79918e',
            fontWeight: mode === 'sign-in' ? 700 : 500,
            fontSize: '12px',
            cursor: 'pointer',
            boxShadow: mode === 'sign-in' ? '0 2px 8px rgba(0,0,0,0.05)' : 'none',
            transition: 'all 0.2s',
          }}
        >
          Sign in
        </button>
        <button
          type="button"
          onClick={() => {
            setMode('sign-up')
            setError('')
            setSuccess('')
          }}
          style={{
            padding: '9px 12px',
            border: 0,
            borderRadius: '10px',
            background: mode === 'sign-up' ? '#fff' : 'transparent',
            color: mode === 'sign-up' ? '#2d5957' : '#79918e',
            fontWeight: mode === 'sign-up' ? 700 : 500,
            fontSize: '12px',
            cursor: 'pointer',
            boxShadow: mode === 'sign-up' ? '0 2px 8px rgba(0,0,0,0.05)' : 'none',
            transition: 'all 0.2s',
          }}
        >
          Create account
        </button>
      </div>

      <p className="eyebrow" style={{ margin: '0 0 6px' }}>
        {mode === 'sign-in' ? 'A FAMILIAR PLACE' : 'YOUR CALM COMPANION'}
      </p>
      <h1>{mode === 'sign-in' ? 'Welcome back.' : 'Create your space.'}</h1>
      <p className="auth-copy">
        {mode === 'sign-in'
          ? 'Sign in to access your saved reflections, books, and private conversations.'
          : 'A private sanctuary to pause, reflect, save books and music, and feel heard.'}
      </p>

      {isSecretKeyConfigured && (
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
            marginBottom: '20px',
            padding: '12px 14px',
            borderRadius: '12px',
            background: '#fff8eb',
            border: '1px solid #fce3b8',
            color: '#9c6500',
            fontSize: '11.5px',
            lineHeight: 1.5,
          }}
        >
          <AlertTriangle style={{ width: '18px', height: '18px', flexShrink: 0, marginTop: '2px', color: '#c47d00' }} />
          <div>
            <strong>Configuration Notice: Secret Key in Browser</strong>
            <p style={{ margin: '3px 0 0' }}>
              Your <code>.env.local</code> has a secret key (<code>sb_secret_...</code>).
              Supabase strictly forbids secret keys in browsers.
              Please copy the <strong>anon (public)</strong> key from your Supabase Dashboard (<em>Project Settings &gt; API</em>) and paste it into <code>.env.local</code>.
            </p>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {mode === 'sign-up' && (
          <label>
            Your Name
            <input
              name="name"
              required
              placeholder="e.g. Alex Morgan"
              autoComplete="name"
            />
          </label>
        )}

        <label>
          Email address
          <input
            name="email"
            type="email"
            required
            placeholder="you@example.com"
            autoComplete="email"
          />
        </label>

        <label>
          Password
          <input
            name="password"
            type="password"
            minLength={6}
            required
            placeholder="At least 6 characters"
            autoComplete={mode === 'sign-in' ? 'current-password' : 'new-password'}
          />
        </label>

        {error && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginTop: '16px',
              padding: '11px 14px',
              borderRadius: '12px',
              background: '#fdf2f2',
              border: '1px solid #f9d6d9',
              color: '#a75d68',
              fontSize: '12px',
            }}
          >
            <AlertCircle style={{ width: '16px', height: '16px', flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginTop: '16px',
              padding: '11px 14px',
              borderRadius: '12px',
              background: '#f0f9f6',
              border: '1px solid #c9ebd9',
              color: '#2d5957',
              fontSize: '12px',
            }}
          >
            <CheckCircle2 style={{ width: '16px', height: '16px', flexShrink: 0 }} />
            <span>{success}</span>
          </div>
        )}

        <button
          type="submit"
          className="auth-submit"
          disabled={pending}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
          }}
        >
          {pending ? (
            'Opening your space…'
          ) : mode === 'sign-in' ? (
            'Sign in to BhaavaBot'
          ) : (
            <>
              <Sparkles style={{ width: '14px', height: '14px' }} />
              Create your account
            </>
          )}
        </button>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            margin: '20px 0 14px',
            color: '#a1b0ad',
            fontSize: '11px',
          }}
        >
          <div style={{ flex: 1, height: '1px', background: '#edf3f0' }} />
          <span>or continue with</span>
          <div style={{ flex: 1, height: '1px', background: '#edf3f0' }} />
        </div>

        <button
          type="button"
          onClick={handleGoogleSignIn}
          disabled={pending}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            width: '100%',
            padding: '12px',
            borderRadius: '11px',
            border: '1px solid #dce9e5',
            background: '#ffffff',
            color: '#2d5957',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
            transition: 'all 0.15s ease',
          }}
        >
          <GoogleIcon />
          <span>Continue with Google</span>
        </button>

        {onContinueGuest && (
          <div style={{ textAlign: 'center', marginTop: '18px' }}>
            <button
              type="button"
              onClick={onContinueGuest}
              style={{
                background: 'transparent',
                border: 0,
                color: '#79918e',
                fontSize: '12px',
                cursor: 'pointer',
                textDecoration: 'underline',
              }}
            >
              Explore without an account (Guest mode)
            </button>
          </div>
        )}
      </form>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          marginTop: '26px',
          paddingTop: '18px',
          borderTop: '1px solid #edf3f0',
          color: '#889f9b',
          fontSize: '11px',
        }}
      >
        <ShieldCheck style={{ width: '13px', height: '13px', color: '#54a99f' }} />
        <span>Protected with Supabase Authentication & encryption</span>
      </div>
    </div>
  )
}
