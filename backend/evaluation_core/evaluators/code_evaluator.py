import subprocess
import tempfile
import os

def evaluate_code(user_code: str, test_cases: list, timeout: int = 2) -> dict:
    """
    Executes user code against multiple test cases in a sandboxed subprocess.
    Returns: {passed: int, total: int, results: list}
    """
    results = []
    passed_count = 0
    total_count = len(test_cases)

    if not user_code.strip():
        return {"passed": 0, "total": total_count, "results": [{"status": "failed", "error": "Empty code submission"}]}

    for idx, test in enumerate(test_cases):
        # Create a temp file for execution
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w') as tmp:
            # Prepare execution wrapper
            # We assume the user code provides the logic, and we append a 'print' to check result
            # or the user code itself performs the printing.
            tmp.write(f"{user_code}\n\n# Verification logic would go here if needed per test")
            tmp_path = tmp.name

        try:
            # Run the process with restricted permissions if possible (omitted for local brevity)
            proc = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            actual_output = proc.stdout.strip()
            # Handle cases where the test expects a specific print output
            expected_output = str(test.get('output', '')).strip()

            if proc.returncode == 0:
                if actual_output == expected_output:
                    passed_count += 1
                    results.append({"case": idx, "status": "passed", "output": actual_output})
                else:
                    results.append({
                        "case": idx, 
                        "status": "failed", 
                        "error": f"Mismatch: Expected '{expected_output}', got '{actual_output}'",
                        "output": actual_output
                    })
            else:
                results.append({"case": idx, "status": "error", "error": proc.stderr.strip()})

        except subprocess.TimeoutExpired:
            results.append({"case": idx, "status": "timeout", "error": f"Execution exceeded {timeout}s"})
        except Exception as e:
            results.append({"case": idx, "status": "error", "error": str(e)})
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

    return {
        "passed": passed_count,
        "total": total_count,
        "results": results,
        "accuracy": passed_count / total_count if total_count > 0 else 0
    }
