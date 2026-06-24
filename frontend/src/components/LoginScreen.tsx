import type { ReactElement } from 'react'
import { loginUrl } from '../api/client'

const LABELS: Record<string, string> = {
  google: 'Entrar com Google',
  github: 'Entrar com GitHub',
}

const ICONS: Record<string, ReactElement> = {
  google: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.27-4.74 3.27-8.1z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.65l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.11a6.6 6.6 0 0 1 0-4.22V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1A11 11 0 0 0 2.18 7.05l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"
      />
    </svg>
  ),
  github: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 1A11 11 0 0 0 8.52 22.45c.55.1.75-.24.75-.53v-1.86c-3.06.67-3.7-1.47-3.7-1.47-.5-1.28-1.23-1.62-1.23-1.62-1-.68.08-.67.08-.67 1.1.08 1.69 1.14 1.69 1.14.98 1.69 2.58 1.2 3.21.92.1-.71.39-1.2.7-1.47-2.44-.28-5.01-1.22-5.01-5.44 0-1.2.43-2.18 1.13-2.95-.11-.28-.49-1.4.11-2.91 0 0 .93-.3 3.04 1.13a10.5 10.5 0 0 1 5.54 0c2.11-1.43 3.03-1.13 3.03-1.13.6 1.51.22 2.63.11 2.91.71.77 1.13 1.75 1.13 2.95 0 4.23-2.58 5.16-5.03 5.43.4.34.75 1.01.75 2.04v3.02c0 .29.2.64.76.53A11 11 0 0 0 12 1z"
      />
    </svg>
  ),
}

interface LoginScreenProps {
  providers: string[]
}

// Shown only when the server reports auth_enabled and the visitor has no valid
// session. Each button is a top-level navigation to the backend OAuth route
// (not an XHR), so there is no CORS involved.
export default function LoginScreen({ providers }: LoginScreenProps) {
  return (
    <div className="login-screen">
      <div className="login-card">
        <h1 className="brand">
          <span className="brand-dot" aria-hidden="true" />
          Chat com Documentos
        </h1>
        <p className="muted">
          Entre para enviar seus documentos e conversar com eles.
        </p>
        <div className="login-buttons">
          {providers.map((p) => (
            <a key={p} className="login-btn" href={loginUrl(p)}>
              {ICONS[p]}
              {LABELS[p] || `Entrar com ${p}`}
            </a>
          ))}
        </div>
        <small className="muted">
          Seus documentos e conversas ficam visíveis apenas para a sua conta.
        </small>
      </div>
    </div>
  )
}
