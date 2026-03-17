import time
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load keys from .env in project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(project_root, ".env"))

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

def call_gemini(system_prompt: str, user_prompt: str, model="gemini-2.0-flash") -> str:
    """Wrapper for calling Google Gemini API using the raw SDK with rate limit backoff."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            model_instance = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt
            )
            
            response = model_instance.generate_content(user_prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            print(f"  [Gemini SDK] Model {model} attempt {attempt + 1} failed: {error_msg}")
            
            if "429" in error_msg or "Quota" in error_msg:
                wait_time = 35  # wait > 1 minute total if hitting the 15 RPM limit
                print(f"  [Gemini Quota] Hit rate limit. Sleeping for {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
                
            # Try generic pro if flash fails (for non-429s)
            if model != "gemini-pro-latest":
                 return call_gemini(system_prompt, user_prompt, model="gemini-pro-latest")
            raise e
            
    raise Exception(f"Gemini API completely failed after {max_retries} retries due to strict Rate Limits.")
