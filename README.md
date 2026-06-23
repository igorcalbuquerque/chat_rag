# Chat with Documents via AI — RAG with semantic search on Redis

**🌐 Language:** **English** · [Português (BR)](README.pt-BR.md)

Full-stack application that lets you **upload documents** (PDF/TXT) and **chat
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
                        LLM (OpenAI / Anthropic / Ollama)
                        Embeddings (OpenAI / Sentence-Transformers)
```

| Layer        | Technology                                   |
|--------------|----------------------------------------------|
| Frontend     | React 18 + Vite, served via Nginx            |
| API          | Python 3.11, FastAPI, LangChain + LangGraph  |
| Vector Store | Redis Stack (RediSearch, HNSW/COSINE index)  |
| LLM          | OpenAI / Anthropic / Ollama (configurable)   |
| Embeddings   | OpenAI / Sentence-Transformers (configurable)|
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
</details>

<details>
<summary><b>Path B — 100% local and free (Ollama) — this is the `.env.example` default</b></summary>

Uses no paid API. The **embeddings** run inside the container
(Sentence-Transformers, downloaded automatically on first use). The **LLM**
runs via [Ollama](https://ollama.com) on your host machine:

```bash
# 1. Install Ollama (https://ollama.com/download) and pull a model:
ollama pull llama3

# 2. Make sure Ollama is running (it usually starts on its own):
ollama serve   # if not already active
```

`.env` (already the default in `.env.example`):
```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=sentence-transformers
LLM_MODEL=llama3
EMBEDDING_MODEL=all-MiniLM-L6-v2
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

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
2. **Upload**: drag a PDF or TXT onto the upload area (or click to select).
   Watch the ingestion progress bar.
3. The document appears in the **Documents** list (with the number of indexed
   chunks).
4. **Ask** in the chat field and press **Enter**. The answer appears as a
   **stream** (token by token).
5. Click **Sources** below each answer to see the chunks used.
6. **Multiple conversations**: create/rename/delete sessions in the sidebar
   (double-click the name to rename).
7. Remove a document with the **✕** in the list — the corresponding vectors are
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
| OpenAI/Anthropic authentication error       | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` missing or invalid in `.env`.                      |
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
| `LLM_PROVIDER`       | `openai` / `anthropic` / `ollama`                  | `ollama`               |
| `EMBEDDING_PROVIDER` | `openai` / `sentence-transformers`                 | `sentence-transformers`|
| `LLM_MODEL`          | chat model name                                    | `llama3`               |
| `EMBEDDING_MODEL`    | embeddings model name                              | `all-MiniLM-L6-v2`     |
| `OPENAI_API_KEY`     | OpenAI key (if applicable)                         | —                      |
| `ANTHROPIC_API_KEY`  | Anthropic key (if applicable)                      | —                      |
| `OLLAMA_BASE_URL`    | Ollama endpoint                                    | `http://host.docker.internal:11434` |
| `REDIS_URL`          | Redis URL (auto in compose)                        | `redis://localhost:6379` |
| `CHUNK_SIZE`         | chunk size (characters)                            | `500`                  |
| `CHUNK_OVERLAP`      | overlap between chunks                             | `50`                   |
| `TOP_K`              | number of chunks retrieved per question            | `5`                    |
| `HISTORY_SIZE`       | number of messages kept per session                | `6`                    |

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
**no real API calls**. Current coverage: **~83%** of the backend (minimum
required: 60%; `pytest` fails automatically if coverage drops below that).

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

The pytest configuration (including `--cov` and the 60% threshold) lives in
`backend/pyproject.toml`.

Structure:
```
backend/tests/
├── conftest.py            # fixtures: redis mock, llm mock, embeddings mock, TestClient
├── test_ingestion.py      # chunking, embeddings, Redis indexing
├── test_api_upload.py     # POST /upload
├── test_api_chat.py       # POST /chat and /chat/stream (RAG pipeline)
└── test_api_documents.py  # GET and DELETE /documents
```

---

## Architecture decisions and trade-offs

- **Configurable provider (OpenAI/Anthropic/Ollama):** factories in `llm.py` and
  `embeddings.py` decouple the rest of the code from the vendor. Lets you run
  100% local and free (Ollama) or with paid APIs, by switching one env var.
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
- ✅ **Document removal** with cleanup of the corresponding vectors in Redis.
