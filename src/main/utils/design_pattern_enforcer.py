import os
import re
import sys

# Rules: (Regex for violation, error message, allowed directories)
RULES = [
    {
        "pattern": r"import\s+(openai|anthropic|cohere|google\.generativeai)",
        "message": "Direct LLM library import detected. Use LLMWrapper instead.",
        "path_filter": "src/main/agent/nodes",
    },
    {
        "pattern": r"import\s+(psycopg2|pymongo|mysql|sqlite3|sqlalchemy)",
        "message": "Direct DB library import detected. Use DBWrapper instead.",
        "path_filter": "src/main/agent/nodes",
    },
    {
        "pattern": r"import\s+(git|github)",
        "message": "Direct Git library import detected. Use GitWrapper instead.",
        "path_filter": "src/main/agent/nodes",
    },
    {
        "pattern": r"class\s+\w+Node\((?!NodeInterface|BaseNode)",
        "message": "Node must implement NodeInterface or inherit from BaseNode.",
        "path_filter": "src/main/agent/nodes",
    }
]

def scan_file(file_path):
    violations = []
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        for rule in RULES:
            # Check if file path matches rule's path filter
            if rule["path_filter"] in file_path.replace("\\", "/"):
                if re.search(rule["pattern"], content):
                    violations.append(f"{file_path}: {rule['message']}")
    return violations

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    all_violations = []
    
    for root, _, files in os.walk(os.path.join(root_dir, "src")):
        for file in files:
            if file.endswith(".py") and file != "design_pattern_enforcer.py":
                file_path = os.path.join(root, file)
                all_violations.extend(scan_file(file_path))
    
    if all_violations:
        print("Architecture Violations Found:")
        for v in all_violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("No architecture violations found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
