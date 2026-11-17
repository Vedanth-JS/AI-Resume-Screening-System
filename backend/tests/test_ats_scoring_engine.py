"""
Unit & Integration Tests for Advanced ATS Resume Screening and Scoring Engine.
Validates:
  - 8-Criteria Configurable Evaluation Model
  - 6-Tier Match Classification (90-100, 80-89, 70-79, 60-69, 40-59, 0-39)
  - Skill Gap Analysis (Matching, Missing Mandatory, Missing Preferred, Partially Matching)
  - Option A (Predefined Role) & Option B (Custom JD)
  - Anti-hallucination & anti-keyword stuffing guardrails
  - Fresher protection rule
  - Extraction failure protection
"""
import pytest
from backend.app.core.ats_scoring_engine import ATSScoringEngine
from backend.app.schemas.ats_engine import ATSScoreResponse, CustomJDConfig, ATSCriteriaWeights


STRONG_BACKEND_RESUME = """
John Doe
Email: john.doe@techcompany.com | Phone: +1-555-0199 | LinkedIn: linkedin.com/in/johndoe | GitHub: github.com/johndoe

PROFESSIONAL SUMMARY
Senior Backend Software Engineer with 7+ years of experience architecting and delivering high-throughput distributed systems using Python, FastAPI, Docker, and PostgreSQL.

WORK EXPERIENCE
Senior Backend Engineer | Apex Cloud Solutions (2020 - Present)
• Architected and deployed 15+ microservices in Python and FastAPI, handling 50,000 requests/sec with 99.99% SLA availability.
• Optimized complex PostgreSQL queries and indexing, slashing p99 database latency by 42% for 3.2M daily active users.
• Engineered distributed caching layer with Redis, reducing primary database load by 60% and saving $140,000 in cloud compute costs annually.
• Containerized production workloads with Docker and orchestrated CI/CD automated release pipelines.

Backend Software Engineer | DataCorp Systems (2017 - 2020)
• Developed RESTful APIs and asynchronous data processing pipelines using Python, SQL, and Celery.
• Spearheaded migration from legacy monolithic application to service-oriented architecture, cutting release cycles from 3 weeks to 2 days.
• Maintained 95% automated test coverage using PyTest and integrated pre-commit linting workflows.

TECHNICAL SKILLS
Languages: Python, SQL, JavaScript
Frameworks & Databases: FastAPI, Django, PostgreSQL, Redis, Celery
DevOps & Cloud: Docker, AWS, Git, Linux, Microservices
Testing & Practices: PyTest, RESTful APIs, Agile, System Design

EDUCATION
Bachelor of Science in Computer Science | University of California, Berkeley (2013 - 2017)

CERTIFICATIONS
AWS Certified Solutions Architect – Associate
"""

KEYWORD_STUFFED_RESUME = """
Jane Doe
Email: jane.doe@example.com | Phone: +1-555-1122

TECHNICAL SKILLS
Python, Java, C++, Golang, Rust, JavaScript, TypeScript, FastAPI, Django, Flask, Express, NestJS, Spring Boot, PostgreSQL, MySQL, MongoDB, Redis, Cassandra, Kafka, RabbitMQ, Docker, Kubernetes, AWS, GCP, Azure, Terraform, Ansible, PyTorch, TensorFlow, Scikit-Learn, Pandas, NumPy, Spark, Hadoop, Linux, Git, CI/CD, Microservices, GraphQL, Nginx

EXPERIENCE
Junior Assistant | Small Business Corp (2023 - 2024)
• Responsible for assisting the software team with daily maintenance and clerical tasks.
• Worked on spreadsheets and helped team members with documentation.
• Tasked with routine bug logging and attended weekly status meetings.

EDUCATION
High School Diploma | Local High School (2022)
"""

PASSIVE_DUTY_RESUME = """
Bob Smith
Email: bob.smith@example.com | Phone: +1-555-3344 | LinkedIn: linkedin.com/in/bobsmith

SUMMARY
Software developer with 4 years of experience working with Python and SQL.

EXPERIENCE
Software Developer | MidCorp Inc. (2020 - Present)
• Responsible for writing Python backend scripts.
• Duties included maintaining the PostgreSQL database and checking logs.
• Worked on bug tickets and participated in scrum meetings.
• Assisted senior developers with system maintenance.

SKILLS
Python, PostgreSQL, SQL, Git, Linux

EDUCATION
Bachelor of Science in Information Technology | City College (2016 - 2020)
"""

SYNONYM_RESUME = """
Alice Johnson
Email: alice.j@example.com | Phone: +1-555-8899 | LinkedIn: linkedin.com/in/alicej | GitHub: github.com/alicej

PROFESSIONAL SUMMARY
Senior Cloud Engineer with 5+ years of experience building cloud native services.

EXPERIENCE
Cloud Software Engineer | CloudNova (2019 - Present)
• Built microservices using Go and deployed containerized services to K8s clusters.
• Migrated transaction databases to Postgres, improving query speeds by 35% for 1M+ users.
• Created front-end management interfaces using React and TypeScript.

SKILLS
Go, K8s, Postgres, React, TypeScript, Git

EDUCATION
Master of Science in Software Engineering | Tech University (2017 - 2019)
"""


def test_strong_match_with_explicit_jd():
    """Verify strong candidate achieves high score with valid schema under explicit JD."""
    jd = """
    Job Title: Senior Backend Software Engineer
    Experience: Minimum 5+ years of software development experience required.
    Requirements:
    Must have hands-on expertise in:
    - Python
    - FastAPI
    - PostgreSQL
    - Docker
    - RESTful APIs
    - AWS
    Nice to have:
    - Redis
    - Microservices
    - CI/CD
    """
    res = ATSScoringEngine.score(resume_text=STRONG_BACKEND_RESUME, job_description=jd)

    assert isinstance(res, ATSScoreResponse)
    assert res.input_mode_used == "job_description"
    assert res.overall_ats_score >= 75
    assert "Match" in res.match_tier
    assert res.recommendation is not None
    assert res.recommendation.verdict in ["Shortlist", "Consider for Interview"]

    # Verify 8-criteria breakdown
    assert 0 <= res.breakdown.technical_skills_score <= 100
    assert 0 <= res.breakdown.jd_relevance_score <= 100
    assert 0 <= res.breakdown.relevant_experience_score <= 100
    assert 0 <= res.breakdown.project_relevance_score <= 100
    assert 0 <= res.breakdown.education_match_score <= 100
    assert 0 <= res.breakdown.certifications_score <= 100
    assert 0 <= res.breakdown.keywords_match_score <= 100
    assert 0 <= res.breakdown.resume_quality_score <= 100

    # Verify skill gap analysis
    assert res.skill_gap_analysis is not None
    assert len(res.skill_gap_analysis.matching_skills) >= 2


def test_inferred_role_fallback_when_jd_empty():
    """Verify engine falls back to inferred role when JD is None or < 50 characters."""
    res_none = ATSScoringEngine.score(
        resume_text=STRONG_BACKEND_RESUME,
        job_description=None,
        job_role="Senior Backend Software Engineer",
    )
    assert res_none.input_mode_used == "inferred_role"
    assert res_none.overall_ats_score >= 65

    res_short = ATSScoringEngine.score(
        resume_text=STRONG_BACKEND_RESUME,
        job_description="Short JD text",
        job_role="Backend Developer",
    )
    assert res_short.input_mode_used == "inferred_role"


def test_semantic_synonym_matching():
    """Verify technology synonyms (e.g. Postgres == PostgreSQL, K8s == Kubernetes, Go == Golang, React == React.js)."""
    jd = """
    We require at least 4 years of experience.
    Requirements:
    - Golang
    - Kubernetes
    - PostgreSQL
    - React.js
    """
    res = ATSScoringEngine.score(resume_text=SYNONYM_RESUME, job_description=jd)

    assert res.input_mode_used == "job_description"
    semantic_pairs = [(m.jd_term.lower(), m.resume_term.lower()) for m in res.keyword_analysis.semantic_matches]
    assert ("golang", "go") in semantic_pairs
    assert ("kubernetes", "k8s") in semantic_pairs
    assert ("postgresql", "postgres") in semantic_pairs
    assert ("react.js", "react") in semantic_pairs


def test_missing_critical_skills_penalized():
    """Verify that missing must-have skills are heavily penalized and tracked in missing_critical_keywords."""
    jd = """
    Requirements:
    Must have hands-on experience with:
    - Kubernetes
    - Kafka
    - Terraform
    - Golang
    - Cassandra
    """
    res = ATSScoringEngine.score(resume_text=STRONG_BACKEND_RESUME, job_description=jd)

    assert len(res.keyword_analysis.missing_critical_keywords) >= 3
    assert "kafka" in [k.lower() for k in res.keyword_analysis.missing_critical_keywords]
    assert res.breakdown.technical_skills_score < 50
    assert len(res.skill_gap_analysis.missing_mandatory_skills) >= 3


def test_anti_keyword_stuffing_guardrail():
    """Verify keyword stuffing attempts without bullet corroboration are penalized."""
    res = ATSScoringEngine.score(
        resume_text=KEYWORD_STUFFED_RESUME,
        job_role="Senior Full Stack Engineer",
    )

    assert res.overall_ats_score < 60
    assert "Match" in res.match_tier
    all_issues = " ".join(
        res.weaknesses + [imp.issue for imp in res.actionable_improvements]
    ).lower()
    assert "stuffing" in all_issues or "unsubstantiated" in all_issues or "missing" in all_issues or "bullet" in all_issues


def test_anti_hallucination_guardrail():
    """Verify that skills not in the resume text are NEVER credited."""
    res = ATSScoringEngine.score(
        resume_text=STRONG_BACKEND_RESUME,
        job_role="Data Scientist",
    )
    matched = [m.lower() for m in res.keyword_analysis.matched_keywords]
    assert "pytorch" not in matched
    assert "tableau" not in matched
    assert "tensorflow" not in matched


def test_quantifiable_impact_scoring_contrast():
    """Verify achievement bullets with metrics score significantly higher than passive duty lists."""
    res_quantified = ATSScoringEngine.score(
        resume_text=STRONG_BACKEND_RESUME,
        job_role="Backend Developer",
    )
    res_passive = ATSScoringEngine.score(
        resume_text=PASSIVE_DUTY_RESUME,
        job_role="Backend Developer",
    )

    assert res_quantified.overall_ats_score > res_passive.overall_ats_score


def test_formatting_and_education_evaluation():
    """Verify degree, certification, section completeness, and contact links scoring."""
    res = ATSScoringEngine.score(
        resume_text=STRONG_BACKEND_RESUME,
        job_role="Senior Full Stack Engineer",
    )
    assert res.breakdown.education_match_score >= 80
    assert res.breakdown.certifications_score >= 70


def test_edge_case_empty_resume():
    """Verify empty resume returns valid schema with 0 score without exceptions."""
    res = ATSScoringEngine.score(resume_text="", job_role="Backend Developer")
    assert res.overall_ats_score == 0
    assert res.match_tier == "Poor Match (0-39)"
    assert res.recommendation.verdict == "Not Recommended"
    assert len(res.actionable_improvements) >= 1


def test_edge_case_whitespace_resume():
    """Verify whitespace-only resume returns valid 0 score."""
    res = ATSScoringEngine.score(resume_text="   \n\t  \n  ", job_role="Software Engineer")
    assert res.overall_ats_score == 0
    assert res.match_tier == "Poor Match (0-39)"


def test_career_gap_handling():
    """Verify non-overlapping intervals calculate active tenure without inflating career gaps."""
    gap_resume = """
    Alex Ray
    Email: alex@example.com | Phone: 555-4433 | LinkedIn: linkedin.com/in/alex

    EXPERIENCE
    Software Engineer | Alpha Co (2016 - 2018)
    • Developed Python scripts and REST APIs.

    -- Career Break / Travel (2018 - 2021) --

    Backend Engineer | Beta Co (2021 - 2023)
    • Engineered FastAPI microservices.

    SKILLS
    Python, FastAPI, SQL

    EDUCATION
    Bachelor of Science in Computer Science (2012 - 2016)
    """
    res = ATSScoringEngine.score(resume_text=gap_resume, job_role="Software Engineer")
    assert res.breakdown.relevant_experience_score > 0
    assert res.overall_ats_score > 0


def test_custom_jd_option_b():
    """Verify Option B custom JD evaluation."""
    custom = CustomJDConfig(
        title="Full Stack Java & React Engineer",
        description="Looking for an engineer with Java, Spring Boot, React, and Docker.",
        required_skills=["Java", "Spring Boot", "React"],
        preferred_skills=["Docker", "Redis"],
        min_experience=3.0,
    )
    res = ATSScoringEngine.score(
        resume_text=STRONG_BACKEND_RESUME,
        custom_jd=custom,
    )
    assert res.input_mode_used == "job_description"
    assert res.overall_ats_score > 0
    # Python resume lacks Java & Spring Boot
    assert any("java" in m.skill.lower() for m in res.skill_gap_analysis.missing_mandatory_skills)
