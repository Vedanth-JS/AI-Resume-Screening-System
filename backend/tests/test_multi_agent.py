import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from app.agents.parser import ResumeParserAgent
from app.agents.matcher import SkillMatcherAgent
from app.agents.bias import BiasDetectorAgent
from app.agents.scorer import ScoringAgent
from app.agents.orchestrator import ScreeningOrchestrator

@pytest.mark.asyncio
async def test_resume_parser_agent_success():
    agent = ResumeParserAgent()
    mock_raw_text = "John Doe\nEmail: john@example.com\nSkills: Python, FastAPI"
    
    with patch("app.agents.parser._call_model", return_value='{"name": "John Doe", "email": "john@example.com", "skills": ["Python", "FastAPI"]}'):
        result = await agent.run({"raw_text": mock_raw_text})
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"
        assert "Python" in result["skills"]
        assert result["extraction_method"] == "llm"

@pytest.mark.asyncio
async def test_resume_parser_fallback():
    agent = ResumeParserAgent()
    mock_raw_text = "Jane Smith\nContact: jane.smith@test.com\nPhone: +1 555 0102"
    
    with patch("app.agents.parser._call_model", return_value="INVALID JSON"):
        result = await agent.run({"raw_text": mock_raw_text})
        assert result["email"] == "jane.smith@test.com"
        assert result["phone"] == "+1 555 0102"
        assert result["extraction_method"] == "hybrid_fallback"

@pytest.mark.asyncio
async def test_skill_matcher_agent():
    agent = SkillMatcherAgent()
    input_data = {
        "resume": {"skills": ["Python", "AWS"]},
        "job": {"required_skills": ["Python", "FastAPI"]}
    }
    
    # Mock embedding and LLM analysis
    with patch("app.agents.matcher.get_embedding", side_effect=[[0.1]*768, [0.2]*768]), \
         patch("app.agents.matcher._call_model", return_value='{"matched_skills": ["Python"], "missing_skills": ["FastAPI"], "skill_analysis_score": 75}'):
        result = await agent.run(input_data)
        assert "skill_score" in result
        assert result["matched_skills"] == ["Python"]
        assert result["skill_analysis_score"] == 75

@pytest.mark.asyncio
async def test_screening_orchestrator():
    # Mock DB session and Redis
    db_mock = AsyncMock()
    
    with patch("app.agents.orchestrator.ScreeningOrchestrator.redis_client", new_callable=PropertyMock) as mock_redis, \
         patch("app.agents.orchestrator.ResumeParserAgent.run", new_callable=AsyncMock) as mock_parser, \
         patch("app.agents.orchestrator.SkillMatcherAgent.run", new_callable=AsyncMock) as mock_matcher, \
         patch("app.agents.orchestrator.BiasDetectorAgent.run", new_callable=AsyncMock) as mock_bias, \
         patch("app.agents.orchestrator.ScoringAgent.run", new_callable=AsyncMock) as mock_scorer, \
         patch("app.core.parser.ResumeParser.extract_text", return_value="Raw PDF Content"):
        
        mock_redis.return_value = None
        
        mock_parser.return_value = {"name": "Test User", "raw_text": "Raw PDF Content"}
        mock_matcher.return_value = {"skill_score": 85}
        mock_bias.return_value = {"bias_risk_level": "LOW"}
        mock_scorer.return_value = {"overall_score": 90, "hire_recommendation": "YES"}
        
        orchestrator = ScreeningOrchestrator(db_mock)
        result = await orchestrator.run_pipeline(b"fake_pdf_data", 1, {"title": "Software Engineer"})
        
        assert result["score"]["overall_score"] == 90
        assert mock_parser.called
        assert mock_matcher.called
        assert mock_bias.called
        assert mock_scorer.called
