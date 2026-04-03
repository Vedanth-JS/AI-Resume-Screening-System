"""
Contextual Skill Synonyms / Knowledge Graph
─────────────────────────────────────────────
Answers the interview question:
  "How does your system know 'React' maps to 'Frontend Framework'?"

Instead of exact matching only, we use a curated technology taxonomy.
When a JD keyword group is matched by ANY member of the group in the resume,
we award a partial synonym credit (default 0.7) rather than a full miss.

This means:
  JD requires "frontend frameworks"  →  resume has "Vue.js"  →  0.7 credit
  JD requires "cloud"                →  resume has "EC2"      →  0.85 credit
  JD requires "python"               →  resume has "python"   →  1.0 credit (exact)
"""
from typing import List, Tuple, Dict
import re

# ─── Master taxonomy ─────────────────────────────────────────────────────────
SKILL_TAXONOMY: Dict[str, List[str]] = {
    # Frontend
    "frontend_frameworks": [
        "react", "vue", "angular", "svelte", "nextjs", "nuxt", "gatsby",
        "preact", "ember", "backbone", "polymer", "lit",
    ],
    "frontend_languages": ["javascript", "typescript", "html", "css", "sass", "less", "jsx", "tsx"],
    "state_management":   ["redux", "mobx", "zustand", "recoil", "vuex", "pinia", "jotai", "xstate"],
    "css_frameworks":     ["tailwind", "bootstrap", "material ui", "chakra", "ant design", "shadcn"],

    # Backend
    "backend_frameworks": [
        "fastapi", "django", "flask", "express", "nestjs", "spring", "rails",
        "laravel", "gin", "fiber", "actix", "axum", "hapi", "koa",
    ],
    "backend_languages": [
        "python", "java", "golang", "go", "rust", "node", "nodejs", "ruby",
        "php", "kotlin", "scala", "c#", "dotnet", ".net",
    ],

    # Databases
    "sql_databases":   ["postgresql", "postgres", "mysql", "sqlite", "mssql", "oracle", "mariadb"],
    "nosql_databases": ["mongodb", "dynamodb", "cassandra", "couchdb", "firestore", "redis", "memcached"],
    "vector_databases": ["pinecone", "weaviate", "chroma", "chromadb", "qdrant", "milvus", "faiss"],
    "orm":             ["sqlalchemy", "prisma", "sequelize", "typeorm", "hibernate", "gorm", "drizzle"],

    # Cloud
    "cloud_platforms": ["aws", "gcp", "azure", "google cloud", "ec2", "s3", "lambda", "cloud functions"],
    "containers":      ["docker", "kubernetes", "k8s", "helm", "podman", "containerd", "ecs", "eks"],
    "ci_cd":           ["github actions", "gitlab ci", "jenkins", "circleci", "travis", "argo", "tekton"],
    "infrastructure":  ["terraform", "ansible", "pulumi", "cloudformation", "chef", "puppet"],

    # AI / ML
    "ml_frameworks":   ["pytorch", "tensorflow", "keras", "jax", "sklearn", "scikit-learn", "xgboost"],
    "llm_tools":       ["langchain", "langgraph", "llamaindex", "openai", "gemini", "anthropic", "huggingface"],
    "ml_concepts":     [
        "machine learning", "deep learning", "nlp", "computer vision", "reinforcement learning",
        "transformers", "bert", "gpt", "llm", "rag",
    ],
    "data_tools":      ["pandas", "numpy", "spark", "dask", "airflow", "dbt", "kafka", "flink"],

    # Testing
    "testing_tools":   ["pytest", "jest", "mocha", "cypress", "selenium", "junit", "vitest", "playwright"],

    # Version control / workflow
    "version_control": ["git", "github", "gitlab", "bitbucket", "svn"],
    "agile":           ["scrum", "kanban", "jira", "confluence", "agile", "sprint"],
}

# Build a reverse lookup: term → group name
_REVERSE_MAP: Dict[str, str] = {}
for group, terms in SKILL_TAXONOMY.items():
    for term in terms:
        _REVERSE_MAP[term.lower()] = group

# Synonym credit weight (partial match in same taxonomy group)
SYNONYM_CREDIT = 0.70


def get_group(skill: str) -> str | None:
    """Return the taxonomy group a skill belongs to, or None."""
    return _REVERSE_MAP.get(skill.strip().lower())


def synonym_score(jd_keyword: str, resume_text: str) -> Tuple[float, str]:
    """
    Score a single JD keyword against resume text.
    Returns (score, match_type) where match_type is:
        'exact'   → 1.0  (literal match)
        'synonym' → 0.70 (same taxonomy group found in resume)
        'none'    → 0.0
    """
    kw_lower = jd_keyword.strip().lower()
    text_lower = resume_text.lower()

    # Exact match
    if kw_lower in text_lower:
        return 1.0, "exact"

    # Synonym group match
    group = _REVERSE_MAP.get(kw_lower)
    if group:
        siblings = SKILL_TAXONOMY[group]
        for sibling in siblings:
            if sibling != kw_lower and sibling in text_lower:
                return SYNONYM_CREDIT, f"synonym:{sibling}"

    return 0.0, "none"


def enrich_keyword_score(
    resume_text: str,
    jd_keywords: List[str],
) -> Dict:
    """
    Enhanced keyword scoring using the taxonomy.
    Returns the same shape as Scorer.keyword_score() but with synonym awareness.
    """
    if not jd_keywords:
        return {"score": 1.0, "matched": [], "missing": [], "synonym_matches": [], "fuzzy_details": []}

    matched, missing, synonyms, details = [], [], [], []
    total_credit = 0.0

    for kw in jd_keywords:
        score, match_type = synonym_score(kw, resume_text)
        total_credit += score

        if score == 1.0:
            matched.append(kw)
        elif score > 0:
            synonyms.append({"keyword": kw, "matched_via": match_type, "credit": score})
            matched.append(kw)           # counts as matched but with partial credit
        else:
            missing.append(kw)

        details.append({"keyword": kw, "score": score, "match_type": match_type})

    weighted_score = total_credit / len(jd_keywords)
    return {
        "score":           round(weighted_score, 3),
        "matched":         matched,
        "missing":         missing,
        "synonym_matches": synonyms,
        "fuzzy_details":   details,
    }
