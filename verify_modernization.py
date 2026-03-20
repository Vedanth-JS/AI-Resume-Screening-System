import os
import sys

# Mock OpenAI if not available for basic import test
try:
    from openai import OpenAI
    print("✅ OpenAI library imported")
except ImportError:
    print("❌ OpenAI library NOT found")

try:
    import fitz
    print("✅ PyMuPDF (fitz) library imported")
except ImportError:
    print("❌ PyMuPDF (fitz) library NOT found")

try:
    import nltk
    print("✅ NLTK library imported")
except ImportError:
    print("❌ NLTK library NOT found")

# Test Parser
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))
try:
    from backend.app.core.parser import ResumeParser
    from backend.app.core.extractor import FeatureExtractor
    from backend.app.core.scorer import Scorer
    print("✅ Core modules imported successfully")
except Exception as e:
    print(f"❌ Error importing core modules: {e}")

# Basic logic test (without network)
test_text = "John Doe is a Python Developer with 5 years of experience in Docker."
extractor = FeatureExtractor(test_text)
skills = extractor.extract_skills()
exp = extractor.extract_experience()
print(f"Test Extraction: Skills={skills}, Exp={exp}")

if "Python" in skills and "Docker" in skills and exp == 5:
    print("✅ Basic extraction logic working")
else:
    print("❌ Basic extraction logic failed")

print("\nModernization verification complete.")
