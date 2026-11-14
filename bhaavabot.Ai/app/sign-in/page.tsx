import { AuthForm } from '@/components/auth-form'

export const metadata = {
  title: 'Sign In · BhaavaBot',
  description: 'Sign in to your BhaavaBot mindful companion space.',
}

export default function SignInPage() {
  return (
    <main className="auth-page">
      <AuthForm mode="sign-in" />
    </main>
  )
}
