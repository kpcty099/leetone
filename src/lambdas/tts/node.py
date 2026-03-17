"""
TTS Node — dispatches audio synthesis tasks to the TTS Worker.
Part of the TTS Lambda module.
"""
from .worker import TTSWorker
from concurrent.futures import ThreadPoolExecutor

def tts_node(state: dict) -> dict:
    chapters = state.get("chapters", [])
    cache_dir = state.get("cache_dir")
    
    print(f"[tts_node] Synthesizing audio for {len(chapters)} chapters...")
    
    worker = TTSWorker(cache_dir)
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(worker.run, {"chapter": c}) for c in chapters]
        updated_chapters = [f.result() for f in futures]
        
    return {"chapters": updated_chapters}
