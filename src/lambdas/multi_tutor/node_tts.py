"""
Multi-TTS Node — generates two separate audio tracks for discussion mode.
Mentor voice: en-US-GuyNeural (deep, confident)
Student voice: en-US-JennyNeural (lighter, inquisitive)
Each chapter produces mentor_audio_path + student_audio_path.
Falls back to single-voice if any voice fails.
"""
import os
import asyncio

AUDIO_DIR = "video_temp/audio"
MENTOR_VOICE  = "en-US-GuyNeural"
STUDENT_VOICE = "en-US-JennyNeural"

from src.lambdas.tts.tools.elevenlabs import async_synthesize
from config.providers import get_tts_settings, TTS_PROVIDER
try:
    from src.core.tools.progress_tracker import tracker as _tracker
except Exception:
    _tracker = None


async def _synth(text: str, voice: str, out_path: str, is_mentor: bool = True) -> bool:
    """Synthesize one audio clip. Returns True on success."""
    if not text.strip():
        return False
    if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
        return True

    try:
        settings = get_tts_settings()
        if TTS_PROVIDER == "elevenlabs" and async_synthesize:
            voice_id = settings.get("voice_id") if is_mentor else settings.get("student_voice_id")
            await async_synthesize(
                text=text,
                voice_id=voice_id,
                output_path=out_path,
                model=settings.get("model"),
                stability=settings.get("stability", 0.45),
                similarity_boost=settings.get("similarity_boost", 0.8),
                style=settings.get("style", 0.35),
                speed=settings.get("speed", 1.0)
            )
        else:
            import edge_tts
            comm = edge_tts.Communicate(text[:4500], voice, rate="+5%")
            await comm.save(out_path)
        return True
    except Exception as e:
        print(f"  [multi_tts] {TTS_PROVIDER} failed for {os.path.basename(out_path)}: {e}")
        return False


async def _synth_chapter(chapter: dict, audio_dir: str) -> dict:
    seg = chapter["segment_id"]

    mentor_text  = chapter.get("mentor_line", "") + " " + chapter.get("mentor_response", "")
    student_text = chapter.get("student_line", "")

    mentor_path  = os.path.join(audio_dir, f"ch{seg:02d}_mentor.mp3")
    student_path = os.path.join(audio_dir, f"ch{seg:02d}_student.mp3")
    combined_path = os.path.join(audio_dir, f"ch{seg:02d}_audio.mp3")

    # Generate sequentially to prevent API rate limits
    m_ok = await _synth(mentor_text,  MENTOR_VOICE,  mentor_path,  is_mentor=True)
    # Add a small delay between requests just to be safe
    await asyncio.sleep(1.5)
    s_ok = await _synth(student_text, STUDENT_VOICE, student_path, is_mentor=False)
    await asyncio.sleep(1.5)

    print(f"  [multi_tts] Ch{seg}: mentor={'[OK]' if m_ok else '✗'} student={'[OK]' if s_ok else '✗'}")

    # Create a combined track for fallback renderers: mentor -> student -> mentor_response
    updated = {**chapter}
    if m_ok:
        updated["mentor_audio_path"] = mentor_path
        updated["audio_path"] = mentor_path  # primary = mentor (longest)
    if s_ok:
        updated["student_audio_path"] = student_path

    # Also build a combined audio file by concatenating with moviepy
    try:
        import moviepy.editor as mp
        clips = []
        if m_ok and os.path.exists(mentor_path):
            clips.append(mp.AudioFileClip(mentor_path))
        if s_ok and os.path.exists(student_path):
            clips.append(mp.AudioFileClip(student_path))
        if clips:
            combined = mp.concatenate_audioclips(clips)
            combined.write_audiofile(combined_path, verbose=False, logger=None)
            updated["audio_path"] = combined_path
    except Exception as e:
        print(f"  [multi_tts] Ch{seg}: combine failed ({e}), using mentor only")

    return updated


def multi_tts_node(state: dict) -> dict:
    """
    LangGraph node: generate two-voice audio for all discussion chapters.
    """
    chapters = state.get("chapters", [])
    if not chapters:
        return {"error": "multi_tts_node: no chapters"}

    audio_dir = state.get("cache_dir", AUDIO_DIR)
    os.makedirs(audio_dir, exist_ok=True)
    print(f"[multi_tts_node] Generating two-voice audio for {len(chapters)} chapters...")

    async def run_all():
        updated = []
        for ch in chapters:
            res = await _synth_chapter(ch, audio_dir)
            updated.append(res)
        return updated

    try:
        updated = asyncio.run(run_all())
        success = sum(1 for c in updated if c.get("audio_path"))
        print(f"[multi_tts_node] [OK] {success}/{len(chapters)} chapters have audio")
        return {"chapters": list(updated), "error": ""}
    except Exception as e:
        return {"error": f"multi_tts_node failed: {e}"}
