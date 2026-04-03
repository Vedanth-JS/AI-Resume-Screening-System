"""
Multi-Agent ATS Pipeline — Gemini 1.5-flash + LangGraph
────────────────────────────────────────────────────
1. ResumeParserAgent: Structured extraction + RAG index
2. SkillMatcherAgent: Semantic + Keyword gap analysis
3. BiasDetectorAgent: Contextual bias assessment
4. ScoringAgent: 5-component math + XAI reasoning
5. InterviewAgent: Targeted behavioral/technical questions
"""
import time
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from ..core.scorer import Scorer
from ..core.parser import ResumeParser
from ..core.bias_detector import BiasDetector
from ..services.llm_service import LLMService, get_embedding
from ..core.logger import log

try:
    from langgraph.graph import StateGraph, END
    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False

# ─── Shared State Schema ─────────────────────────────────────────────────────

class ATSState(TypedDict):
    # Inputs
    file_content:  bytes
    filename:      str
    jd_text:       str
    req_skills:    List[str]
    min_exp:       int
    org_id:        int
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

# ─── Node Functions ─────────────────────────────────────────────────────────

async def node_parse_resume(state: ATSState) -> ATSState:
    """Agent 1: ResumeParserAgent."""
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

async def node_analyze_jd(state: ATSState) -> ATSState:
    """Agent 2: JDAgent."""
    try:
        jd_profile = await LLMService.analyze_jd(state["jd_text"])
        state["jd_profile"] = jd_profile
    except Exception as e:
        log.error("node_analyze_jd.error", error=str(e))
    return state

async def node_match_skills(state: ATSState) -> ATSState:
    """Agent 3: SkillMatcherAgent (Keyword + Semantic)."""
    try:
        resume_text = state["parsed_resume"].get("raw_text", "")
        # Compute keyword match
        res = Scorer.compute_full_score(resume_text, state["jd_text"], state["req_skills"])
        
        # Compute semantic match (cosine similarity)
        resume_vec = await get_embedding(resume_text[:2000])
        jd_vec = await get_embedding(state["jd_text"][:2000])
        
        # Manual cosine similarity if vectors exist
        if resume_vec and jd_vec:
            dot = sum(a*b for a, b in zip(resume_vec, jd_vec))
            norm_a = sum(a*a for a in resume_vec)**0.5
            norm_b = sum(b*b for b in jd_vec)**0.5
            similarity = (dot / (norm_a * norm_b)) * 100
            res["semantic_score"] = round(similarity, 2)
            # Recalculate overall
            res["overall_score"] = (res["keyword_score"] * 0.4) + (res["semantic_score"] * 0.4) + (res["format_score"] * 0.1) + (res["section_score"] * 0.1)
            
        state["ats_breakdown"] = res
        state["final_score"] = res["overall_score"]
    except Exception as e:
        log.error("node_match_skills.error", error=str(e))
    return state

async def node_detect_bias(state: ATSState) -> ATSState:
    """Agent 4: BiasDetectorAgent."""
    try:
        state["bias_report"] = await LLMService.detect_bias_llm(state["jd_text"])
    except Exception as e:
        log.error("node_detect_bias.error", error=str(e))
    return state

async def node_generate_iq(state: ATSState) -> ATSState:
    """Agent 5: InterviewQuestionAgent."""
    try:
        gaps = state["ats_breakdown"].get("keyword_detail", {}).get("missing", [])
        state["interview_qs"] = await LLMService.generate_interview_questions(gaps, state["jd_text"])
    except Exception as e:
        log.error("node_generate_iq.error", error=str(e))
    return state

async def node_scoring_xai(state: ATSState) -> ATSState:
    """Agent 6: ScoringAgent (XAI)."""
    try:
        xai = await LLMService.generate_xai_reasoning(
            state["parsed_resume"].get("name", "Candidate"),
            state["ats_breakdown"],
            state["jd_text"],
            state["parsed_resume"].get("raw_text", "")
        )
        state["explanation"] = xai.get("hiring_recommendation")
    except Exception as e:
        log.error("node_scoring_xai.error", error=str(e))
    return state

# ─── Orchestrator ───────────────────────────────────────────────────────────

def _build_graph():
    if not _LANGGRAPH_AVAILABLE:
        return None
    graph = StateGraph(ATSState)
    graph.add_node("parse", node_parse_resume)
    graph.add_node("jd", node_analyze_jd)
    graph.add_node("match", node_match_skills)
    graph.add_node("bias", node_detect_bias)
    graph.add_node("questions", node_generate_iq)
    graph.add_node("xai", node_scoring_xai)
    
    graph.set_entry_point("parse")
    graph.add_edge("parse", "jd")
    graph.add_edge("jd", "match")
    graph.add_edge("match", "bias")
    graph.add_edge("bias", "questions")
    graph.add_edge("questions", "xai")
    graph.add_edge("xai", END)
    return graph.compile()

_compiled_graph = _build_graph()

class ATSWorkflow:
    async def process(self, file_content: bytes, filename: str, jd_text: str, req_skills: List[str], min_exp: int, org_id: int) -> Dict[str, Any]:
        initial_state: ATSState = {
            "file_content": file_content, "filename": filename, "jd_text": jd_text, "req_skills": req_skills,
            "min_exp": min_exp, "org_id": org_id, "parsed_resume": None, "jd_profile": None, "ats_breakdown": {},
            "bias_report": None, "interview_qs": [], "final_score": 0, "explanation": "", "error": None, "start_time": time.time()
        }
        
        if _LANGGRAPH_AVAILABLE:
            final = await _compiled_graph.ainvoke(initial_state)
        else:
            # Fallback linear
            s = initial_state
            for fn in [node_parse_resume, node_analyze_jd, node_match_skills, node_detect_bias, node_generate_iq, node_scoring_xai]:
                s = await fn(s)
            final = s
            
        return {
            "candidate": final["parsed_resume"],
            "score": final["final_score"],
            "explanation": final["explanation"],
            "breakdown": final["ats_breakdown"],
            "bias": final["bias_report"],
            "questions": final["interview_qs"],
            "metadata": {"time_ms": int((time.time() - final["start_time"]) * 1000)}
        }
