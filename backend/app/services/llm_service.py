"""
LLM Service — all Gemini API calls.
Uses google-generativeai with structured prompts and robust JSON parsing.

Retry strategy (tenacity):
  - max 4 attempts
  - exponential backoff: 1s → 2s → 4s → 8s (capped at 60s)
  - retries on: network errors, 429 rate limits, 500 server errors
"""
import json
import re
import time
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from ..core.config import settings
from ..core.logger import log

# ─── Tenacity retry setup ──────────────────────────────────────────────────────
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception,
        RetryError,
    )
    _TENACITY_AVAILABLE = True
except ImportError:
    _TENACITY_AVAILABLE = False
    log.warning("tenacity_not_installed", note="Install tenacity for LLM retry support.")

def _is_retryable(exc: Exception) -> bool:
    """Return True if the exception is a transient LLM error worth retrying."""
    msg = str(exc).lower()
    return any(kw in msg for kw in [
        "429", "rate limit", "quota", "resource exhausted",
        "503", "502", "500", "internal server error",
        "connection", "timeout", "deadline", "transport",
    ])


def _make_retry_decorator():
    """Build a tenacity retry decorator if available; else return identity."""
    if not _TENACITY_AVAILABLE:
        def noop(fn):
            return fn
        return noop
    return retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )


_llm_retry = _make_retry_decorator()

# ─── Gemini setup ─────────────────────────────────────────────────────────────
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    _model = genai.GenerativeModel("gemini-1.5-flash")
    _embedding_model = "models/text-embedding-004"
else:
    _model = None
    _embedding_model = None
    log.warning("gemini_not_configured", note="Set GOOGLE_API_KEY for AI features.")


@_llm_retry
def _embed_with_retry(text: str, task_type: str = "retrieval_document") -> List[float]:
    """
    Synchronous Gemini embedding call wrapped in tenacity retry.
    Separated so tenacity can intercept and retry without async complexity.
    """
    result = genai.embed_content(
        model=_embedding_model,
        content=text,
        task_type=task_type,
        title="Resume Content",
    )
    return result["embedding"]


async def get_embedding(text: str) -> List[float]:
    """Generate 768-dim vector using Gemini's text-embedding-004 with retry."""
    if not _embedding_model or not text:
        return []
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _embed_with_retry, text)
    except Exception as e:
        log.error("gemini_embedding_error", error=str(e))
        return []


# ─── JSON parsing ──────────────────────────────────────────────────────────────

def _parse_json_response(text: str) -> Optional[Dict]:
    """Robustly extract JSON from a Gemini response (may be wrapped in ```json blocks)."""
    if not text:
        return None
    # Strip markdown code fences
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Try to find the first { ... } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


def _generate_xai_fallback(
    score_breakdown: dict,
    candidate_name: str,
    job_title: str = "",
) -> dict:
    """Rule-based XAI when LLM is unavailable."""
    b = score_breakdown
    verdict = "ACCEPT" if b.get("overall_score", 0) >= 70 else \
              "REVIEW"  if b.get("overall_score", 0) >= 40 else "REJECT"
    missing = b.get("keyword_detail", {}).get("missing", [])
    matched = b.get("keyword_detail", {}).get("matched", [])
    return {
        "verdict": verdict,
        "overall_score": b.get("overall_score", 0),
        "reasoning": {
            "keyword":    f"Matched {len(matched)} required skills" + (f"; missing: {', '.join(missing[:3])}" if missing else "."),
            "semantic":   f"Semantic alignment with JD: {b.get('semantic_score', 0):.0f}%.",
            "format":     f"Resume format quality: {b.get('format_score', 0):.0f}%.",
            "section":    f"Section completeness: {b.get('section_score', 0):.0f}%.",
            "experience": f"Experience match: {b.get('experience_score', 0):.0f}%.",
        },
        "key_strengths": [f"Matched skill: {s}" for s in matched[:3]],
        "key_gaps":       missing[:3],
        "red_flags":      [],
        "hiring_recommendation": f"{verdict} — {candidate_name} scored {b.get('overall_score', 0):.1f}% overall.",
        "source": "rule_based",
    }


# ─── Core model caller with retry ────────────────────────────────────────────

@_llm_retry
def _call_model_sync(prompt: str) -> str:
    """Synchronous Gemini call wrapped in tenacity retry decorator."""
    if not _model:
        return ""
    resp = _model.generate_content(prompt)
    return resp.text or ""


async def _call_model(prompt: str, context: str = "") -> str:
    """Async Gemini call with tenacity retry — uses run_in_executor."""
    if not _model:
        return ""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _call_model_sync, prompt)
    except Exception as e:
        log.error("gemini_call_error", context=context, error=str(e))
        return ""


# ─── Agent-level LLM functions ────────────────────────────────────────────────

class GeminiService:
    @staticmethod
    async def generate_content(prompt: str) -> str:
        """Low-level method to call Gemini and return raw text."""
        return await _call_model(prompt)

    @staticmethod
    async def extract_resume_data(text: str) -> Dict[str, Any]:
        """Agent 1 — Resume Parser with few-shot example."""
        prompt = f"""You are an expert resume parser. Extract structured data from the resume text.

EXAMPLE OUTPUT:
{{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "phone": "+1 555-0123",
  "linkedin_url": null,
  "github_url": "github.com/janesmith",
  "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
  "education": [{{"school": "MIT", "degree": "B.S. Computer Science", "year": "2020"}}],
  "experience": [
    {{"company": "TechCorp", "role": "Senior Backend Engineer", "duration": "Jan 2021 – Present", "years": 3.5}},
    {{"company": "StartupX", "role": "Junior Developer", "duration": "Jun 2018 – Dec 2020", "years": 2.5}}
  ],
  "projects": [{{"title": "E-commerce API", "description": "Built scalable REST API handling 10k req/s", "technologies": ["FastAPI", "PostgreSQL", "Redis"]}}],
  "certifications": ["AWS Solutions Architect Associate", "Kubernetes CKAD"],
  "total_years_experience": 6.0,
  "summary": "Full-stack engineer with 6 years building high-throughput APIs and cloud-native systems.",
  "confidence": 0.95
}}

Now parse this resume:
{text[:6000]}

Return ONLY valid JSON with the same keys as the example. Include a "confidence" field (0-1) estimating extraction accuracy.
"""
        raw = await _call_model(prompt, context="extract_resume_data")
        parsed = _parse_json_response(raw)
        if parsed:
            parsed["raw_text"] = text
            if "confidence" not in parsed:
                parsed["confidence"] = 0.7
        else:
            # Retry with shorter text
            raw2 = await _call_model(prompt[:2000], context="extract_resume_data_retry")
            parsed = _parse_json_response(raw2) or {}
            parsed["raw_text"] = text
            parsed["confidence"] = 0.3
        return parsed

    @staticmethod
    async def analyze_jd(jd_text: str) -> Dict[str, Any]:
        """Agent 2 — JD Analyzer. Extracts structured JD profile."""
        prompt = f"""
You are a Job Description analyst. Analyze the JD below and return ONLY a JSON object:
{{
  "role_title": "string",
  "seniority_level": "junior | mid | senior | lead | manager",
  "must_have_skills": ["critical skills"],
  "nice_to_have_skills": ["bonus skills"],
  "required_experience_years": 0,
  "required_education": "string",
  "key_responsibilities": ["list"],
  "culture_signals": ["collaborative", "fast-paced"],
  "compensation_signals": "remote | hybrid | onsite | not_specified"
}}

Job Description:
{jd_text[:4000]}
"""
        raw = await _call_model(prompt, context="analyze_jd")
        return _parse_json_response(raw) or {
            "role_title": "Unknown",
            "must_have_skills": [],
            "nice_to_have_skills": [],
            "required_experience_years": 0,
        }

    @staticmethod
    async def generate_interview_questions(
        resume_gaps: List[str],
        jd_text: str,
        candidate_name: str = "the candidate",
    ) -> List[Dict[str, str]]:
        """Agent 5 — Interview Question Generator."""
        gaps_str = ", ".join(resume_gaps) if resume_gaps else "general fit"
        prompt = f"""
You are a technical interview expert. Generate exactly 5 targeted interview questions
for {candidate_name} based on their skill gaps ({gaps_str}) vs this job description.

Job Description (excerpt):
{jd_text[:2000]}

Return ONLY a JSON array of 5 objects:
[
  {{
    "question": "Specific interview question text",
    "rationale": "Why this question targets a gap or verifies a strength",
    "type": "technical | behavioral | situational | system_design"
  }}
]
"""
        raw = await _call_model(prompt, context="generate_interview_questions")
        raw_clean = re.sub(r"```json\s*|```\s*", "", raw or "").strip()
        try:
            result = json.loads(raw_clean)
            if isinstance(result, list):
                return result[:5]
        except Exception:
            pass
        return [{"question": "Tell me about your relevant experience.", "rationale": "General fit", "type": "behavioral"}]

    @staticmethod
    async def detect_bias_llm(jd_text: str) -> Dict[str, Any]:
        """Enhanced bias detection with Gemini confidence scores."""
        prompt = f"""
You are an inclusive hiring expert. Analyze this job description for potential bias.
Return ONLY a JSON object:
{{
  "gender_bias": {{
    "detected": true/false,
    "confidence": 0.0-1.0,
    "masculine_coded_words": ["list"],
    "feminine_coded_words": ["list"],
    "verdict": "masculine_skewed | feminine_skewed | neutral"
  }},
  "age_bias": {{
    "detected": true/false,
    "confidence": 0.0-1.0,
    "signals": ["digital native", "fresh graduate", "seasoned"]
  }},
  "prestige_bias": {{
    "detected": true/false,
    "confidence": 0.0-1.0,
    "signals": ["top university", "ivy league"]
  }},
  "overall_bias_score": 0.0-1.0,
  "recommendations": ["actionable suggestion 1", "suggestion 2"]
}}

Job Description:
{jd_text[:3000]}
"""
        raw = await _call_model(prompt, context="detect_bias_llm")
        return _parse_json_response(raw) or {
            "overall_bias_score": 0.0,
            "recommendations": ["Could not perform LLM bias analysis. GOOGLE_API_KEY required."],
        }

    @staticmethod
    async def evaluate_candidate(jd: str, resume_text: str) -> str:
        """Legacy — full narrative evaluation (used in JobDetail view)."""
        if not _model:
            return "Gemini API key not configured. Evaluation unavailable."
        prompt = f"""
Analyze this candidate's resume against the Job Description.

Job Description:
{jd[:2000]}

Resume:
{resume_text[:3000]}

Provide a concise assessment:
1. Hiring Recommendation (Accept / Review / Reject) with 1-line reason
2. Top 3 Strengths
3. Top 3 Gaps vs. JD
4. Resume Improvement Tips (2-3 bullets)
"""
        return await _call_model(prompt, context="evaluate_candidate") or "Evaluation unavailable."

    @staticmethod
    async def compare_candidates(jd: str, resume1: str, resume2: str) -> str:
        """Side-by-side candidate comparison."""
        prompt = f"Compare these two candidates for the job:\n{jd}\n\nCandidate 1:\n{resume1[:2000]}\n\nCandidate 2:\n{resume2[:2000]}"
        return await _call_model(prompt, context="compare_candidates") or "Comparison unavailable."

    @staticmethod
    async def generate_xai_reasoning(
        candidate_name: str,
        score_breakdown: dict,
        jd_text: str,
        resume_text: str,
        job_title: str = "",
    ) -> dict:
        """
        Agent XAI — Generate structured, explainable reasoning for every hiring decision.
        Returns a JSON object describing exactly WHY a candidate scored the way they did.
        Falls back to rule-based reasoning if LLM is unavailable.
        """
        if not _model:
            return _generate_xai_fallback(score_breakdown, candidate_name, job_title)

        b = score_breakdown
        prompt = f"""
You are an explainable AI system for a hiring platform. Generate a clear, structured
justification for why {candidate_name} received an ATS score of {b.get('overall_score', 0):.1f}%.

Score Breakdown:
- Keyword Match:        {b.get('keyword_score', 0):.0f}%
- Semantic Similarity:  {b.get('semantic_score', 0):.0f}%
- Resume Format:        {b.get('format_score', 0):.0f}%
- Section Completeness: {b.get('section_score', 0):.0f}%
- Experience Match:     {b.get('experience_score', 0):.0f}%

Matched Skills: {', '.join(b.get('keyword_detail', {}).get('matched', [])[:8]) or 'None'}
Missing Skills: {', '.join(b.get('keyword_detail', {}).get('missing', [])[:5]) or 'None'}

Job Description (excerpt):
{jd_text[:1500]}

Resume (excerpt):
{resume_text[:1500]}

Return ONLY a JSON object:
{{
  "verdict": "ACCEPT | REVIEW | REJECT",
  "overall_score": {b.get('overall_score', 0):.1f},
  "reasoning": {{
    "keyword":    "1-sentence explanation of keyword match result",
    "semantic":   "1-sentence explanation of semantic alignment",
    "format":     "1-sentence explanation of format quality finding",
    "section":    "1-sentence explanation of section completeness",
    "experience": "1-sentence explanation of experience match"
  }},
  "key_strengths": ["strength 1", "strength 2", "strength 3"],
  "key_gaps": ["gap 1", "gap 2"],
  "red_flags": ["any concerns about the resume or candidate"],
  "hiring_recommendation": "2-3 sentence actionable recommendation for the recruiter",
  "source": "llm"
}}
"""
        raw = await _call_model(prompt, context="generate_xai_reasoning")
        parsed = _parse_json_response(raw)
        if parsed:
            return parsed
        return _generate_xai_fallback(score_breakdown, candidate_name, job_title)


# Backward Compatibility Alias
LLMService = GeminiService
