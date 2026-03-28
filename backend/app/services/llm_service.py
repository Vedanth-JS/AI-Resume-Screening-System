import google.generativeai as genai
import os
import json
from typing import Dict, Any, List

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    # Using 1.5-flash for faster, more cost-effective structural parsing
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

class LLMService:
    @staticmethod
    async def extract_resume_data(text: str) -> Dict[str, Any]:
        if not model:
            # Fallback will be handled by ParsingAgent
            return {}
            
        prompt = f"""
        Extract structured information from the following resume text. 
        Return ONLY a JSON object with the following keys:
        - name: string
        - email: string
        - phone: string
        - skills: list of strings
        - education: list of objects (school, degree, year)
        - experience: list of objects (company, role, duration, years)
        - projects: list of strings
        - certifications: list of strings
        - total_years_experience: float

        Resume Text:
        {text}
        """
        
        try:
            response = model.generate_content(prompt)
            # Find JSON in response (Gemini sometimes adds markdown blocks)
            content = response.text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
        except Exception as e:
            print(f"LLM Extraction Error: {e}")
            return {}

    @staticmethod
    async def evaluate_candidate(jd: str, resume_text: str) -> str:
        if not model:
            return "Gemini API key not configured. Evaluation unavailable."
        
        prompt = f"""
        Analyze this candidate's resume against the following Job Description.
        
        Job Description:
        {jd}
        
        Resume:
        {resume_text}
        
        Provide:
        1. Fit summary (Accept/Review/Reject)
        2. Top 3 strengths
        3. Top 3 missing requirements
        4. Suggestions for resume improvement
        5. 5 targeted interview questions
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error during LLM evaluation: {str(e)}"

    @staticmethod
    async def compare_candidates(jd: str, resume1: str, resume2: str) -> str:
        if not model:
            return "Comparison unavailable due to missing API key."
            
        prompt = f"Compare these two candidates for the job: {jd}\n\nCandidate 1:\n{resume1}\n\nCandidate 2:\n{resume2}"
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return str(e)
