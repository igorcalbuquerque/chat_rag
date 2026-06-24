# Checklist de Deploy — Render (free tier) + Redis Cloud

Deploy gratuito com **login Google/GitHub** e **BYOK** (nenhuma chave de IA no
servidor). Dois serviços (definidos em `render.yaml`): `chat-rag-api` (backend) e
`chat-rag-web` (frontend estático). O Redis é externo (Redis Cloud).

> Ordem importa: as OAuth apps precisam das URLs públicas, que só existem **depois**
> do 1º deploy. Por isso: sobe tudo → anota URLs → cria OAuth apps → preenche
> segredos → redeploy.

URLs esperadas (a Render gera a partir do nome do serviço):
- Backend: `https://chat-rag-api.onrender.com`
- Frontend: `https://chat-rag-web.onrender.com`

---

## 0. Pré-requisitos
- [ ] Código no GitHub (repositório que a Render vai ler).
- [ ] Conta na [Render](https://render.com) e na [Redis Cloud](https://redis.io/cloud/).
- [ ] `render.yaml` presente na raiz (já está).

## 1. Redis Cloud (free 30 MB **com módulo Search**)
- [ ] Criar um database free. **Importante:** habilitar o módulo **RediSearch/Search**
      (KNN não funciona sem ele).
- [ ] Copiar a connection string TLS: `rediss://default:<senha>@<host>:<porta>`.
- [ ] Guardar para usar como `REDIS_URL` (etapa 4).

## 2. Primeiro deploy (cria os serviços e revela as URLs)
- [ ] Na Render: **New → Blueprint** → apontar para o repo → ela lê o `render.yaml`.
- [ ] Aplicar. Os dois serviços começam a buildar. (Vão subir mesmo sem os
      segredos ainda — o login só funciona após a etapa 4.)
- [ ] Anotar as URLs reais de `chat-rag-api` e `chat-rag-web` (confirmar se batem
      com as esperadas acima; se renomeou, use as reais nas próximas etapas).

## 3. Criar as OAuth apps
**Google** — [Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
- [ ] OAuth consent screen: tipo **External**; em *Test users*, adicionar os emails
      que poderão entrar (enquanto o app estiver em "Testing").
- [ ] **Create Credentials → OAuth client ID → Web application**.
- [ ] Authorized redirect URI (idêntico, sem barra final):
      `https://chat-rag-api.onrender.com/auth/callback/google`
- [ ] Copiar **Client ID** e **Client Secret**.

**GitHub** — [Settings → Developer settings → OAuth Apps](https://github.com/settings/developers)
- [ ] **New OAuth App**.
- [ ] Homepage URL: `https://chat-rag-web.onrender.com`
- [ ] Authorization callback URL:
      `https://chat-rag-api.onrender.com/auth/callback/github`
- [ ] Copiar **Client ID** e gerar/copiar **Client Secret**.

## 4. Variáveis de ambiente na Render
Gerar um segredo forte:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Serviço `chat-rag-api`** (Environment) — preencher os `sync: false`:
- [ ] `REDIS_URL` = string TLS do Redis Cloud (etapa 1)
- [ ] `AUTH_ENABLED` = `true`
- [ ] `BACKEND_URL` = `https://chat-rag-api.onrender.com`
- [ ] `FRONTEND_URL` = `https://chat-rag-web.onrender.com`
- [ ] `SESSION_SECRET` = segredo gerado acima
- [ ] `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`
- [ ] `GITHUB_OAUTH_CLIENT_ID` / `GITHUB_OAUTH_CLIENT_SECRET`
- (já no `render.yaml`, não precisa mexer: `LLM_PROVIDER`, `EMBEDDING_PROVIDER`,
  `LLM_MODEL`, `EMBEDDING_MODEL`, `PYTHON_VERSION`)
- (NÃO definir `OPENAI_API_KEY` — é BYOK: a chave vem da UI por requisição)

**Serviço `chat-rag-web`**:
- [ ] `VITE_API_BASE_URL` = `https://chat-rag-api.onrender.com`  ← **sem `/api`**

## 5. Redeploy
- [ ] Backend: salvar as envs já dispara redeploy.
- [ ] Frontend: **Manual Deploy → Clear build cache & deploy** (o `VITE_API_BASE_URL`
      entra **no build**; sem rebuild ele não pega).

## 6. Verificação pós-deploy
- [ ] `curl https://chat-rag-api.onrender.com/health` → `{"status":"ok","redis":"connected"}`
- [ ] `curl https://chat-rag-api.onrender.com/config` → `"auth_enabled":true` e
      `"auth_providers":["google","github"]`
- [ ] Abrir `https://chat-rag-web.onrender.com` → aparece a **tela de login**.
- [ ] Entrar com **Google** e depois com **GitHub** → nome no canto + botão **Sair**.
- [ ] Colar a chave do LLM (BYOK) na barra lateral, subir um PDF/DOCX/TXT, perguntar
      → resposta com **fontes**.
- [ ] **Isolamento**: logar com outra conta → não vê os documentos da primeira.

## 7. Pós-go-live (opcional)
- [ ] Google: publicar o consent screen (sair de "Testing") para liberar além dos
      test users.
- [ ] Anotar o link do app no `README` (fecha o diferencial "deploy em nuvem").

---

## Troubleshooting
| Sintoma | Causa provável / correção |
|---|---|
| `redirect_uri_mismatch` (Google) | O callback registrado difere de `BACKEND_URL` + `/auth/callback/google`. Tem que ser **idêntico** (mesmo `https`, sem barra final). |
| GitHub "redirect URI mismatch" | Mesmo motivo no callback do GitHub. |
| Google "Access blocked / app not verified" | Consent em "Testing": só *Test users* entram. Adicione o email ou publique o app. |
| Login abre mas volta deslogado | `SESSION_SECRET` diferente entre deploys, ou `FRONTEND_URL` errado (o callback redireciona pra lugar errado). |
| Busca não retorna nada | Redis Cloud **sem o módulo Search**, ou documentos indexados antes de existir o campo `user_id` (re-suba os arquivos). |
| Chat dá erro 500 de auth do provider | Chave do LLM (BYOK na UI) ausente/ inválida para o provider escolhido. |
| Upload 413 | Arquivo acima do limite do proxy. No deploy estático da Render isso não se aplica; localmente é o `client_max_body_size` do Nginx (300M). |
| 1ª requisição lenta (~30–60s) | Cold start do free tier (o serviço hiberna). Normal. |
| Mudou o nome do serviço/URL | Atualize `BACKEND_URL`, `FRONTEND_URL`, `VITE_API_BASE_URL` **e** os callbacks nas duas OAuth apps. |

## Rodar local (sem login) — referência rápida
Login é **opcional**: localmente, deixe `AUTH_ENABLED` ausente/`false` e rode
`docker compose up --build`. App aberto, sem tela de login. Para testar o login
localmente, veja a seção de autenticação no `README` (precisa de OAuth apps com
callback em `http://localhost:8000/...`).
