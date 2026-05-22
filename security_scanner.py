import os
import re
import json

# Patterns to match
PATTERNS = {
    "OpenAI API Key": r"sk-[a-zA-Z0-9]{48}",
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "Generic API Key": r"(?i)(api[_-]?key|secret|token|password)[\s]*[:=][\s]*['\"][a-zA-Z0-9_\-\.]{10,}['\"]",
    "Database URI": r"(?i)(postgres|mysql|mongodb)://[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-]+@",
    "Email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    # Add a rudimentary check for phone numbers if needed, but emails/keys are most critical
}

EXCLUDE_DIRS = {'.git', '.gemini', 'node_modules', '__pycache__', 'build', 'dist', 'quant'}
EXCLUDE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.zip', '.msi', '.exe', '.pdf', '.csv', '.parquet'}

def scan_file(filepath):
    results = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                # Skip overly long lines (e.g. minified JS or huge JSON arrays)
                if len(line) > 1000:
                    continue
                for name, pattern in PATTERNS.items():
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        # Exclude some false positives like example@example.com
                        val = match.group()
                        if 'example.com' in val or 'test@' in val or 'your_api_key' in val:
                            continue
                        results.append({
                            "type": name,
                            "line_num": i + 1,
                            "match": val[:10] + "..." + val[-5:] if len(val) > 20 else val
                        })
    except UnicodeDecodeError:
        pass # Not a text file
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return results

def main():
    root_dir = r"C:\Users\user\.gemini\antigravity\scratch"
    report = {}
    
    print("Starting security scan...")
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Exclude directories
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in EXCLUDE_EXTS:
                continue
            
            filepath = os.path.join(dirpath, filename)
            # Skip the scanner itself
            if filename == "security_scanner.py":
                continue
                
            file_results = scan_file(filepath)
            if file_results:
                rel_path = os.path.relpath(filepath, root_dir)
                report[rel_path] = file_results
                
    with open(os.path.join(root_dir, 'security_report.json'), 'w') as f:
        json.dump(report, f, indent=4)
        
    print(f"Scan complete. Found potential issues in {len(report)} files.")
    for file, issues in report.items():
        print(f"\n{file}:")
        for issue in issues:
            print(f"  - Line {issue['line_num']}: [{issue['type']}] {issue['match']}")

if __name__ == "__main__":
    main()
