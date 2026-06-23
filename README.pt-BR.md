# Chat com Documentos via IA — RAG com busca semântica em Redis

**🌐 Idioma:** [English](README.md) · **Português (BR)**

Aplicação full-stack que permite fazer **upload de documentos** (PDF/TXT/DOCX) e
**conversar com eles** usando RAG (Retrieval-Augmented Generation): busca
semântica vetorial em Redis + geração de resposta por um LLM, com exibição das
fontes utilizadas.

---

## Arquitetura

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

| Camada       | Tecnologia                                   |
|--------------|----------------------------------------------|
| Frontend     | React 18 + Vite, servido via Nginx           |
| API          | Python 3.11, FastAPI, LangChain + LangGraph  |
| Vector Store | Redis Stack (RediSearch, índice HNSW/COSINE) |
| LLM          | OpenAI / Anthropic / Gemini / Ollama (configurável) |
| Embeddings   | OpenAI / Gemini / Sentence-Transformers (config.)  |
| Infra        | Docker Compose                               |

---

## Como rodar (passo a passo)

O projeto inteiro sobe com **um único comando** (`docker-compose up --build`).
Você **não precisa** instalar Python, Node ou Redis na máquina — apenas Docker.

### Pré-requisitos

| Requisito                     | Versão mínima | Como verificar             |
|-------------------------------|---------------|----------------------------|
| Docker                        | 20.10+        | `docker --version`         |
| Docker Compose                | v2 (plugin)   | `docker compose version`   |
| (opcional) Ollama no host     | 0.1+          | `ollama --version`         |

> **Docker Compose v1 vs v2:** nas versões novas o comando é `docker compose`
> (com espaço). Se você usa a v1 antiga, troque por `docker-compose` (com hífen).
> Os exemplos abaixo usam `docker compose`.

### Passo 1 — Clonar e entrar no diretório

```bash
git clone <url-do-repositorio>
cd chat_rag
```

### Passo 2 — Criar o arquivo `.env`

```bash
cp .env.example .env
```

### Passo 3 — Escolher o provedor de LLM/embeddings

O sistema é **provider-agnóstico** (configurado por variáveis no `.env`).
Escolha **um** dos caminhos abaixo e edite o `.env` de acordo.

<details open>
<summary><b>Caminho A — Com chave de API (mais simples e rápido) ⭐</b></summary>

Não exige instalar nada além do Docker. Basta colar sua chave no `.env`.

**OpenAI:**
```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...        # sua chave aqui
```

**Anthropic (LLM Claude) + embeddings locais gratuitos:**
```env
LLM_PROVIDER=anthropic
EMBEDDING_PROVIDER=sentence-transformers
LLM_MODEL=claude-3-5-sonnet-latest
EMBEDDING_MODEL=all-MiniLM-L6-v2
ANTHROPIC_API_KEY=sk-ant-... # sua chave aqui
```

**Google Gemini (tem free tier — LLM + embeddings):**
```env
LLM_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
EMBEDDING_MODEL=models/text-embedding-004
GOOGLE_API_KEY=...           # sua chave aqui
```
</details>

<details>
<summary><b>Caminho B — 100% local e sem custo (Ollama)</b></summary>

Não usa nenhuma API paga. As **embeddings** rodam dentro do container
(Sentence-Transformers, baixadas automaticamente no primeiro uso). O **LLM**
roda via [Ollama](https://ollama.com) na sua máquina host:

```bash
# 1. Instale o Ollama (https://ollama.com/download) e baixe um modelo:
ollama pull llama3

# 2. Garanta que o Ollama está rodando (normalmente sobe sozinho):
ollama serve   # se ainda não estiver ativo
```

`.env`:
```env
LLM_PROVIDER=ollama
EMBEDDING_PROVIDER=sentence-transformers
LLM_MODEL=llama3
EMBEDDING_MODEL=all-MiniLM-L6-v2
OLLAMA_BASE_URL=http://host.docker.internal:11434
# Obrigatório para embeddings locais: instala sentence-transformers + torch.
# Isso deixa a imagem da API bem maior e mais lenta para buildar.
INSTALL_LOCAL_EMBEDDINGS=true
```

> A imagem padrão é **slim** e traz só a stack de provedores via API. As
> embeddings locais (Sentence-Transformers + torch) são um extra de build,
> habilitado por `INSTALL_LOCAL_EMBEDDINGS=true`, então a dependência pesada só
> é instalada quando realmente necessária.
>
> O `docker-compose.yml` já mapeia `host.docker.internal` para o host no Linux,
> então o container `api` enxerga o Ollama da sua máquina.
</details>

### Passo 4 — Subir a aplicação

```bash
docker compose up --build
```

A primeira execução baixa as imagens e instala dependências (pode levar alguns
minutos). Quando estiver pronto, você verá os logs dos 3 serviços (`redis`,
`api`, `frontend`). Para rodar em segundo plano, use `docker compose up --build -d`.

### Passo 5 — Acessar

| Serviço                         | URL                            |
|---------------------------------|--------------------------------|
| **Aplicação (Frontend)**        | <http://localhost:3000>        |
| API — documentação Swagger      | <http://localhost:8000/docs>   |
| API — health check              | <http://localhost:8000/health> |
| RedisInsight (inspeção do Redis)| <http://localhost:8001>        |

### Passo 6 — Parar / limpar

```bash
docker compose down       # para os serviços (mantém os dados do Redis)
docker compose down -v    # para e APAGA o volume do Redis (reset total)
```

> ⚠️ **Ao trocar o modelo de embeddings**, rode `docker compose down -v` antes de
> subir de novo. A dimensão do índice vetorial é derivada do modelo (1536 para
> OpenAI, 384 para `all-MiniLM-L6-v2`); um índice criado com outra dimensão é
> incompatível.

---

## Usando a aplicação

1. Acesse <http://localhost:3000>.
2. **Modelo de chat (opcional)**: na barra lateral, escolha o provedor do LLM e
   cole a chave dele. Pule se o servidor já tiver chave no `.env`, ou se usar um
   provedor local (Ollama) que não precisa de chave.
3. **Upload**: arraste um PDF, TXT ou DOCX para a área de upload (ou clique para
   selecionar). Acompanhe o progresso (envio → processamento); você pode
   **Cancelar** um envio em andamento — útil para arquivos grandes.
4. O documento aparece na lista **Documentos** (com o nº de chunks indexados).
5. **Pergunte** no campo de chat e pressione **Enter**. A resposta aparece em
   **streaming** (token a token).
6. Clique em **Fontes** abaixo de cada resposta para ver os trechos usados.
7. **Múltiplas conversas**: crie/renomeie/exclua sessões na barra lateral
   (duplo-clique no nome para renomear).
8. Remova um documento pelo **✕** na lista — os vetores correspondentes são
   apagados do Redis.

---

## Verificação rápida (via terminal)

Confirme que a stack está saudável e o fluxo end-to-end funciona, sem abrir o
navegador:

```bash
# 1. Health check (deve retornar redis: "connected")
curl http://localhost:8000/health
# {"status":"ok","redis":"connected"}

# 2. Upload de um documento de exemplo
echo "O lucro do terceiro trimestre cresceu 20% em relacao ao Q2." > exemplo.txt
curl -F "files=@exemplo.txt" http://localhost:8000/upload
# {"files":[{"file_id":"...","name":"exemplo.txt","chunks_indexed":1,...}],...}

# 3. Listar documentos indexados
curl http://localhost:8000/documents

# 4. Perguntar (RAG)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Qual foi o resultado do Q3?","session_id":"demo"}'
# {"answer":"...","sources":[{"chunk":"...","source":"exemplo.txt","score":0.9}],"session_id":"demo"}

# 5. Streaming (Server-Sent Events)
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Resuma o documento","session_id":"demo"}'
```

---

## Solução de problemas

| Sintoma                                   | Causa provável / solução                                                                 |
|-------------------------------------------|------------------------------------------------------------------------------------------|
| `/health` retorna `redis: "disconnected"` | O serviço `redis` ainda está subindo — aguarde o healthcheck ou veja `docker compose logs redis`. |
| Erro de dimensão no upload/chat           | Trocou o modelo de embeddings sem resetar o índice. Rode `docker compose down -v` e suba de novo. |
| Chat retorna erro com `LLM_PROVIDER=ollama` | Ollama não está rodando ou o modelo não foi baixado (`ollama pull llama3`). Verifique `OLLAMA_BASE_URL`. |
| Erro de autenticação do provedor (500)    | Chave (no `.env` ou no campo da barra lateral) ausente/ inválida para o provedor escolhido. |
| "Nenhum texto extraído" num PDF           | PDF escaneado/imagem — habilite OCR (`INSTALL_OCR=true`, veja abaixo) e rebuilde.          |
| Upload retorna 413 (muito grande)         | Arquivo acima do limite do Nginx (`client_max_body_size`, padrão 300M em `frontend/nginx.conf`). |
| Porta 3000/8000/6379 já em uso            | Pare o processo conflitante ou ajuste o mapeamento de portas no `docker-compose.yml`.     |

Logs úteis:
```bash
docker compose logs -f api       # logs da API
docker compose logs -f           # todos os serviços
```

---

## Variáveis de ambiente

| Variável             | Descrição                                          | Default                |
|----------------------|----------------------------------------------------|------------------------|
| `LLM_PROVIDER`       | `openai` / `anthropic` / `gemini` / `ollama`       | `ollama`               |
| `EMBEDDING_PROVIDER` | `openai` / `gemini` / `sentence-transformers`      | `sentence-transformers`|
| `LLM_MODEL`          | nome do modelo de chat                             | `llama3`               |
| `EMBEDDING_MODEL`    | nome do modelo de embeddings                       | `all-MiniLM-L6-v2`     |
| `OPENAI_API_KEY`     | chave OpenAI (se aplicável)                        | —                      |
| `ANTHROPIC_API_KEY`  | chave Anthropic (se aplicável)                     | —                      |
| `GOOGLE_API_KEY`     | chave do Google Gemini (se aplicável)              | —                      |
| `OLLAMA_BASE_URL`    | endpoint do Ollama                                 | `http://host.docker.internal:11434` |
| `REDIS_URL`          | URL do Redis (auto em compose)                     | `redis://localhost:6379` |
| `CHUNK_SIZE`         | tamanho do chunk (tokens)                          | `500`                  |
| `CHUNK_OVERLAP`      | sobreposição entre chunks                          | `50`                   |
| `TOP_K`              | nº de chunks recuperados por pergunta              | `5`                    |
| `EF_RUNTIME`         | amplitude da busca HNSW (maior = melhor recall)    | `128`                  |
| `HISTORY_SIZE`       | nº de mensagens mantidas por sessão                | `6`                    |
| `INSTALL_LOCAL_EMBEDDINGS` | flag de build: instala Sentence-Transformers + torch | `false`           |
| `INSTALL_OCR`        | flag de build: instala o OCR p/ PDFs escaneados    | `false`                |
| `OCR_LANGUAGE`       | idiomas do Tesseract (separados por `+`)           | `por+eng`              |
| `OCR_DPI`            | DPI de renderização usado no OCR                   | `200`                  |

### Provedor do chat + chave de API (traga a sua — BYOK)

Na barra lateral, cada visitante **escolhe o provedor do LLM do chat** (dentre os
`supported_llm_providers` do servidor, veja `/config`) e **cola a chave desse
provedor**. São enviados por requisição nos headers `X-LLM-Provider` e
`X-API-Key`, sobrepondo a config do servidor só naquela requisição (a chave fica
apenas no navegador).

As chaves também podem vir do **`.env` do servidor** (`OPENAI_API_KEY` /
`ANTHROPIC_API_KEY` / `GOOGLE_API_KEY`), usado como fallback quando não há header
— conveniente para rodar local. Assim dá pra publicar o app **sem subir nenhuma
chave**: cada visitante traz a sua.

> **Embeddings ficam fixos no servidor** (provedor + modelo). Só o **LLM do
> chat** é por requisição, porque a dimensão do índice vetorial no Redis é
> definida pelo modelo de embeddings e precisa ser consistente entre todos os
> documentos e consultas.

### PDFs escaneados (OCR)

PDFs **com camada de texto** e TXT funcionam direto. **PDFs escaneados (só
imagem)** não têm texto extraível, então a ingestão precisa de OCR. O OCR é um
extra de build opcional (mantém a imagem padrão pequena):

```env
# .env
INSTALL_OCR=true
```
```bash
docker compose up --build   # reconstrói a imagem da API com Tesseract + PyMuPDF
```

Sem isso, subir um PDF escaneado retorna um erro claro em vez de indexar um
documento vazio. Atenção: o OCR é **lento** para documentos grandes (renderiza e
lê cada página), então espere tempos de processamento altos em arquivos extensos.

---

## Endpoints da API

| Método | Rota                  | Descrição                                  |
|--------|-----------------------|--------------------------------------------|
| POST   | `/upload`             | Recebe arquivo(s) e dispara a ingestão     |
| GET    | `/documents`          | Lista documentos indexados                 |
| DELETE | `/documents/{id}`     | Remove documento e seus vetores            |
| POST   | `/chat`               | Pergunta + resposta RAG com fontes         |
| POST   | `/chat/stream`        | Igual ao `/chat`, com streaming SSE        |
| GET    | `/health`             | Health check (status + conectividade Redis)|
| GET    | `/config`             | Providers configurados + se exige chave de API |

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

---

## Pipeline RAG com LangGraph

O fluxo é orquestrado por um grafo LangGraph (`app/services/rag_graph.py`) com
quatro nós, em vez de uma chain simples — o que torna o fluxo explícito e fácil
de estender com validação, retry ou branching condicional:

```
retriever_node → context_builder_node → llm_node → response_formatter_node
```

1. **retriever_node** — gera o embedding da pergunta e faz busca KNN no Redis.
2. **context_builder_node** — monta o prompt com o contexto recuperado e o
   histórico da sessão.
3. **llm_node** — chama o LLM configurado com o prompt montado.
4. **response_formatter_node** — formata a resposta final, incluindo as fontes.

O streaming (`/chat/stream`) reusa os nós de retrieval/contexto e transmite os
tokens do LLM via SSE.

---

## Testes

Suíte com `pytest`, mocando Redis (`fakeredis`), embeddings e LLM — **sem
chamadas reais a APIs**. Cobertura atual: **100%** do backend (o `pytest` falha
automaticamente se a cobertura cair abaixo do limite de 95%).

**Opção 1 — via Docker (sem instalar Python):**
```bash
make test
```

**Opção 2 — localmente (requer Python 3.11+):**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                 # ou: make test-local (a partir da raiz)
```

A configuração do pytest (incluindo `--cov` e o limite de 95%) está em
`backend/pyproject.toml`.

Estrutura:
```
backend/tests/
├── conftest.py                   # fixtures: mocks de redis/llm/embeddings, TestClient
├── test_ingestion.py             # chunking, extração PDF/TXT/DOCX, fallback de OCR
├── test_api_upload.py            # POST /upload
├── test_api_chat.py              # POST /chat e /chat/stream (RAG, headers BYOK)
├── test_api_documents.py         # GET e DELETE /documents
├── test_factories.py             # factories de LLM/embeddings (todos os provedores)
├── test_redis_client.py          # conexão, ping, criação do índice
├── test_retriever.py             # parsing do resultado KNN
├── test_main.py                  # lifespan, /health, /config
├── test_misc.py                  # config, histórico, edge cases
└── test_retriever_integration.py # Redis Stack real (opt-in, `-m integration`)
```

---

## Decisões de arquitetura e trade-offs

- **Provider configurável (OpenAI/Anthropic/Gemini/Ollama):** factories em
  `llm.py` e `embeddings.py` desacoplam o restante do código do fornecedor.
  Permite rodar 100% local e sem custo (Ollama) ou com APIs pagas/grátis,
  trocando uma env var — e o visitante pode trocar o LLM do chat por requisição
  (BYOK).
- **LangGraph em vez de chain simples:** maior controle e extensibilidade do
  fluxo RAG (nós de validação/retry/branching futuros).
- **Índice HNSW + COSINE:** bom equilíbrio entre velocidade e qualidade para
  busca de similaridade semântica; dimensão derivada do modelo de embeddings.
- **Chunk como HASH no Redis** (`doc:{file_id}:chunk:{n}`): metadados (source,
  chunk_index, uploaded_at) ficam junto do vetor, simplificando listagem e
  remoção por `file_id`.
- **Histórico por sessão no Redis** (lista capada por `HISTORY_SIZE`): contexto
  de curto prazo sem dependência de estado em memória da API.
- **Streaming via SSE** com `fetch` no frontend (POST), `proxy_buffering off`
  no Nginx para entrega token a token.

---

## Estrutura do repositório

```
chat_rag/
├── backend/        # FastAPI + LangGraph + serviços RAG + testes
├── frontend/       # React + Vite (Nginx em produção)
├── .github/workflows/ci.yml   # CI: pytest + build do frontend
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md       # Inglês
└── README.pt-BR.md # Português (este arquivo)
```

---

## Diferenciais implementados

- ✅ **Streaming de respostas** (Server-Sent Events).
- ✅ **Pipeline RAG com LangGraph** (em vez de chain simples).
- ✅ **Múltiplas sessões de chat** com nomes customizáveis no frontend.
- ✅ **CI com GitHub Actions** (testes + build a cada push).
- ✅ **Suporte a múltiplos arquivos** no upload.
- ✅ **Suporte a DOCX** (além dos PDF/TXT obrigatórios).
- ✅ **OCR para PDFs escaneados** (build opcional, Tesseract).
- ✅ **Remoção de documentos** com limpeza dos vetores no Redis.
- ✅ **Traga sua chave (BYOK) + escolha do provedor do LLM** na interface.
- ✅ **Google Gemini** como provedor (LLM + embeddings), com caminho free-tier.
- ✅ **Upload cancelável** e cobertura de testes de 100% no backend.
