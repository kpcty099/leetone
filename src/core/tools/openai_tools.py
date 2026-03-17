import os
from openai import OpenAI
from dotenv import load_dotenv

# Load keys from .env in project root
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
load_dotenv(dotenv_path, override=True)

def call_openai(system_prompt: str, user_prompt: str, model="gpt-4o-mini", max_tokens=4096) -> str:
    """
    Standardized wrapper for calling OpenAI API.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment. Please check your .env file.")
    
    client = OpenAI(api_key=api_key)
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[OpenAI] API Error: {e}")
        raise e
