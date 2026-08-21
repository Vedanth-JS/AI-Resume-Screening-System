import os
import google.generativeai as genai

api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)

try:
    print("Listing models:")
    for m in genai.list_models():
        print(f"Name: {m.name}, Supported methods: {m.supported_generation_methods}")
except Exception as e:
    print("Error listing models:", e)
