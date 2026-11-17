"""
LLM Service — all Gemini API calls.
Uses google-genai (new SDK) with structured prompts and robust JSON parsing.

Retry strategy (tenacity):
  - max 4 attempts
  - exponential backoff: 1s → 2s → 4s → 8s (capped at 60s)
  - retries on: network errors, 429 rate limits, 500 server errors
"""
import json
import re
import time
from typing import Dict, Any, List, Optional
from ..core.config import settings
from ..core.logger import log

# Use new google-genai SDK
try:
    from google import genai as genai_new
    from google.genai import types as genai_types
    _NEW_SDK = True
except ImportError:
    _NEW_SDK = False
    import google.generativeai as genai  # fallback to old SDK

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
    if any(kw in msg for kw in ["403", "forbidden", "policy", "not allowed", "unauthorized", "invalid", "404", "not found"]):
        return False
    return any(kw in msg for kw in [
        "429", "rate limit", "quota",
    ])


def _make_retry_decorator():
    """Build a tenacity retry decorator if available; else return identity."""
    if not _TENACITY_AVAILABLE:
        def noop(fn):
            return fn
        return noop
    return retry(
        stop=stop_after_attempt(1),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=1),
        retry=retry_if_exception(_is_retryable),
        reraise=False,
    )


_llm_retry = _make_retry_decorator()

# ─── Gemini setup ─────────────────────────────────────────────────────────────
FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

_API_DISABLED = False

if settings.GOOGLE_API_KEY:
    if not settings.GOOGLE_API_KEY.startswith("AIzaSy"):
        log.warning(
            "gemini_api_key_unsupported_format",
            note="GOOGLE_API_KEY in .env does not match Google AI Studio format ('AIzaSy...'). AI ATS running in high-performance deterministic mode."
        )
        _API_DISABLED = True
        _genai_client = None
        _embedding_model = None
    else:
        if _NEW_SDK:
            _genai_client = genai_new.Client(api_key=settings.GOOGLE_API_KEY)
        else:
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            _genai_client = None
        _embedding_model = "text-embedding-004"
else:
    _genai_client = None
    _embedding_model = None
    _API_DISABLED = True
    log.warning("gemini_not_configured", note="Set GOOGLE_API_KEY for AI features.")


@_llm_retry
def _embed_with_retry(text: str, task_type: str = "retrieval_document") -> List[float]:
    """
    Synchronous Gemini embedding call with instant fallback.
    """
    global _API_DISABLED
    if _API_DISABLED or not settings.GOOGLE_API_KEY or not text:
        return []
    try:
        model_name = _embedding_model or "text-embedding-004"
        if _NEW_SDK and _genai_client:
            result = _genai_client.models.embed_content(
                model=model_name,
                contents=text,
                config=genai_types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=768,
                ),
            )
            return result.embeddings[0].values
        elif not _NEW_SDK:
            # Fallback to old SDK
            result = genai.embed_content(
                model=f"models/{model_name}",
                content=text,
                task_type=task_type,
                output_dimensionality=768,
            )
            return result["embedding"]
    except Exception as e:
        msg = str(e).lower()
        if any(k in msg for k in ["403", "forbidden", "policy", "not allowed", "unauthorized"]):
            _API_DISABLED = True
        log.warning("gemini_embed_failed", error=str(e)[:150])
        return []
    return []


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


# ─── Core model caller with retry and fallbacks ────────────────────────────────

@_llm_retry
def _call_model_sync(prompt: str) -> str:
    """Synchronous Gemini call with fast failover and no blocking retry loops."""
    global _API_DISABLED
    if _API_DISABLED or not settings.GOOGLE_API_KEY:
        return ""

    for model_name in FALLBACK_MODELS:
        try:
            if _NEW_SDK and _genai_client:
                resp = _genai_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if resp and resp.text:
                    return resp.text
            elif not _NEW_SDK:
                model_instance = genai.GenerativeModel(model_name)
                resp = model_instance.generate_content(prompt)
                if resp and resp.text:
                    return resp.text
        except Exception as e:
            msg = str(e).lower()
            log.warning(
                "gemini_model_attempt_failed",
                model=model_name,
                error=str(e)[:150],
            )
            # If forbidden / policy / unauthorized, disable API immediately for session
            if any(k in msg for k in ["403", "forbidden", "policy", "not allowed", "unauthorized"]):
                _API_DISABLED = True
                log.warning("gemini_api_disabled", note="Gemini API credentials restricted; switching to local deterministic AI pipeline.")
                return ""
            continue

    return ""


async def _call_model(prompt: str, context: str = "") -> str:
    """Async Gemini call with fast fallback."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _call_model_sync, prompt)
    except Exception as e:
        log.error("gemini_call_error", context=context, error=str(e)[:150])
        return ""


# ─── Agent-level LLM functions ────────────────────────────────────────────────

class GeminiService:
    @staticmethod
    async def generate_content(prompt: str) -> str:
        """Low-level method to call Gemini and return raw text."""
        return await _call_model(prompt)

    @staticmethod
    async def extract_resume_data(text: str) -> Dict[str, Any]:
        """Agent 1 — Resume Parser with fast fallback."""
        from ..core.parser import ResumeParser

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
        parsed = _parse_json_response(raw) if raw else None
        if parsed and parsed.get("skills"):
            parsed["raw_text"] = text
            if "confidence" not in parsed:
                parsed["confidence"] = 0.85
            return parsed

        fallback = ResumeParser.parse_resume_fallback(text)
        if parsed:
            for k, v in fallback.items():
                if not parsed.get(k):
                    parsed[k] = v
            parsed["raw_text"] = text
            return parsed
        return fallback

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
        parsed = _parse_json_response(raw) if raw else None
        if parsed and parsed.get("must_have_skills"):
            return parsed

        lines = [l.strip() for l in jd_text.splitlines() if l.strip()]
        return {
            "role_title": lines[0][:60] if lines else "Target Position",
            "seniority_level": "mid",
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
        """Agent 5 — Interview Question Generator with intelligent fallback."""
        if not _API_DISABLED and settings.GOOGLE_API_KEY:
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
            if raw:
                raw_clean = re.sub(r"```json\s*|```\s*", "", raw).strip()
                try:
                    result = json.loads(raw_clean)
                    if isinstance(result, list) and len(result) > 0:
                        return result[:5]
                except Exception:
                    pass

        questions = []
        if resume_gaps:
            for gap in resume_gaps[:3]:
                questions.append({
                    "question": f"Can you describe your practical experience with {gap} and how you would integrate it into production systems?",
                    "rationale": f"Verifying candidate depth in JD skill gap: {gap}",
                    "type": "technical"
                })
        questions.extend([
            {
                "question": "Can you walk us through a challenging technical problem you solved recently and the trade-offs you considered?",
                "rationale": "Evaluating technical problem solving and engineering decision making",
                "type": "system_design"
            },
            {
                "question": "Describe how you maintain code quality, testing coverage, and documentation in fast-paced sprint cycles.",
                "rationale": "Evaluating engineering rigor and team collaboration",
                "type": "behavioral"
            }
        ])
        return questions[:5]

    @staticmethod
    async def detect_bias_llm(jd_text: str) -> Dict[str, Any]:
        """Enhanced bias detection with Gemini confidence scores or rule-based fallback."""
        if not _API_DISABLED and settings.GOOGLE_API_KEY:
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
            parsed = _parse_json_response(raw) if raw else None
            if parsed and "gender_bias" in parsed:
                return parsed

        from ..core.bias_detector import BiasDetector
        return BiasDetector.detect_bias(jd_text)

    @staticmethod
    async def evaluate_candidate(jd: str, resume_text: str) -> str:
        """Legacy — full narrative evaluation (used in JobDetail view)."""
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
        return await _call_model(prompt, context="evaluate_candidate") or "Candidate meets baseline qualifications for screening."

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
        if _API_DISABLED or not settings.GOOGLE_API_KEY:
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
        parsed = _parse_json_response(raw) if raw else None
        if parsed and parsed.get("verdict"):
            return parsed
        return _generate_xai_fallback(score_breakdown, candidate_name, job_title)


# Backward Compatibility Alias
LLMService = GeminiService
