# SOL AI: Django Service Lifecycle & Architecture Notes

**Document**: `DJANGO_MIGRATION_NOTES.md`  
**Phase**: P0 / Step 1 (Backend Migration to Django)  
**Date**: September 29, 2026  

---

## 1. Service Lifecycle and Initialization Architecture

### 1.1 Problem Analysis
In SOL AI, initializing `RetrievalEngine` is an expensive operation (~0.98s):
- It instantiates multiple linguistic resource adapters (`ThamizhiMorphAdapter`, `ThaniThamizhAkarathiAdapter`, `TamilWordNetAdapter`, `SentamizhAdapter`, `TamilWiktionaryAdapter`).
- It opens persistent SQLite database handles (WordNet, Sentamizh, Wiktionary).
- It verifies Foma FST finite-state morphological binaries.
- It parses or loads JSON dictionary indices.

If this initialization were executed inside an HTTP view function or recreated per-request:
- Every query would incur a ~1,000ms latency penalty.
- Concurrent SQLite connection churn could exhaust system file descriptors.

Conversely, if initialization were placed blindly in global module scope or eagerly triggered on Django import:
- `manage.py check`, `manage.py test`, `manage.py makemigrations`, or CLI utilities would unexpectedly trigger full resource loading and database opening.
- Django's development auto-reloader spawns two processes (a monitor process and a worker process), causing duplicate initialization and doubled memory usage.
- Unit tests mocking or inspecting views would suffer unnecessary slow startups.

---

## 2. Chosen Design: Lazy Process-Local Service Registry

The final implementation in [`backend/sol_django/api/services.py`](file:///c:/Vishwa/Projects/SOL_AI/backend/sol_django/api/services.py) uses a **Thread-Safe, Lazy Process-Local Service Registry** (`SOLServiceRegistry`).

### 2.1 Concurrency & Isolation Characteristics
1. **Thread-Safe Double-Checked Locking**:
   - The registry uses `threading.Lock()` to prevent race conditions during the initial request under multithreaded workers (Gunicorn threads, uWSGI threads, Django runserver).
2. **Process-Local Scope**:
   - The singleton `_instance` and its `_engine` reference reside in process memory.
   - When running multi-process servers (e.g. Gunicorn with multiple worker processes), each process lazily initializes its own isolated engine.
   - **No cross-process state** or shared memory IPC is introduced. SQLite connections remain thread-safe and process-safe.
3. **Lazy First-Query Initialization**:
   - Non-query endpoints like `GET /api/health` and `GET /health` execute in **< 1ms** because they never access or trigger `RetrievalEngine`.
   - `RetrievalEngine` is initialized only when the first `POST /api/query` arrives in that worker process.
4. **Clean Management Command Decoupling**:
   - `python manage.py check` executes in **< 0.1s** with zero resource adapter loading.
5. **Autoreload Safety**:
   - Autoreload process monitor never touches `RetrievalEngine`.
6. **Optional Eager Pre-warming**:
   - For production environments where zero cold-start latency is desired, setting `SOL_PREWARM_ON_STARTUP=true` in `.env` triggers `AppConfig.ready()` in `api/apps.py` to pre-warm the engine inside the active worker process (`RUN_MAIN=true` or non-reload mode).

---

## 3. Layer Separation Architecture

```
HTTP Request (Browser / Extension / CLI)
    ↓
Django Middleware (CORS headers, routing)
    ↓
api/views.py (Request validation, status code mapping, JSON serialization)
    ↓
api/services.py (SOLServiceRegistry: engine lookup, EvidencePack orchestration, fallback, overrides)
    ↓
backend/retrieval/engine.py (RetrievalEngine: multi-pass surface/lemma lookups)
    ↓
backend/resources/ (ThamizhiMorph, WordNet, Akarathi, Sentamizh adapters)
```

### Strict Boundary Guarantees:
- **`api/views.py`**: Contains zero morphological parsing, zero dictionary lookup, zero literary context logic, and zero direct imports of resource adapters.
- **Domain code**: `backend/retrieval/`, `backend/interpretation/`, and `backend/resources/` have zero dependencies on Django (`import django` is completely forbidden in domain layers).
- **ORM Independence**: No Django ORM models or database migrations were created. Linguistic datasets remain managed by their specialized high-performance domain adapters.

---

## 4. Error Handling & Degradation Mapping

| Scenario | HTTP Status | Response Contract |
| :--- | :---: | :--- |
| Empty request body | `400` | `{"error": "Missing JSON payload..."}` |
| Malformed JSON | `400` | `{"error": "Invalid JSON payload in request body."}` |
| Missing or whitespace `query` | `400` | `{"error": "Field 'query' is required and cannot be empty."}` |
| Unknown endpoint | `404` | `{"error": "Endpoint not found: <path>"}` |
| Missing provider API key | `400` | `{"error": "<PROVIDER>_API_KEY environment variable is not configured..."}` |
| Primary LLM failure | `200` | Fallback cascade (Primary -> Groq -> Mock) returning structured grounded response |
| Unhandled server crash | `500` | `{"error": "An error occurred while processing query..."}` |
