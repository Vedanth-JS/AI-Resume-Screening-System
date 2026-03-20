import re
from typing import List, Dict, Any

# Load spaCy model lazily
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"Warning: Could not load spaCy model: {e}")
            _nlp = None
    return _nlp

SKILLS_ONTOLOGY = [
    "Python", "Java", "C++", "JavaScript", "React", "Node.js", "FastAPI", "SQL", "PostgreSQL",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Machine Learning", "NLP", "Scikit-learn",
    "TensorFlow", "PyTorch", "Pandas", "NumPy", "Git", "CI/CD", "Redis", "Celery", "NoSQL",
    "MongoDB", "HTML", "CSS", "Tailwind", "REST API", "GraphQL", "TypeScript", "Spark", "Kafka"
]

class FeatureExtractor:
    def __init__(self, text: str):
        self.text = text
        nlp = get_nlp()
        self.doc = nlp(text) if nlp else None

    def extract_skills(self) -> List[str]:
        found_skills = []
        for skill in SKILLS_ONTOLOGY:
            if re.search(rf"\b{re.escape(skill)}\b", self.text, re.IGNORECASE):
                found_skills.append(skill)
        return list(set(found_skills))

    def extract_experience(self) -> int:
        # Look for patterns like "5 years", "10+ years", "3 yrs"
        patterns = [
            r"(\d+)\+?\s*years?",
            r"(\d+)\+?\s*yrs?"
        ]
        max_exp = 0
        for pattern in patterns:
            matches = re.finditer(pattern, self.text, re.IGNORECASE)
            for match in matches:
                exp = int(match.group(1))
                if exp > max_exp:
                    max_exp = exp
        return max_exp

    def extract_education(self) -> str:
        degrees = ["B.Tech", "B.E", "B.S", "M.Tech", "M.E", "M.S", "PhD", "Bachelor", "Master"]
        for degree in degrees:
            if re.search(rf"\b{re.escape(degree)}\b", self.text, re.IGNORECASE):
                return degree
        return "Not Specified"

    def extract_entities(self) -> Dict[str, List[str]]:
        entities = {"PERSON": [], "ORG": [], "GPE": []}
        
        # Simple Regex Fallback for Person Names (Upper case words at start of text)
        # Usually names are in the first 100 characters
        header = self.text[:100]
        name_matches = re.findall(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", header, re.MULTILINE)
        if name_matches:
            entities["PERSON"] = [name_matches[0]]
        else:
            # Try to find common email prefix as a fallback name
            email_match = re.search(r'([a-zA-Z0-9._%+-]+)@[a-zA-Z0-9.-]+\.[A-Z|a-z]{2,}', self.text)
            if email_match:
                entities["PERSON"] = [email_match.group(1).capitalize()]
                
        # Optional: Add simple regex for common orgs or locations if needed
        return entities
