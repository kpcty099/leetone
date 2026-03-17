"""
Provider Configuration — swap LLMs and TTS with one line.
Supports free tier → paid upgrade seamlessly.
"""

# ── LLM Providers ─────────────────────────────────────────────────────────────
# Options: "huggingface" | "openai" | "anthropic" | "gemini"
LLM_PROVIDER = "huggingface"

# ── TTS Providers ─────────────────────────────────────────────────────────────
# Options: "edge_tts" | "elevenlabs" | "openai_tts" | "gtts"
TTS_PROVIDER = "elevenlabs"

# ── Provider Settings ─────────────────────────────────────────────────────────
PROVIDER_SETTINGS = {
    "huggingface": {
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "api_key_env": "HUGGINGFACE_API_KEY",
        "max_tokens": 512,
    },
    "openai": {
        "model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
        "max_tokens": 8192,
    },
    "anthropic": {
        "model": "claude-3-haiku-20240307",
        "api_key_env": "ANTHROPIC_API_KEY",
        "max_tokens": 1024,
    },
    "gemini": {
        "model": "gemini-1.5-flash",
        "api_key_env": "GEMINI_API_KEY",
        "max_tokens": 1024,
    },
    "edge_tts": {
        "voice": "en-US-GuyNeural",
        "rate": "+5%",
    },
    "elevenlabs": {
        "api_key_env":       "ELEVENLABS_API_KEY",
        "voice_id":          "JBFqnCBsd6RMkjVDRZzb",   # George — deep, educational
        "student_voice_id": "EXAVITQu4vr4xnSDxMaL",   # Sarah  — lighter, inquisitive
        "model":             "eleven_multilingual_v2",   # Best quality
        "stability":         0.45,
        "similarity_boost":  0.80,
        "style":             0.35,
        "speed":             1.0,
    },
    "openai_tts": {
        "api_key_env": "OPENAI_API_KEY",
        "voice": "onyx",
        "model": "tts-1-hd",
    },
}


def get_llm_settings() -> dict:
    return PROVIDER_SETTINGS[LLM_PROVIDER]


def get_tts_settings() -> dict:
    return PROVIDER_SETTINGS[TTS_PROVIDER]
