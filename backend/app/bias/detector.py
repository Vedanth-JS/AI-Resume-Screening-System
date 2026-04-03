import re
from typing import Dict, Any, List

class BiasDetector:
    def __init__(self):
        # Generic accreditation-based tier mapping instead of specific college names
        self.ACCREDITATION_TIERS = {
            "Tier-1": ["national institute", "centrally funded", "accredited a++", "nba accredited"],
            "Tier-2": ["state university", "accredited a", "government college"],
            "Tier-3": ["private", "affiliated", "autonomous"]
        }

    def detect_age_bias(self, text: str) -> List[str]:
        flags = []
        # Graduation year inference (e.g., 1990 graduation implies older candidate)
        match = re.search(r'\b(19[789]\d|200\d)\b', text)
        if match:
            flags.append(f"Graduation year {match.group(0)} detected (potential age bias)")
        
        # Specific phrasing
        phrases = ["digital native", "young and energetic", "recent graduate", "energetic youth"]
        for p in phrases:
            if p in text.lower():
                flags.append(f"Phrasing '{p}' detected (potential age bias)")
        return flags

    def detect_gender_bias(self, text: str) -> List[str]:
        flags = []
        gendered_pronouns = ["he", "him", "his", "she", "her", "hers"]
        for p in gendered_pronouns:
            if re.search(rf'\b{p}\b', text.lower()):
                flags.append(f"Gendered pronoun '{p}' detected")
        
        gendered_titles = ["chairman", "salesman", "foreman", "waitress", "stewardess"]
        for t in gendered_titles:
            if t in text.lower():
                flags.append(f"Gendered job title '{t}' detected")
        return flags

    def analyze_institution_prestige(self, text: str) -> Dict[str, Any]:
        detected_tiers = []
        for tier, keywords in self.ACCREDITATION_TIERS.items():
            for kw in keywords:
                if kw in text.lower():
                    detected_tiers.append(tier)
                    break
        
        return {
            "detected_tiers": list(set(detected_tiers)),
            "is_prestigious": "Tier-1" in detected_tiers
        }

    def detect_career_gaps(self, text: str) -> List[str]:
        # Simple heuristic for career gaps (this would normally be more complex parsed logic)
        # For now, we look for "Break in career" or "Gap year"
        flags = []
        if "gap year" in text.lower() or "career break" in text.lower():
            flags.append("Intentional career gap detected")
        return flags

    def run_bias_audit(self, resume_text: str, candidate_name: str = "") -> Dict[str, Any]:
        """Runs the full fairness audit."""
        age_flags = self.detect_age_bias(resume_text)
        gender_flags = self.detect_gender_bias(resume_text)
        inst_analysis = self.analyze_institution_prestige(resume_text)
        gap_flags = self.detect_career_gaps(resume_text)
        
        # Name-Origin Bias (Proxy detection - log only)
        # In production, this would use a more sophisticated ethnic proxy model
        name_bias_flag = len(candidate_name.split()) > 0 # Simple flag if name is provided
        
        risk_level = "LOW"
        if len(age_flags) + len(gender_flags) > 3:
            risk_level = "HIGH"
        elif len(age_flags) + len(gender_flags) > 0:
            risk_level = "MED"

        return {
            "risk_level": risk_level,
            "flags": age_flags + gender_flags + gap_flags,
            "prestige_analysis": inst_analysis,
            "name_bias_logged": name_bias_flag,
            "recommendations": [
                "Remove graduation years to mitigate age bias.",
                "Use gender-neutral titles (e.g., 'Chair', 'Sales Associate').",
                "Review career gaps manually for context."
            ]
        }
