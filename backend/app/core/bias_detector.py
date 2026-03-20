import re
from typing import List, Tuple, Dict

GENDER_NEUTRAL_PAIRS = {
    "rockstar": "expert",
    "ninja": "skilled professional",
    "aggressive": "driven",
    "guru": "specialist",
    "dominant": "leading",
    "man": "person",
    "he": "they",
    "she": "they"
}

class BiasDetector:
    @staticmethod
    def detect_bias(jd_text: str) -> List[Dict[str, str]]:
        biases = []
        for word, neutral in GENDER_NEUTRAL_PAIRS.items():
            if re.search(rf"\b{re.escape(word)}\b", jd_text, re.IGNORECASE):
                biases.append({
                    "word": word,
                    "suggestion": neutral,
                    "reason": "This term may carry gendered connotations."
                })
        return biases

    @staticmethod
    def anonymize_text(text: str, entities: Dict[str, List[str]]) -> str:
        anonymized = text
        for person in entities.get("PERSON", []):
            anonymized = anonymized.replace(person, "[NAME]")
        # Could also anonymize email/phone using regex
        anonymized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', anonymized)
        anonymized = re.sub(r'\b\d{10,}\b', '[PHONE]', anonymized)
        return anonymized

    @staticmethod
    def flag_requirements(jd_text: str) -> List[str]:
        flags = []
        if "prestigious university" in jd_text.lower():
            flags.append("May introduce socio-economic bias.")
        if "native speaker" in jd_text.lower():
            flags.append("May introduce origin-based bias.")
        return flags
