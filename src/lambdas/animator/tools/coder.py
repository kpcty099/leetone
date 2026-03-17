"""
Coder Agent (LLM) Tool for the Animator Lambda.
"""
from src.core.tools.llm_factory import call_llm

def generate_manim_logic(problem_context):
    """LLM assistance for complex Manim choreo."""
    return "class CustomScene(Scene): ..."
