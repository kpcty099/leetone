"""
Reasoning Tool for the Planner Lambda.
"""
from src.core.tools.llm_factory import call_llm
from src.prompts.reasoning_prompt import REASONING_SYSTEM_PROMPT, REASONING_USER_PROMPT_TEMPLATE

ALGO_PATTERNS = {
    "two_pointers": "Two Pointers (e.g., 3Sum, Two Sum II, Valid Palindrome)",
    "sliding_window": "Sliding Window (Fixed/Variable) (e.g., Longest Substring)",
    "hashmap_hashing": "Hash Map / Hashing (e.g., Two Sum, Group Anagrams)",
    # ... (Rest of patterns)
}

def analyze_pattern(title, content, code_snippet):
    """LLM reasoning to detect algorithm pattern."""
    prompt = REASONING_USER_PROMPT_TEMPLATE.format(
        title=title,
        difficulty="Medium",
        problem_statement=content,
        code_snippet=code_snippet,
        patterns="\n".join([f"- {k}: {v}" for k, v in ALGO_PATTERNS.items()]),
        strategies="pointer_motion"
    )
    # call_llm logic...
    return {"pattern": "two_pointers", "visual_strategy": "pointer_motion"}
