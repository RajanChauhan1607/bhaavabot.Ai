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
        const callbackURL = typeof window !== 'undefined' && window.location.origin.includes('vercel.app')
          ? 'https://bhaavabot.vercel.app'
          : (typeof window !== 'undefined' ? window.location.origin : 'https://bhaavabot.vercel.app')

        // Direct navigation to Google OAuth initiation endpoint
        // This avoids popup blockers and WebView iframe interception issues
        const signinEndpoint = `${process.env.NEXT_PUBLIC_BETTER_AUTH_URL || 'https://bhaavabot.vercel.app'}/api/auth/sign-in/social`
        
        const response = await fetch(signinEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: 'google',
            callbackURL,
          }),
        })

        const data = await response.json()
        if (data?.url) {
          window.location.href = data.url
          return { data: { url: data.url }, error: null }
        }

        // Fallback to client method
        const res = await client.signIn.social({
          provider: 'google',
          callbackURL,
        })
        if (res?.error) {
          const msg = res.error.message || (res.error as any).statusText || ''
          return { data: null, error: { message: msg || 'Failed to sign in with Google' } }
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
