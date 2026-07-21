"""
Multi-Agent ATS Pipeline v3.0
─────────────────────────────
Parallel execution with Gemini 768d embeddings for semantic scoring.

Pipeline (optimised order):
  1. ResumeParserAgent — LLM extraction
  2. [parallel] JDAgent + Gemini embeddings for resume + JD
  3. SkillMatcherAgent — keyword + semantic + experience scoring
  4. BiasDetectorAgent — LLM bias audit
  5. ScoringAgent — XAI reasoning
  6. InterviewAgent — targeted questions based on detected gaps

All I/O is async. Falls back to linear execution if LangGraph is not installed.
"""
import asyncio
import time
from typing import Dict, Any, List, Optional, TypedDict
from ..core.scorer import Scorer
from ..core.parser import ResumeParser
from ..core.bias_detector import BiasDetector
from ..services.llm_service import LLMService, get_embedding
from ..core.logger import log
from ..core.config import settings

try:
    from langgraph.graph import StateGraph, END
    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False


class ATSState(TypedDict):
    file_content:  bytes
    filename:      str
    jd_text:       str
    req_skills:    List[str]
    min_exp:       int
    org_id:        int
    parsed_resume: Optional[Dict[str, Any]]
    jd_profile:    Optional[Dict[str, Any]]
    resume_embedding: Optional[List[float]]
    jd_embedding:  Optional[List[float]]
    ats_breakdown: Optional[Dict[str, Any]]
    bias_report:   Optional[Dict[str, Any]]
    interview_qs:  Optional[List[Dict[str, str]]]
    final_score:   Optional[float]
    explanation:   Optional[str]
    error:         Optional[str]
    start_time:    Optional[float]


# ─── Node Functions ───────────────────────────────────────────────────────────

async def node_parse_resume(state: ATSState) -> ATSState:
    log.info("node_parse_resume.start", filename=state["filename"])
    try:
        text = ResumeParser.extract_text(state["file_content"], state["filename"])
        parsed = await LLMService.extract_resume_data(text)
        parsed["raw_text"] = text
        state["parsed_resume"] = parsed
    except Exception as e:
        log.error("node_parse_resume.error", error=str(e))
        state["error"] = f"Parse error: {e}"
    return state


async def node_analyze_jd_and_embed(state: ATSState) -> ATSState:
    """Analyse JD + generate embeddings for both resume and JD in parallel."""
    resume_text = state["parsed_resume"].get("raw_text", "")
    jd_text = state["jd_text"]

    try:
        jd_profile, resume_emb, jd_emb = await asyncio.gather(
            LLMService.analyze_jd(jd_text),
            get_embedding(resume_text[:3000]),
            get_embedding(jd_text[:3000]),
            return_exceptions=True,
        )
        if not isinstance(jd_profile, Exception):
            state["jd_profile"] = jd_profile
        if not isinstance(resume_emb, Exception):
            state["resume_embedding"] = resume_emb
        if not isinstance(jd_emb, Exception):
            state["jd_embedding"] = jd_emb
    except Exception as e:
        log.error("node_analyze_jd_and_embed.error", error=str(e))

    return state


async def node_score_all(state: ATSState) -> ATSState:
    """Compute keyword, semantic, format, section, and experience scores."""
    try:
        resume_text = state["parsed_resume"].get("raw_text", "")
        candidate_years = float(state["parsed_resume"].get("total_years_experience", 0) or 0)

        # Semantic: prefer Gemini embedding; fall back to ST
        sem_override = None
        if state.get("resume_embedding") and state.get("jd_embedding"):
            rv = state["resume_embedding"]
            jv = state["jd_embedding"]
            dot = sum(a * b for a, b in zip(rv, jv))
            na  = sum(a * a for a in rv) ** 0.5
            nb  = sum(b * b for b in jv) ** 0.5
            if na > 0 and nb > 0:
                sem_override = round((dot / (na * nb)) * 100, 2)

        res = Scorer.compute_full_score(
            resume_text=resume_text,
            jd_text=state["jd_text"],
            jd_keywords=state["req_skills"],
            candidate_years=candidate_years,
            required_years=state.get("min_exp", 0),
            semantic_score_override=sem_override,
        )

        state["ats_breakdown"] = res
        state["final_score"] = res["overall_score"]
    except Exception as e:
        log.error("node_score_all.error", error=str(e))
    return state


async def node_detect_bias(state: ATSState) -> ATSState:
    try:
        state["bias_report"] = await LLMService.detect_bias_llm(state["jd_text"])
    except Exception as e:
        log.error("node_detect_bias.error", error=str(e))
    return state


async def node_generate_iq(state: ATSState) -> ATSState:
    try:
        gaps = state.get("ats_breakdown", {}).get("keyword_detail", {}).get("missing", [])
        name = state.get("parsed_resume", {}).get("name", "Candidate")
        state["interview_qs"] = await LLMService.generate_interview_questions(
            gaps, state["jd_text"], name
        )
    except Exception as e:
        log.error("node_generate_iq.error", error=str(e))
    return state


async def node_scoring_xai(state: ATSState) -> ATSState:
    try:
        xai = await LLMService.generate_xai_reasoning(
            candidate_name=state.get("parsed_resume", {}).get("name", "Candidate"),
            score_breakdown=state.get("ats_breakdown", {}),
            jd_text=state["jd_text"],
            resume_text=state.get("parsed_resume", {}).get("raw_text", ""),
            job_title=state.get("jd_profile", {}).get("role_title", ""),
        )
        state["explanation"] = xai.get("hiring_recommendation", "")
        state["ats_breakdown"]["xai"] = xai
    except Exception as e:
        log.error("node_scoring_xai.error", error=str(e))
    return state


# ─── Graph Builder ────────────────────────────────────────────────────────────

def _build_graph():
    if not _LANGGRAPH_AVAILABLE:
        return None
    graph = StateGraph(ATSState)
    graph.add_node("parse",      node_parse_resume)
    graph.add_node("embed",      node_analyze_jd_and_embed)
    graph.add_node("score",      node_score_all)
    graph.add_node("bias",       node_detect_bias)
    graph.add_node("questions",  node_generate_iq)
    graph.add_node("xai",        node_scoring_xai)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "embed")
    graph.add_edge("embed", "score")
    # bias, questions, xai can run in parallel after scoring
    graph.add_edge("score", "bias")
    graph.add_edge("score", "questions")
    graph.add_edge("bias", "xai")
    graph.add_edge("questions", "xai")
    graph.add_edge("xai", END)
    return graph.compile()


_compiled_graph = _build_graph()


# ─── Orchestrator ─────────────────────────────────────────────────────────────

class ATSWorkflow:
    async def process(
        self,
        file_content: bytes,
        filename: str,
        jd_text: str,
        req_skills: List[str],
        min_exp: int,
        org_id: int,
    ) -> Dict[str, Any]:
        initial_state: ATSState = {
            "file_content":     file_content,
            "filename":         filename,
            "jd_text":          jd_text,
            "req_skills":       req_skills,
            "min_exp":          min_exp,
            "org_id":           org_id,
            "parsed_resume":    None,
            "jd_profile":       None,
            "resume_embedding": None,
            "jd_embedding":     None,
            "ats_breakdown":    {},
            "bias_report":      None,
            "interview_qs":     [],
            "final_score":      0,
            "explanation":      "",
            "error":            None,
            "start_time":       time.time(),
        }

        if _LANGGRAPH_AVAILABLE and _compiled_graph:
            final = await _compiled_graph.ainvoke(initial_state)
        else:
            # Linear fallback — still uses optimised parallel embed step
            s = initial_state
            s = await node_parse_resume(s)
            s = await node_analyze_jd_and_embed(s)
            s = await node_score_all(s)
            # Run bias, questions, xai concurrently
            bias_task    = node_detect_bias(s)
            q_task       = node_generate_iq(s)
            s_bias, s_q  = await asyncio.gather(bias_task, q_task)
            s["bias_report"]  = s_bias.get("bias_report")
            s["interview_qs"] = s_q.get("interview_qs")
            s = await node_scoring_xai(s)
            final = s

        return {
            "candidate":  final.get("parsed_resume"),
            "score":      final.get("final_score"),
            "explanation": final.get("explanation"),
            "breakdown":  final.get("ats_breakdown"),
            "bias":       final.get("bias_report"),
            "questions":  final.get("interview_qs"),
            "metadata":   {
                "time_ms": int((time.time() - final.get("start_time", time.time())) * 1000),
            },
        }
