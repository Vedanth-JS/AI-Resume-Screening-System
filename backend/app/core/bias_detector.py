import re
from typing import Dict, Any, List

class BiasDetector:
    GENDERED_KEYWORDS = {
        "masculine": ["competitive", "leader", "dominant", "objective", "ambitious", "decisive"],
        "feminine": ["supportive", "collaborative", "sensitive", "interpersonal", "trusting", "compassionate"]
    }
    
    COLLEGE_TIERS = {
        "tier_1": ["IIT", "MIT", "Stanford", "Harvard", "Oxford", "Cambridge", "BITS", "IIM"],
        "tier_2": ["State University", "SJTU", "NTU", "Local Institute"]
    }

    @staticmethod
    def detect_bias(text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        
        # Gendered Language Detection
        detected_masculine = [w for w in BiasDetector.GENDERED_KEYWORDS["masculine"] if w in text_lower]
        detected_feminine = [w for w in BiasDetector.GENDERED_KEYWORDS["feminine"] if w in text_lower]
        
        # College Prestige Bias
        detected_tier_1 = [c for c in BiasDetector.COLLEGE_TIERS["tier_1"] if c.lower() in text_lower]
        
        # Sentiment/Tone check for JD (Simple heuristic)
        bias_score = len(detected_masculine) - len(detected_feminine)
        
        status = "neutral"
        if bias_score > 2: status = "masculine_skewed"
        elif bias_score < -2: status = "feminine_skewed"
        
        return {
            "gender_bias": {
                "masculine_terms": detected_masculine,
                "feminine_terms": detected_feminine,
                "status": status
            },
            "prestige_bias": {
                "tier_1_detected": detected_tier_1,
                "flag": len(detected_tier_1) > 0
            },
            "recommendation": "Use gender-neutral terms like 'expert', 'enthusiast', or 'professional' to improve inclusivity."
        }

    @staticmethod
    def identify_demographics(text: str) -> Dict[str, Any]:
        # Simple regex for gendered pronouns/titles
        gender_markers = {
            "male": ["he", "him", "his", "mr.", "man", "boy"],
            "female": ["she", "her", "hers", "ms.", "mrs.", "woman", "girl"]
        }
        
        found_male = [m for m in gender_markers["male"] if re.search(rf'\b{m}\b', text.lower())]
        found_female = [f for f in gender_markers["female"] if re.search(rf'\b{f}\b', text.lower())]
        
        return {
            "male_markers": found_male,
            "female_markers": found_female
        }
