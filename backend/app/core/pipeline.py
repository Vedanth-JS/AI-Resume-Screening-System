"""
Multi-Agent ATS Pipeline — LangGraph StateGraph
─────────────────────────────────────────────────
5 Nodes (Agents):
  1. parse_resume   — PDF text extraction + LLM structured parsing
  2. analyze_jd     — JD must-haves / nice-to-haves extraction
  3. score_ats      — 4-component scoring (keyword/semantic/format/section)
  4. detect_bias    — Gender, age, prestige bias with LLM confidence
  5. gen_questions  — 5 targeted interview questions with rationale

Orchestrator: LangGraph StateGraph wiring all nodes linearly.
On error in any node, the state's 'error' field is set and pipeline
continues (graceful degradation — partial results still returned).
"""
import time
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from ..core.scorer import Scorer
from ..core.parser import ResumeParser
from ..core.bias_detector import BiasDetector
from ..services.llm_service import LLMService
from ..core.logger import log

# ─── LangGraph imports ────────────────────────────────────────────────────────
try:
    from langgraph.graph import StateGraph, END
    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False
    log.warning("langgraph_not_installed", note="Falling back to linear pipeline.")


# ─── Shared State Schema ─────────────────────────────────────────────────────

class ATSState(TypedDict):
    # Inputs
    file_content:  bytes
    filename:      str
    jd_text:       str
    req_skills:    List[str]
    min_exp:       int
    # Agent outputs
    parsed_resume: Optional[Dict[str, Any]]
    jd_profile:    Optional[Dict[str, Any]]
    ats_breakdown: Optional[Dict[str, Any]]
    bias_report:   Optional[Dict[str, Any]]
    interview_qs:  Optional[List[Dict[str, str]]]
    final_score:   Optional[float]
    explanation:   Optional[str]
    error:         Optional[str]
    start_time:    Optional[float]


# ─── Node Functions (each is a LangGraph node) ───────────────────────────────

async def node_parse_resume(state: ATSState) -> ATSState:
    """Agent 1: Extract text + parse structured resume data via LLM."""
    log.info("node_parse_resume.start", filename=state["filename"])
    try:
        text = ResumeParser.extract_text(state["file_content"], state["filename"])
        parsed = await LLMService.extract_resume_data(text)
        if not parsed or not parsed.get("name") or parsed.get("name") == "Unknown":
            parsed = ResumeParser.parse_resume_fallback(text)
        else:
            parsed["raw_text"] = text
        state["parsed_resume"] = parsed
        log.info("node_parse_resume.done", name=parsed.get("name"))
    except Exception as e:
        log.error("node_parse_resume.error", error=str(e))
        state["error"] = f"Parse error: {e}"
        # Minimal fallback
        state["parsed_resume"] = {"name": "Unknown", "email": None, "phone": None, "raw_text": "", "skills": []}
    return state


async def node_analyze_jd(state: ATSState) -> ATSState:
    """Agent 2: Extract structured profile from JD."""
    log.info("node_analyze_jd.start")
    try:
        jd_profile = await LLMService.analyze_jd(state["jd_text"])
        # Merge LLM-extracted must-haves with recruiter-specified skills
        llm_must_haves = jd_profile.get("must_have_skills", [])
        combined_skills = list(set(state["req_skills"] + llm_must_haves))
        jd_profile["combined_required_skills"] = combined_skills
        state["jd_profile"] = jd_profile
        log.info("node_analyze_jd.done", role=jd_profile.get("role_title"))
    except Exception as e:
        log.error("node_analyze_jd.error", error=str(e))
        state["jd_profile"] = {"role_title": "Unknown", "must_have_skills": state["req_skills"], "combined_required_skills": state["req_skills"]}
    return state


async def node_score_ats(state: ATSState) -> ATSState:
    """Agent 3: Run 4-component ATS scoring."""
    log.info("node_score_ats.start")
    try:
        resume_text = (state["parsed_resume"] or {}).get("raw_text", "")
        jd_keywords = (state["jd_profile"] or {}).get("combined_required_skills", state["req_skills"])

        breakdown = Scorer.compute_full_score(
            resume_text=resume_text,
            jd_text=state["jd_text"],
            jd_keywords=jd_keywords,
        )

        # Also factor in experience match
        candidate_exp = (state["parsed_resume"] or {}).get("total_years_experience", 0)
        if isinstance(candidate_exp, str):
            try: candidate_exp = float(candidate_exp)
            except: candidate_exp = 0.0
        min_exp = state["min_exp"]
        exp_score = min(candidate_exp / min_exp, 1.0) if min_exp > 0 else 1.0
        breakdown["experience_score"] = round(exp_score * 100, 2)
        breakdown["candidate_exp"] = candidate_exp
        breakdown["required_exp"] = min_exp

        state["ats_breakdown"] = breakdown
        state["final_score"]   = breakdown["overall_score"]
        log.info("node_score_ats.done", score=breakdown["overall_score"])
    except Exception as e:
        log.error("node_score_ats.error", error=str(e))
        state["ats_breakdown"] = {"overall_score": 0, "keyword_score": 0, "semantic_score": 0, "format_score": 0, "section_score": 0, "suggestions": []}
        state["final_score"] = 0.0
    return state


async def node_detect_bias(state: ATSState) -> ATSState:
    """Agent 4: Bias detection with LLM confidence + rule-based fallback."""
    log.info("node_detect_bias.start")
    try:
        # Rule-based (fast, always runs)
        rule_based = BiasDetector.detect_bias(state["jd_text"])
        # LLM-enhanced (may fail gracefully)
        llm_report = await LLMService.detect_bias_llm(state["jd_text"])
        # Merge
        merged = {**rule_based, **llm_report, "rule_based": rule_based}
        state["bias_report"] = merged
        log.info("node_detect_bias.done", bias_score=llm_report.get("overall_bias_score", 0))
    except Exception as e:
        log.error("node_detect_bias.error", error=str(e))
        state["bias_report"] = BiasDetector.detect_bias(state["jd_text"])
    return state


async def node_gen_questions(state: ATSState) -> ATSState:
    """Agent 5: Generate 5 targeted interview questions."""
    log.info("node_gen_questions.start")
    try:
        missing_skills = (state["ats_breakdown"] or {}).get("keyword_detail", {}).get("missing", [])
        candidate_name = (state["parsed_resume"] or {}).get("name", "the candidate")
        questions = await LLMService.generate_interview_questions(
            resume_gaps=missing_skills,
            jd_text=state["jd_text"],
            candidate_name=candidate_name,
        )
        state["interview_qs"] = questions
        log.info("node_gen_questions.done", count=len(questions))
    except Exception as e:
        log.error("node_gen_questions.error", error=str(e))
        state["interview_qs"] = []
    return state


async def node_aggregate(state: ATSState) -> ATSState:
    """Final aggregation: build explanation, compute elapsed time."""
    b = state.get("ats_breakdown") or {}
    name = (state.get("parsed_resume") or {}).get("name", "Candidate")
    score = state.get("final_score", 0)

    if score >= 70:   verdict = "ACCEPT"
    elif score >= 40: verdict = "REVIEW"
    else:             verdict = "REJECT"

    state["explanation"] = (
        f"{verdict} — {name} scored {score:.1f}% overall. "
        f"Keyword: {b.get('keyword_score', 0):.0f}% | "
        f"Semantic: {b.get('semantic_score', 0):.0f}% | "
        f"Format: {b.get('format_score', 0):.0f}% | "
        f"Sections: {b.get('section_score', 0):.0f}%."
    )

    elapsed = time.time() - (state.get("start_time") or time.time())
    b["processing_time_ms"] = int(elapsed * 1000)
    state["ats_breakdown"] = b
    log.info("node_aggregate.done", verdict=verdict, score=score, elapsed_ms=b["processing_time_ms"])
    return state


# ─── Build the LangGraph StateGraph ──────────────────────────────────────────

def _build_graph():
    if not _LANGGRAPH_AVAILABLE:
        return None
    graph = StateGraph(ATSState)
    graph.add_node("parse_resume",  node_parse_resume)
    graph.add_node("analyze_jd",    node_analyze_jd)
    graph.add_node("score_ats",     node_score_ats)
    graph.add_node("detect_bias",   node_detect_bias)
    graph.add_node("gen_questions", node_gen_questions)
    graph.add_node("aggregate",     node_aggregate)

    graph.set_entry_point("parse_resume")
    graph.add_edge("parse_resume",  "analyze_jd")
    graph.add_edge("analyze_jd",    "score_ats")
    graph.add_edge("score_ats",     "detect_bias")
    graph.add_edge("detect_bias",   "gen_questions")
    graph.add_edge("gen_questions", "aggregate")
    graph.add_edge("aggregate",     END)
    return graph.compile()


_compiled_graph = _build_graph()


# ─── Public Interface ─────────────────────────────────────────────────────────

class ATSWorkflow:
    """
    Public entry point used by routes.py and celery_tasks.py.
    Uses LangGraph StateGraph when available, falls back to linear execution.
    """

    async def process(
        self,
        file_content: bytes,
        filename: str,
        job_description: str,
        req_skills: List[str],
        min_exp: int,
    ) -> Dict[str, Any]:
        initial_state: ATSState = {
            "file_content":  file_content,
            "filename":      filename,
            "jd_text":       job_description,
            "req_skills":    req_skills,
            "min_exp":       min_exp,
            "parsed_resume": None,
            "jd_profile":    None,
            "ats_breakdown": None,
            "bias_report":   None,
            "interview_qs":  None,
            "final_score":   None,
            "explanation":   None,
            "error":         None,
            "start_time":    time.time(),
        }

        if _compiled_graph:
            log.info("ats_workflow.langgraph", mode="StateGraph")
            final = await _compiled_graph.ainvoke(initial_state)
        else:
            # Linear fallback if langgraph not installed
            log.info("ats_workflow.linear", mode="fallback")
            s = initial_state
            for fn in [node_parse_resume, node_analyze_jd, node_score_ats, node_detect_bias, node_gen_questions, node_aggregate]:
                s = await fn(s)
            final = s

        b = final.get("ats_breakdown") or {}
        pr = final.get("parsed_resume") or {}

        return {
            # Legacy-compatible keys (routes.py uses these)
            "candidate": pr,
            "skill_analysis": {
                "score":   (b.get("keyword_score", 0) / 100),
                "matched": b.get("keyword_detail", {}).get("matched", []),
                "missing": b.get("keyword_detail", {}).get("missing", []),
            },
            "experience_analysis": {
                "score":         b.get("experience_score", 0) / 100,
                "candidate_exp": b.get("candidate_exp", 0),
                "required_exp":  b.get("required_exp", 0),
            },
            "semantic_score":  b.get("semantic_score", 0),
            "llm_evaluation":  final.get("explanation", ""),
            "final_result": {
                "final_score": final.get("final_score", 0),
                "explanation": final.get("explanation", ""),
                "verdict":     "accept" if (final.get("final_score") or 0) >= 70 else "review" if (final.get("final_score") or 0) >= 40 else "reject",
            },
            # New rich data
            "ats_breakdown":   b,
            "jd_profile":      final.get("jd_profile"),
            "bias_report":     final.get("bias_report"),
            "interview_questions": final.get("interview_qs", []),
            "suggestions":     b.get("suggestions", []),
            "processing_time_ms": b.get("processing_time_ms", 0),
        }
