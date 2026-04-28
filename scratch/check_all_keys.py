import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

keys = [
    os.getenv("GEMINI_API_KEY_1"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"),
    os.getenv("GEMINI_API_KEY")
]

for i, key in enumerate(keys):
    name = f"GEMINI_API_KEY_{i+1}" if i < 3 else "GEMINI_API_KEY"
    if not key:
        print(f"{name}: [MISSING]")
        continue
    
    print(f"Testing {name}: {key[:5]}...{key[-5:]}")
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("ping")
        print(f"✅ {name} works! Response: {response.text.strip()}")
    except Exception as e:
        print(f"❌ {name} failed: {str(e)}")
    print("-" * 20)
