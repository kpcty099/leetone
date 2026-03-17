"""
Edge TTS Tool for the TTS Lambda.
"""
import edge_tts

async def synthesize_edge(text, output_path):
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
    await communicate.save(output_path)
