import { loginUrl } from '../api/client'

const LABELS = {
  google: 'Entrar com Google',
  github: 'Entrar com GitHub',
}

// Shown only when the server reports auth_enabled and the visitor has no valid
// session. Each button is a top-level navigation to the backend OAuth route
// (not an XHR), so there is no CORS involved.
export default function LoginScreen({ providers }) {
  return (
    <div className="login-screen">
      <div className="login-card">
        <h1 className="brand">Chat com Documentos</h1>
        <p className="muted">Faça login para enviar documentos e conversar com eles.</p>
        <div className="login-buttons">
          {providers.map((p) => (
            <a key={p} className="login-btn" href={loginUrl(p)}>
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
