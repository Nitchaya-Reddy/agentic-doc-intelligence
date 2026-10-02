# Agentic AI Document Intelligence Platform

A portfolio-grade **agentic RAG** application that ingests PDFs/text/Markdown, stores chunk embeddings in PostgreSQL + pgvector, and answers questions with source-grounded citations through a LangGraph workflow.

This version uses the **Gemini Developer API** instead of OpenAI so it can run on Google's free API tier within Google's current quota limits.

## Tech stack

**Python, FastAPI, React, LangChain, LangGraph, Gemini API, PostgreSQL/pgvector, Docker**

Default AI models:

- Chat / agent reasoning: `gemini-3.5-flash-lite`
- Text embeddings: `gemini-embedding-2`
- Embedding dimensions: `1536`

## What this project demonstrates

- **Agentic RAG:** query classification, retrieval, generation, fact verification, and conditional retry/human-review routing.
- **Vector + metadata retrieval:** pgvector cosine similarity with source/tag filters.
- **Grounded answers:** every answer is instructed to cite retrieved sources as `[S1]`, `[S2]`, etc.
- **Evaluation:** retrieval relevance, faithfulness, citation accuracy, citation coverage, and hallucination rate.
- **Guardrails:** prompt-injection detection, structured Pydantic outputs, restricted tool registry, low-confidence fallback, and coding-agent output verification.
- **Full stack:** FastAPI, React/Vite, PostgreSQL/pgvector, Docker Compose.

## Architecture

```text
React UI
  |
  v
FastAPI -------------------------------------------------------+
  |                                                            |
  +--> Document ingestion --> chunking --> Gemini Embedding 2  |
  |                                      |                     |
  |                                      v                     |
  |                               PostgreSQL + pgvector        |
  |                                                            |
  +--> Query API --> Guardrail --> LangGraph ------------------+
                               classify
                                  |
                               retrieve
                                  |
                               generate
                                  |
                                verify
                              /        \
                         finalize     retry (max 1)
                                         |
                                  human-review fallback
```

## LangGraph workflow

1. **classify** — Gemini returns a structured classification such as `document_qa`, `summary`, `comparison`, or `unsupported`.
2. **retrieve** — Gemini Embedding 2 embeds the query and pgvector performs cosine-distance search with optional source/tag filtering.
3. **generate** — Gemini creates an answer constrained to the retrieved context and explicit `[S#]` citations.
4. **verify** — deterministic metrics plus a second structured Gemini check evaluate factual grounding and confidence.
5. **route** — high-confidence answers finish; weak answers retry retrieval once with a larger `top_k`, then route to a human-review fallback.

## Free Gemini API setup

### 1. Create a Gemini API key

Open Google AI Studio:

https://aistudio.google.com/app/apikey

Create a key for a project on the Gemini Developer API free tier. You do **not** need an OpenAI API key for this project.

> Free-tier availability and rate limits are controlled by Google and may change. Do not enable a paid billing tier if your goal is to keep API usage free. Free-tier prompts/content may be handled differently from paid-tier data, so do not use confidential documents in a public portfolio demo.

### 2. Configure the project

```bash
cp .env.example .env
```

Open `.env` and paste only your key:

```env
GEMINI_API_KEY=your_google_ai_studio_key_here
GEMINI_CHAT_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_DIMENSIONS=1536
```

Never commit `.env` to GitHub. The repository ignores it through `.gitignore`.

### 3. Start everything

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## If you previously ran the OpenAI version

Embeddings created by different model families must not be mixed in the same vector index. Reset the local demo database once before ingesting documents with Gemini:

```bash
docker compose down -v
docker compose up --build
```

This deletes the **local Docker demo database volume**, so only run it if you do not need the existing local demo data.

## Local development

### Backend

From the repository root, copy `.env.example` to `.env` first. Then:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

When running the backend directly rather than through Docker, set `DATABASE_URL` to a PostgreSQL instance reachable from your host, for example:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/docintel
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## API examples

### Upload a document

```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@sample_docs/employee_handbook.txt" \
  -F 'tags=["hr","policy"]'
```

Uploading performs chunking + **Gemini Embedding 2** vectorization before storing the chunks in pgvector.

### Ask a question

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How many vacation days do employees receive?",
    "top_k": 5,
    "metadata_filter": {"tags": ["hr"]}
  }'
```

## Evaluation benchmark

A small benchmark is included at `backend/evals/sample_dataset.jsonl`.

```bash
cd backend
python -m app.evaluation.run_eval evals/sample_dataset.jsonl
```

Each run reports:

- `retrieval_relevance`: overlap between the question and retrieved source text.
- `faithfulness`: proportion of answer content terms supported by retrieved evidence.
- `citation_accuracy`: fraction of used citations that refer to valid retrieved sources.
- `citation_coverage`: whether substantive answer sentences include citations.
- `hallucination_rate`: `1 - faithfulness`.

The live LangGraph verifier combines these transparent deterministic metrics with a structured Gemini factuality judgment.

## Security / AI guardrails

- Detects common prompt-injection phrases before graph execution.
- Treats document text as **untrusted data**, never executable instructions.
- Restricts the graph to an explicit tool allowlist (`retrieve_documents`).
- Uses Pydantic structured outputs for classification and verification.
- Rejects unsupported citation IDs through evaluation checks.
- Routes low-confidence outputs to retry and then human-review fallback.
- Includes a coding-agent output verifier that checks requested constraints, exposed API keys, and suspicious shell/destructive patterns without executing generated code.
- Keeps `GEMINI_API_KEY` server-side; the React frontend never receives it.

## Repository layout

```text
backend/app/
  api/                 FastAPI routes
  evaluation/          metric implementation + benchmark runner
  services/            Gemini client, ingestion, retrieval, guardrails
  graph.py             LangGraph orchestration
  models.py            SQLAlchemy models + pgvector column
  schemas.py           API + structured LLM schemas
frontend/src/          React application
sample_docs/           demo document
```

## Model / storage notes

- `gemini-embedding-2` supports configurable embedding dimensions. This project requests **1536** dimensions and defines the pgvector column with the same size.
- If you change `EMBEDDING_DIMENSIONS`, recreate the local vector table/database before ingesting data.
- If you change embedding **models**, re-embed your documents even when the dimensions happen to match.
- The Docker database image includes the pgvector extension.
- Uploaded files are processed in memory in this demo; add object storage such as GCS/S3 for a production deployment.

## Run tests

```bash
cd backend
pytest -q
```
