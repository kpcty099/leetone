"""
Renderer Node — dispatches video rendering tasks to the Renderer Worker.
Part of the Renderer Lambda module.
"""
from .worker import RendererWorker
from concurrent.futures import ThreadPoolExecutor

def renderer_node(state: dict) -> dict:
    chapters = state.get("chapters", [])
    cache_dir = state.get("cache_dir")
    
    print(f"[renderer_node] Rendering {len(chapters)} video segments...")
    
    worker = RendererWorker(cache_dir)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(worker.run, {"chapter": c}) for c in chapters]
        updated_chapters = [f.result() for f in futures]
        
    return {"chapters": updated_chapters}
