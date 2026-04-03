# Portfolio Project Summary - Antigravity AI ATS

This document provides a concise overview of the technical achievements and business value delivered by the Antigravity project, specifically designed for placement interviews and portfolio reviews.

---

## 🎯 Problem Statement
Recruitment teams at high-growth tech firms face an "applicant avalanche," where 1000s of resumes are uploaded for a single role. Manual screening is slow, prone to cognitive bias, and inconsistent. Organizations need a system that can pre-parse and score resumes at scale while maintaining fairness and transparency.

## 🛠 Technical Challenges & Solutions

### 1. High-Performance Text Extraction
- **Challenge**: Parsing complex, multi-column PDF resumes without losing structure or character encoding.
- **Solution**: Developed a dual-strategy `PDFExtractor` using `PyMuPDF` for high-speed primary parsing and `pdfminer.six` as a high-accuracy fallback for legacy or non-standard PDF formats.

### 2. Multi-Agent AI Pipeline
- **Challenge**: Generic LLM prompts often miss domain-specific nuances (e.g., distinguishing between 'Java' and 'JavaScript').
- **Solution**: Architected a 4-agent LangGraph pipeline:
    *   **ParserAgent** (Extraction)
    *   **SkillMatcher** (Semantic Alignment)
    *   **BiasDetector** (Fairness Audit)
    *   **ScoringAgent** (Final Decision)
  This modularity allows for improving specific parts of the pipeline (like switching models for parsing) without affecting the scoring logic.

### 3. Asynchronous Orchestration at Scale
- **Challenge**: Web servers blocking while waiting for 20-30 second AI API calls, leading to 504 Timeouts.
- **Solution**: Decoupled the screening logic into an asynchronous background pool using **Celery, Redis, and Flower**. Implemented **SSE (Server-Sent Events)** to provide real-time UI updates on screening progress.

### 4. Database Optimization
- **Challenge**: Semantic search (finding "Software Engineer" using a "Backend Developer" query) is impossible with standard SQL `LIKE`.
- **Solution**: Leveraged **pgvector** and **Gemini Embeddings** to store and search vector representations of resumes, enabling high-recall semantic matching.

---

## 📊 Scale Metrics (Designed For)
- **Daily Volume**: Optimized to screen up to 10,000 resumes per day via horizontal worker scaling.
- **Inference Speed**: Average screening time of 3-5 seconds per resume using Gemini-1.5-Flash.
- **Concurrency**: 2 API replicas and 4-worker Celery pool providing sub-second UI responsiveness.

---

## 🙋 Interview Q&A Preparation

### "Why did you choose Gemini over OpenAI?"
**Answer**: "Gemini-1.5-Flash offers an industry-leading balance of speed, cost, and a massive 1M token context window. In an ATS context, the ability to process long, detailed resumes quickly while maintaining high instruction-following accuracy was the deciding factor."

### "How did you handle race conditions in the bulk upload flow?"
**Answer**: "We used Celery Chords for atomic batch finalization. Every file has a unique SHA256 hash stored in Redis, ensuring that duplicate uploads are detected and skipped before any expensive AI tasks are triggered, preventing redundant costs and state conflicts."

### "Tell me about a time you had to pivot your technical approach."
**Answer**: "Initially, I used synchronous API calls which caused the frontend to hang during large uploads. I pivoted to a distributed task queue architecture using Celery and Redis. This required a major shift in how the frontend tracks state, which I solved by implementing the SSE (Server-Sent Events) progress stream."
