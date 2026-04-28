import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"API Key found: {bool(api_key)}")
if api_key:
    print(f"Key preview: {api_key[:5]}...{api_key[-5:]}")
    
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content("Hello! Are you working?")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Gemini Error: {str(e)}")
