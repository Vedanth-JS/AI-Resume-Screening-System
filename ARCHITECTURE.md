# System Architecture - Antigravity AI ATS

Antigravity is built on a modern, high-concurrency architecture that prioritises scalability, developer experience, and AI reliability.

---

## 🏛 Architectural Decisions

### Why FastAPI over Django?
- **Asynchronous First**: FastAPI's native support for `async/await` allows the system to process high volumes of concurrent I/O operations (API calls, database queries) efficiently.
- **Pydantic V2**: Provides high-performance data validation and automatic OpenAPI documentation, reducing boilerplate significantly compared to DRF.

### Why Gemini 1.5 Flash over OpenAI?
-   **Lower Latency**: Gemini 1.5 Flash is optimised for speed, making it ideal for the high-volume resume parsing required in an ATS.
-   **Massive Context Window**: Allows for deep analysis across long, multi-page CVs without truncation.

### Why pgvector over Pinecone?
-   **Unified Storage**: Storing relational application data and vector embeddings in the same database (PostgreSQL) reduces operational complexity and ensures atomic consistency.
-   **SQL-Native**: Allows for complex queries that combine traditional metadata (e.g., location, experience) with semantic similarity in a single scan.

---

## 🌊 Data Flow: Resume Screening Pipeline

The screening process is entirely asynchronous to ensure a responsive UI for recruiters.

1.  **Ingestion**: User uploads a set of PDFs via the `BulkUpload` API.
2.  **Preprocessing**: `PDFExtractor` converts files into raw text with a fallback strategy (PyMuPDF -> pdfminer).
3.  **Task Queuing**: A Celery `Chord` is created for the batch. Individual `screen_resume` tasks are pushed to the Redis `screening` queue.
4.  **AI Pipeline**:
    *   **ParserAgent**: Extracts structured JSON from raw text.
    *   **SkillMatcher**: Computes semantic overlap between JD requirements and extracted skills.
    *   **BiasDetector**: Flags name, age, or gender bias in the screening reasoning.
    *   **ScoringAgent**: Aggregates weights and generates a final 0-100 score.
5.  **Finalization**: The chord callback triggers a notification to the recruiter and updates the `BatchJob` status.

---

## 📈 Scaling Considerations
Antigravity is designed to scale horizontally across multiple instances.

### Handling 10k+ Resumes/Day
-   **Horizontal Worker Scaling**: Additional Celery workers can be spawned on separate nodes to handle peak ingestion volumes.
-   **Rate Limiting**: Integrated Redis token-bucket rate limiting prevents AI API quota exhaustion.
-   **Task Consolidation**: Pre-parsing resumes (once) and caching embeddings allows for rapid re-screening against new job postings without redundant LLM calls.

---

## 🛡️ Security Model
- **Auth**: Secure JWT-based authentication with high-entropy `SECRET_KEY` and Bcrypt hashing.
- **Multi-Tenancy**: Application-level data isolation using `org_id` filters on every repository query and middleware-enforced tenant context.
- **Audit Trails**: Every AI decision and recruiter action is logged in a tamper-evident `audit_logs` table with model versions and input/output hashes.
