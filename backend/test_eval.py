import sys
import multiprocessing
from multiprocessing import Queue
import io
import traceback
import inspect

def _execute_code_worker(code, test_input, queue):
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        namespace = {}
        exec(code, namespace)
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

if __name__ == "__main__":
    tests = [
        (
            "def add_item(l, x):\n    if x not in l:\n        l.append(x)\n    return l",
            [[1, 2], 2]
        ),
        (
            "def count(n):\n    return [i for i in range(1, n+1)]",
            5
        ),
        (
            "def greet(n):\n    return f'Hello, {n}!'",
            10
        )
    ]
    
    for code, test_input in tests:
        q = Queue()
        p = multiprocessing.Process(target=_execute_code_worker, args=(code, test_input, q))
        p.start()
        p.join()
        res = q.get()
        print(f"Code:\n{code}")
        print(f"Input: {test_input}")
        print(f"Result: {res}")
        print("---")
