# Estudo do Case — Chat com Documentos (RAG)

> Documento pessoal de estudo. Explica **o que foi construído**, **por que cada
> decisão foi tomada** e os **tradeoffs** envolvidos. Serve para você revisar e
> conseguir defender o projeto numa conversa técnica.

---

## 1. Visão geral em uma frase

Uma aplicação full-stack onde o usuário **faz upload de documentos** (PDF, DOCX,
TXT), o backend os **fatia, vetoriza e indexa no Redis**, e o usuário **conversa**
com esses documentos via **RAG** (Retrieval-Augmented Generation), recebendo a
resposta **em streaming** com as **fontes** que a embasaram.

**Stack:** FastAPI + React (Vite) + Redis Stack (RediSearch) + LangGraph, tudo
orquestrado por Docker Compose e executável com `docker-compose up --build`.

---

## 2. O que é RAG e por que usar

**Problema:** um LLM puro não conhece os seus documentos e "alucina" quando
perguntado sobre eles.

**RAG resolve em 2 etapas:**
1. **Retrieval (busca):** transforma a pergunta em um vetor e busca, por
   similaridade semântica, os trechos mais relevantes dos documentos indexados.
2. **Generation (geração):** injeta esses trechos como **contexto** no prompt do
   LLM, que responde *baseado apenas naquele contexto*.

**Por que é melhor do que fine-tuning aqui:**
- Não precisa re-treinar modelo quando chega documento novo — basta indexar.
- Permite **citar a fonte** (rastreabilidade / auditoria).
- Reduz alucinação porque o prompt instrui a responder só pelo contexto.

**Tradeoff:** a qualidade da resposta depende totalmente da qualidade do
*retrieval*. Se a busca traz o trecho errado, o LLM responde errado com confiança.
Por isso tanto cuidado com chunking, embeddings e recall (ver seções 6 e 11).

---

## 3. Arquitetura geral

```
┌──────────────┐    HTTP/SSE    ┌──────────────────────────┐
│  React (UI)  │ ─────────────► │  FastAPI (backend)       │
│  - upload    │                │  - /upload  /chat        │
│  - chat SSE  │ ◄───────────── │  - /chat/stream (SSE)    │
│  - sessões   │   tokens       │  - /documents /health    │
└──────────────┘                │  - /config               │
                                └───────────┬──────────────┘
                                            │
                          ┌─────────────────┴─────────────────┐
                          │                                    │
                  ┌───────▼────────┐                  ┌────────▼────────┐
                  │  LangGraph     │                  │  Redis Stack    │
                  │  (pipeline RAG)│ ───busca KNN───► │  (RediSearch)   │
                  └───────┬────────┘                  │  HNSW + COSINE  │
                          │                           └─────────────────┘
                  ┌───────▼────────┐
                  │  LLM provider  │  OpenAI / Anthropic / Gemini / Ollama
                  └────────────────┘
```

**Decisão central:** separar em camadas/serviços (`config`, `redis_client`,
`embeddings`, `llm`, `ingestion`, `retriever`, `rag_graph`, `history`). Cada
arquivo tem uma responsabilidade única e os *routers* só orquestram.

**Por quê:** testabilidade (mockar uma camada de cada vez) e legibilidade — o
avaliador encontra cada coisa onde espera. **Tradeoff:** mais arquivos/boilerplate
do que jogar tudo em um `main.py`, mas paga-se isso em manutenção e testes.

---

## 4. Backend — fluxo de upload (ingestion)

Arquivo: `backend/app/services/ingestion.py`

Pipeline: **parse → chunk → embed → index**.

1. **Parse (`_extract_text`)** — escolhe o extrator pela extensão:
   - PDF: `pypdf` lê a *camada de texto*. Se vier vazia (PDF escaneado) e o OCR
     estiver instalado, cai para `_ocr_pdf` (PyMuPDF renderiza + pytesseract lê).
     Sem OCR, levanta `TextExtractionError` com mensagem clara.
   - DOCX: `python-docx`, incluindo **células de tabela** (senão perderia dados
     tabulares).
   - TXT: decode UTF-8 tolerante a erro.
   - Outros: `UnsupportedFileType`.

   **Decisão:** OCR é **opt-in** (build arg `INSTALL_OCR`), não vem por padrão.
   **Tradeoff:** imagem menor e build rápido por padrão vs. PDFs escaneados só
   funcionam se você ativar (Tesseract + PyMuPDF pesam).

2. **Chunk (`chunk_text`)** — `RecursiveCharacterTextSplitter.from_tiktoken_encoder`
   com `chunk_size=500` e `overlap=50` **medidos em tokens**, não em caracteres.

   **Por quê tokens:** o orçamento de contexto do LLM e o custo de embedding são
   contados em tokens. Chunk de 500 *tokens* é previsível; 500 *caracteres* varia
   muito conforme o idioma. O *overlap* evita cortar uma frase no meio e perder o
   sentido entre dois chunks. **Tradeoff:** overlap duplica um pouco de texto →
   mais vetores armazenados, mas melhora recall em respostas que ficam na "junção".

3. **Embed** — `get_embeddings().embed_documents(chunks)` gera um vetor por chunk.

4. **Index** — cada chunk vira um **HASH** no Redis com `content`, `source`,
   `file_id` (UUID que agrupa o documento), `chunk_index`, `uploaded_at` e
   `embedding` (bytes float32). Tudo gravado num **pipeline** Redis (1 round-trip).

   **Decisão float32 em bytes:** RediSearch exige o vetor serializado em
   `np.float32().tobytes()`. **Tradeoff:** por isso o cliente Redis usa
   `decode_responses=False` — os campos de texto são decodificados manualmente
   no retriever (`_decode`), senão o decode global quebraria os bytes do vetor.

---

## 5. Backend — busca semântica (retriever)

Arquivo: `backend/app/services/retriever.py`

1. Embeda a pergunta → bytes float32.
2. Monta a query KNN do RediSearch:
   ```
   *=>[KNN {k} @embedding $vec EF_RUNTIME {ef} AS score]
   ```
   ordenando por `score` (distância), com `dialect(2)` (obrigatório p/ sintaxe de
   vetores).
3. Converte **distância cosseno → similaridade**: `score = round(1 - distance, 4)`
   (1 = idêntico, 0 = ortogonal). Isso é o número amigável que aparece nas fontes.

**Decisão crítica — `EF_RUNTIME`:** `ef = max(settings.ef_runtime, k)` com default
128. Ver seção 11 (bug de recall) para entender por que isso foi essencial.

---

## 6. Backend — pipeline RAG com LangGraph

Arquivo: `backend/app/services/rag_graph.py`

Em vez de uma "chain" linear do LangChain, usei um **StateGraph** com 4 nós:

```
retriever_node → context_builder_node → llm_node → response_formatter_node
```

- **retriever_node** — busca os chunks (seção 5).
- **context_builder_node** — monta as mensagens: `SystemMessage` (instrução de
  responder *só pelo contexto* e *no idioma da pergunta*) + histórico da sessão +
  `HumanMessage` com o contexto numerado e a pergunta.
- **llm_node** — chama o modelo escolhido.
- **response_formatter_node** — devolve `answer` + `sources` (chunk, source,
  score, chunk_index).

**Por que LangGraph e não chain simples:** o case pedia LangGraph como
diferencial, e ele torna o fluxo **explícito e extensível** — dá para inserir um
nó de validação, *retry* ou *branch condicional* sem reescrever tudo. O grafo é
compilado e **cacheado** (`@lru_cache`) porque a topologia não muda.

**Tradeoff honesto:** para um fluxo estritamente linear, LangGraph é "overkill" —
uma chain faria o mesmo com menos código. Adotei pela exigência do case e pela
extensibilidade futura.

**Detalhe de streaming (`stream_rag`):** os nós de retrieval/contexto rodam
normalmente, mas o passo do LLM usa `llm.stream()` fora do grafo compilado. Token
a token mapeia melhor para a interface `.stream()` do modelo do que para updates
de estado do grafo. As **fontes são calculadas antes** do streaming, então a UI
pode mostrar a resposta chegando e as fontes no fim.

---

## 7. Abstração de provedores (a decisão de design mais importante)

Arquivos: `llm.py`, `embeddings.py`, `config.py`

Toda escolha de modelo passa por **uma factory**:
- `get_llm(api_key, provider)` → OpenAI / Anthropic / Gemini / Ollama.
- `get_embeddings(api_key)` → OpenAI / Gemini / Sentence-Transformers (local).

O resto do código **nunca** sabe qual provider está ativo — só pede "me dá um
LLM" / "me dá um embedder". A config vem de `pydantic-settings` (tipada,
validada, lida do `.env`), centralizada em `config.py`. Nada de `os.environ`
espalhado.

**Imports lazy dentro de cada branch** (`from langchain_openai import ...` só
quando o provider é openai): permite instalar apenas o SDK que você usa e manter
a imagem enxuta. **Tradeoff:** o erro de "SDK não instalado" só aparece em
runtime, não no import — mitigado com mensagens de erro explícitas.

### A restrição que mais gera pergunta: por que embeddings é fixo no servidor?

A **dimensão do índice vetorial** (HNSW) é definida na criação e **não pode
mudar** depois. OpenAI=1536, MiniLM=384, Gemini=768. Se um usuário indexasse com
um modelo e buscasse com outro, as dimensões não bateriam e a busca quebraria.

**Decisão:** o **provider de embeddings é fixo por servidor**; só o **LLM de chat
é escolhível por requisição**. É uma restrição real do RAG, não preguiça — e está
documentada no README e no tooltip da UI.

---

## 8. Bring-Your-Own-Key (BYOK)

Para hospedar publicamente **sem pagar/expor minha chave**: o visitante cola a
chave dele no front. Ela vai:
- Guardada **só no `localStorage`** do navegador (nunca persistida no servidor).
- Enviada **por requisição** nos headers `X-API-Key` e `X-LLM-Provider`.
- Com **fallback para a `.env`** do servidor quando o campo está vazio (assim quem
  roda local com chave no `.env` não precisa digitar nada).

Caminho da chave: header → router (`chat.py`/`upload.py`) → `run_rag/ingest_file`
→ factory `get_llm/get_embeddings`. Em nenhum momento ela é logada ou salva.

**Segurança/tradeoff:** é um modelo adequado para **demo/portfólio**, não para
produção multiusuário — não há autenticação e os documentos ficam num índice
único compartilhado. Está explicitamente assumido como escopo de demo.

O front também consome `/config` para saber **quais providers são permitidos**
(`supported_llm_providers`) e **quais exigem chave** (`KEY_PROVIDERS`), evitando
que o usuário cole, p.ex., uma chave de um provider que não suportamos. Provider
local (Ollama) esconde o campo de chave.

---

## 9. Endpoints (FastAPI)

- `POST /upload` — multipart; trata `UnsupportedFileType`→415 e
  `TextExtractionError`→422. Lê `X-API-Key`.
- `POST /chat` — resposta completa (answer + sources). Lê `X-API-Key` +
  `X-LLM-Provider`; valida o provider (`400` se desconhecido).
- `POST /chat/stream` — **SSE** (`event: token` … `event: done`).
- `GET /documents` / `DELETE /documents/{id}` — lista/remove documentos.
- `GET /health` — retorna **503** quando o Redis está fora (não só 200 textual),
  para o healthcheck do Compose marcar o container como `unhealthy` corretamente.
- `GET /config` — diz ao front qual provider/embeddings o servidor usa e o que é
  permitido.

**`top_k` limitado** via Pydantic `Field(ge=1, le=20)`: impede 0/negativo/absurdo
chegar à query Redis.

---

## 10. Frontend (React + Vite)

- **Chat com streaming** via `fetch` + leitura incremental do corpo SSE.
- **Multi-sessão**: cada conversa é uma sessão persistida em `localStorage`;
  trocar de aba não perde histórico.
- **Upload com feedback**: fases `uploading → processing → done`, barra de
  progresso, **botão cancelar** (`AbortController`), tratamento de 413 e aviso
  quando o documento não gera texto.
- **ApiKeyInput**: dropdown de provider (vindo do `/config`) + campo de chave
  (escondido para provider local).

**Bug de estado corrigido (streaming):** o updater de mensagens precisava ser
**funcional** e resolvido dentro do `setSessions` (estado sempre mais recente),
fixando o `session.id` capturado no início do envio. Sem isso, cada token
sobrescrevia o anterior usando um snapshot velho, e trocar de aba durante o
streaming escrevia na sessão errada.

**Nginx (produção):** serve o build estático e faz proxy de `/api` com
`proxy_buffering off` (essencial p/ SSE não bufferizar) e
`client_max_body_size 300M` (uploads grandes).

---

## 11. Bugs reais resolvidos (os mais instrutivos)

Estes valem ouro numa entrevista porque mostram depuração de verdade:

1. **RESP3 quebrava o KNN silenciosamente** *(está na memória do projeto)*
   O redis-py 8.x passou a usar **RESP3** por padrão. O helper `search()` do
   RediSearch não parseia RESP3 corretamente → KNN retornava **0 docs** mesmo com
   dados indexados (`num_docs=1`, mas `retrieve` vazio). **Fix:** forçar
   `protocol=2` (RESP2) no cliente. Diagnóstico foi por eliminação: confirmei que
   o dado existia e que a query estava certa, então o problema só podia ser
   serialização do protocolo.

2. **Recall ruim do HNSW** — com ~622 chunks, a busca devolvia o chunk certo com
   score 0.15 quando o esperado era ~0.80. O vetor armazenado estava correto
   (cosseno 0.80 confirmado na mão); o HNSW só não o *encontrava* com a largura de
   busca padrão. **Fix:** `EF_RUNTIME=128`. HNSW é um índice **aproximado** —
   `EF_RUNTIME` controla quantos candidatos ele explora; baixo demais = ele "passa
   batido" pelo vizinho verdadeiro. **Tradeoff:** EF maior = recall melhor, custo
   de latência um pouco maior (aceitável aqui).

3. **413 só pelo front** — upload funcionava no Swagger mas dava 413 pelo front.
   Causa: limite **default do Nginx (1MB)**, não do FastAPI. **Fix:**
   `client_max_body_size 300M`.

4. **"Upload conclui mas não indexa"** — erro de chave OpenAI ausente; raiz era um
   **typo no `.env`** (`TOPENAI_API_KEY`). Lição: validar a config cedo e dar erro
   claro. (O valor da chave nunca foi exposto ao depurar.)

5. **Imagem de 9.18GB → 960MB** — `sentence-transformers` arrasta o **torch**.
   **Fix:** tornar embeddings locais **opt-in** (`requirements-local.txt` +
   `INSTALL_LOCAL_EMBEDDINGS`). Por padrão a imagem usa providers de API (leves).

6. **Texto da fonte "uma palavra por linha"** — CSS: `.source-chunk` herdava
   `white-space: pre-wrap` da bolha. **Fix:** `white-space: normal` +
   `overflow-wrap: anywhere`.

---

## 12. Testes

- **pytest + fakeredis** para unit tests (rápidos, sem Redis real).
- SDKs de provider são injetados como **módulos fake via `sys.modules`** — cada
  branch das factories é exercitado sem instalar/chamar OpenAI/Anthropic/etc.
- **Teste de integração** (`test_retriever_integration.py`) roda contra um Redis
  Stack **real** (auto-pula se indisponível), exercitando criação de índice, query
  KNN, dimensão e serialização float32 — coisas que o mock não cobre.
- **Cobertura: 100%** (o case pedia ≥60%). Gate em 95% no `pyproject.toml`.
- **CI (GitHub Actions):** jobs `backend-tests`, `frontend-build` e
  `integration-tests` (com serviço redis-stack).

**Tradeoff de cobertura 100%:** alguns trechos (fallback de import do redis-py,
OCR nativo) usam `# pragma: no cover` porque dependem de ambiente nativo — cobrir
de verdade exigiria infra que não agrega valor de teste.

---

## 13. Docker / Infra

- **Multi-stage no frontend:** Vite build → Nginx (imagem final só com estáticos).
- **Build args** no backend: `INSTALL_LOCAL_EMBEDDINGS` e `INSTALL_OCR` ligam as
  dependências pesadas só quando necessário.
- **Compose:** API + Redis Stack + frontend; `depends_on` com healthcheck; volume
  para persistir os dados do Redis.
- Um comando: `docker-compose up --build`.

---

## 13b. Login opcional (OAuth) + isolamento por usuário

Adicionado depois: **local roda sem login**; **em produção** exige entrar com
Google ou GitHub, e cada usuário só vê seus próprios documentos/conversas.

**A decisão que amarra tudo — um único caminho de código:** toda operação é
escopada por um `user_id`.
- `AUTH_ENABLED=false` (default, local) → `user_id = "public"`. Nenhum token
  exigido; comportamento idêntico ao de antes.
- `AUTH_ENABLED=true` (produção) → exige token; `user_id` = identidade OAuth.

Assim ingestão, busca e histórico têm **um só código**, parametrizado por
`user_id`. O `get_current_user` (dependency) devolve o usuário público quando o
login está off e valida o token quando está on.

**Mecanismo (por que token e não cookie):** o handshake OAuth roda no backend
(Authlib + `SessionMiddleware`, cookie só durante o handshake). No callback o
backend emite um **token assinado** (itsdangerous) e redireciona para o front
com o token no **fragmento** da URL (`#token=...`, não vai a logs nem ao
servidor). O front guarda no `localStorage` e manda como `Authorization: Bearer`
— mesmo padrão do BYOK. A API continua **stateless**, o que evita a dor de
**cookies cross-site** quando front e back estão em domínios diferentes (Render).

**Isolamento no Redis:** cada chunk ganhou um campo `user_id` (TAG no índice). A
busca virou uma **query híbrida**: pré-filtra por dono e só então faz o KNN —
`(@user_id:{id})=>[KNN ...]`. O histórico passou a ter chave namespeada por
usuário (`session:{user_id}:{session_id}`). O delete confere o dono antes de
remover (um usuário não apaga documento de outro).

**Tradeoffs:**
- O `user_id` é sanitizado para alfanumérico/underscore no login, para entrar
  direto como valor de TAG sem precisar de escaping na query.
- Mudou o schema do índice (campo novo) → no startup, se o índice antigo não tem
  `user_id`, ele é dropado e recriado; documentos antigos sem o campo ficam
  invisíveis e precisam de re-upload (em deploy novo não há legado).
- `SessionMiddleware` é sempre instalado (inofensivo quando o login está off: sem
  escrita, sem cookie) — simplifica o app e os testes.
- Modelo adequado a produção real (dados separados por conta), mas sem perfis/
  papéis/quotas — escopo de portfólio.

---

## 14. Mapa de decisões × tradeoffs (resumo para revisão rápida)

| Decisão | Por quê | Tradeoff |
|---|---|---|
| RAG (não fine-tune) | Documentos mudam; precisa citar fonte | Qualidade depende do retrieval |
| LangGraph (4 nós) | Exigência do case + extensível | Overkill p/ fluxo linear |
| Embeddings fixo no servidor | Dimensão do índice é imutável | Usuário não escolhe o embedder |
| LLM por requisição (BYOK) | Hospedar sem expor/pagar chave | Sem auth → só p/ demo |
| Chunk por tokens | Casa com orçamento do LLM | Overlap duplica texto |
| `EF_RUNTIME=128` | Recall correto no HNSW | +latência pequena |
| `protocol=2` (RESP2) | RESP3 quebra o KNN | Perde features do RESP3 |
| Embeddings locais opt-in | Imagem 960MB vs 9GB | PDF/local exige rebuild |
| OCR opt-in | Build rápido por padrão | Escaneado só com `INSTALL_OCR` |
| `decode_responses=False` | Vetor é bytes float32 | Decode manual no texto |
| Cobertura 100% | Confiança/qualidade | `pragma: no cover` em código nativo |

---

## 15. O que ficou de fora (e por quê)

- **Deploy em nuvem com link** — único diferencial do PDF não entregue; é
  **opcional**. Caminho planejado é gratuito (Render + Redis Cloud, BYOK para não
  subir chave). Foi deixado para o fim conscientemente.
- **Autenticação / multitenancy** — fora do escopo de uma demo; documentos vivem
  num índice único compartilhado.

---

## 16. Perguntas prováveis numa entrevista (e a resposta curta)

- *"Por que Redis e não um vector DB dedicado (Pinecone, pgvector)?"* — Redis
  Stack já traz RediSearch com HNSW, é um só container, zero custo, e o case
  sugeria Redis. Para escala maior, trocaria a camada `redis_client`/`retriever`
  sem tocar no resto (a abstração permite).
- *"Como você garante que o LLM não alucina?"* — system prompt restringe a
  responder só pelo contexto e a dizer quando não achar; e as fontes ficam
  visíveis para auditoria.
- *"E se dois embeddings tiverem dimensões diferentes?"* — não acontece: o
  embedder é fixo no servidor e a dimensão do índice deriva do modelo (`config`).
- *"Como testou sem gastar com API?"* — fakes via `sys.modules` nos unit tests e
  embeddings determinísticos no teste de integração.
- *"Maior bug que você pegou?"* — o RESP3 quebrando o KNN silenciosamente; achei
  por eliminação (dado existia, query correta → só sobrava o protocolo).
```
