# Project Decisions

This document records the major architectural, algorithmic, and engineering decisions made during the design, development, and evaluation of **Oracle RAG**.

## Decision 1 — Model Selection

**Decision:**  
We selected a compact, non-reasoning local instruction model (`llama3.2:3b`) served locally via Ollama, configured with strict deterministic sampling (`temperature = 0.0`) and enforced Ollama client timeouts (`OLLAMA_TIMEOUT = 180.0`).

**Alternatives considered:**  
Across multiple evaluation rounds, we tested several open-weight local model families and parameter sizes to find the optimal balance between rule comprehension and live tabletop latency:

- **`qwen3:8b`:**  
  While demonstrating good linguistic depth and reasoning in standard queries, its active reasoning mode caused latency spikes and reasoning loops. In complex conditional queries, it stalled indefinitely causing time out errors.
- **`qwen2.5:3b`:**  
  Delivered fast inference, but produced noticeably lower answer quality. It struggled to reliably adhere to strict negative constraints, occasionally inventing filler mechanics when excerpts were partial.
- **`qwen2.5:7b`:**  
  Delivered well-structured, authoritative answers with excellent formatting, but local inference times were consistently too long for real-time tabletop pacing, frequently exceeding acceptable wait times.
- **`qwen3.5:4b`:**  
  Originally designated in our initial project proposal. During practical testing, however, it exhibited excessive generation latency and recurring token limit bottlenecks where response context limits were prematurely exhausted.
- **`llama3.2:1b`:**  
  Extremely lightweight and fast with near-zero latency, but its 1B parameter capacity was simply too constrained to reliably parse dense TTRPG jargon and conditional mechanics, leading to frequent reading comprehension errors.

**Why we chose this:**
- **Tabletop Session Latency:** In a live TTRPG session, a Game Master or player cannot halt game momentum for 60–120 seconds waiting for an answer. `llama3.2:3b` achieved a 100% completion rate with zero timeouts and an average response time of 11.2 seconds across all 27 evaluation cases.
- **Strict Arbiter Role:** In a rules assistant, creative extrapolation is a defect. Setting `temperature = 0.0` combined with explicit anti-premise prompt constraints forces `llama3.2:3b` into an impartial arbiter role.
- **Hardware Accessibility:** With an active memory inferior to 3 GB of VRAM, the model runs smoothly on standard consumer laptops and older dedicated GPUs, making it possible for players or Game Masters to run it locally without high-end hardware.

## Decision 2 — Additional AI Capabilities (RAG + Conversational Memory)

**Decision:**  
We implemented two additional AI application capabilities beyond basic model interaction:
1. **Retrieval-Augmented Generation (RAG)** featuring Docling document conversion, semantic chunking (`HybridChunker`), ChromaDB vector persistence, and a **Hybrid BM25 Reciprocal Rank Fusion (RRF)** re-ranking pipeline.
2. **Short-Term Conversational Memory** (`ConversationMemory`) maintaining a sliding window of the last 3 user turns for reference resolution.

**Why it is needed:**
- **TTRPG Grounding & Hallucination Elimination:** TTRPG rulebooks span hundreds of pages of complex, interlocking systems. Standard LLMs frequently confuse game editions or bleed mechanics across distinct rule systems. RAG grounds every response in authoritative, cited text segments and triggers strict fallback refusals when rules are not found in the indexed scripture.
- **Why Hybrid BM25 RRF was added:** Vector-only embeddings can cluster technical RPG jargon (such as "Bonus Die", "Penalty Die", or "Sanity Loss") with general dice-rolling passages. Integrating an in-memory `rank-bm25` index with Reciprocal Rank Fusion ensures exact rule terminology receives priority ranking without incurring neural re-ranker latency.
- **Why Conversational Memory is needed:** Players naturally ask follow-up questions at the game table, for example: *"What if the target is one size larger?"* or *"Can I escape on my next turn?"*. A pure single-turn system forces users to retype all rules context. Short-term memory provides reference resolution while intentionally capping history to 3 turns to prevent context window saturation and avoid polluting rule prompts.

**Alternatives considered:**
- **Full Conversational History (Unbounded Memory):** Rejected because retaining the entire chat session causes prompt bloat, increases inference latency, and causes old combat encounters to bleed into unrelated rules inquiries.
- **Cross-Encoder Neural Re-Rankers:** Evaluated for retrieval improvement, but rejected in favor of BM25 RRF to avoid adding heavy neural model dependencies and runtime latency on local machines.

## Decision 3 — System Architecture

**Decision:**  
We designed a clean, layered architecture featuring a **Streamlit UI**, an authoritative service layer (`AIService`), and a **native, lightweight Python RAG pipeline**, deliberately **removing LangChain from the project entirely**.

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

**Why we made these architectural choices:**

1. **Strict UI Isolation Rule:**  
   The UI layer (`app/ui.py`) never communicates with the LLM client, vector database, or document chunker directly. All interactions flow through typed Pydantic request/response schemas (`UserRequest`, `AIResponse`, `RuleCitation`) handled by `AIService`. This decouples the presentation from the business logic and allows automated testing without running Streamlit.

2. **Why LangChain was Removed:**  
   The starter template initially suggested LangChain. We removed it early in development for three key reasons:
   - **Elimination of Dependency Bloat:** LangChain imports a considerable amount of transitive dependencies.
   - **Transparency & Maintainability:** Our custom `RAGPipeline` and `AIService` are written in clean, standard Python. There are no opaque abstractions, hidden prompt wrappers, or complex execution graphs. Chunking, retrieval, score filtering, and prompt delivery are 100% visible and debuggable.
   - **Fast, Deterministic Tests:** Without LangChain's initialization overhead, our entire automated test suite executes in just a couple of seconds.

3. **Why Streamlit Replaced Gradio:**  
   The starter template shipped with Gradio. We transitioned to Streamlit because:
   - It supported an immersive, responsive "Arcane Tome" dark-fantasy aesthetic tailored to tabletop players and Game Masters.
   - It allowed robust state management across multiple independent chat sessions and native elements to handle the necessities of our project.

## Decision 4 — Multi-Tome Consultation & Balanced Retrieval

**Problem Domain Scope & Context:**  
In standard tabletop play, Game Masters and players consult rulebooks from a single game system at a time, as any given campaign operates under one consistent ruleset. Consequently, simultaneous multi-system consultation was outside the original problem domain. 

However, we decided to extend the application to handle multi-tome consultations robustly, turning the Oracle into a more versatile tool.

**Decision:**  
When multiple rulebooks are selected in the library, the retrieval engine executes **balanced per-tome querying with round-robin allocation** rather than a single global vector search.

**Why:**  
In testing, querying multiple tomes resulted in the larger rulebook drowning out the smaller book due to collection density. By retrieving top candidates per tome and balancing across tomes using relevance-weighted round-robin allocation, the Oracle guarantees fair representation across all consulted game systems.