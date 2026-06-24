# Chat with Documents via AI — RAG with semantic search on Redis

**🌐 Language:** **English** · [Português (BR)](README.pt-BR.md)

Full-stack application that lets you **upload documents** (PDF/TXT/DOCX) and **chat
with them** using RAG (Retrieval-Augmented Generation): semantic vector search
on Redis + answer generation by an LLM, displaying the sources used.

---

## Architecture

```
┌──────────────┐      ┌──────────────────────┐      ┌──────────────────┐
│  Frontend     │ HTTP │   API (FastAPI)       │      │  Redis Stack      │
│  React + Vite │─────▶│   /upload /chat ...   │─────▶│  RediSearch       │
│  (Nginx)      │ SSE  │   LangGraph RAG       │      │  (HNSW / COSINE)  │
└──────────────┘      └──────────┬───────────┘      └──────────────────┘
                                  │
                                  ▼
                        LLM (OpenAI / Anthropic / Gemini / Ollama)
                        Embeddings (OpenAI / Gemini / Sentence-Transformers)
```

| Layer        | Technology                                   |
|--------------|----------------------------------------------|
| Frontend     | React 18 + Vite, served via Nginx            |
| API          | Python 3.11, FastAPI, LangChain + LangGraph  |
| Vector Store | Redis Stack (RediSearch, HNSW/COSINE index)  |
| LLM          | OpenAI / Anthropic / Gemini / Ollama (configurable) |
| Embeddings   | OpenAI / Gemini / Sentence-Transformers (config.)  |
| Infra        | Docker Compose                               |

---

## How to run (step by step)

The whole project comes up with **a single command** (`docker-compose up --build`).
You **don't need** to install Python, Node or Redis on your machine — only Docker.

### Prerequisites

| Requirement                  | Minimum version | How to check               |
|------------------------------|-----------------|----------------------------|
| Docker                       | 20.10+          | `docker --version`         |
| Docker Compose               | v2 (plugin)     | `docker compose version`   |
| (optional) Ollama on host    | 0.1+            | `ollama --version`         |

> **Docker Compose v1 vs v2:** in newer versions the command is `docker compose`
> (with a space). If you use the old v1, replace it with `docker-compose` (with a
> hyphen). The examples below use `docker compose`.

### Step 1 — Clone and enter the directory

```bash
git clone <repository-url>
cd chat_rag
```

### Step 2 — Create the `.env` file

```bash
cp .env.example .env
```

### Step 3 — Choose the LLM/embeddings provider

The system is **provider-agnostic** (configured via variables in `.env`).
Pick **one** of the paths below and edit `.env` accordingly.

<details open>
<summary><b>Path A — With an API key (simplest and fastest) ⭐</b></summary>

Requires nothing beyond Docker. Just paste your key into `.env`.

**OpenAI:**
```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...        # your key here
```

**Anthropic (Claude LLM) + free local embeddings:**
```env
LLM_PROVIDER=anthropic
EMBEDDING_PROVIDER=sentence-transformers
LLM_MODEL=claude-3-5-sonnet-latest
EMBEDDING_MODEL=all-MiniLM-L6-v2
ANTHROPIC_API_KEY=sk-ant-... # your key here
```

**Google Gemini (has a free tier — LLM + embeddings):**
```env
LLM_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
EMBEDDING_MODEL=models/text-embedding-004
GOOGLE_API_KEY=...           # your key here
```
</details>

<details>
<summary><b>Path B — 100% local and free (Ollama)</b></summary>

Uses no paid API. The **embeddings** run inside the container
(Sentence-Transformers, downloaded automatically on first use). The **LLM**
runs via [Ollama](https://ollama.com) on your host machine:

```bash
# 1. Install Ollama (https://ollama.com/download) and pull a model:
ollama pull llama3

# 2. Make sure Ollama is running (it usually starts on its own):
ollama serve   # if not already active
```

`.env`:
```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=sentence-transformers
LLM_MODEL=llama3
EMBEDDING_MODEL=all-MiniLM-L6-v2
OLLAMA_BASE_URL=http://host.docker.internal:11434
# Required for local embeddings: installs sentence-transformers + torch.
# This makes the API image significantly larger and slower to build.
INSTALL_LOCAL_EMBEDDINGS=true
```

> The default image is **slim** and ships only the API-provider stack. Local
> embeddings (Sentence-Transformers + torch) are an opt-in build extra enabled
> by `INSTALL_LOCAL_EMBEDDINGS=true`, so the heavy dependency is only installed
> when you actually need it.
>
> The `docker-compose.yml` already maps `host.docker.internal` to the host on
> Linux, so the `api` container can reach the Ollama running on your machine.
</details>

### Step 4 — Start the application

```bash
docker compose up --build
```

The first run pulls images and installs dependencies (may take a few minutes).
Once ready, you'll see logs from all 3 services (`redis`, `api`, `frontend`).
To run in the background, use `docker compose up --build -d`.

### Step 5 — Access

| Service                          | URL                            |
|----------------------------------|--------------------------------|
| **Application (Frontend)**       | <http://localhost:3000>        |
| API — Swagger docs               | <http://localhost:8000/docs>   |
| API — health check               | <http://localhost:8000/health> |
| RedisInsight (Redis inspection)  | <http://localhost:8001>        |

### Step 6 — Stop / clean up

```bash
docker compose down       # stop services (keeps Redis data)
docker compose down -v    # stop and DELETE the Redis volume (full reset)
```

> ⚠️ **When changing the embeddings model**, run `docker compose down -v` before
> bringing it up again. The vector index dimension is derived from the model
> (1536 for OpenAI, 384 for `all-MiniLM-L6-v2`); an index created with a
> different dimension is incompatible.

---

## Using the application

1. Open <http://localhost:3000>.
2. **Chat model (optional)**: in the sidebar, pick the LLM provider and paste its
   API key. Skip this if the server already has a key in `.env`, or if you use a
   local provider (Ollama) that needs no key.
3. **Upload**: drag a PDF, TXT or DOCX onto the upload area (or click to select).
   Watch the progress (upload → processing); you can **Cancel** an upload in
   progress — handy for large files.
4. The document appears in the **Documents** list (with the number of indexed
   chunks).
5. **Ask** in the chat field and press **Enter**. The answer appears as a
   **stream** (token by token).
6. Click **Sources** below each answer to see the chunks used.
7. **Multiple conversations**: create/rename/delete sessions in the sidebar
   (double-click the name to rename).
8. Remove a document with the **✕** in the list — the corresponding vectors are
   deleted from Redis.

---

## Quick verification (via terminal)

Confirm the stack is healthy and the end-to-end flow works, without opening the
browser:

```bash
# 1. Health check (should return redis: "connected")
curl http://localhost:8000/health
# {"status":"ok","redis":"connected"}

# 2. Upload a sample document
echo "Third-quarter profit grew 20% compared to Q2." > sample.txt
curl -F "files=@sample.txt" http://localhost:8000/upload
# {"files":[{"file_id":"...","name":"sample.txt","chunks_indexed":1,...}],...}

# 3. List indexed documents
curl http://localhost:8000/documents

# 4. Ask a question (RAG)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What was the Q3 result?","session_id":"demo"}'
# {"answer":"...","sources":[{"chunk":"...","source":"sample.txt","score":0.9}],"session_id":"demo"}

# 5. Streaming (Server-Sent Events)
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Summarize the document","session_id":"demo"}'
```

---

## Troubleshooting

| Symptom                                     | Likely cause / fix                                                                        |
|---------------------------------------------|------------------------------------------------------------------------------------------|
| `/health` returns `redis: "disconnected"`   | The `redis` service is still starting — wait for the healthcheck or check `docker compose logs redis`. |
| Dimension error on upload/chat              | You changed the embeddings model without resetting the index. Run `docker compose down -v` and start again. |
| Chat errors with `LLM_PROVIDER=ollama`      | Ollama is not running or the model wasn't pulled (`ollama pull llama3`). Check `OLLAMA_BASE_URL`. |
| Provider authentication error (500)         | The API key (in `.env` or the sidebar field) is missing/invalid for the selected provider. |
| "No text extracted" on a PDF                | The PDF is scanned/image-only — enable OCR (`INSTALL_OCR=true`, see below) and rebuild.    |
| Upload returns 413 (too large)              | File exceeds the Nginx limit (`client_max_body_size`, default 300M in `frontend/nginx.conf`). |
| Port 3000/8000/6379 already in use          | Stop the conflicting process or adjust the port mapping in `docker-compose.yml`.          |

Useful logs:
```bash
docker compose logs -f api       # API logs
docker compose logs -f           # all services
```

---

## Environment variables

| Variable             | Description                                        | Default                |
|----------------------|----------------------------------------------------|------------------------|
| `LLM_PROVIDER`       | `openai` / `anthropic` / `gemini` / `ollama`       | `ollama`               |
| `EMBEDDING_PROVIDER` | `openai` / `gemini` / `sentence-transformers`      | `sentence-transformers`|
| `LLM_MODEL`          | chat model name                                    | `llama3`               |
| `EMBEDDING_MODEL`    | embeddings model name                              | `all-MiniLM-L6-v2`     |
| `OPENAI_API_KEY`     | OpenAI key (if applicable)                         | —                      |
| `ANTHROPIC_API_KEY`  | Anthropic key (if applicable)                      | —                      |
| `GOOGLE_API_KEY`     | Google Gemini key (if applicable)                  | —                      |
| `OLLAMA_BASE_URL`    | Ollama endpoint                                    | `http://host.docker.internal:11434` |
| `REDIS_URL`          | Redis URL (auto in compose)                        | `redis://localhost:6379` |
| `CHUNK_SIZE`         | chunk size (tokens)                                | `500`                  |
| `CHUNK_OVERLAP`      | overlap between chunks                             | `50`                   |
| `TOP_K`              | number of chunks retrieved per question            | `5`                    |
| `EF_RUNTIME`         | HNSW search breadth (higher = better recall)       | `128`                  |
| `HISTORY_SIZE`       | number of messages kept per session                | `6`                    |
| `INSTALL_LOCAL_EMBEDDINGS` | build flag: install Sentence-Transformers + torch | `false`           |
| `INSTALL_OCR`        | build flag: install OCR stack for scanned PDFs      | `false`                |
| `OCR_LANGUAGE`       | Tesseract languages (`+`-separated)                | `por+eng`              |
| `OCR_DPI`            | render DPI used for OCR                             | `200`                  |
| `AUTH_ENABLED`       | require Google/GitHub login (production)            | `false`                |
| `BACKEND_URL`        | public backend URL (for OAuth redirect URIs)       | —                      |
| `FRONTEND_URL`       | where to return after login                         | `/`                    |
| `SESSION_SECRET`     | signs the login token (change in production)        | `dev-insecure-…`       |
| `GOOGLE_OAUTH_CLIENT_ID` / `..._SECRET` | Google OAuth app credentials    | —                      |
| `GITHUB_OAUTH_CLIENT_ID` / `..._SECRET` | GitHub OAuth app credentials    | —                      |

### Authentication / login (optional)

Login is **off by default**: running locally needs no accounts — just start it
and use it. For a **public deployment** set `AUTH_ENABLED=true` and visitors must
sign in with **Google or GitHub**; each user then only sees **their own**
documents and conversations (data is tagged per user). This is independent of
BYOK — the LLM key in the sidebar still works the same way.

How it works: the OAuth handshake happens on the backend (Authlib); on success
the backend issues a **signed token** and redirects back to the UI, which stores
it and sends it as `Authorization: Bearer` on every request. The API stays
stateless (no cross-site cookies).

**Enabling it (production):**

1. **Create the OAuth apps** and register the callback URLs:
   - Google — [Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
     → *OAuth client ID* (type *Web*). Authorized redirect URI:
     `<BACKEND_URL>/auth/callback/google`
   - GitHub — [Settings → Developer settings → OAuth Apps](https://github.com/settings/developers)
     → *New OAuth App*. Authorization callback URL:
     `<BACKEND_URL>/auth/callback/github`
2. Set `AUTH_ENABLED=true`, `BACKEND_URL`, `FRONTEND_URL`, a strong
   `SESSION_SECRET`, and the four `*_OAUTH_*` values.
3. Redeploy. The UI now shows a login screen until the user signs in.

### Chat provider + API key (bring-your-own-key)

The frontend sidebar lets each visitor **pick the chat LLM provider** (from the
server's `supported_llm_providers`, see `/config`) and **paste that provider's
key**. They are sent per request as `X-LLM-Provider` and `X-API-Key`, overriding
the server config for that request only (the key is stored just in the browser).

Keys can also come from the **server `.env`** (`OPENAI_API_KEY` /
`ANTHROPIC_API_KEY` / `GOOGLE_API_KEY`), which is the fallback when no header is
sent — convenient for local runs. This makes a public deploy possible **without
shipping any key**: each visitor brings their own.

> **Embeddings stay fixed on the server** (provider + model). Only the **chat
> LLM** is per-request, because the Redis vector index dimension is set by the
> embedding model and must stay consistent across all documents and queries.

### Scanned PDFs (OCR)

PDFs **with a text layer** and TXT work out of the box. **Scanned / image-only
PDFs** have no extractable text, so ingestion needs OCR. OCR is an opt-in build
extra (keeps the default image small):

```env
# .env
INSTALL_OCR=true
```
```bash
docker compose up --build   # rebuilds the API image with Tesseract + PyMuPDF
```

Without it, uploading a scanned PDF returns a clear error instead of indexing an
empty document. Note: OCR is **slow** for large documents (it renders and reads
every page), so expect long processing times on big scanned files.

---

## API endpoints

| Method | Route                 | Description                                |
|--------|-----------------------|--------------------------------------------|
| POST   | `/upload`             | Receives file(s) and triggers ingestion    |
| GET    | `/documents`          | Lists indexed documents                    |
| DELETE | `/documents/{id}`     | Removes a document and its vectors         |
| POST   | `/chat`               | Question + RAG answer with sources         |
| POST   | `/chat/stream`        | Same as `/chat`, with SSE streaming        |
| GET    | `/health`             | Health check (status + Redis connectivity) |
| GET    | `/config`             | Configured providers + whether an API key is required |

Example `POST /chat`:
```json
{ "question": "What were the main Q3 results?", "session_id": "abc-123", "top_k": 5 }
```
```json
{
  "answer": "The main Q3 results were...",
  "sources": [{ "chunk": "...", "source": "report_q3.pdf", "score": 0.91 }],
  "session_id": "abc-123"
}
```

---

## RAG pipeline with LangGraph

The flow is orchestrated by a LangGraph graph (`app/services/rag_graph.py`) with
four nodes, instead of a simple chain — which makes the flow explicit and easy
to extend with validation, retry or conditional branching:

```
retriever_node → context_builder_node → llm_node → response_formatter_node
```

1. **retriever_node** — embeds the question and runs a KNN search on Redis.
2. **context_builder_node** — builds the prompt from the retrieved context and
   the session history.
3. **llm_node** — calls the configured LLM with the assembled prompt.
4. **response_formatter_node** — formats the final response, including sources.

Streaming (`/chat/stream`) reuses the retrieval/context nodes and streams the
LLM tokens over SSE.

---

## Tests

Suite built with `pytest`, mocking Redis (`fakeredis`), embeddings and the LLM —
**no real API calls**. Current coverage: **100%** of the backend (`pytest` fails
automatically if coverage drops below the 95% threshold).

**Option 1 — via Docker (no Python install):**
```bash
make test
```

**Option 2 — locally (requires Python 3.11+):**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                 # or: make test-local (from the repo root)
```

The pytest configuration (including `--cov` and the 95% threshold) lives in
`backend/pyproject.toml`.

Structure:
```
backend/tests/
├── conftest.py                   # fixtures: redis/llm/embeddings mocks, TestClient
├── test_ingestion.py             # chunking, PDF/TXT/DOCX extraction, OCR fallback
├── test_api_upload.py            # POST /upload
├── test_api_chat.py              # POST /chat and /chat/stream (RAG, BYOK headers)
├── test_api_documents.py         # GET and DELETE /documents
├── test_factories.py             # LLM/embedding provider factories (all providers)
├── test_redis_client.py          # connection, ping, index creation
├── test_retriever.py             # KNN result parsing
├── test_main.py                  # lifespan, /health, /config
├── test_auth.py                  # OAuth login, tokens, user isolation gate
├── test_misc.py                  # config, history, small edge cases
└── test_retriever_integration.py # real Redis Stack (opt-in, `-m integration`)
```

---

## Architecture decisions and trade-offs

- **Configurable provider (OpenAI/Anthropic/Gemini/Ollama):** factories in
  `llm.py` and `embeddings.py` decouple the rest of the code from the vendor.
  Lets you run 100% local and free (Ollama) or with paid/free APIs, by switching
  one env var — and the visitor can override the chat LLM per request (BYOK).
- **LangGraph instead of a simple chain:** more control and extensibility of the
  RAG flow (future validation/retry/branching nodes).
- **HNSW + COSINE index:** good balance between speed and quality for semantic
  similarity search; dimension derived from the embeddings model.
- **Chunk as a Redis HASH** (`doc:{file_id}:chunk:{n}`): metadata (source,
  chunk_index, uploaded_at) lives next to the vector, simplifying listing and
  deletion by `file_id`.
- **Per-session history in Redis** (list capped by `HISTORY_SIZE`): short-term
  context with no dependency on in-memory API state.
- **Streaming via SSE** with `fetch` on the frontend (POST), `proxy_buffering off`
  in Nginx for token-by-token delivery.
- **Optional auth via one code path:** every operation is scoped to a `user_id`
  (a fixed public id when login is off, the OAuth identity when on). The same
  ingestion/retrieval/history code runs in both modes; the retriever simply adds
  a `@user_id` pre-filter to the KNN query. Token-based (no cross-site cookies),
  so the API stays stateless and works across split frontend/backend domains.

---

## Repository structure

```
chat_rag/
├── backend/        # FastAPI + LangGraph + RAG services + tests
├── frontend/       # React + Vite (Nginx in production)
├── .github/workflows/ci.yml   # CI: pytest + frontend build
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md       # English (this file)
└── README.pt-BR.md # Portuguese
```

---

## Implemented differentials

- ✅ **Response streaming** (Server-Sent Events).
- ✅ **RAG pipeline with LangGraph** (instead of a simple chain).
- ✅ **Multiple chat sessions** with custom names on the frontend.
- ✅ **CI with GitHub Actions** (tests + build on every push).
- ✅ **Multi-file support** on upload.
- ✅ **DOCX support** (in addition to the required PDF/TXT).
- ✅ **OCR for scanned PDFs** (opt-in build, Tesseract).
- ✅ **Document removal** with cleanup of the corresponding vectors in Redis.
- ✅ **Bring-your-own-key + per-request LLM provider** chosen in the UI.
- ✅ **Google Gemini** provider (LLM + embeddings), incl. a free-tier path.
- ✅ **Cancelable uploads** and 100% backend test coverage.
- ✅ **Optional Google/GitHub login** with per-user document/conversation
  isolation (off locally, on in production).
