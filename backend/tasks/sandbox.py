import sys
import io
import traceback
import inspect

def execute_code_worker(code, test_input, queue):
    """Worker for sandboxed code execution in subprocess (no Django imports)."""
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        namespace = {}
        exec(code, namespace)
        # Find the first callable function
        func = None
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith('_'):
                func = obj
                break

        if func is None:
            queue.put({"error": "No function found in your code."})
            return

        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if len(params) == 1:
            result = func(test_input)
        elif isinstance(test_input, list):
            result = func(*test_input)
        else:
            result = func(test_input)

        printed = sys.stdout.getvalue()
        queue.put({"result": result, "stdout": printed})
    except Exception as e:
        queue.put({"error": str(e), "traceback": traceback.format_exc()})
    finally:
        sys.stdout = old_stdout
