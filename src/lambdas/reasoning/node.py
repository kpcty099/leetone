"""
Algorithm Reasoning Engine — Node #1 of the Knowledge Factory.
Detects patterns and visual strategies to ensure verified video generation.
"""

import json
import os
from typing import Dict, Any, List
import ast
from src.core.state import AgentState
from src.core.tools.llm_factory import call_llm
from src.prompts.reasoning_prompt import REASONING_SYSTEM_PROMPT, REASONING_USER_PROMPT_TEMPLATE
import traceback

# ── Algorithm Pattern Registry (The ~40 Patterns) ─────────────────────────────
ALGO_PATTERNS = {
    "two_pointers": "Two Pointers (e.g., 3Sum, Two Sum II, Valid Palindrome)",
    "sliding_window": "Sliding Window (Fixed/Variable) (e.g., Longest Substring)",
    "fast_slow_pointers": "Fast & Slow Pointers (Tortoise & Hare) (e.g., Cycle Detection)",
    "merge_intervals": "Merge Intervals (e.g., Insert Interval)",
    "cyclic_sort": "Cyclic Sort (e.g., Find Missing Number)",
    "linked_list_reversal": "In-place Reversal of a Linked List",
    "tree_bfs": "Tree Breadth First Search (Level Order)",
    "tree_dfs": "Tree Depth First Search (Pre/In/Post Order)",
    "two_heaps": "Two Heaps (e.g., Find Median from Data Stream)",
    "subsets": "Subsets / Powerset (e.g., Permutations, Combinations)",
    "binary_search_modified": "Modified Binary Search (e.g., Search in Rotated Array)",
    "top_k_elements": "Top 'K' Elements (using Heap)",
    "k_way_merge": "K-way Merge (e.g., Merge K Sorted Lists)",
    "topological_sort": "Topological Sort (Graph)",
    "dp_01_knapsack": "Dynamic Programming (0/1 Knapsack Pattern)",
    "dp_unbounded_knapsack": "Dynamic Programming (Unbounded Pattern)",
    "dp_fibonacci": "Dynamic Programming (Fibonacci / Climbing Stairs)",
    "dp_lcs": "Longest Common Subsequence Pattern",
    "dp_lis": "Longest Increasing Subsequence Pattern",
    "monotonic_stack": "Monotonic Stack (e.g., Next Greater Element)",
    "monotonic_queue": "Monotonic Queue (e.g., Constrained Subsequence Sum)",
    "trie": "Prefix Tree (Trie) (e.g., Implement Trie)",
    "union_find": "Disjoint Set Union (DSU) (e.g., Number of Provinces)",
    "backtracking": "Backtracking (e.g., N-Queens, Sudoku)",
    "greedy": "Greedy Algorithms (e.g., Gas Station, Jump Game)",
    "bit_manipulation": "Bit Manipulation (e.g., Single Number)",
    "matrix_traversal": "Matrix / Grid Traversal (BFS/DFS)",
    "prefix_sum": "Prefix Sum / Accumulator (e.g., Subarray Sum Equals K)",
    "divide_and_conquer": "Divide and Conquer (e.g., Merge Sort, Quick Sort)",
    "segment_tree": "Segment Tree / Fenwick Tree (Range Queries)",
    "math_geometry": "Mathematical / Geometry specific patterns",
    "hashmap_hashing": "Hash Map / Hashing (e.g., Two Sum, Group Anagrams)",
    "string_kmp": "String Matching (KMP, Rabin-Karp)",
    "graph_shortest_path": "Graph Shortest Path (Dijkstra, Bellman-Ford)",
    "unknown": "Custom / Unclassified Algorithm"
}

# ── Visual Strategy Registry ──────────────────────────────────────────────────
VISUAL_STRATEGIES = {
    "pointer_motion": "Focus on array elements with moving index arrows/pointers.",
    "hashmap_grid": "Highlight key-value lookups in a dynamic grid structure.",
    "sliding_window_highlight": "Highlight a moving range of elements in an array/string.",
    "tree_traversal": "Visualize nodes flashing in order as we traverse a tree.",
    "stack_queue_anim": "Animate elements pushing/popping from a container.",
    "matrix_heatmap": "Colorize cells in a 2D grid as they are processed.",
    "recursion_tree": "Visualize the state space tree of a recursive algorithm.",
    "bit_mask_binary": "Show numbers in their binary representation during manipulation.",
    "graph_node_blink": "Animate edge relaxation or node visiting in a graph."
}


def reasoning_node(state: AgentState) -> dict:
    """
    Analyzes the problem and classifies it into a standard pattern and visual strategy.
    """
    prob = state.get("problem_data", {})
    title = state.get("problem_title", prob.get("title", "Unknown Problem"))
    problem_statement = prob.get("problem", {}).get("content_html", "")
    difficulty = prob.get("problem", {}).get("difficulty", "Unknown")
    code_snippet = prob.get("problem", {}).get("code_snippet_python", "")
    
    print(f"[reasoning_node] Analyzing algorithm patterns for '{title}'...")

    system_prompt = REASONING_SYSTEM_PROMPT

    user_prompt = REASONING_USER_PROMPT_TEMPLATE.format(
        title=title,
        difficulty=difficulty,
        problem_statement=problem_statement,
        code_snippet=code_snippet,
        patterns="\n".join([f"- {k}: {v}" for k, v in ALGO_PATTERNS.items()]),
        strategies="\n".join([f"- {k}: {v}" for k, v in VISUAL_STRATEGIES.items()])
    )
    
    try:
        response_text = call_llm(
            system_prompt,
            user_prompt
        )
        
        # Strip potential markdown fences
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].strip()
            
        res = json.loads(response_text)
        
        print(f"  Pattern: {res.get('pattern', 'unknown')}")
        print(f"  Strategy: {res.get('visual_strategy', 'unknown')}")
        
        return {
            "pattern": res.get("pattern", "unknown"),
            "visual_strategy": res.get("visual_strategy", "unknown"),
            "reasoning": res.get("reasoning", "No reasoning provided."),
            "algorithm_data": {
                "pseudocode": res.get("pseudocode", ""),
                "reasoning_raw": res
            }
        }
    except Exception as e:
        print(f"  [reasoning_node] Error: {e}")
        print(f"  [reasoning_node] LLM Response (raw): {response_text}")
        print(f"  [reasoning_node] Traceback: {traceback.format_exc()}")
        return {
            "pattern": "unknown",
            "visual_strategy": "pointer_motion",
            "reasoning": f"Reasoning failed due to error: {e}",
            "error": "reasoning_node failed"
        }
