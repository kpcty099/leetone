"""
Knowledge Factory Review Tool — CLI for approving and editing algorithm knowledge bundles.
"""

import os
import json
import sys

DATA_DIR = "data/problems"

def list_problems():
    if not os.path.exists(DATA_DIR):
        print(f"Error: Directory {DATA_DIR} does not exist.")
        return []
    return [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]

def review_problem(slug):
    prob_dir = os.path.join(DATA_DIR, slug)
    algo_file = os.path.join(prob_dir, "algorithm_data.json")
    
    if not os.path.exists(algo_file):
        print(f"Error: {algo_file} not found.")
        return
    
    with open(algo_file, 'r') as f:
        data = json.load(f)
    
    print("\n" + "="*80)
    print(f" PROBLEM: {slug.upper()}")
    print("="*80)
    print(f"PATTERN:  {data.get('pattern')}")
    print(f"STRATEGY: {data.get('visual_strategy')}")
    print(f"REASONING: {data.get('reasoning')}")
    print("-" * 40)
    
    # Show first few steps of dry run
    trace = data.get("dry_run", [])
    print(f"DRY RUN ({len(trace)} steps):")
    for step in trace[:3]:
         print(f"  [{step['step']}] {step['line']} -> {step['variables']}")
    if len(trace) > 3:
         print(f"  ... [+{len(trace)-3} more steps]")
    
    print("-" * 40)
    choice = input("Approve this Knowledge Bundle? (y/n/edit): ").lower()
    
    if choice == 'y':
        data['approved'] = True
        with open(algo_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"✓ {slug} approved and saved to Knowledge Asset Store.")
    elif choice == 'edit':
        print("Edit feature coming soon (modify JSON manually for now).")
    else:
        print("Problem not approved. Review later.")

if __name__ == "__main__":
    problems = list_problems()
    if not problems:
        print("No problems found in data/problems.")
    else:
        print("Available Problems:")
        for p in problems:
            print(f"- {p}")
        
        if len(sys.argv) > 1:
            review_problem(sys.argv[1])
        else:
            choice = input("\nEnter slug to review (or 'all'): ")
            if choice == 'all':
                for p in problems:
                    review_problem(p)
            elif choice in problems:
                review_problem(choice)
            else:
                print("Invalid slug.")
