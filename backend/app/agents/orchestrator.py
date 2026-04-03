import asyncio
import hashlib
import json
import redis
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from .parser import ResumeParserAgent
from .matcher import SkillMatcherAgent
from .bias import BiasDetectorAgent
from .scorer import ScoringAgent
from ..core.config import settings
from ..core.logger import log

class ScreeningOrchestrator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = ResumeParserAgent()
        self.matcher = SkillMatcherAgent()
        self.bias = BiasDetectorAgent()
        self.scorer = ScoringAgent()
        self._redis = None

    @property
    def redis_client(self):
        if self._redis is None:
            try:
                self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
            except Exception as e:
                log.warning("redis_connection_error", error=str(e))
        return self._redis

    async def run_pipeline(self, pdf_bytes: bytes, job_id: int, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the full multi-agent screening pipeline.
        1. Check Cache
        2. Agent 1 (Sequential)
        3. Agent 2 & 3 (Parallel)
        4. Agent 4 (Sequential)
        """
        # 1. SHA256 Caching logic
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        cache_key = f"parsed_resume:{file_hash}"
        
        parsed_data = None
        if self.redis_client:
            cached = self.redis_client.get(cache_key)
            if cached:
                log.info("cache_hit", key=cache_key)
                parsed_data = json.loads(cached)

        # 2. Agent 1 — ResumeParserAgent (Sequential)
        if not parsed_data:
            from ..core.parser import ResumeParser
            raw_text = ResumeParser.extract_text(pdf_bytes, "resume.pdf") 
            parsed_data = await self.parser.run({"raw_text": raw_text})
            
            # Cache for 7 days
            if self.redis_client and "error" not in parsed_data:
                self.redis_client.setex(cache_key, 60*60*24*7, json.dumps(parsed_data))

        raw_text = parsed_data.get("raw_text", "") # Ensure raw_text is available for bias detection

        # 3. Agent 2 (Matcher) & Agent 3 (Bias) — Parallel
        matcher_task = self.matcher.run({"resume": parsed_data, "job": job_data})
        bias_task = self.bias.run({"resume_text": raw_text, "parsed_resume": parsed_data})
        
        matcher_results, bias_results = await asyncio.gather(matcher_task, bias_task)

        # 4. Fetch RAG Context (Successive past hires)
        # Placeholder for RAG service call
        past_hires = await self._get_rag_context(job_id)

        # 5. Agent 4 — ScoringAgent (Sequential)
        final_results = await self.scorer.run({
            "parser_data": parsed_data,
            "matcher_data": matcher_results,
            "bias_data": bias_results,
            "job_data": job_data,
            "past_hires": past_hires
        })

        # 6. Store intermediate and final outputs
        # This would typically save to `screening_results` table
        # We return the full bundle for the caller to handle DB commit if needed
        return {
            "parser": parsed_data,
            "matcher": matcher_results,
            "bias": bias_results,
            "score": final_results,
            "metadata": {
                "file_hash": file_hash,
                "job_id": job_id
            }
        }

    async def _get_rag_context(self, job_id: int) -> List[str]:
        """Fetch top 3 similar past successful hires from pgvector."""
        # This will be implemented in the RAG search service
        return ["Senior Developer with 8 years of Flask experience", "Fullstack dev with React/Postgres focus"]
