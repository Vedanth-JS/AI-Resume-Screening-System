"""
Dynamic Role Benchmark Inferrer.
──────────────────────────────────────────────────────────────────────────────
Comprehensive industry-standard benchmarks for 16 predefined roles plus dynamic
fallback heuristics for custom titles.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
from .skill_synonyms import SKILL_TAXONOMY


@dataclass
class RoleBenchmark:
    role_title: str
    seniority_level: str  # "intern", "junior", "mid", "senior", "lead", "staff", "executive"
    min_years_experience: float
    must_have_skills: List[str] = field(default_factory=list)
    nice_to_have_skills: List[str] = field(default_factory=list)
    core_competencies: List[str] = field(default_factory=list)
    expected_action_verbs: List[str] = field(default_factory=list)
    expected_metrics: List[str] = field(default_factory=list)
    expected_degree_fields: List[str] = field(default_factory=list)
    synthetic_jd_text: str = ""


# Curated Industry-Standard Archetypes for all 16 predefined roles
PREDEFINED_ROLES: List[str] = [
    "Software Engineer",
    "Senior Full Stack Engineer",
    "Java Developer",
    "Python Developer",
    "Frontend Developer",
    "Backend Developer",
    "Data Analyst",
    "Data Scientist",
    "Machine Learning Engineer",
    "AI Engineer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Cybersecurity Engineer",
    "Database Administrator",
    "QA Engineer",
    "UI/UX Designer",
]

_ROLE_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "software engineer": {
        "title": "Software Engineer",
        "must_have": ["python", "java", "sql", "git", "data structures", "algorithms", "rest", "object-oriented programming"],
        "nice_to_have": ["docker", "ci/cd", "unit testing", "system design", "linux", "cloud"],
        "competencies": [
            "Data Structures & Algorithmic Problem Solving", "Modular Clean Code & OOP",
            "API Design & Integration", "Unit & Integration Testing", "Git Version Control"
        ],
        "action_verbs": ["engineered", "built", "implemented", "optimized", "developed", "debugged", "refactored", "delivered"],
        "metrics": ["code coverage (%)", "execution latency (ms)", "bug resolution rate", "feature delivery speed"],
        "degrees": ["Computer Science", "Software Engineering", "Information Technology", "Computer Engineering"],
    },
    "senior full stack engineer": {
        "title": "Senior Full Stack Engineer",
        "must_have": ["react", "typescript", "javascript", "node", "python", "postgresql", "sql", "rest", "docker", "system design"],
        "nice_to_have": ["nextjs", "fastapi", "redis", "aws", "kubernetes", "graphql", "tailwind", "ci/cd", "microservices"],
        "competencies": [
            "End-to-End Distributed Architecture", "Reactive State Management & Core Web Vitals",
            "Relational & NoSQL Schema Optimization", "Microservices & Asynchronous Messaging", "Cloud Deployment & CI/CD"
        ],
        "action_verbs": ["architected", "spearheaded", "developed", "scaled", "deployed", "delivered", "mentored", "orchestrated"],
        "metrics": ["active users (dau/mau)", "p99 latency reduction (%)", "uptime (99.9x%)", "cloud infrastructure cost savings ($)"],
        "degrees": ["Computer Science", "Software Engineering", "Information Technology"],
    },
    "java developer": {
        "title": "Java Developer",
        "must_have": ["java", "spring boot", "spring", "hibernate", "sql", "postgresql", "rest", "maven", "git"],
        "nice_to_have": ["microservices", "docker", "kafka", "redis", "junit", "aws", "kubernetes", "gradle"],
        "competencies": [
            "Enterprise Java & Spring Boot Microservices", "ORM / Hibernate Query Optimization",
            "Concurrency & JVM Tuning", "RESTful API Development", "Robust Unit Testing with JUnit/Mockito"
        ],
        "action_verbs": ["developed", "engineered", "designed", "optimized", "refactored", "migrated", "implemented"],
        "metrics": ["throughput (rps/tps)", "memory footprint reduction (%)", "transaction processing speed", "uptime"],
        "degrees": ["Computer Science", "Information Technology", "Software Engineering"],
    },
    "python developer": {
        "title": "Python Developer",
        "must_have": ["python", "fastapi", "django", "sql", "postgresql", "rest", "git", "docker"],
        "nice_to_have": ["flask", "redis", "celery", "pytest", "aws", "asyncio", "pandas", "microservices"],
        "competencies": [
            "Asynchronous Python Architecture (FastAPI/AsyncIO)", "ORM Schema Design (SQLAlchemy/Django ORM)",
            "Background Task Queues (Celery/Redis)", "Automated Testing with PyTest", "Containerization"
        ],
        "action_verbs": ["built", "architected", "automated", "optimized", "engineered", "scaled", "integrated"],
        "metrics": ["api response time (ms)", "database query reduction (%)", "records processed per second", "test coverage (%)"],
        "degrees": ["Computer Science", "Information Systems", "Software Engineering"],
    },
    "frontend developer": {
        "title": "Frontend Developer",
        "must_have": ["javascript", "typescript", "react", "html", "css", "state management", "git", "responsive design"],
        "nice_to_have": ["nextjs", "tailwind", "redux", "jest", "playwright", "graphql", "vite", "webpack", "ci/cd"],
        "competencies": [
            "Component-Driven UI Architecture", "Client-Side State Management",
            "Web Performance & Core Web Vitals", "Cross-Browser Compatibility", "Accessibility (a11y)"
        ],
        "action_verbs": ["built", "designed", "optimized", "redesigned", "accelerated", "streamlined", "implemented", "integrated"],
        "metrics": ["page load time (ms/sec)", "lighthouse score", "core web vitals (lcp/cls/fid)", "conversion rate (%)", "active users"],
        "degrees": ["Computer Science", "Web Development", "Human-Computer Interaction", "Information Systems"],
    },
    "backend developer": {
        "title": "Backend Developer",
        "must_have": ["python", "node", "fastapi", "postgresql", "sql", "rest", "api", "git", "docker"],
        "nice_to_have": ["redis", "kafka", "kubernetes", "aws", "microservices", "ci/cd", "graphql", "pytest"],
        "competencies": [
            "RESTful API Architecture", "Database Schema Design & Query Optimization",
            "Distributed Systems", "Caching & Concurrency", "System Reliability & Unit Testing"
        ],
        "action_verbs": ["architected", "engineered", "optimized", "implemented", "reduced", "scaled", "deployed", "refactored"],
        "metrics": ["latency reduction (ms)", "throughput (rps/qps)", "uptime / sla (%)", "database query time (%)", "data scale (users/events)"],
        "degrees": ["Computer Science", "Software Engineering", "Information Technology", "Computer Engineering"],
    },
    "data analyst": {
        "title": "Data Analyst",
        "must_have": ["sql", "excel", "tableau", "power bi", "data analysis", "python", "data visualization", "reporting"],
        "nice_to_have": ["r", "pandas", "numpy", "statistics", "dashboards", "etl", "snowflake", "google analytics"],
        "competencies": [
            "SQL Aggregation & Complex Window Functions", "Executive BI Dashboarding (Tableau/PowerBI)",
            "Exploratory Data Analysis & Trend Discovery", "Business Metric Tracking & KPI Reporting", "Data Cleansing & Validation"
        ],
        "action_verbs": ["analyzed", "visualized", "synthesized", "identified", "reported", "streamlined", "modeled", "presented"],
        "metrics": ["reporting cycle reduction (%)", "revenue impact discovered ($)", "executive adoption rate", "data accuracy (%)"],
        "degrees": ["Statistics", "Data Analytics", "Economics", "Business Analytics", "Computer Science"],
    },
    "data scientist": {
        "title": "Data Scientist",
        "must_have": ["python", "sql", "pandas", "numpy", "scikit-learn", "machine learning", "statistics", "data analysis"],
        "nice_to_have": ["r", "tensorflow", "pytorch", "tableau", "power bi", "feature engineering", "a/b testing", "xgboost"],
        "competencies": [
            "Statistical Modeling & Hypothesis Testing", "Predictive Machine Learning Algorithms",
            "Exploratory Data Analysis", "Feature Selection & Engineering", "Executive Visualization"
        ],
        "action_verbs": ["analyzed", "modeled", "predicted", "discovered", "evaluated", "trained", "formulated", "improved"],
        "metrics": ["model accuracy / auc / f1 score", "revenue lift ($)", "churn reduction (%)", "prediction latency", "sample size / statistical confidence"],
        "degrees": ["Data Science", "Statistics", "Computer Science", "Mathematics", "Physics", "Economics"],
    },
    "machine learning engineer": {
        "title": "Machine Learning Engineer",
        "must_have": ["python", "pytorch", "tensorflow", "machine learning", "deep learning", "nlp", "scikit-learn", "git", "docker"],
        "nice_to_have": ["transformers", "huggingface", "cuda", "mlops", "vector database", "onnx", "fastapi", "mlflow"],
        "competencies": [
            "Deep Learning & Neural Network Architectures", "Model Training, Validation & Hyperparameter Tuning",
            "MLOps Pipelines & Model Registry", "High-Throughput Model Serving", "Feature Store Integration"
        ],
        "action_verbs": ["trained", "deployed", "optimized", "benchmarked", "fine-tuned", "architected", "scaled", "quantized"],
        "metrics": ["inference latency (ms)", "memory footprint reduction (%)", "model accuracy / f1 score", "throughput (qps)"],
        "degrees": ["Computer Science", "Artificial Intelligence", "Electrical Engineering", "Applied Math"],
    },
    "ai engineer": {
        "title": "AI Engineer",
        "must_have": ["python", "llm", "rag", "langchain", "langgraph", "embeddings", "vector database", "git", "fastapi"],
        "nice_to_have": ["pytorch", "huggingface", "openai", "gemini", "fine-tuning", "prompt engineering", "docker", "redis"],
        "competencies": [
            "Large Language Model (LLM) Application Architecture", "Retrieval-Augmented Generation (RAG) Pipelines",
            "Vector Search & Semantic Indexing", "Prompt Engineering & Guardrails", "Multi-Agent System Orchestration"
        ],
        "action_verbs": ["architected", "integrated", "fine-tuned", "prompted", "deployed", "scaled", "automated", "benchmarked"],
        "metrics": ["retrieval precision/recall (%)", "token cost reduction ($/%)", "response latency (ms)", "eval score"],
        "degrees": ["Computer Science", "Artificial Intelligence", "Computational Linguistics", "Engineering"],
    },
    "devops engineer": {
        "title": "DevOps Engineer",
        "must_have": ["docker", "kubernetes", "aws", "ci/cd", "terraform", "linux", "git", "bash"],
        "nice_to_have": ["ansible", "helm", "gcp", "azure", "prometheus", "grafana", "argo", "github actions"],
        "competencies": [
            "Infrastructure as Code (IaC) with Terraform", "Container Orchestration (Kubernetes/Helm)",
            "Automated CI/CD Delivery Pipelines", "Cloud Infrastructure & High Availability", "Observability & Alerting"
        ],
        "action_verbs": ["automated", "provisioned", "migrated", "reduced", "scaled", "configured", "deployed", "hardened"],
        "metrics": ["deployment frequency increase", "lead time reduction (%)", "mttr (mean time to recovery)", "uptime (99.9x%)", "cloud cost savings ($)"],
        "degrees": ["Computer Science", "Computer Engineering", "Network Engineering", "Information Systems"],
    },
    "cloud engineer": {
        "title": "Cloud Engineer",
        "must_have": ["aws", "cloud", "terraform", "docker", "linux", "networking", "iam", "ci/cd", "git"],
        "nice_to_have": ["azure", "gcp", "kubernetes", "lambda", "serverless", "cloudformation", "ansible", "python"],
        "competencies": [
            "Multi-Cloud Architecture & Migration", "Cloud Security & IAM Governance",
            "VPC / Subnet / Hybrid Networking", "Serverless & Event-Driven Architecture", "Cloud Cost Optimization"
        ],
        "action_verbs": ["architected", "migrated", "provisioned", "secured", "optimized", "monitored", "deployed"],
        "metrics": ["cloud spend reduction ($/%)", "security compliance score (%)", "failover time (seconds)", "system availability"],
        "degrees": ["Computer Science", "Cloud Computing", "Information Technology", "Electrical Engineering"],
    },
    "cybersecurity engineer": {
        "title": "Cybersecurity Engineer",
        "must_have": ["security", "vulnerability assessment", "incident response", "network security", "linux", "firewalls", "siem"],
        "nice_to_have": ["penetration testing", "cissp", "ceh", "python", "soc", "compliance", "iso 27001", "zero trust"],
        "competencies": [
            "Threat Detection & SIEM Monitoring", "Vulnerability Scanning & Remediation",
            "Incident Response & Digital Forensics", "Security Compliance & Audit Protocols", "Zero Trust Network Defense"
        ],
        "action_verbs": ["hardened", "detected", "mitigated", "audited", "remediated", "secured", "investigated", "implemented"],
        "metrics": ["vulnerabilities resolved", "mean time to detect/contain (mttd/mttc)", "audit compliance pass rate (%)", "security incidents prevented"],
        "degrees": ["Cybersecurity", "Computer Science", "Information Assurance", "Computer Engineering"],
    },
    "database administrator": {
        "title": "Database Administrator",
        "must_have": ["sql", "postgresql", "mysql", "database", "backup & recovery", "indexing", "query optimization", "linux"],
        "nice_to_have": ["oracle", "mongodb", "redis", "sharding", "replication", "high availability", "python", "bash"],
        "competencies": [
            "Database Schema Design & Query Optimization", "High Availability & Multi-Node Replication",
            "Automated Backup & Disaster Recovery", "Storage Capacity Planning & Partitioning", "Database Security & Access Control"
        ],
        "action_verbs": ["tuned", "optimized", "migrated", "recovered", "configured", "partitioned", "backed up", "monitored"],
        "metrics": ["query execution speedup (x)", "database downtime reduction (%)", "rpo/rto targets met", "i/o throughput"],
        "degrees": ["Computer Science", "Database Administration", "Information Systems"],
    },
    "qa engineer": {
        "title": "QA Engineer",
        "must_have": ["automation", "testing", "python", "javascript", "selenium", "cypress", "playwright", "api testing", "git"],
        "nice_to_have": ["pytest", "jest", "ci/cd", "postman", "load testing", "jmeter", "test automation framework", "docker"],
        "competencies": [
            "End-to-End Test Automation", "API & Regression Testing",
            "CI/CD Test Integration", "Defect Tracking & Root Cause Analysis", "Performance / Load Testing"
        ],
        "action_verbs": ["automated", "tested", "designed", "uncovered", "validated", "reduced", "executed", "prevented"],
        "metrics": ["test coverage percentage (%)", "regression test execution time reduction (%)", "critical bug leakage reduction", "qa cycle time"],
        "degrees": ["Computer Science", "Software Engineering", "Information Systems"],
    },
    "ui/ux designer": {
        "title": "UI/UX Designer",
        "must_have": ["figma", "wireframing", "prototyping", "user research", "ui design", "ux design", "design systems", "usability testing"],
        "nice_to_have": ["adobe xd", "sketch", "user flows", "information architecture", "html", "css", "interaction design", "accessibility"],
        "competencies": [
            "High-Fidelity Prototyping & Wireframing in Figma", "Design System Creation & Component Tokens",
            "User Research & Usability Testing", "Information Architecture & User Journeys", "Responsive UI Design & Design Handoff"
        ],
        "action_verbs": ["designed", "prototyped", "researched", "tested", "created", "redesigned", "crafted", "facilitated"],
        "metrics": ["usability test success rate (%)", "task completion time reduction", "user satisfaction / sus score", "design-to-dev velocity"],
        "degrees": ["Human-Computer Interaction", "Graphic Design", "Digital Media", "Computer Science"],
    },
}

_SENIORITY_RULES = [
    (re.compile(r"\b(intern|internship|trainee|fresher|graduate)\b", re.I), "intern", 0.0),
    (re.compile(r"\b(junior|entry|associate|jr|level\s*1|l1)\b", re.I), "junior", 1.0),
    (re.compile(r"\b(lead|team\s*lead|tech\s*lead)\b", re.I), "lead", 6.0),
    (re.compile(r"\b(principal|staff|architect|fellow)\b", re.I), "staff", 8.0),
    (re.compile(r"\b(manager|director|vp|head\s*of)\b", re.I), "executive", 7.0),
    (re.compile(r"\b(senior|sr|level\s*3|l3|expert)\b", re.I), "senior", 5.0),
]


def infer_role_benchmarks(job_role: Optional[str] = None) -> RoleBenchmark:
    """
    Dynamically infers industry-standard core competencies, tech stacks, action verbs,
    and role benchmarks from a target Job Role Title.
    """
    clean_title = (job_role or "Software Engineer").strip()
    clean_lower = clean_title.lower()

    # 1. Detect Seniority Level & Experience Expectation
    seniority = "mid"
    exp_years = 3.0  # default mid-level expectation
    for pattern, level, yrs in _SENIORITY_RULES:
        if pattern.search(clean_lower):
            seniority = level
            exp_years = yrs
            break

    # 2. Match Archetype (exact or key phrase)
    matched_archetype_key = None
    for key, arch in _ROLE_ARCHETYPES.items():
        if key == clean_lower:
            matched_archetype_key = key
            break

    if not matched_archetype_key:
        for key, arch in _ROLE_ARCHETYPES.items():
            if key in clean_lower or clean_lower in key:
                matched_archetype_key = key
                break

    # Additional heuristics for title matching
    if not matched_archetype_key:
        if any(term in clean_lower for term in ["ui", "ux", "designer", "figma"]):
            matched_archetype_key = "ui/ux designer"
        elif any(term in clean_lower for term in ["front", "react", "vue", "web"]):
            matched_archetype_key = "frontend developer"
        elif any(term in clean_lower for term in ["java", "spring"]):
            matched_archetype_key = "java developer"
        elif any(term in clean_lower for term in ["python", "django", "fastapi"]):
            matched_archetype_key = "python developer"
        elif any(term in clean_lower for term in ["full", "stack"]):
            matched_archetype_key = "senior full stack engineer"
        elif any(term in clean_lower for term in ["dba", "database", "sql"]):
            matched_archetype_key = "database administrator"
        elif any(term in clean_lower for term in ["back", "api"]):
            matched_archetype_key = "backend developer"
        elif any(term in clean_lower for term in ["cloud", "azure", "gcp"]):
            matched_archetype_key = "cloud engineer"
        elif any(term in clean_lower for term in ["devops", "sre", "platform", "infrastructure"]):
            matched_archetype_key = "devops engineer"
        elif any(term in clean_lower for term in ["ai", "prompt", "llm"]):
            matched_archetype_key = "ai engineer"
        elif any(term in clean_lower for term in ["machine learning", "deep learning", "nlp"]):
            matched_archetype_key = "machine learning engineer"
        elif any(term in clean_lower for term in ["data sci", "statistician"]):
            matched_archetype_key = "data scientist"
        elif any(term in clean_lower for term in ["data analyst", "business analyst", "tableau", "bi"]):
            matched_archetype_key = "data analyst"
        elif any(term in clean_lower for term in ["qa", "quality", "test", "sdet", "automation"]):
            matched_archetype_key = "qa engineer"
        elif any(term in clean_lower for term in ["security", "cyber", "infosec", "soc"]):
            matched_archetype_key = "cybersecurity engineer"
        else:
            matched_archetype_key = "software engineer"

    arch = _ROLE_ARCHETYPES[matched_archetype_key]

    must_have = list(arch["must_have"])
    nice_to_have = list(arch["nice_to_have"])

    if seniority in ("senior", "lead", "staff"):
        if nice_to_have:
            must_have.extend(nice_to_have[:2])
            nice_to_have = nice_to_have[2:]
        if "architecture" not in must_have and "system design" not in must_have:
            must_have.append("system design")
    elif seniority in ("intern", "junior"):
        must_have = [s for s in must_have if s not in ["kubernetes", "system design", "docker"]]
        if "docker" not in nice_to_have:
            nice_to_have.append("docker")

    synthetic_jd = (
        f"Role: {clean_title} ({seniority.capitalize()} Level).\n"
        f"Required experience: Minimum {exp_years:.0f} years of relevant industry experience.\n"
        f"Core Competencies: {', '.join(arch['competencies'])}.\n"
        f"Required Must-Have Skills: {', '.join(must_have)}.\n"
        f"Preferred Qualifications: {', '.join(nice_to_have)}.\n"
        f"Expected Action & Impact: Ability to {', '.join(arch['action_verbs'][:5])} high-impact features and systems "
        f"measuring {', '.join(arch['metrics'][:3])}."
    )

    return RoleBenchmark(
        role_title=clean_title,
        seniority_level=seniority,
        min_years_experience=exp_years,
        must_have_skills=must_have,
        nice_to_have_skills=nice_to_have,
        core_competencies=arch["competencies"],
        expected_action_verbs=arch["action_verbs"],
        expected_metrics=arch["metrics"],
        expected_degree_fields=arch["degrees"],
        synthetic_jd_text=synthetic_jd,
    )
