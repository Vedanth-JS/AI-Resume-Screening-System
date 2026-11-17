"""
Advanced Deterministic-plus-Semantic ATS Resume Screening and Scoring Engine (v5.0).
──────────────────────────────────────────────────────────────────────────────
Features:
  - 8-Criteria Configurable Weighted Evaluation Model:
      1. Technical Skills Match (30%)
      2. Job Description Relevance (20%)
      3. Relevant Experience (15%)
      4. Project Relevance (10%)
      5. Education Match (10%)
      6. Certifications (5%)
      7. Keywords Match (5%)
      8. Resume Quality (5%)
  - Option A (Predefined Job Roles) & Option B (Custom Job Description)
  - 6-Tier Match Classification (90-100, 80-89, 70-79, 60-69, 40-59, 0-39)
  - Skill Gap Analysis (Matching, Missing Mandatory, Missing Preferred, Partially Matching,
    Additional Skills, Relevant Technologies) with detailed explanations
  - Recruiter Recommendations (Shortlist, Consider for Interview, Needs Further Review, Not Recommended)
  - Fresher Protection: Zero penalty on experience when JD/role allows entry-level/freshers
  - Anti-Hallucination & Anti-Keyword Stuffing Guardrails
  - Strict Extraction Error Handling (no score assigned if extraction fails)
"""
import re
import math
from typing import Dict, Any, List, Tuple, Optional, Set
from datetime import datetime

from .skill_synonyms import SKILL_TAXONOMY
from .role_inferrer import infer_role_benchmarks, RoleBenchmark, PREDEFINED_ROLES
from ..schemas.ats_engine import (
    ATSScoreResponse,
    ATSScoreBreakdown,
    ATSCriteriaWeights,
    KeywordAnalysis,
    SemanticMatch,
    SkillItem,
    SkillGapAnalysis,
    RecruiterRecommendation,
    ParsedCandidateProfile,
    CandidateScreeningResult,
    CustomJDConfig,
    ActionableImprovement,
)

# ═══════════════════════════════════════════════════════════════════════════════
# Regular Expressions & Curated Taxonomies
# ═══════════════════════════════════════════════════════════════════════════════

_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_REGEX = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
_URL_REGEX = re.compile(r"(https?://\S+|linkedin\.com/\S+|github\.com/\S+|gitlab\.com/\S+)", re.I)

# Metric Regexes: %, $, numbers with units, latency, multipliers, scale
_METRIC_PERCENT = re.compile(r"\b\d+(?:\.\d+)?%\b")
_METRIC_CURRENCY = re.compile(r"(?:[\$€£₹]|USD|EUR)\s*\d+[\d,]*(?:\.\d+)?\s*(?:k|m|b|million|billion)?\b", re.I)
_METRIC_MULTIPLIER = re.compile(r"\b\d+(?:\.\d+)?x\b", re.I)
_METRIC_LATENCY = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|milliseconds?|sec|seconds?|minutes?|hours?)\b", re.I)
_METRIC_THROUGHPUT = re.compile(r"\b\d+[\d,]*(?:\.\d+)?\s*(?:req/s|rps|qps|queries/sec|tps|events/sec|transactions?)\b", re.I)
_METRIC_SCALE = re.compile(r"\b\d+[\d,]*(?:\.\d+)?\+?\s*(?:k|m|b|million|billion|k\+)?\s*(?:users|active users|dau|mau|records|nodes|servers|customers|subscribers|downloads|requests|hits|concurrent)\b", re.I)
_METRIC_SLA = re.compile(r"\b99(?:\.\d+)?%\s*(?:uptime|sla|slo|availability)\b", re.I)

# Strong Action Verbs for ATS Achievement Quality
_STRONG_ACTION_VERBS = {
    "architected", "engineered", "designed", "developed", "built", "spearheaded",
    "implemented", "orchestrated", "automated", "optimized", "streamlined",
    "scaled", "reduced", "decreased", "increased", "accelerated", "delivered",
    "launched", "deployed", "refactored", "migrated", "mentored", "led",
    "formulated", "established", "eliminated", "generated", "published",
    "revamped", "restructured", "centralized", "consolidated", "secured", "hardened"
}

_PASSIVE_PHRASES = [
    "responsible for", "duties included", "worked on", "assisted with",
    "helped with", "part of a team that", "tasked with", "handled day-to-day",
    "participated in", "involved in"
]

# Comprehensive bidirectional synonym & alias mappings
_SYNONYM_PAIRS: List[Tuple[str, str]] = [
    ("postgres", "postgresql"),
    ("react", "react.js"),
    ("react", "reactjs"),
    ("react.js", "reactjs"),
    ("node", "node.js"),
    ("node", "nodejs"),
    ("node.js", "nodejs"),
    ("k8s", "kubernetes"),
    ("aws", "amazon web services"),
    ("gcp", "google cloud platform"),
    ("gcp", "google cloud"),
    ("golang", "go"),
    ("ci/cd", "continuous integration"),
    ("ci/cd", "continuous deployment"),
    ("ci/cd", "cicd"),
    ("mongo", "mongodb"),
    ("vue", "vue.js"),
    ("vue", "vuejs"),
    ("vue.js", "vuejs"),
    ("nextjs", "next.js"),
    ("fastapi", "fast-api"),
    ("sklearn", "scikit-learn"),
    ("rest", "restful"),
    ("rest api", "restful api"),
    ("rest api", "rest"),
    ("api", "apis"),
    ("system design", "distributed systems"),
    ("system design", "systems architecture"),
    ("system design", "system architecture"),
    ("docker", "containerization"),
    ("docker", "containers"),
    ("typescript", "ts"),
    ("javascript", "js"),
    ("python", "py"),
    ("machine learning", "ml"),
    ("deep learning", "dl"),
    ("natural language processing", "nlp"),
    ("large language models", "llm"),
    ("large language models", "llms"),
    ("rag", "retrieval augmented generation"),
    ("qa", "quality assurance"),
    ("sdet", "test automation"),
    ("pyspark", "spark"),
    ("microservices", "microservice"),
    ("microservices", "micro-services"),
    ("power bi", "powerbi"),
    ("figma", "wireframing"),
]

# Build bidirectional map: term -> Set[synonyms]
_SYNONYM_LOOKUP: Dict[str, Set[str]] = {}
for _t1, _t2 in _SYNONYM_PAIRS:
    _SYNONYM_LOOKUP.setdefault(_t1.lower(), set()).add(_t2.lower())
    _SYNONYM_LOOKUP.setdefault(_t2.lower(), set()).add(_t1.lower())

# Recognized Degree Keywords & Base Scores
_DEGREE_PATTERNS = [
    (re.compile(r"\b(ph\.?d\.?|doctor of philosophy|doctorate)\b", re.I), "Doctorate (PhD)", 100),
    (re.compile(r"\b(m\.?s\.?|master of science|m\.?tech|m\.?eng|m\.?b\.?a\.?|master)\b", re.I), "Master's Degree", 95),
    (re.compile(r"\b(b\.?s\.?|bachelor of science|b\.?e\.?|b\.?tech|b\.?eng|bachelor)\b", re.I), "Bachelor's Degree", 90),
    (re.compile(r"\b(associate degree|diploma)\b", re.I), "Associate Degree / Diploma", 65),
]

_STEM_FIELDS = [
    "computer science", "software engineering", "computer engineering",
    "information technology", "data science", "mathematics", "statistics",
    "electrical engineering", "cybersecurity", "artificial intelligence", "design"
]

_CERTIFICATION_KEYWORDS = [
    "aws certified", "solutions architect", "certified kubernetes administrator",
    "cka", "ckad", "gcp certified", "google cloud certified", "azure certified",
    "cissp", "ceh", "pmp", "comptia security+", "comptia network+", "terraform associate",
    "hashicorp certified", "certified scrum master", "csm", "oracle certified",
    "istqb", "nielsen norman"
]


class ATSScoringEngine:
    """
    Advanced Deterministic-plus-Semantic ATS Scoring Engine.
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. Advanced Candidate Information Extraction
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def extract_candidate_profile(cls, raw_text: str, file_name: str = "") -> ParsedCandidateProfile:
        """
        Intelligently extracts Candidate Name, Email, Phone, Education, College,
        Graduation Year, Technical Skills (Languages, Frameworks, DBs, Tools),
        Work Experience, Projects, Certifications, and Achievements.
        """
        clean_text = raw_text.strip()
        sections = cls._segment_resume_sections(clean_text)

        # 1. Email & Phone
        emails = _EMAIL_REGEX.findall(clean_text)
        email = emails[0] if emails else None

        phones = _PHONE_REGEX.findall(clean_text)
        phone = phones[0] if phones else None

        # 2. Candidate Name
        name = cls._extract_candidate_name(clean_text, file_name)

        # 3. Education, College & Grad Year
        edu_text = sections.get("education", "") or clean_text
        detected_degree = None
        for pat, deg_label, _ in _DEGREE_PATTERNS:
            if pat.search(edu_text):
                detected_degree = deg_label
                break

        # Extract College/University
        college = cls._extract_college_name(edu_text)

        # Extract Grad Year (e.g. 2018, 2022)
        grad_year_match = re.findall(r"\b(19\d{2}|20[0-2]\d)\b", edu_text)
        graduation_year = grad_year_match[-1] if grad_year_match else None

        # 4. Extract Structured Skills
        tech_skills, prog_langs, frameworks, databases, tools = cls._extract_categorized_skills(clean_text)

        # 5. Experience Years & Entries
        experience_years, exp_entries = cls._extract_experience_details(clean_text, sections)

        # 6. Projects & Certifications
        projects = cls._extract_project_entries(sections.get("projects", ""), clean_text)
        certifications = cls._extract_certifications(clean_text)
        achievements = cls._extract_achievements(clean_text, sections)

        return ParsedCandidateProfile(
            name=name,
            email=email,
            phone=phone,
            education=detected_degree or "Degree Not Explicitly Specified",
            college=college,
            graduation_year=graduation_year,
            technical_skills=tech_skills,
            programming_languages=prog_langs,
            frameworks=frameworks,
            databases=databases,
            tools_and_technologies=tools,
            work_experience_years=round(experience_years, 1),
            experience_entries=exp_entries,
            internship_experience=[e for e in exp_entries if "intern" in e.get("title", "").lower()],
            projects=projects,
            certifications=certifications,
            achievements=achievements,
            raw_text=clean_text,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. Main Scoring Engine (8 Weighted Criteria)
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def score(
        cls,
        resume_text: Optional[str] = None,
        job_description: Optional[str] = None,
        job_role: Optional[str] = None,
        custom_jd: Optional[CustomJDConfig] = None,
        weights: Optional[ATSCriteriaWeights] = None,
        parsed_resume: Optional[Dict[str, Any]] = None,
    ) -> ATSScoreResponse:
        """
        Main scoring entry point. Evaluates candidate resume against target role / JD
        across the 8 weighted criteria with configurable weights.
        """
        raw_text = (resume_text or "").strip()

        # Handle Extraction Failure (empty text)
        if not raw_text:
            return cls._empty_resume_response(job_description, job_role)

        # Determine Effective Weights (Default to 30/20/15/10/10/5/5/5)
        w = weights or ATSCriteriaWeights()
        weight_sum = (
            w.technical_skills + w.jd_relevance + w.relevant_experience
            + w.project_relevance + w.education_match + w.certifications
            + w.keywords_match + w.resume_quality
        )
        if weight_sum <= 0:
            weight_sum = 100.0

        # Parse Requirements: Custom JD vs Predefined Role vs Plain JD
        reqs, input_mode_used = cls._resolve_requirements(
            job_description=job_description,
            job_role=job_role,
            custom_jd=custom_jd,
        )

        # Extract Candidate Profile
        candidate_profile = cls.extract_candidate_profile(raw_text)
        sections = cls._segment_resume_sections(raw_text)

        # 1. Technical Skills Match (0-100)
        (
            tech_skills_score,
            kw_analysis,
            skill_gap_analysis,
            skill_strengths,
            skill_weaknesses,
            is_stuffed,
        ) = cls._evaluate_technical_skills(
            candidate_profile=candidate_profile,
            sections=sections,
            must_have=reqs["must_have_skills"],
            preferred=reqs["nice_to_have_skills"],
        )

        # 2. Job Description Relevance (0-100)
        jd_relevance_score, jd_strengths, jd_weaknesses = cls._evaluate_jd_relevance(
            raw_text=raw_text,
            jd_text=reqs["effective_jd_text"],
            core_competencies=reqs.get("core_competencies", []),
        )

        # 3. Relevant Experience (0-100) — with Fresher Protection
        is_fresher_allowed = reqs["min_experience"] <= 1.0 or any(
            f in reqs["role_title"].lower() for f in ["junior", "intern", "entry", "fresher"]
        )
        exp_score, exp_strengths, exp_weaknesses = cls._evaluate_experience(
            candidate_years=candidate_profile.work_experience_years,
            required_years=reqs["min_experience"],
            is_fresher_allowed=is_fresher_allowed,
            sections=sections,
            role_title=reqs["role_title"],
            seniority_level=reqs["seniority_level"],
        )

        # 4. Project Relevance (0-100)
        proj_score, proj_strengths, proj_weaknesses = cls._evaluate_project_relevance(
            candidate_profile=candidate_profile,
            must_have_skills=reqs["must_have_skills"],
            role_title=reqs["role_title"],
        )

        # 5. Education Match (0-100)
        edu_score, edu_strengths, edu_weaknesses = cls._evaluate_education_match(
            candidate_profile=candidate_profile,
            sections=sections,
            expected_fields=reqs.get("expected_degree_fields", _STEM_FIELDS),
        )

        # 6. Certifications (0-100)
        cert_score, cert_strengths, cert_weaknesses = cls._evaluate_certifications(
            candidate_profile=candidate_profile,
            sections=sections,
        )

        # 7. Keywords Match (0-100)
        keyword_score, kw_strengths, kw_weaknesses = cls._evaluate_keywords_and_verbs(
            raw_text=raw_text,
            sections=sections,
            expected_verbs=reqs.get("expected_action_verbs", list(_STRONG_ACTION_VERBS)[:8]),
        )

        # 8. Resume Quality (0-100)
        quality_score, quality_strengths, quality_weaknesses, improvements = cls._evaluate_resume_quality(
            raw_text=raw_text,
            sections=sections,
            candidate_profile=candidate_profile,
        )

        # Compute Final Weighted ATS Score (Normalized to 0-100)
        weighted_sum = (
            (tech_skills_score * w.technical_skills)
            + (jd_relevance_score * w.jd_relevance)
            + (exp_score * w.relevant_experience)
            + (proj_score * w.project_relevance)
            + (edu_score * w.education_match)
            + (cert_score * w.certifications)
            + (keyword_score * w.keywords_match)
            + (quality_score * w.resume_quality)
        )
        overall_ats_score = int(round(weighted_sum / weight_sum))
        overall_ats_score = max(0, min(100, overall_ats_score))

        # Classify Score Tier (6 Ranges)
        match_tier = cls._classify_match_tier(overall_ats_score)

        # Generate AI-Powered Recruiter Recommendation
        recommendation = cls._generate_recommendation(
            overall_score=overall_ats_score,
            tech_skills_score=tech_skills_score,
            exp_score=exp_score,
            is_stuffed=is_stuffed,
            candidate_name=candidate_profile.name,
            role_title=reqs["role_title"],
            breakdown_dict={
                "Technical Skills Match (30%)": f"{tech_skills_score:.1f}/100",
                "Job Description Relevance (20%)": f"{jd_relevance_score:.1f}/100",
                "Relevant Experience (15%)": f"{exp_score:.1f}/100",
                "Project Relevance (10%)": f"{proj_score:.1f}/100",
                "Education Match (10%)": f"{edu_score:.1f}/100",
                "Certifications (5%)": f"{cert_score:.1f}/100",
                "Keywords Match (5%)": f"{keyword_score:.1f}/100",
                "Resume Quality (5%)": f"{quality_score:.1f}/100",
            },
        )

        # Backward compatibility 4-component integer breakdown
        hard_skills_pts = int(round((tech_skills_score / 100.0) * 40.0))
        experience_pts = int(round((exp_score / 100.0) * 25.0))
        impact_metrics_pts = int(round((quality_score / 100.0) * 20.0))
        formatting_edu_pts = int(round((edu_score / 100.0) * 15.0))

        breakdown = ATSScoreBreakdown(
            technical_skills_score=round(tech_skills_score, 1),
            jd_relevance_score=round(jd_relevance_score, 1),
            relevant_experience_score=round(exp_score, 1),
            project_relevance_score=round(proj_score, 1),
            education_match_score=round(edu_score, 1),
            certifications_score=round(cert_score, 1),
            keywords_match_score=round(keyword_score, 1),
            resume_quality_score=round(quality_score, 1),
            hard_skills_score=hard_skills_pts,
            experience_score=experience_pts,
            impact_metrics_score=impact_metrics_pts,
            formatting_and_education_score=formatting_edu_pts,
        )

        all_strengths = (skill_strengths + exp_strengths + proj_strengths + edu_strengths + quality_strengths)[:6]
        all_weaknesses = (skill_weaknesses + exp_weaknesses + proj_weaknesses + edu_weaknesses + quality_weaknesses)[:6]

        # Actionable improvements
        if skill_gap_analysis.missing_mandatory_skills:
            missing_names = [m.skill for m in skill_gap_analysis.missing_mandatory_skills[:3]]
            improvements.insert(
                0,
                ActionableImprovement(
                    section="Technical Skills",
                    issue=f"Missing mandatory requirements: {', '.join(missing_names)}.",
                    suggested_fix=f"Explicitly add {', '.join(missing_names)} with verifiable project or work experience bullets.",
                ),
            )

        return ATSScoreResponse(
            overall_ats_score=overall_ats_score,
            match_tier=match_tier,
            input_mode_used=input_mode_used,
            breakdown=breakdown,
            keyword_analysis=kw_analysis,
            skill_gap_analysis=skill_gap_analysis,
            recommendation=recommendation,
            strengths=all_strengths,
            critical_gaps=all_weaknesses,
            weaknesses=all_weaknesses,
            actionable_improvements=improvements[:5],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. Bulk Screen Coordinator
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def evaluate_bulk(
        cls,
        file_items: List[Tuple[str, bytes]],  # List of (filename, file_bytes)
        job_role: Optional[str] = None,
        job_description: Optional[str] = None,
        custom_jd: Optional[CustomJDConfig] = None,
        weights: Optional[ATSCriteriaWeights] = None,
    ) -> List[CandidateScreeningResult]:
        """
        Bulk processes up to 50 resumes asynchronously with deduplication,
        corrupt file handling, extraction failure protection, and rank ordering.
        """
        from .parser import ResumeParser
        results: List[CandidateScreeningResult] = []
        seen_hashes: Set[str] = set()

        for idx, (filename, file_bytes) in enumerate(file_items):
            file_id = f"cand-{idx+1}-{hash(filename) % 100000}"

            # 1. Deduplication check via content hash
            import hashlib
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            if file_hash in seen_hashes:
                continue
            seen_hashes.add(file_hash)

            # 2. Extract Text with failure handling
            try:
                raw_text = ResumeParser.extract_text(file_bytes, filename)
            except Exception as e:
                raw_text = ""

            clean_text = (raw_text or "").strip()

            # 3. If extraction failed or document is empty: Display extraction error (no score assigned!)
            if not clean_text or len(clean_text) < 20:
                empty_profile = ParsedCandidateProfile(
                    name=filename.rsplit(".", 1)[0].replace("_", " ").title(),
                    raw_text="",
                )
                results.append(
                    CandidateScreeningResult(
                        id=file_id,
                        rank=len(results) + 1,
                        candidate=empty_profile,
                        overall_ats_score=None,
                        match_tier=None,
                        recommendation=None,
                        breakdown=None,
                        skill_gap_analysis=None,
                        keyword_analysis=None,
                        strengths=[],
                        weaknesses=["Document text could not be extracted."],
                        actionable_improvements=[
                            ActionableImprovement(
                                section="File Format",
                                issue="Unreadable or corrupt document.",
                                suggested_fix="Upload a text-searchable PDF, DOCX, or TXT file.",
                            )
                        ],
                        status="ERROR",
                        extraction_error="Extraction Error: Unable to extract readable text. Ensure file is not scanned image without OCR, corrupt, or password-protected.",
                        file_name=filename,
                        file_size=len(file_bytes),
                    )
                )
                continue

            # 4. Successfully extracted: Run ATS evaluation
            try:
                eval_res = cls.score(
                    resume_text=clean_text,
                    job_description=job_description,
                    job_role=job_role,
                    custom_jd=custom_jd,
                    weights=weights,
                )
                cand_profile = cls.extract_candidate_profile(clean_text, filename)

                results.append(
                    CandidateScreeningResult(
                        id=file_id,
                        rank=1,
                        candidate=cand_profile,
                        overall_ats_score=eval_res.overall_ats_score,
                        match_tier=eval_res.match_tier,
                        recommendation=eval_res.recommendation,
                        breakdown=eval_res.breakdown,
                        skill_gap_analysis=eval_res.skill_gap_analysis,
                        keyword_analysis=eval_res.keyword_analysis,
                        strengths=eval_res.strengths,
                        weaknesses=eval_res.weaknesses,
                        actionable_improvements=eval_res.actionable_improvements,
                        status="COMPLETED",
                        extraction_error=None,
                        file_name=filename,
                        file_size=len(file_bytes),
                    )
                )
            except Exception as eval_err:
                results.append(
                    CandidateScreeningResult(
                        id=file_id,
                        rank=len(results) + 1,
                        candidate=ParsedCandidateProfile(name=filename, raw_text=clean_text[:200]),
                        overall_ats_score=None,
                        match_tier=None,
                        status="ERROR",
                        extraction_error=f"Processing Error: {str(eval_err)}",
                        file_name=filename,
                        file_size=len(file_bytes),
                    )
                )

        # 5. Rank ordering by highest ATS score (errors placed at end)
        results.sort(
            key=lambda x: (x.status == "COMPLETED", x.overall_ats_score or 0),
            reverse=True,
        )
        for i, item in enumerate(results):
            item.rank = i + 1

        return results

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. Criteria Evaluators
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def _evaluate_technical_skills(
        cls,
        candidate_profile: ParsedCandidateProfile,
        sections: Dict[str, str],
        must_have: List[str],
        preferred: List[str],
    ) -> Tuple[float, KeywordAnalysis, SkillGapAnalysis, List[str], List[str], bool]:
        """
        Criterion 1: Technical Skills Match (30%).
        Generates full Skill Gap Analysis with detailed explanations.
        """
        raw_lower = candidate_profile.raw_text.lower()
        exp_proj_lower = (sections.get("experience", "") + "\n" + sections.get("projects", "")).lower()
        skills_text_lower = sections.get("skills", "").lower()

        # Check for keyword stuffing:
        # e.g., >20 skills in dump, but minimal evidence in experience
        skills_words = [w.strip() for w in re.split(r"[,•|;\n]", skills_text_lower) if len(w.strip()) > 1]
        is_stuffed = len(skills_words) >= 20 and len(exp_proj_lower) > 100

        matching_skills: List[SkillItem] = []
        missing_mandatory: List[SkillItem] = []
        missing_preferred: List[SkillItem] = []
        partially_matching: List[SkillItem] = []
        semantic_matches: List[SemanticMatch] = []
        matched_keywords: List[str] = []
        missing_critical: List[str] = []

        total_must = max(1, len(must_have))
        total_pref = max(1, len(preferred))

        must_pts = 0.0
        pref_pts = 0.0

        for term in must_have:
            t_clean = term.strip().lower()
            matched, matched_term, is_syn, in_bullets = cls._match_skill_with_corroboration(
                target_skill=t_clean,
                raw_text=raw_lower,
                exp_text=exp_proj_lower,
            )
            if matched:
                if matched_term not in matched_keywords:
                    matched_keywords.append(matched_term)
                if is_syn:
                    semantic_matches.append(SemanticMatch(jd_term=term, resume_term=matched_term))

                if in_bullets:
                    must_pts += 1.0
                    matching_skills.append(
                        SkillItem(
                            skill=term,
                            reason=f"Mandatory requirement '{term}' verified with hands-on project/experience evidence.",
                        )
                    )
                else:
                    must_pts += 0.25 if is_stuffed else 0.5
                    partially_matching.append(
                        SkillItem(
                            skill=term,
                            reason=f"Listed '{term}' in standalone skills section, but lacks documented project accomplishments.",
                        )
                    )
            else:
                missing_critical.append(term)
                missing_mandatory.append(
                    SkillItem(
                        skill=term,
                        reason=f"Mandatory role requirement '{term}' was not found anywhere in the resume.",
                    )
                )

        for term in preferred:
            t_clean = term.strip().lower()
            matched, matched_term, is_syn, in_bullets = cls._match_skill_with_corroboration(
                target_skill=t_clean,
                raw_text=raw_lower,
                exp_text=exp_proj_lower,
            )
            if matched:
                if matched_term not in matched_keywords:
                    matched_keywords.append(matched_term)
                if is_syn:
                    semantic_matches.append(SemanticMatch(jd_term=term, resume_term=matched_term))

                if in_bullets:
                    pref_pts += 1.0
                    matching_skills.append(
                        SkillItem(
                            skill=term,
                            reason=f"Preferred skill '{term}' confirmed with active project usage.",
                        )
                    )
                else:
                    pref_pts += 0.25 if is_stuffed else 0.5
                    partially_matching.append(
                        SkillItem(
                            skill=term,
                            reason=f"Preferred skill '{term}' mentioned in skills block without project details.",
                        )
                    )
            else:
                missing_preferred.append(
                    SkillItem(
                        skill=term,
                        reason=f"Preferred skill '{term}' is absent; candidate could upskill here.",
                    )
                )

        # Additional & Relevant Technologies
        req_set = {m.lower() for m in must_have} | {p.lower() for p in preferred}
        additional_skills = [
            s for s in candidate_profile.technical_skills if s.lower() not in req_set
        ][:8]
        relevant_technologies = [
            t for t in (candidate_profile.frameworks + candidate_profile.databases + candidate_profile.tools_and_technologies)
            if t.lower() not in req_set
        ][:6]

        # Calculate Technical Score (0-100)
        # 75% weight on mandatory skills, 25% on preferred
        must_ratio = must_pts / total_must
        pref_ratio = pref_pts / total_pref
        score = (must_ratio * 75.0) + (pref_ratio * 25.0)
        tech_score = max(0.0, min(100.0, score))

        # Strengths & Weaknesses
        strengths = []
        weaknesses = []
        if len(matching_skills) >= 3:
            strengths.append(
                f"Strong technical alignment: Verified {len(matching_skills)} mandatory/preferred skills in hands-on context."
            )
        if missing_mandatory:
            weaknesses.append(
                f"Missing {len(missing_mandatory)} mandatory requirements: {', '.join([m.skill for m in missing_mandatory[:3]])}."
            )
        if is_stuffed:
            weaknesses.append("Keyword stuffing detected: multiple tools listed in skills block without experience evidence.")

        kw_analysis = KeywordAnalysis(
            matched_keywords=matched_keywords,
            missing_critical_keywords=missing_critical,
            semantic_matches=semantic_matches,
        )

        skill_gap = SkillGapAnalysis(
            matching_skills=matching_skills,
            missing_mandatory_skills=missing_mandatory,
            missing_preferred_skills=missing_preferred,
            partially_matching_skills=partially_matching,
            additional_skills=additional_skills,
            relevant_technologies=relevant_technologies,
        )

        return tech_score, kw_analysis, skill_gap, strengths, weaknesses, is_stuffed

    @classmethod
    def _evaluate_jd_relevance(
        cls,
        raw_text: str,
        jd_text: str,
        core_competencies: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        """Criterion 2: Job Description Relevance (20%)."""
        lower_raw = raw_text.lower()
        strengths = []
        weaknesses = []

        # Token overlap with core competencies
        matched_comps = 0
        for comp in core_competencies:
            comp_words = [w.lower() for w in comp.split() if len(w) > 3]
            if any(w in lower_raw for w in comp_words):
                matched_comps += 1

        comp_ratio = matched_comps / max(1, len(core_competencies))
        score = comp_ratio * 100.0

        if comp_ratio >= 0.6:
            strengths.append(f"High domain relevance: Matches {matched_comps}/{len(core_competencies)} core JD competency areas.")
        elif comp_ratio < 0.4:
            weaknesses.append(f"Domain mismatch: Resume reflects limited overlap with target JD core responsibilities.")

        return max(10.0, min(100.0, score)), strengths, weaknesses

    @classmethod
    def _evaluate_experience(
        cls,
        candidate_years: float,
        required_years: float,
        is_fresher_allowed: bool,
        sections: Dict[str, str],
        role_title: str,
        seniority_level: str,
    ) -> Tuple[float, List[str], List[str]]:
        """
        Criterion 3: Relevant Experience (15%).
        Implements Fresher Protection Rule: Freshers are not penalized when
        JD allows fresh graduates / entry-level roles.
        """
        strengths = []
        weaknesses = []
        exp_text = sections.get("experience", "")

        # Fresher Protection
        if is_fresher_allowed:
            if candidate_years >= 1.0 or len(exp_text) > 100 or len(sections.get("projects", "")) > 100:
                strengths.append(f"Fresher/Entry-level role qualification: Candidate possesses suitable internship or project background.")
                return 95.0, strengths, weaknesses
            return 85.0, strengths, weaknesses

        req_yrs = max(1.0, required_years)
        ratio = candidate_years / req_yrs

        if ratio >= 1.0:
            score = 100.0
            strengths.append(f"Meets seniority benchmark: {candidate_years:.1f} years experience exceeds required {required_years:.0f} years.")
        elif ratio >= 0.75:
            score = 80.0
        elif ratio >= 0.5:
            score = 60.0
            weaknesses.append(f"Experience deficit: {candidate_years:.1f} years detected vs {required_years:.0f} years target.")
        else:
            score = max(20.0, ratio * 100.0)
            weaknesses.append(f"Significant experience gap: {candidate_years:.1f} years detected vs {required_years:.0f} years required.")

        return score, strengths, weaknesses

    @classmethod
    def _evaluate_project_relevance(
        cls,
        candidate_profile: ParsedCandidateProfile,
        must_have_skills: List[str],
        role_title: str,
    ) -> Tuple[float, List[str], List[str]]:
        """Criterion 4: Project Relevance (10%)."""
        projects = candidate_profile.projects
        strengths = []
        weaknesses = []

        if not projects:
            return 30.0, [], ["No distinct projects found in resume; work history is purely duty-based."]

        tech_used_in_projects = 0
        must_set = {m.lower() for m in must_have_skills}

        for proj in projects:
            p_text = (proj.get("title", "") + " " + proj.get("description", "") + " " + " ".join(proj.get("technologies", []))).lower()
            if any(m in p_text for m in must_set):
                tech_used_in_projects += 1

        proj_ratio = tech_used_in_projects / max(1, len(projects))
        score = min(100.0, 50.0 + (proj_ratio * 50.0))

        if proj_ratio >= 0.5:
            strengths.append(f"Hands-on project relevance: {tech_used_in_projects} projects directly utilize target technology stacks.")

        return score, strengths, weaknesses

    @classmethod
    def _evaluate_education_match(
        cls,
        candidate_profile: ParsedCandidateProfile,
        sections: Dict[str, str],
        expected_fields: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        """Criterion 5: Education Match (10%)."""
        edu_text = (sections.get("education", "") + " " + (candidate_profile.education or "")).lower()
        strengths = []
        weaknesses = []

        base_score = 60.0
        deg_label = "Degree"
        for pat, label, pts in _DEGREE_PATTERNS:
            if pat.search(edu_text):
                base_score = pts
                deg_label = label
                break

        is_stem = any(f.lower() in edu_text for f in expected_fields)
        if is_stem:
            base_score = min(100.0, base_score + 10.0)
            strengths.append(f"Educational alignment: {deg_label} in STEM/related field.")
        else:
            if base_score > 70:
                strengths.append(f"Educational qualification: {deg_label}.")
            else:
                weaknesses.append("No explicit STEM/University degree detected.")

        return base_score, strengths, weaknesses

    @classmethod
    def _evaluate_certifications(
        cls,
        candidate_profile: ParsedCandidateProfile,
        sections: Dict[str, str],
    ) -> Tuple[float, List[str], List[str]]:
        """Criterion 6: Certifications (5%)."""
        certs = candidate_profile.certifications
        strengths = []
        weaknesses = []

        if len(certs) >= 2:
            strengths.append(f"Industry certifications: Verified {len(certs)} credentials ({', '.join(certs[:2])}).")
            return 100.0, strengths, weaknesses
        elif len(certs) == 1:
            strengths.append(f"Industry certification: {certs[0]}.")
            return 80.0, strengths, weaknesses
        elif "certif" in sections.get("certifications", "").lower():
            return 60.0, strengths, weaknesses

        return 30.0, [], []

    @classmethod
    def _evaluate_keywords_and_verbs(
        cls,
        raw_text: str,
        sections: Dict[str, str],
        expected_verbs: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        """Criterion 7: Keywords Match (5%)."""
        lower_raw = raw_text.lower()
        strengths = []
        weaknesses = []

        found_verbs = sum(1 for v in expected_verbs if re.search(r"\b" + v + r"\b", lower_raw))
        ratio = found_verbs / max(1, len(expected_verbs))
        score = min(100.0, ratio * 100.0)

        if ratio >= 0.5:
            strengths.append(f"Action-oriented keyword phrasing: High presence of role-specific achievement verbs.")
        else:
            weaknesses.append("Lacks dynamic action keywords; profile describes passive duties.")

        return max(20.0, score), strengths, weaknesses

    @classmethod
    def _evaluate_resume_quality(
        cls,
        raw_text: str,
        sections: Dict[str, str],
        candidate_profile: ParsedCandidateProfile,
    ) -> Tuple[float, List[str], List[str], List[ActionableImprovement]]:
        """
        Criterion 8: Resume Quality (5%).
        Evaluates formatting hygiene, contact links, and quantifiable metrics.
        """
        strengths = []
        weaknesses = []
        improvements: List[ActionableImprovement] = []

        score = 70.0
        # Contact info check
        if candidate_profile.email and candidate_profile.phone:
            score += 15.0
        else:
            weaknesses.append("Missing contact details (email or phone).")
            improvements.append(
                ActionableImprovement(
                    section="Contact Info",
                    issue="Incomplete contact credentials.",
                    suggested_fix="Ensure valid email address and international phone number are present.",
                )
            )

        # URLs
        if _URL_REGEX.search(raw_text):
            score += 15.0
            strengths.append("Verified online presence: Includes LinkedIn/GitHub portfolio links.")
        else:
            improvements.append(
                ActionableImprovement(
                    section="Contact Info",
                    issue="No LinkedIn or GitHub portfolio link.",
                    suggested_fix="Include your LinkedIn URL or GitHub profile for technical verification.",
                )
            )

        # Metrics check
        has_metrics = bool(_METRIC_PERCENT.search(raw_text) or _METRIC_SCALE.search(raw_text))
        if has_metrics:
            strengths.append("Measurable impact quality: Resume contains quantifiable metrics.")

        return max(20.0, min(100.0, score)), strengths, weaknesses, improvements

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. Helpers & Classifiers
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def _classify_match_tier(cls, score: int) -> str:
        """Classifies ATS score into 6 official ranges."""
        if score >= 90:
            return "Excellent Match (90-100)"
        elif score >= 80:
            return "Strong Match (80-89)"
        elif score >= 70:
            return "Good Match (70-79)"
        elif score >= 60:
            return "Moderate Match (60-69)"
        elif score >= 40:
            return "Low Match (40-59)"
        else:
            return "Poor Match (0-39)"

    @classmethod
    def _generate_recommendation(
        cls,
        overall_score: int,
        tech_skills_score: float,
        exp_score: float,
        is_stuffed: bool,
        candidate_name: str,
        role_title: str,
        breakdown_dict: Dict[str, str],
    ) -> RecruiterRecommendation:
        """
        Generates unbiased, job-related AI recruiter recommendations:
        Shortlist | Consider for Interview | Needs Further Review | Not Recommended.
        """
        if overall_score >= 80 and tech_skills_score >= 70:
            verdict = "Shortlist"
            reasoning = (
                f"{candidate_name} exhibits strong alignment with the {role_title} requirements, "
                f"achieving {overall_score}/100 with proven hands-on technical skills ({tech_skills_score:.0f}%) "
                f"and verified project experience."
            )
        elif overall_score >= 70:
            verdict = "Consider for Interview"
            reasoning = (
                f"{candidate_name} demonstrates good core qualifications ({overall_score}/100) and meets baseline requirements. "
                f"Recommend conducting a technical interview to evaluate specific depth in missing preferred skills."
            )
        elif overall_score >= 50 and not is_stuffed:
            verdict = "Needs Further Review"
            reasoning = (
                f"{candidate_name} scored {overall_score}/100. While showing potential in foundational areas, "
                f"they present gaps in core mandatory technologies or seniority fit. Manual recruiter review recommended."
            )
        else:
            verdict = "Not Recommended"
            reasoning = (
                f"{candidate_name} scored {overall_score}/100, which falls below the threshold for {role_title}. "
                f"Significant gaps identified across mandatory technical competencies and role expectations."
            )

        explanation = (
            f"ATS Compatibility Score: {overall_score}/100 computed deterministically using weighted rubric: "
            + ", ".join([f"{k}: {v}" for k, v in breakdown_dict.items()])
        )

        return RecruiterRecommendation(
            verdict=verdict,
            reasoning=reasoning,
            score_explanation=explanation,
        )

    @classmethod
    def _resolve_requirements(
        cls,
        job_description: Optional[str],
        job_role: Optional[str],
        custom_jd: Optional[CustomJDConfig],
    ) -> Tuple[Dict[str, Any], str]:
        """Resolves target requirements from Custom JD (Option B) or Role/Plain JD (Option A)."""
        # Option B: Custom JD
        if custom_jd and (custom_jd.description or custom_jd.required_skills or custom_jd.title):
            must_have = list(custom_jd.required_skills)
            nice_to_have = list(custom_jd.preferred_skills)
            min_exp = custom_jd.min_experience or 0.0
            title = custom_jd.title or "Custom Role"

            # Supplement from text if skills were not explicitly split
            if not must_have and custom_jd.description:
                auto_reqs = cls._extract_requirements_from_jd(custom_jd.description)
                must_have = auto_reqs["must_have_skills"]
                nice_to_have = auto_reqs["nice_to_have_skills"]
                if not min_exp:
                    min_exp = auto_reqs["min_experience"]

            return {
                "role_title": title,
                "seniority_level": "mid" if min_exp >= 3 else "junior",
                "min_experience": min_exp,
                "must_have_skills": must_have,
                "nice_to_have_skills": nice_to_have,
                "core_competencies": custom_jd.mandatory_requirements or ["Domain Competency"],
                "effective_jd_text": custom_jd.description or f"{title}: {', '.join(must_have)}",
                "expected_degree_fields": _STEM_FIELDS,
            }, "job_description"

        # Option A: Explicit JD text
        clean_jd = (job_description or "").strip()
        if len(clean_jd) >= 50:
            reqs = cls._extract_requirements_from_jd(clean_jd)
            reqs["role_title"] = job_role or reqs.get("role_title", "Software Engineer")
            reqs["effective_jd_text"] = clean_jd
            return reqs, "job_description"

        # Option A: Predefined Role Inferrer
        benchmark = infer_role_benchmarks(job_role)
        reqs = {
            "role_title": benchmark.role_title,
            "seniority_level": benchmark.seniority_level,
            "min_experience": benchmark.min_years_experience,
            "must_have_skills": benchmark.must_have_skills,
            "nice_to_have_skills": benchmark.nice_to_have_skills,
            "core_competencies": benchmark.core_competencies,
            "expected_action_verbs": benchmark.expected_action_verbs,
            "expected_degree_fields": benchmark.expected_degree_fields,
            "effective_jd_text": benchmark.synthetic_jd_text,
        }
        return reqs, "inferred_role"

    @classmethod
    def _extract_requirements_from_jd(cls, jd_text: str) -> Dict[str, Any]:
        """Extracts required skills and experience from JD text."""
        lower_jd = jd_text.lower()
        exp_match = re.search(
            r"\b(\d+)\+?\s*(?:-\s*(\d+))?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)?\b",
            lower_jd,
        )
        min_exp = float(exp_match.group(1)) if exp_match else 3.0

        seniority = "mid"
        if re.search(r"\b(senior|sr|lead|principal|staff)\b", lower_jd):
            seniority = "senior"
        elif re.search(r"\b(junior|entry|intern|graduate|fresher)\b", lower_jd):
            seniority = "junior"

        found_keywords: Set[str] = set()
        for group_name, terms in SKILL_TAXONOMY.items():
            for term in terms:
                pattern = r"\b" + re.escape(term) + r"(?:s|ful|ing)?\b"
                if re.search(pattern, lower_jd):
                    found_keywords.add(term)

        for t1, t2 in _SYNONYM_PAIRS:
            for term in (t1, t2):
                pattern = r"\b" + re.escape(term) + r"(?:s|ful|ing)?\b"
                if re.search(pattern, lower_jd):
                    found_keywords.add(term)

        must_have: List[str] = []
        nice_to_have: List[str] = []

        req_split = re.split(r"\b(requirements|qualifications|must have|what you need|what you'll bring)\b", lower_jd)
        pref_split = re.split(r"\b(preferred|bonus|nice to have|pluses|optional)\b", lower_jd)

        req_section = req_split[-1] if len(req_split) > 1 else lower_jd
        pref_section = pref_split[-1] if len(pref_split) > 1 else ""

        for kw in sorted(found_keywords):
            kw_pat = r"\b" + re.escape(kw) + r"\b"
            if pref_section and re.search(kw_pat, pref_section):
                nice_to_have.append(kw)
            elif re.search(kw_pat, req_section):
                must_have.append(kw)
            else:
                must_have.append(kw)

        if not must_have and not nice_to_have:
            must_have = ["python", "sql", "git", "api"]
            nice_to_have = ["docker", "cloud"]
        elif not must_have:
            must_have = nice_to_have[:3]
            nice_to_have = nice_to_have[3:]

        return {
            "role_title": "Target Role",
            "seniority_level": seniority,
            "min_experience": min_exp,
            "must_have_skills": must_have,
            "nice_to_have_skills": nice_to_have,
            "core_competencies": ["API Architecture", "Database Design", "Testing"],
            "effective_jd_text": jd_text,
            "expected_degree_fields": _STEM_FIELDS,
        }

    @classmethod
    def _segment_resume_sections(cls, text: str) -> Dict[str, str]:
        """Segments resume into canonical sections."""
        section_headers = {
            "contact": ["contact", "personal info", "contact information"],
            "summary": ["summary", "professional summary", "profile", "about me", "objective", "executive summary"],
            "experience": ["experience", "work experience", "employment history", "professional experience", "work history"],
            "projects": ["projects", "personal projects", "key projects", "technical projects"],
            "skills": ["skills", "technical skills", "technologies", "competencies", "core competencies", "tools & technologies"],
            "education": ["education", "academic background", "academics", "educational qualification", "university"],
            "certifications": ["certifications", "certificates", "licenses", "courses", "credentials"],
        }

        lines = text.splitlines()
        found_markers: List[Tuple[int, str]] = []

        for idx, line in enumerate(lines):
            clean_line = line.strip().lower()
            clean_line = re.sub(r"[:\-_|#*]", "", clean_line).strip()
            if not clean_line or len(clean_line) > 35:
                continue

            for section_key, aliases in section_headers.items():
                if clean_line in aliases:
                    found_markers.append((idx, section_key))
                    break

        found_markers.sort(key=lambda x: x[0])

        segmented: Dict[str, str] = {
            "contact": "\n".join(lines[:12]),
            "summary": "",
            "experience": "",
            "projects": "",
            "skills": "",
            "education": "",
            "certifications": "",
        }

        if not found_markers:
            segmented["experience"] = text
            return segmented

        for i, (line_idx, section_name) in enumerate(found_markers):
            start = line_idx + 1
            end = found_markers[i + 1][0] if i + 1 < len(found_markers) else len(lines)
            content = "\n".join(lines[start:end]).strip()
            segmented[section_name] = (segmented.get(section_name, "") + "\n" + content).strip()

        return segmented

    @classmethod
    def _match_skill_with_corroboration(
        cls,
        target_skill: str,
        raw_text: str,
        exp_text: str,
    ) -> Tuple[bool, str, bool, bool]:
        """Returns: (matched, matched_as_string, is_semantic_synonym, is_in_experience_bullets)."""
        clean_target = target_skill.strip().lower()

        pattern = r"\b" + re.escape(clean_target) + r"(?:s|ful|ing|ed)?\b"
        match = re.search(pattern, raw_text)
        if match:
            in_bullets = bool(re.search(pattern, exp_text))
            return True, clean_target, False, in_bullets

        synonyms = _SYNONYM_LOOKUP.get(clean_target, set())
        for syn in synonyms:
            syn_pattern = r"\b" + re.escape(syn) + r"(?:s|ful|ing|ed)?\b"
            match = re.search(syn_pattern, raw_text)
            if match:
                in_bullets = bool(re.search(syn_pattern, exp_text))
                return True, syn, True, in_bullets

        return False, "", False, False

    # ═══════════════════════════════════════════════════════════════════════════
    # Extraction Helpers (Name, College, Skills, Projects, Experience)
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def _extract_candidate_name(cls, raw_text: str, file_name: str) -> str:
        """Extracts candidate name from top lines of resume or filename."""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for line in lines[:8]:
            clean = re.sub(r"[^a-zA-Z\s]", "", line).strip()
            words = clean.split()
            if 2 <= len(words) <= 4 and len(clean) <= 40:
                lower_c = clean.lower()
                if not any(hdr in lower_c for hdr in [
                    "resume", "curriculum", "vitae", "summary", "profile", "contact",
                    "experience", "education", "phone", "email", "developer", "engineer"
                ]):
                    return clean.title()

        if file_name:
            base = file_name.rsplit(".", 1)[0].replace("_", " ").replace("-", " ")
            clean_base = re.sub(r"[^a-zA-Z\s]", "", base).strip().title()
            if len(clean_base) > 3:
                return clean_base

        return "Candidate"

    @classmethod
    def _extract_college_name(cls, edu_text: str) -> Optional[str]:
        """Extracts college / university name."""
        college_pattern = re.compile(
            r"([A-Z][a-zA-Z\s&]{2,40}(?:University|College|Institute|Polytechnic|Academy|Campus|School of \w+))",
            re.M,
        )
        match = college_pattern.search(edu_text)
        if match:
            return match.group(1).strip()

        # Check standard tech colleges like IIT, BITS, MIT, Stanford, Berkeley
        popular = ["MIT", "Stanford", "Harvard", "Berkeley", "IIT", "BITS", "Carnegie Mellon", "UCLA", "Caltech"]
        for p in popular:
            if re.search(r"\b" + p + r"\b", edu_text, re.I):
                return p

        return None

    @classmethod
    def _extract_categorized_skills(
        cls,
        raw_text: str,
    ) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
        """Extracts skills and partitions into Languages, Frameworks, DBs, and Tools."""
        lower_text = raw_text.lower()
        all_found = set()

        prog_langs = []
        frameworks = []
        databases = []
        tools = []

        lang_keywords = ["python", "java", "javascript", "typescript", "c++", "c#", "golang", "go", "ruby", "rust", "php", "kotlin", "swift", "r", "scala", "sql", "bash"]
        framework_keywords = ["react", "vue", "angular", "nextjs", "fastapi", "django", "flask", "spring boot", "spring", "express", "nestjs", "laravel", "tailwind", "redux"]
        db_keywords = ["postgresql", "postgres", "mysql", "mongodb", "redis", "cassandra", "sqlite", "oracle", "dynamodb", "elasticsearch", "snowflake"]
        tool_keywords = ["docker", "kubernetes", "k8s", "aws", "gcp", "azure", "git", "ci/cd", "terraform", "linux", "jenkins", "kafka", "graphql", "celery", "airflow", "figma"]

        for kw in lang_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower_text):
                prog_langs.append(kw.title() if len(kw) > 3 else kw.upper())
                all_found.add(kw)

        for kw in framework_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower_text):
                frameworks.append(kw.title())
                all_found.add(kw)

        for kw in db_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower_text):
                databases.append(kw.title())
                all_found.add(kw)

        for kw in tool_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", lower_text):
                tools.append(kw.title() if len(kw) > 3 else kw.upper())
                all_found.add(kw)

        all_skills = sorted(list(set(prog_langs + frameworks + databases + tools)))
        return all_skills, prog_langs, frameworks, databases, tools

    @classmethod
    def _extract_experience_details(
        cls,
        raw_text: str,
        sections: Dict[str, str],
    ) -> Tuple[float, List[Dict[str, Any]]]:
        """Calculates experience years and extracts role entries."""
        current_year = datetime.now().year
        exp_text = sections.get("experience", "") or raw_text

        # Explicit claim
        explicit_matches = re.findall(
            r"\b(\d{1,2})\+?\s*(?:years?|yrs?)(?:\s*of)?\s*(?:experience|exp)\b",
            raw_text,
            re.I,
        )
        explicit_years = [float(m) for m in explicit_matches if 0.5 <= float(m) <= 40]

        date_pattern = re.compile(
            r"\b(20\d{2}|19\d{2})\s*(?:[-–to/]+)\s*(20\d{2}|19\d{2}|present|current|now)\b",
            re.I,
        )
        intervals: List[Tuple[int, int]] = []
        for match in date_pattern.finditer(exp_text):
            start_yr = int(match.group(1))
            end_val = match.group(2).lower()
            end_yr = current_year if end_val in ("present", "current", "now") else int(end_val)
            if start_yr <= end_yr and (end_yr - start_yr) <= 30:
                intervals.append((start_yr, end_yr))

        total_calc_years = 0.0
        if intervals:
            intervals.sort(key=lambda x: x[0])
            merged = [intervals[0]]
            for start, end in intervals[1:]:
                prev_start, prev_end = merged[-1]
                if start <= prev_end:
                    merged[-1] = (prev_start, max(prev_end, end))
                else:
                    merged.append((start, end))
            total_calc_years = sum(end - start for start, end in merged)
            total_calc_years = max(total_calc_years, 0.5)

        years = max(explicit_years) if explicit_years else total_calc_years

        # Extract basic entries
        entries = []
        lines = [l.strip() for l in exp_text.splitlines() if len(l.strip()) > 10]
        for l in lines[:5]:
            if any(role_word in l.lower() for role_word in ["engineer", "developer", "lead", "analyst", "intern", "architect"]):
                entries.append({"title": l, "duration": "Documented Tenure"})

        return years, entries

    @classmethod
    def _extract_project_entries(cls, proj_text: str, raw_text: str) -> List[Dict[str, Any]]:
        """Extracts project titles and descriptions."""
        source_text = proj_text if len(proj_text) > 30 else raw_text
        projects = []
        lines = [l.strip() for l in source_text.splitlines() if len(l.strip()) > 10]

        current_proj = None
        for line in lines:
            if line.startswith(("•", "-", "*", "▶", "►")):
                if current_proj:
                    current_proj["description"] += " " + line
            elif len(line.split()) <= 6 and not line.endswith("."):
                if current_proj:
                    projects.append(current_proj)
                current_proj = {"title": line, "description": "", "technologies": []}
                if len(projects) >= 4:
                    break

        if current_proj and current_proj not in projects:
            projects.append(current_proj)

        return projects[:4]

    @classmethod
    def _extract_certifications(cls, raw_text: str) -> List[str]:
        """Extracts recognized certifications."""
        lower_raw = raw_text.lower()
        found = []
        for c in _CERTIFICATION_KEYWORDS:
            if c in lower_raw:
                found.append(c.title())
        return list(set(found))

    @classmethod
    def _extract_achievements(cls, raw_text: str, sections: Dict[str, str]) -> List[str]:
        """Extracts notable achievements."""
        ach_text = sections.get("certifications", "") + "\n" + raw_text
        achievements = []
        for line in ach_text.splitlines():
            clean = line.strip()
            if any(term in clean.lower() for term in ["award", "1st place", "hackathon", "scholarship", "patent", "dean's list", "published"]):
                if len(clean) > 15:
                    achievements.append(clean)
        return achievements[:3]

    # ═══════════════════════════════════════════════════════════════════════════
    # Empty / Extraction Failure Handler
    # ═══════════════════════════════════════════════════════════════════════════

    @classmethod
    def _empty_resume_response(
        cls,
        job_description: Optional[str],
        job_role: Optional[str],
    ) -> ATSScoreResponse:
        """Returns valid zero-score response when text extraction fails."""
        input_mode = "job_description" if (job_description and len(job_description.strip()) >= 50) else "inferred_role"
        return ATSScoreResponse(
            overall_ats_score=0,
            match_tier="Poor Match (0-39)",
            input_mode_used=input_mode,
            breakdown=ATSScoreBreakdown(),
            keyword_analysis=KeywordAnalysis(
                matched_keywords=[],
                missing_critical_keywords=["Document text could not be extracted."],
                semantic_matches=[],
            ),
            skill_gap_analysis=SkillGapAnalysis(),
            recommendation=RecruiterRecommendation(
                verdict="Not Recommended",
                reasoning="Resume text could not be extracted or file is empty.",
                score_explanation="Score 0/100 due to extraction error.",
            ),
            strengths=[],
            critical_gaps=["No readable text extracted from file."],
            weaknesses=["Document is unreadable or empty."],
            actionable_improvements=[
                ActionableImprovement(
                    section="File Format",
                    issue="Unreadable document.",
                    suggested_fix="Upload a text-searchable PDF, DOCX, or TXT file.",
                )
            ],
        )
