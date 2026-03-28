from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Any

# Load lightweight model for performance
# Using 'all-MiniLM-L6-v2' as it is fast and accurate enough for ATS tasks
model = SentenceTransformer('all-MiniLM-L6-v2')

class Scorer:
    @staticmethod
    def get_similarity(text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        embeddings1 = model.encode(text1, convert_to_tensor=True)
        embeddings2 = model.encode(text2, convert_to_tensor=True)
        cosine_scores = util.cos_sim(embeddings1, embeddings2)
        return float(cosine_scores[0][0])
