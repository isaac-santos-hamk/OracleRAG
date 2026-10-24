# Oracle RAG

## Team members

- Isaac Lívi dos Santos (isaac.lividossantos@student.hamk.fi)
- Ronak Kadyan (ronak.kadyan@student.hamk.fi)
- Shreshtha Kumar (shreshtha.kumar@student.hamk.fi)

## Problem

### Intended users
- The primary target users for this application are players and Game Masters of Tabletop Role-Playing Games (TTRPG).

### Problem statement
- Players and Game Masters need to be able to answer questions regarding game rules quickly during a session.
- The application solves this problem by allowing users to upload their own rulebooks and extract accurate answers from them.

### Why AI is appropriate
- Traditional deterministic solutions rely on literal keyword searches, whereas TTRPG rules require natural language understanding to parse complex context and intent. AI (specifically through RAG) perfectly fills the need to both find the rule and interpret it to provide a direct answer to the user's question.

## Solution

The project is a rules arbiter for TTRPG players and Game Masters. The core value proposition of the application is to read uploaded PDF rulebooks with Docling, store their embeddings in ChromaDB, and retrieve relevant passages through a native Python RAG pipeline with BM25 lexical re-ranking. The retrieved context is passed to a local Ollama model (`llama3.2:3b` by default). By employing strict system prompts, we guarantee that the system will output answers only using the provided rulebook context, mitigating the risk of hallucinated rules. The system also includes short-term conversational memory to handle follow-up questions effectively.

## Main user workflow

1. **User Input:** The user uploads the rulebook and submits a query via a Streamlit user interface.
2. **Processing & Guardrails:** The application service layer (`src/services/ai_service.py`) validates and formats the request. The native RAG pipeline combines ChromaDB similarity search with BM25 reciprocal-rank-fusion re-ranking to identify relevant context.
3. **Model Response:** The model client calls the configured model via the local Ollama server and returns the formatted response back through the service layer to the UI.

## Technologies Summary

- **Environment Manager:** Conda
- **User Interface:** Streamlit
- **Local Model Serving & Inference:** Ollama running `llama3.2:3b`
- **Document Ingestion & Semantic Chunking:** Docling
- **Vector Storage:** ChromaDB
- **Lexical Search & Re-Ranking:** Rank-BM25
- **Data Validation & Schemas:** Pydantic
- **Automated Testing:** Pytest

## Architecture

The implemented architecture is documented in [`docs/architecture.md`](docs/architecture.md).

```text
User
  ↓
Streamlit UI (app/ui.py)
  ↓
Application / AI Service (src/services/ai_service.py)
  ├── ConversationMemory (src/capabilities/memory.py)
  ├── RAGPipeline (src/capabilities/rag.py)
  │     ├── Docling document conversion and semantic chunking
  │     ├── ChromaDB persistent vector storage
  │     └── BM25 lexical re-ranking with reciprocal rank fusion
  └── OllamaModelClient (src/models/model_client.py)
          ↓
      Ollama (local inference server)
          ↓
      Configured local model (llama3.2:3b)
```
> **Core Architectural Rule:** The user interface NEVER communicate directly with the model client or Ollama. All interactions pass through the service layer (`ai_service.py`).

## Model

- **Model used:** `llama3.2:3b` by default, configurable through `MODEL_NAME` (running locally via Ollama).
- **Selection rationale:** This model was chosen because it is lightweight and performs efficiently on local hardware.

## Additional AI capability

Select at least one additional capability to implement for your final project:

- [x] RAG (Retrieval-Augmented Generation)
- [ ] Tools / External API integration
- [ ] Model Context Protocol (MCP)
- [ ] Agentic workflow (Model-selected actions based on observations)
- [x] Memory / Persistent state
- [ ] Multimodal interaction (Text + Images)
- [ ] Other: ______________________

### Capability justification

- The implementation of **RAG** is the core mechanism of the tool, allowing the application to ingest and search original rulebooks uploaded by users.
- The addition of **Memory / Persistent state** provides conversational functionality, allowing players to ask follow-up or clarifying questions without repeating the full context.

## Setup

### 1. Create the Conda environment

```bash
conda env create -f environment.yml
```

### 2. Activate the environment

The environment is named `oracle_rag` in [`environment.yml`](environment.yml):

```bash
conda activate oracle_rag
```

### 3. Configure environment variables

Copy `.env.example` to create your local `.env` configuration file:

On Linux / macOS:
```bash
cp .env.example .env
```

On Windows (Command Prompt / PowerShell):
```powershell
copy .env.example .env
```

Ensure `.env` contains valid values for your local environment:
```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama3.2:3b
MODEL_TEMPERATURE=0.0
OLLAMA_TIMEOUT=180.0

# Vector Database & RAG Configuration
CHROMA_DB_DIR=./data/chroma
RAG_COLLECTION_NAME=oracle_rules
SIMILARITY_THRESHOLD=1.2
RAG_TOP_K=6
```

### 4. Start Ollama

Make sure Ollama is installed and running locally, then pull your configured model:

```bash
ollama run llama3.2:3b
```

### 5. Run the application

From the project root, start the Streamlit application with:

```bash
streamlit run app/main.py
```

Streamlit serves the application at `http://localhost:8501` by default. The
application requires Streamlit's runtime.

### 6. Run automated tests

```bash
pytest
```

## Evaluation

We evaluated Oracle RAG across 11 iterative development rounds using an automated benchmark suite ([`evaluation/evaluation.py`](evaluation/evaluation.py)) against 27 structured test cases covering three distinct categories:
- **Successful Cases (9 cases):** Standard rules lookups and combat actions across diverse RPG systems.
- **Difficult Cases (12 cases):** Multi-turn conversational memory, rule synthesis, anti-premise protection, and multi-tome consultations.
- **Failure / Guardrail Cases (6 cases):** Prompt injection defense, out-of-scope non-RPG queries, and empty inputs.

### Round 11 Key Results

| Metric | Result |
| :--- | :--- |
| **Strict Pass Rate** | **15 / 27 (55.6%)** |
| **Partial Credit Rate** | **10 / 27 (37.0%)** |
| **Failed Rate** | **2 / 27 (7.4%)** |
| **Grounded & Safe Response Rate (Pass + Partial)** | **25 / 27 (92.6%)** |
| **Cross-System Rule Bleed / Hallucinations** | **0 / 27 (0.0%)** |
| **Timeouts / Stalled Inferences** | **0 / 27 (0.0%)** |
| **Average Response Latency** | **11.16 seconds** |

For more information, refer to [`evaluation/evaluation_results.md`](evaluation/evaluation_results.md) and [`evaluation/test_cases.json`](evaluation/test_cases.json).

## Known limitations

- **Memory Restraints & Question-Only Window:** Conversational memory maintains a sliding window of the last 3 user turns for reference resolution. To strictly prevent self-poisoning and hallucination feedback loops, prior assistant responses are excluded from the prompt context, meaning the Oracle cannot refer back to its own previous conversational verdicts.
- **Strict Fallback Refusal:** The model will never guess or extrapolate mechanics outside the provided text. If retrieval confidence falls below the similarity threshold, or if an action assumes mechanics from an unindexed companion rulebook, the system outputs an explicit refusal decree rather than improvising.
- **Multi-Clause Rule Synthesis:** While the compact `llama3.2:3b` model ensures fast tabletop latency, it can occasionally hedge or omit secondary constraints when required to synthesize 3 or more disjoint, multi-condition rules clauses in a single query.
- **OCR of Scanned Complex Tables:** Scanned rulebook PDFs with unbordered tables, decorative sidebars, or mathematical fractions may occasionally suffer from OCR parsing artifacts during Docling conversion.
- **Document Ingestion Processing Time:** Thorough document layout analysis and OCR extraction with Docling require significant CPU/GPU compute. Ingesting dense 300+ page rulebooks takes noticeable time before vector persistence is completed.

## Future improvements

- **Metadata Breadcrumbs & Hierarchical Chunking:** Enrich chunk metadata during Docling ingestion with full hierarchical path headers (`System > Edition > Chapter > Section`) and merge short sibling subsections to preserve context across multi-condition rules.
- **OCR Artifact & Table Normalization:** Add automated preprocessing and regex sanitization during ingestion to correct fragmented tabular fractions and unbordered tables in scanned rulebooks.
- **Sub-Query Decomposition for Complex Queries:** Automatically split multi-condition user inquiries into atomic rule lookups before passing them to the hybrid retrieval pipeline.
