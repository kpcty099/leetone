"""
ElevenLabs TTS Tool — high-quality neural voice synthesis.
Reads ELEVENLABS_API_KEY from environment.

Recommended voices for coding education:
  George      : JBFqnCBsd6RMkjVDRZzb  — deep, confident, educational
  Christopher : iP95p4xoKVk53GoZ742B  — clear, measured, engaging
  Josh        : TxGEqnHWrfWFTfGW9XjX  — casual, fast-paced, relatable
  Aria        : 9BWtsMINqrJLrRacOk9x  — female, calm, professional
  Sarah       : EXAVITQu4vr4xnSDxMaL  — female, lighter, inquisitive (good for student voice)
"""

import os
import requests

API_BASE = "https://api.elevenlabs.io/v1"

# ── Default voices ────────────────────────────────────────────────────────────
DEFAULT_MENTOR_VOICE  = "JBFqnCBsd6RMkjVDRZzb"   # George — deep & educational
DEFAULT_STUDENT_VOICE = "EXAVITQu4vr4xnSDxMaL"   # Sarah  — lighter, inquisitive

# Model options (ordered best → fastest)
MODEL_MULTILINGUAL = "eleven_multilingual_v2"   # Best quality, all languages
MODEL_TURBO        = "eleven_turbo_v2_5"        # ~2× faster, nearly same quality
MODEL_FLASH        = "eleven_flash_v2_5"        # Fastest, lower quality


def _get_api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise EnvironmentError(
            "ELEVENLABS_API_KEY not set. "
            "Run: $env:ELEVENLABS_API_KEY = 'your_key_here'"
        )
    return key


def synthesize(
    text: str,
    voice_id: str = DEFAULT_MENTOR_VOICE,
    output_path: str = "output.mp3",
    model: str = MODEL_MULTILINGUAL,
    stability: float = 0.45,
    similarity_boost: float = 0.80,
    style: float = 0.35,
    speed: float = 1.0,
) -> str:
    """
    Synthesize text to speech using ElevenLabs API.
    Returns output_path on success, raises on failure.

    Args:
        text:             Voiceover text (max ~5000 chars recommended)
        voice_id:         ElevenLabs voice ID
        output_path:      Where to save the .mp3
        model:            TTS model to use
        stability:        0 (variable) → 1 (stable). 0.45 sounds natural.
        similarity_boost: 0 → 1. Higher = closer to original voice.
        style:            0 → 1. Higher = more expressive (costs more).
        speed:            0.7 → 1.2. 1.0 = normal, 1.1 = slightly faster.
    """
    api_key = _get_api_key()

    # Truncate to ~5000 chars to avoid huge cost in one call
    text = text[:5000]

    url = f"{API_BASE}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability":        stability,
            "similarity_boost": similarity_boost,
            "style":            style,
            "use_speaker_boost": True,
            "speed":            speed,
        },
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs API error {resp.status_code}: {resp.text[:300]}"
        )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)

    size_kb = os.path.getsize(output_path) // 1024
    print(f"  [elevenlabs] Saved {size_kb}KB -> {output_path}")
    return output_path


async def async_synthesize(*args, **kwargs) -> str:
    """Async wrapper for synthesize."""
    import asyncio
    return await asyncio.to_thread(synthesize, *args, **kwargs)


def get_available_voices() -> list[dict]:
    """List all available voices on the account."""
    api_key = _get_api_key()
    try:
        resp = requests.get(
            f"{API_BASE}/voices",
            headers={"xi-api-key": api_key},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("voices", [])
    except Exception as e:
        print(f"  [elevenlabs] Warning: Could not list voices (Admin permission missing?): {e}")
        return []


def get_remaining_characters() -> int:
    """Return remaining character quota on the account."""
    api_key = _get_api_key()
    try:
        resp = requests.get(
            f"{API_BASE}/user/subscription",
            headers={"xi-api-key": api_key},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        used  = data.get("character_count", 0)
        limit = data.get("character_limit", 0)
        remaining = limit - used
        print(f"  [elevenlabs] Characters: {used:,} used / {limit:,} total ({remaining:,} remaining)")
        return remaining
    except Exception as e:
        print(f"  [elevenlabs] Warning: Could not check characters (Admin permission missing?): {e}")
        return -1
