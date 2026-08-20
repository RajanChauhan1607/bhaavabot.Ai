'use client'

import { FormEvent, useState } from 'react'
import { useRouter } from 'next/navigation'
import { authClient } from '@/lib/auth-client'

export function AuthForm({ mode }: { mode: 'sign-in' | 'sign-up' }) {
  const router = useRouter(); const [error, setError] = useState(''); const [pending, setPending] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) { event.preventDefault(); setPending(true); setError(''); const data = new FormData(event.currentTarget); const result = mode === 'sign-in' ? await authClient.signIn.email({ email: String(data.get('email')), password: String(data.get('password')) }) : await authClient.signUp.email({ email: String(data.get('email')), password: String(data.get('password')), name: String(data.get('name')) }); setPending(false); if (result.error) { setError('We could not complete that request. Please check your details and try again.'); return } router.push('/'); router.refresh() }
  return <form className="auth-card" onSubmit={submit}><div className="auth-mark">•••</div><p className="eyebrow">YOUR CALM COMPANION</p><h1>{mode === 'sign-in' ? 'Welcome back' : 'Create your space'}</h1><p className="auth-copy">{mode === 'sign-in' ? 'Continue your reflections with BhaavaBot.' : 'A private place to pause, reflect, and feel heard.'}</p>{mode === 'sign-up' && <label>Name<input name="name" required placeholder="Alex Morgan" /></label>}<label>Email<input name="email" type="email" required placeholder="you@example.com" /></label><label>Password<input name="password" type="password" minLength={8} required placeholder="At least 8 characters" /></label>{error && <p className="auth-error">{error}</p>}<button className="auth-submit" disabled={pending}>{pending ? 'Opening your space…' : mode === 'sign-in' ? 'Sign in' : 'Create account'}</button><p className="auth-switch">{mode === 'sign-in' ? <>New here? <a href="/sign-up">Create an account</a></> : <>Already have an account? <a href="/sign-in">Sign in</a></>}</p></form>
}
