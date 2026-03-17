import os
import asyncio
from typing import Dict, Any, List
from src.core.worker import BaseWorker
from config.providers import get_tts_settings, TTS_PROVIDER

try:
    from src.lambdas.tts.tools.elevenlabs import async_synthesize
except ImportError:
    async_synthesize = None

VOICE = "en-US-GuyNeural"

class TTSWorker(BaseWorker):
    """
    Worker for generating TTS audio for chapters.
    Implementation of the "Local Lambda" for TTS.
    """

    def __init__(self, cache_dir: str):
        super().__init__("tts", cache_dir)

    def execute(self, payload: Dict[str, Any]) -> Any:
        """
        Payload: {
            "chapter": dict,
            "audio_dir": str
        }
        """
        chapter = payload.get("chapter")
        audio_dir = payload.get("audio_dir", self.cache_dir)
        
        if not chapter:
            raise ValueError("No chapter data provided to TTSWorker")

        # Use asyncio to run the synthesis
        return asyncio.run(self._synthesize(chapter, audio_dir))

    async def _synthesize(self, chapter: dict, audio_dir: str) -> dict:
        seg_id = chapter["segment_id"]
        text = chapter.get("voiceover", chapter.get("chapter", "No content"))
        out_path = os.path.join(audio_dir, f"ch{seg_id:02d}_audio.mp3")

        # 1. Cache check
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            self.log(f"Ch{seg_id}: using cached audio")
            return {**chapter, "audio_path": out_path}

        self.log(f"Ch{seg_id}: generating TTS ({len(text.split())} words)...")
        
        try:
            settings = get_tts_settings()
            provider = TTS_PROVIDER

            if provider == "elevenlabs" and async_synthesize:
                await async_synthesize(
                    text=text,
                    voice_id=settings.get("voice_id"),
                    output_path=out_path,
                    model=settings.get("model"),
                    stability=settings.get("stability", 0.45),
                    similarity_boost=settings.get("similarity_boost", 0.8),
                    style=settings.get("style", 0.35),
                    speed=settings.get("speed", 1.0)
                )
            else:
                import edge_tts
                communicate = edge_tts.Communicate(text, VOICE, rate="+5%")
                await communicate.save(out_path)

            size_kb = os.path.getsize(out_path) // 1024
            self.log(f"Ch{seg_id}: [OK] saved {size_kb}KB -> {out_path}")
            return {**chapter, "audio_path": out_path}
            
        except Exception as e:
            self.log(f"Ch{seg_id}: {provider} failed ({e}), trying gTTS fallback...")
            return await self._gtts_fallback(chapter, out_path, text)

    async def _gtts_fallback(self, chapter: dict, out_path: str, text: str) -> dict:
        try:
            from gtts import gTTS
            tts = gTTS(text=text[:4000], lang="en", slow=False)
            tts.save(out_path)
            self.log(f"Ch{chapter['segment_id']}: [OK] gTTS fallback saved")
            return {**chapter, "audio_path": out_path}
        except Exception as e2:
            self.log(f"Ch{chapter['segment_id']}: all TTS failed ({e2})")
            return {**chapter, "audio_path": None}
