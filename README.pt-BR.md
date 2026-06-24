# 💬 Chat com Documentos via IA — RAG com busca semântica em Redis

**🌐 Idioma:** [English](README.md) · **Português (BR)**

> Faça upload dos seus documentos (**PDF / TXT / DOCX**) e **converse com eles**. A
> aplicação encontra os trechos mais relevantes com **busca vetorial semântica no
> Redis** e um LLM escreve a resposta **citando exatamente as fontes** que usou —
> isso é **RAG (Retrieval-Augmented Generation)**.

**🚀 Demo em produção:** <https://chat-rag-web.onrender.com>

> Hospedado no plano gratuito do Render, então a **primeira** requisição pode
> levar ~30–60s para acordar os serviços. Depois disso fica rápido.

---

## 📑 Índice

1. [Telas](#-telas)
2. [Início rápido (TL;DR)](#-início-rápido-tldr) — rodando em 3 comandos
3. [O que dá para fazer](#-o-que-dá-para-fazer)
4. [Arquitetura](#-arquitetura)
5. [Rodar localmente — passo a passo](#-rodar-localmente--passo-a-passo)
6. [Usando a aplicação](#-usando-a-aplicação)
7. [Verificar que funciona (terminal)](#-verificar-que-funciona-terminal)
8. [Variáveis de ambiente](#-variáveis-de-ambiente)
9. [Endpoints da API](#-endpoints-da-api)
10. [Pipeline RAG (LangGraph)](#-pipeline-rag-langgraph)
11. [Testes](#-testes)
12. [Decisões de arquitetura & trade-offs](#-decisões-de-arquitetura--trade-offs)
13. [Solução de problemas](#-solução-de-problemas)
14. [Estrutura do repositório](#-estrutura-do-repositório)
15. [Diferenciais & cobertura dos requisitos](#-diferenciais--cobertura-dos-requisitos)

---

## 📸 Telas

**Login**

![Tela de login](utils/1.Login.png)

> A tela de login só aparece no ambiente de **produção**
> (<https://chat-rag-web.onrender.com>), onde a autenticação está habilitada para
> que cada usuário veja apenas **seus próprios** documentos e conversas. Ao rodar
> localmente com `docker compose up`, a autenticação vem **desligada por padrão**
> — você vai direto para a tela inicial, sem necessidade de login.

**Tela inicial**

![Tela inicial](utils/2.Tela_Inicial.png)

---

## ⚡ Início rápido (TL;DR)

Você só precisa de **Docker**. Nada além disso — sem Python, Node ou Redis na sua
máquina.

```bash
git clone <url-do-repositório> && cd chat_rag   # 1. baixe o código
cp .env.example .env                             # 2. crie sua config (já funciona para LLM local)
docker compose up --build                        # 3. construa e rode tudo
```

Depois abra **<http://localhost:3000>** 🎉

> 💡 A config padrão roda **100% local e grátis** via [Ollama](https://ollama.com)
> (é preciso ter o Ollama rodando na sua máquina — veja a [Opção B](#opção-b--100-local-e-grátis-ollama)).
> Prefere o caminho mais simples? Basta colar uma chave de API no `.env` — veja a
> [Opção A](#opção-a--com-chave-de-api-mais-simples--rápido-).

Toda a stack sobe com **um único comando** — exatamente como o desafio exige
(`docker compose up --build`).

---

## ✨ O que dá para fazer

- 📤 **Upload** de PDF, TXT ou DOCX (drag-and-drop ou seletor, vários arquivos de uma vez).
- 🔎 O texto é **dividido em chunks, vetorizado e indexado** para busca semântica no Redis.
- 💬 **Pergunte** e receba respostas **transmitidas token a token**, cada uma
  exibindo as **fontes** em que se baseou.
- 🗂️ Gerencie **múltiplas sessões de chat** (criar, renomear, excluir).
- 🧹 **Exclua um documento** e seus vetores são removidos do Redis.
- 🔌 **Troque o provedor de LLM/embeddings** (OpenAI, Anthropic, Gemini, Ollama)
  com uma variável de ambiente — ou deixe cada visitante **usar a própria chave**
  pela interface.

---

## 🏗️ Arquitetura

```
┌──────────────┐      ┌──────────────────────┐      ┌──────────────────┐
│  Frontend     │ HTTP │   API (FastAPI)       │      │  Redis Stack      │
│  React + Vite │─────▶│   /upload /chat ...   │─────▶│  RediSearch       │
│  (Nginx)      │ SSE  │   LangGraph RAG       │◀─────│  (HNSW / COSINE)  │
└──────────────┘      └──────────┬───────────┘      └──────────────────┘
                                  │
                                  ▼
                  LLM         (OpenAI / Anthropic / Gemini / Ollama)
                  Embeddings  (OpenAI / Gemini / Sentence-Transformers)
```

| Camada       | Tecnologia                                            |
|--------------|-------------------------------------------------------|
| Frontend     | React 18 + TypeScript + Vite, servido via Nginx       |
| API          | Python 3.11, FastAPI, LangChain + LangGraph           |
| Vector Store | Redis Stack (RediSearch, índice HNSW / COSINE)        |
| LLM          | OpenAI / Anthropic / Gemini / Ollama (configurável)   |
| Embeddings   | OpenAI / Gemini / Sentence-Transformers (configurável)|
| Infra        | Docker Compose                                        |

---

## 🛠️ Rodar localmente — passo a passo

Esta seção é propositalmente **à prova de erros**: siga de cima a baixo e vai
funcionar. A única coisa que você instala é o **Docker**.

### Pré-requisitos

| Requisito                  | Versão mínima | Como verificar           |
|----------------------------|---------------|--------------------------|
| Docker                     | 20.10+        | `docker --version`       |
| Docker Compose             | v2 (plugin)   | `docker compose version` |
| (opcional) Ollama no host  | 0.1+          | `ollama --version`       |

> **`docker compose` vs `docker-compose`:** o Docker moderno usa
> `docker compose` (com espaço). Se você estiver na v1 antiga, use
> `docker-compose` (com hífen) — ambos fazem a mesma coisa.

### Passo 1 — Clone o repositório

```bash
git clone <url-do-repositório>
cd chat_rag
```

### Passo 2 — Crie seu `.env`

```bash
cp .env.example .env
```

Esse arquivo guarda suas configurações e chaves. **Ele está no `.gitignore`** —
suas chaves nunca são commitadas.

### Passo 3 — Escolha um provedor (escolha UMA opção)

A aplicação é **agnóstica de provedor**: você decide quem gera os embeddings e as
respostas, só editando o `.env`.

#### Opção A — Com chave de API (mais simples & rápido) ⭐

Nada para instalar além do Docker. Cole sua chave e pronto.

<details open>
<summary><b>OpenAI</b></summary>

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...          # 👈 sua chave aqui
```
</details>

<details>
<summary><b>Anthropic (Claude) + embeddings locais grátis</b></summary>

```env
LLM_PROVIDER=anthropic
EMBEDDING_PROVIDER=sentence-transformers
LLM_MODEL=claude-3-5-sonnet-latest
EMBEDDING_MODEL=all-MiniLM-L6-v2
ANTHROPIC_API_KEY=sk-ant-...   # 👈 sua chave aqui
INSTALL_LOCAL_EMBEDDINGS=true  # embeddings rodam local → ative o extra pesado
```
</details>

<details>
<summary><b>Google Gemini (tem free tier — LLM + embeddings)</b></summary>

```env
LLM_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
EMBEDDING_MODEL=models/text-embedding-004
GOOGLE_API_KEY=...             # 👈 sua chave aqui
```
</details>

#### Opção B — 100% local e grátis (Ollama)

Sem API paga. Os **embeddings** rodam dentro do container (Sentence-Transformers,
baixados no primeiro uso). O **LLM** roda via [Ollama](https://ollama.com) na sua
máquina host:

```bash
# 1. Instale o Ollama (https://ollama.com/download) e baixe um modelo:
ollama pull llama3

# 2. Garanta que o Ollama está rodando (normalmente sobe sozinho):
ollama serve        # só se ainda não estiver ativo
```

`.env`:
```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=sentence-transformers
LLM_MODEL=llama3
EMBEDDING_MODEL=all-MiniLM-L6-v2
OLLAMA_BASE_URL=http://host.docker.internal:11434
INSTALL_LOCAL_EMBEDDINGS=true   # instala sentence-transformers + torch (imagem maior)
```

> A imagem padrão é **slim** (apenas a stack de provedores via API). Embeddings
> locais (Sentence-Transformers + torch) são um extra opt-in ativado por
> `INSTALL_LOCAL_EMBEDDINGS=true`, então só são instalados quando você precisa.
> O `docker-compose.yml` já mapeia `host.docker.internal` no Linux, para o
> container `api` alcançar o Ollama da sua máquina.

### Passo 4 — Suba tudo

```bash
docker compose up --build
```

O primeiro run baixa imagens e instala dependências (alguns minutos). Quando
estiver pronto, você verá os logs dos **3 serviços** (`redis`, `api`,
`frontend`). Acrescente `-d` para rodar em segundo plano:
`docker compose up --build -d`.

### Passo 5 — Acesse

| O quê                           | URL                            |
|---------------------------------|--------------------------------|
| **Aplicação (Frontend)**        | <http://localhost:3000>        |
| API — docs Swagger              | <http://localhost:8000/docs>   |
| API — health check              | <http://localhost:8000/health> |
| RedisInsight (inspecionar Redis)| <http://localhost:8001>        |

### Passo 6 — Parar / resetar

```bash
docker compose down       # para os serviços (mantém os dados do Redis)
docker compose down -v    # para E apaga o volume do Redis (reset total)
```

> ⚠️ **Vai trocar o modelo de embeddings?** Rode `docker compose down -v` antes. A
> dimensão do índice vetorial vem do modelo (1536 para OpenAI, 384 para
> `all-MiniLM-L6-v2`); um índice criado com outra dimensão é incompatível.

---

## 🖱️ Usando a aplicação

1. Abra <http://localhost:3000>.
2. **Modelo de chat (opcional):** na barra lateral, escolha o provedor de LLM e
   cole a chave dele. Pule isso se o servidor já tem chave no `.env`, ou se você
   usa um provedor local sem chave (Ollama).
3. **Upload:** arraste um PDF / TXT / DOCX para a área de upload (ou clique para
   selecionar). Acompanhe o progresso (envio → processamento). Você pode
   **Cancelar** um upload em andamento — útil para arquivos grandes.
4. O arquivo aparece na lista de **Documentos** com o número de chunks indexados.
5. **Pergunte** no campo de chat e pressione **Enter**. A resposta vem em
   **streaming**, token a token.
6. Clique em **Fontes** abaixo de qualquer resposta para ver os trechos usados.
7. **Múltiplas conversas:** crie / renomeie / exclua sessões na barra lateral
   (duplo clique no nome para renomear).
8. Remova um documento com o **✕** na lista — seus vetores são apagados do Redis.

---

## ✅ Verificar que funciona (terminal)

Confirme o fluxo de ponta a ponta sem abrir o navegador:

```bash
# 1. Health check (espera-se redis: "connected")
curl http://localhost:8000/health
# {"status":"ok","redis":"connected"}

# 2. Upload de um documento de exemplo
echo "O lucro do terceiro trimestre cresceu 20% em relação ao Q2." > exemplo.txt
curl -F "files=@exemplo.txt" http://localhost:8000/upload
# {"files":[{"file_id":"...","name":"exemplo.txt","chunks_indexed":1,...}],...}

# 3. Listar documentos indexados
curl http://localhost:8000/documents

# 4. Fazer uma pergunta (RAG)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Qual foi o resultado do Q3?","session_id":"demo"}'
# {"answer":"...","sources":[{"chunk":"...","source":"exemplo.txt","score":0.9}],"session_id":"demo"}

# 5. Resposta em streaming (Server-Sent Events)
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Resuma o documento","session_id":"demo"}'
```

---

## ⚙️ Variáveis de ambiente

Referência completa — cada variável, o que faz e seu padrão. No dia a dia você só
mexe nas de provedor, do [Passo 3](#passo-3--escolha-um-provedor-escolha-uma-opção).

| Variável                                | Descrição                                          | Padrão                               |
|-----------------------------------------|----------------------------------------------------|--------------------------------------|
| `LLM_PROVIDER`                          | `openai` / `anthropic` / `gemini` / `ollama`       | `ollama`                             |
| `EMBEDDING_PROVIDER`                    | `openai` / `gemini` / `sentence-transformers`      | `sentence-transformers`              |
| `LLM_MODEL`                             | nome do modelo de chat                             | `llama3`                             |
| `EMBEDDING_MODEL`                       | nome do modelo de embeddings                       | `all-MiniLM-L6-v2`                   |
| `OPENAI_API_KEY`                        | chave OpenAI (se aplicável)                        | —                                    |
| `ANTHROPIC_API_KEY`                     | chave Anthropic (se aplicável)                     | —                                    |
| `GOOGLE_API_KEY`                        | chave Google Gemini (se aplicável)                 | —                                    |
| `OLLAMA_BASE_URL`                       | endpoint do Ollama                                 | `http://host.docker.internal:11434`  |
| `REDIS_URL`                             | URL do Redis (definida automaticamente no compose) | `redis://localhost:6379`             |
| `CHUNK_SIZE`                            | tamanho do chunk (tokens)                          | `500`                                |
| `CHUNK_OVERLAP`                         | sobreposição entre chunks (tokens)                 | `50`                                 |
| `TOP_K`                                 | chunks recuperados por pergunta                    | `5`                                  |
| `EF_RUNTIME`                            | amplitude de busca HNSW (maior = melhor recall)    | `128`                                |
| `HISTORY_SIZE`                          | mensagens mantidas por sessão                      | `6`                                  |
| `INSTALL_LOCAL_EMBEDDINGS`              | flag de build: instala Sentence-Transformers + torch | `false`                           |
| `INSTALL_OCR`                           | flag de build: instala a stack de OCR para PDFs escaneados | `false`                      |
| `OCR_LANGUAGE`                          | idiomas do Tesseract (separados por `+`)           | `por+eng`                            |
| `OCR_DPI`                               | DPI de renderização usado no OCR                   | `200`                                |
| `AUTH_ENABLED`                          | exigir login Google/GitHub (produção)              | `false`                              |
| `BACKEND_URL`                           | URL pública do backend (para os redirect URIs OAuth)| —                                   |
| `FRONTEND_URL`                          | para onde voltar após o login                      | `/`                                  |
| `SESSION_SECRET`                        | assina o token de login (troque em produção)       | `dev-insecure-…`                     |
| `GOOGLE_OAUTH_CLIENT_ID` / `..._SECRET` | credenciais do app OAuth do Google                 | —                                    |
| `GITHUB_OAUTH_CLIENT_ID` / `..._SECRET` | credenciais do app OAuth do GitHub                 | —                                    |

### 🔑 Bring-your-own-key (LLM por requisição)

A barra lateral deixa cada visitante **escolher o provedor de LLM do chat** (a
partir de `supported_llm_providers` do servidor, veja `/config`) e **colar a
chave desse provedor**. Ela é enviada por requisição como `X-LLM-Provider` /
`X-API-Key`, sobrescrevendo a config do servidor só naquela requisição (a chave
fica apenas no navegador). As chaves também podem vir do `.env` do servidor como
fallback. Assim, um deploy público **não precisa de nenhuma chave embarcada** —
cada visitante traz a sua.

> **Os embeddings ficam fixos no servidor** (provedor + modelo). Apenas o **LLM
> do chat** é por requisição, porque a dimensão do índice vetorial no Redis é
> definida pelo modelo de embeddings e precisa ser consistente em todos os
> documentos e consultas.

### 🔒 Autenticação / login (opcional)

O login vem **desligado por padrão** — rodar localmente não exige contas. Para um
**deploy público**, defina `AUTH_ENABLED=true` e os visitantes precisam entrar com
**Google ou GitHub**; cada usuário então vê apenas **seus próprios** documentos e
conversas (os dados são marcados por usuário).

Como funciona: o handshake OAuth acontece no backend (Authlib); no sucesso o
backend emite um **token assinado** e redireciona de volta para a UI, que o envia
como `Authorization: Bearer` em toda requisição. A API permanece stateless (sem
cookies cross-site).

<details>
<summary><b>Habilitando em produção</b></summary>

1. **Crie os apps OAuth** e registre as URLs de callback:
   - Google — [Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
     → *OAuth client ID* (tipo *Web*). Redirect URI:
     `<BACKEND_URL>/auth/callback/google`
   - GitHub — [Settings → Developer settings → OAuth Apps](https://github.com/settings/developers)
     → *New OAuth App*. Callback URL: `<BACKEND_URL>/auth/callback/github`
2. Defina `AUTH_ENABLED=true`, `BACKEND_URL`, `FRONTEND_URL`, um `SESSION_SECRET`
   forte e os quatro valores `*_OAUTH_*`.
3. Faça o redeploy. A UI passa a mostrar a tela de login até o usuário entrar.

</details>

### 📄 PDFs escaneados (OCR)

PDFs **com camada de texto** e TXT funcionam de imediato. **PDFs escaneados / só
imagem** não têm texto extraível, então a ingestão precisa de OCR — um extra
opt-in de build (mantém a imagem padrão pequena):

```env
# .env
INSTALL_OCR=true
```
```bash
docker compose up --build   # reconstrói a imagem da API com Tesseract + PyMuPDF
```

Sem isso, subir um PDF escaneado retorna um **erro claro** em vez de indexar um
documento vazio. O OCR é **lento** em arquivos grandes (renderiza e lê cada página).

---

## 🌐 Endpoints da API

| Método | Rota                | Descrição                                          |
|--------|---------------------|----------------------------------------------------|
| POST   | `/upload`           | Recebe arquivo(s) e dispara a ingestão             |
| GET    | `/documents`        | Lista os documentos indexados                      |
| DELETE | `/documents/{id}`   | Remove um documento e seus vetores                 |
| POST   | `/chat`             | Pergunta + resposta RAG com fontes                 |
| POST   | `/chat/stream`      | Igual ao `/chat`, com streaming SSE                |
| GET    | `/health`           | Health check (status + conectividade do Redis)     |
| GET    | `/config`           | Provedores configurados + se exige chave de API    |

Exemplo `POST /chat`:
```json
{ "question": "Quais foram os principais resultados do Q3?", "session_id": "abc-123", "top_k": 5 }
```
```json
{
  "answer": "Os principais resultados do Q3 foram...",
  "sources": [{ "chunk": "...", "source": "relatorio_q3.pdf", "score": 0.91 }],
  "session_id": "abc-123"
}
```

Docs interativos (Swagger UI): <http://localhost:8000/docs>.

---

## 🧠 Pipeline RAG (LangGraph)

O fluxo é orquestrado por um grafo **LangGraph**
(`backend/app/services/rag_graph.py`) com quatro nós — em vez de uma chain
simples — o que torna o fluxo explícito e fácil de estender (validação, retry,
branching condicional):

```
retriever_node → context_builder_node → llm_node → response_formatter_node
```

1. **retriever_node** — gera o embedding da pergunta e roda uma **busca KNN** no Redis.
2. **context_builder_node** — monta o prompt com o contexto recuperado **mais o
   histórico da sessão**.
3. **llm_node** — chama o LLM configurado com o prompt montado.
4. **response_formatter_node** — formata a resposta final, **incluindo as fontes**.

O streaming (`/chat/stream`) reaproveita os nós de retrieval/contexto e transmite
os tokens do LLM via SSE.

---

## 🧪 Testes

### Backend (pytest)

Construídos com `pytest`, mockando Redis (`fakeredis`), embeddings e o LLM — então
**nenhuma chamada real de API** é feita. **Cobertura: 100%** do backend (o
`pytest` falha automaticamente se cair abaixo do limite de 95%).

**Opção 1 — via Docker (sem instalar Python):**
```bash
make test
```

**Opção 2 — localmente (requer Python 3.11+):**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                 # ou, na raiz do repo: make test-local
```

> Testes de integração que precisam de um **Redis Stack real** são opt-in: `pytest -m integration`.

A configuração do pytest (`--cov` + o limite de 95%) fica em `backend/pyproject.toml`.

```
backend/tests/
├── conftest.py                   # fixtures: mocks de redis/llm/embeddings, TestClient
├── test_ingestion.py             # chunking, extração PDF/TXT/DOCX, fallback de OCR
├── test_api_upload.py            # POST /upload
├── test_api_chat.py              # POST /chat e /chat/stream (RAG, headers BYOK)
├── test_api_documents.py         # GET e DELETE /documents
├── test_factories.py             # factories de provedor LLM/embeddings (todos)
├── test_redis_client.py          # conexão, ping, criação de índice
├── test_retriever.py             # parsing do resultado KNN
├── test_main.py                  # lifespan, /health, /config
├── test_auth.py                  # login OAuth, tokens, isolamento por usuário
├── test_misc.py                  # config, histórico, pequenos edge cases
└── test_retriever_integration.py # Redis Stack real (opt-in, `-m integration`)
```

### Frontend (Vitest + Testing Library)

O frontend é **TypeScript** (modo strict) e coberto por uma suíte **Vitest** com
React Testing Library, mockando a camada de API (`fetch` / `axios`) — sem rede
real. **38 testes, ~88% de cobertura** (um gate de threshold falha o run se cair).

```bash
cd frontend
npm install
npm run typecheck      # tsc --noEmit (strict)
npm test               # vitest run
npm run test:coverage  # com cobertura + gate de threshold
```

Ou, sem Node local, na raiz do repo: `make test-frontend`.

```
frontend/src/
├── api/client.test.ts            # helpers de token, parser de streaming SSE, 401
├── api/client.axios.test.ts      # chamadas HTTP upload / documents / chat / config
├── App.test.tsx                  # gating de auth (tela de login vs UI principal)
├── components/ChatWindow.test.tsx     # enviar no Enter, resposta em stream, erros
├── components/FileUpload.test.tsx     # filtro de tipo, upload, erro de extração vazia
├── components/ApiKeyInput.test.tsx    # troca de provedor + persistência da chave
├── components/SessionSidebar.test.tsx # criar / selecionar / renomear / excluir
├── components/DocumentList.test.tsx   # lista + remoção
├── components/SourcesPanel.test.tsx   # recolher / expandir
├── components/MessageBubble.test.tsx  # usuário vs assistente, pending, fontes
└── test/setup.ts                 # matchers jest-dom, polyfills do jsdom
```

---

## 🧭 Decisões de arquitetura & trade-offs

- **Provedor configurável (OpenAI/Anthropic/Gemini/Ollama):** factories em
  `llm.py` e `embeddings.py` desacoplam o resto do código do fornecedor. Rode
  100% local e grátis (Ollama) ou com APIs pagas/gratuitas trocando uma variável
  — e o visitante pode sobrescrever o LLM do chat por requisição (BYOK).
- **LangGraph em vez de chain simples:** mais controle e extensibilidade do fluxo
  RAG (espaço para futuros nós de validação/retry/branching).
- **Índice HNSW + COSINE:** bom equilíbrio velocidade/qualidade para similaridade
  semântica; a dimensão é derivada do modelo de embeddings.
- **Chunk como HASH no Redis** (`doc:{file_id}:chunk:{n}`): os metadados (source,
  chunk_index, uploaded_at) ficam ao lado do vetor, simplificando listagem e
  exclusão por `file_id`.
- **Histórico por sessão no Redis** (lista limitada por `HISTORY_SIZE`): contexto
  de curto prazo sem depender de estado em memória da API.
- **Streaming via SSE** com `fetch` no frontend (POST) e `proxy_buffering off` no
  Nginx para entrega real token a token.
- **Auth opcional num único caminho de código:** toda operação é escopada por um
  `user_id` (um id público fixo quando o login está off; a identidade OAuth
  quando on). O mesmo código de ingestão/retrieval/histórico roda nos dois modos;
  o retriever apenas adiciona um pré-filtro `@user_id` na consulta KNN. Baseado em
  token (sem cookies cross-site), então a API segue stateless entre domínios
  separados de frontend/backend.

---

## 🩺 Solução de problemas

| Sintoma                                   | Causa provável / solução                                                                  |
|-------------------------------------------|-------------------------------------------------------------------------------------------|
| `/health` mostra `redis: "disconnected"`  | O `redis` ainda está subindo — aguarde o healthcheck ou rode `docker compose logs redis`. |
| Erro de dimensão no upload/chat           | Você trocou o modelo de embeddings sem resetar o índice → `docker compose down -v` e suba de novo. |
| Chat falha com `LLM_PROVIDER=ollama`      | O Ollama não está rodando ou o modelo não foi baixado (`ollama pull llama3`). Cheque `OLLAMA_BASE_URL`. |
| Erro de autenticação do provedor (500)    | A chave de API (no `.env` ou na barra lateral) está ausente/inválida para o provedor escolhido. |
| "No text extracted" num PDF               | O PDF é escaneado/só imagem → habilite OCR (`INSTALL_OCR=true`) e reconstrua.              |
| Upload retorna 413 (muito grande)         | O arquivo excede o limite do Nginx (`client_max_body_size`, padrão 300M em `frontend/nginx.conf`). |
| Porta 3000 / 8000 / 6379 já em uso        | Pare o processo conflitante ou ajuste o mapeamento de portas no `docker-compose.yml`.     |

Logs úteis:
```bash
docker compose logs -f api    # só os logs da API
docker compose logs -f        # todos os serviços
```

---

## 🗂️ Estrutura do repositório

```
chat_rag/
├── backend/                    # FastAPI + LangGraph + serviços RAG + testes
│   ├── app/
│   │   ├── main.py             # app FastAPI, CORS, lifespan
│   │   ├── routers/            # endpoints upload, chat, documents, auth
│   │   ├── services/           # ingestion, retriever, rag_graph, llm, embeddings, …
│   │   ├── models/schemas.py   # modelos Pydantic de request/response
│   │   └── config.py           # configurações via env vars
│   ├── tests/                  # suíte pytest (100% de cobertura)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                   # React + TypeScript + Vite (Nginx em produção)
│   ├── src/components/         # *.tsx: ChatWindow, FileUpload, DocumentList, …
│   ├── src/**/*.test.{ts,tsx}  # suíte Vitest + Testing Library
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── package.json
├── .github/workflows/ci.yml    # CI: pytest + integração + build do frontend
├── docker-compose.yml          # redis + api + frontend (um comando para subir)
├── render.yaml + DEPLOY.md     # deploy em nuvem (Render)
├── .env.example
├── Makefile
├── README.md                   # Inglês
└── README.pt-BR.md             # Português (este arquivo)
```

---

## 🏅 Diferenciais & cobertura dos requisitos

**Tudo o que o desafio pede — e onde encontrar.**

| Requisito do desafio                                    | Status | Onde |
|---------------------------------------------------------|:------:|------|
| Ingestão de **PDF & TXT** (+ chunking com overlap)      | ✅ | `services/ingestion.py`, `CHUNK_SIZE`/`CHUNK_OVERLAP` |
| Embeddings (OpenAI **ou** Sentence-Transformers)        | ✅ | `services/embeddings.py` |
| Vetores no **Redis Stack / RediSearch** (HNSW, COSINE)  | ✅ | `services/redis_client.py`, `retriever.py` |
| Endpoints `/upload`, `/documents`, `DELETE`, `/chat`, `/health` | ✅ | [Endpoints da API](#-endpoints-da-api) |
| Fluxo **RAG** com **LangChain/LangGraph**               | ✅ | [Pipeline RAG](#-pipeline-rag-langgraph) |
| **Histórico de conversa** por sessão                    | ✅ | `services/history.py`, `HISTORY_SIZE` |
| `sources` retornadas em cada resposta                   | ✅ | resposta de `POST /chat` |
| UI de chat em **React** (upload, progresso, docs, fontes, Enter, loading) | ✅ | `frontend/src/` |
| **Docker Compose** (api + frontend + redis, volumes, healthchecks) | ✅ | `docker-compose.yml` |
| Roda com **um comando** `docker compose up --build`     | ✅ | [Início rápido](#-início-rápido-tldr) |
| **Testes unitários** com mocks (≥60% de cobertura exigida) | ✅ | **100%** de cobertura — [Testes](#-testes) |
| README: setup, variáveis, decisões, como testar         | ✅ | este arquivo |

**Diferenciais extras implementados (bônus):**

- ✅ **Streaming de respostas** (Server-Sent Events).
- ✅ **Pipeline RAG com LangGraph** (em vez de chain simples).
- ✅ **Múltiplas sessões de chat** com nomes customizáveis.
- ✅ **CI com GitHub Actions** (testes + build a cada push).
- ✅ **Deploy em nuvem** com link funcional (Render).
- ✅ **Upload de múltiplos arquivos** + **suporte a DOCX** (além do PDF/TXT exigido).
- ✅ **OCR para PDFs escaneados** (build opt-in, Tesseract).
- ✅ **Remoção de documentos** com limpeza dos vetores no Redis.
- ✅ **Bring-your-own-key** + provedor de LLM por requisição escolhido na UI.
- ✅ Provedor **Google Gemini** (LLM + embeddings), incl. caminho com free tier.
- ✅ **Uploads canceláveis** e **100%** de cobertura de testes no backend.
- ✅ **Login opcional Google/GitHub** com isolamento de dados por usuário.
- ✅ **Frontend em TypeScript** (strict) com suíte **Vitest + Testing Library**
  (38 testes, ~88% de cobertura) integrada ao CI.

---

<p align="center"><sub>Feito por <a href="https://www.linkedin.com/in/igorcezaralbuquerque"><strong>Igor Albuquerque</strong></a></sub></p>
