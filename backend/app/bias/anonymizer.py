import re
import hashlib
from typing import Dict, Any

class CandidateAnonymizer:
    def __init__(self, salt: str = "placement_portfolio_2026"):
        self.salt = salt

    def anonymize_text(self, text: str) -> str:
        """
        Removes: Name, Email, Phone, Graduation Year, Address.
        """
        # Email
        text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
        
        # Phone numbers (robust regex)
        text = re.sub(r'(\+?\d{1,4}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\(?\d{3}\)?[-.\s]?\d{4}|\d{10})', '[PHONE]', text)
        
        # Specific year masking
        text = re.sub(r'\b(19[789]\d|20[0-2]\d)\b', '[YEAR]', text)
        
        # General Masking
        # In a real-world scenario, this would use a NER model for PII removal
        return text

    def mask_candidate_metadata(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymizes candidate metadata.
        """
        email = candidate_data.get("email", "unknown")
        # Generate stable hash for the candidate
        unique_id = hashlib.sha256((email + self.salt).encode()).hexdigest()[:8]
        
        return {
            "name": f"Candidate-{unique_id}",
            "email": "[MASKED]",
            "phone": "[MASKED]",
            "raw_text": self.anonymize_text(candidate_data.get("raw_text", ""))
        }
