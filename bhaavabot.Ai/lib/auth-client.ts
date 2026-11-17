'use client'

import { createAuthClient } from 'better-auth/react'

export const client = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_BETTER_AUTH_URL || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000'),
})

export const authClient = {
  signIn: {
    email: async ({ email, password }: { email: string; password: string }) => {
      try {
        const res = await client.signIn.email({ email: email.trim(), password })
        if (res.error) {
          return { data: null, error: { message: res.error.message || 'Failed to sign in' } }
        }
        return { data: res.data, error: null }
      } catch (err: any) {
        return { data: null, error: { message: err?.message || 'Failed to sign in' } }
      }
    },
    google: async () => {
      try {
        const callbackURL = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000'
        const res = await client.signIn.social({
          provider: 'google',
          callbackURL,
        })
        if (res?.error) {
          const msg = res.error.message || (res.error as any).statusText || ''
          let friendly = msg || 'Failed to sign in with Google'
          if (msg.includes('not found') || msg.includes('PROVIDER_NOT_FOUND') || msg.includes('CLIENT_ID') || msg.includes('missing')) {
            friendly = 'Google OAuth keys are not configured properly in .env.local. Please check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.'
          } else if (msg.toLowerCase().includes('password') || msg.toLowerCase().includes('authentication failed') || msg.toLowerCase().includes('database')) {
            friendly = 'Database authentication failed. Please verify your Neon DATABASE_URL credentials.'
          }
          return { data: null, error: { message: friendly } }
        }
        return { data: res?.data, error: null }
      } catch (err: any) {
        return { data: null, error: { message: err?.message || 'Failed to sign in with Google' } }
      }
    },
  },
  signUp: {
    email: async ({
      email,
      password,
      name,
    }: {
      email: string
      password: string
      name?: string
    }) => {
      try {
        const res = await client.signUp.email({
          email: email.trim(),
          password,
          name: name?.trim() || email.split('@')[0],
        })
        if (res.error) {
          return { data: null, error: { message: res.error.message || 'Failed to sign up' } }
        }
        return { data: res.data, error: null }
      } catch (err: any) {
        return { data: null, error: { message: err?.message || 'Failed to sign up' } }
      }
    },
  },
  signOut: async () => {
    try {
      await client.signOut()
    } catch (e) {
      console.warn('Sign out warning:', e)
    }
    window.location.href = '/'
  },
  useSession: () => {
    const session = client.useSession()
    const user = session.data?.user
      ? {
          id: session.data.user.id,
          email: session.data.user.email || undefined,
          name: session.data.user.name || session.data.user.email?.split('@')[0] || 'Explorer',
        }
      : null

    return {
      data: user ? { user } : null,
      isPending: session.isPending,
    }
  },
}
