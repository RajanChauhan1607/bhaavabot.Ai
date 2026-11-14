import { AuthForm } from '@/components/auth-form'

export const metadata = {
  title: 'Create Account · BhaavaBot',
  description: 'Create your private mindful companion space on BhaavaBot.',
}

export default function SignUpPage() {
  return (
    <main className="auth-page">
      <AuthForm mode="sign-up" />
    </main>
  )
}
