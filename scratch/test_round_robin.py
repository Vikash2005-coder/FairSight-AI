import os
import asyncio
from dotenv import load_dotenv
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.orchestrator import _safe_generate, _get_model, GEMINI_KEYS

async def test_rotation():
    print(f"Testing with {len(GEMINI_KEYS)} keys.")
    model = _get_model()
    prompt = "Reply with 'OK' if you see this."
    
    try:
        # This should trigger rotation if the first key is bad, or just work if it's good
        response = await _safe_generate(model, prompt)
        print(f"Success: {response.text}")
    except Exception as e:
        print(f"Final failure after rotations: {e}")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(test_rotation())
