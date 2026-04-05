import subprocess
import tempfile
import os
import re
import json

def evaluate_code(user_code: str, test_cases: list, timeout: int = 3) -> dict:
    """
    Executes user code against multiple test cases by wrapping the logic with a printer.
    """
    results = []
    passed_count = 0
    total_count = len(test_cases)
    
    if not user_code.strip():
        return {"passed": 0, "total": total_count, "results": [{"status": "failed", "error": "Empty code"}]}

    # 1. Detect the function name (e.g. def greet(n) -> greet)
    func_match = re.search(r"def\s+(\w+)\s*\(", user_code)
    func_name = func_match.group(1) if func_match else None

    for idx, test in enumerate(test_cases):
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as tmp:
            raw_input = test.get('input', '')
            
            # 2. Build execution wrapper
            wrapper = ""
            if func_name:
                # Format: print(func_name(input))
                wrapper = f"\nimport json\nprint(json.dumps({func_name}({raw_input})))"
            
            tmp.write(f"{user_code}\n{wrapper}")
            tmp_path = tmp.name

        try:
            proc = subprocess.run(["python", tmp_path], capture_output=True, text=True, timeout=timeout)
            
            if proc.returncode != 0:
                results.append({"case": idx, "status": "error", "error": proc.stderr})
                continue

            # 3. Handle JSON-based comparison
            actual = proc.stdout.strip()
            expected = json.dumps(test.get('output', ''))
            
            if actual == expected:
                passed_count += 1
                results.append({"case": idx, "status": "passed", "output": actual})
            else:
                results.append({"case": idx, "status": "failed", "actual": actual, "expected": expected})
        
        except Exception as e:
            results.append({"case": idx, "status": "error", "error": str(e)})
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)

    return {
        "passed": passed_count, 
        "total": total_count, 
        "results": results, 
        "accuracy": (passed_count/total_count)*100 if total_count > 0 else 0
    }
