import anthropic
import json
import os
import re
from dotenv import load_dotenv
from schemas import ScreeningResult, RecommendationEnum

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4-5"


def screen_resume(
    resume_text: str,
    job_title: str,
    job_description: str,
    required_skills: list[str],
) -> ScreeningResult:
    """Send resume + job info to Claude and get structured screening result."""

    system_prompt = """You are an expert HR recruiter and resume screening specialist. 
Your task is to evaluate a candidate's resume against a job description and required skills.
You MUST respond with ONLY valid JSON, no other text, no markdown code blocks.
The JSON must have exactly these fields:
{
  "score": <number 0-100>,
  "matched_skills": [<list of skills from required_skills that candidate has>],
  "missing_skills": [<list of skills from required_skills that candidate lacks>],
  "summary": "<2-3 sentence professional summary of the candidate's fit>",
  "recommendation": "<exactly one of: Strong Fit, Maybe, Reject>"
}

Scoring guide:
- 80-100: Strong Fit - candidate meets most/all requirements
- 50-79: Maybe - candidate meets some requirements, has potential
- 0-49: Reject - candidate significantly lacks required skills/experience"""

    user_prompt = f"""Please evaluate this candidate for the following position:

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

REQUIRED SKILLS:
{', '.join(required_skills) if required_skills else 'Not specified'}

CANDIDATE RESUME:
{resume_text[:8000]}

Respond with JSON only."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )

    raw = message.content[0].text.strip()

    # Strip markdown code blocks if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    data = json.loads(raw)

    # Normalize recommendation
    rec_map = {
        "strong fit": RecommendationEnum.strong_fit,
        "maybe": RecommendationEnum.maybe,
        "reject": RecommendationEnum.reject,
    }
    rec_str = data.get("recommendation", "Reject").lower().strip()
    recommendation = rec_map.get(rec_str, RecommendationEnum.reject)

    return ScreeningResult(
        score=float(data.get("score", 0)),
        matched_skills=data.get("matched_skills", []),
        missing_skills=data.get("missing_skills", []),
        summary=data.get("summary", ""),
        recommendation=recommendation,
    )
