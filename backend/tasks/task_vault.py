VAULT = {
    'beginner': [
        {'title': 'Off-by-One Counter', 'description': 'Correct the range in the loop.', 'starter_code': 'def count(n):\n    return [i for i in range(n)]', 'test_cases': [{'input': 5, 'output': [0,1,2,3,4,5]}], 'domain': 'math'},
        {'title': 'Boolean Flip Fix', 'description': 'Invert the logic correctly.', 'starter_code': 'def is_valid(x):\n    return x > 0', 'test_cases': [{'input': -5, 'output': True}], 'domain': 'logic'},
        {'title': 'List Append Bug', 'description': 'Append only if not exists.', 'starter_code': 'def add_item(l, x):\n    l.append(x)\n    return l', 'test_cases': [{'input': [[1, 2], 2], 'output': [1, 2]}], 'domain': 'data'},
        {'title': 'Empty String Return', 'description': 'Return "N/A" if empty.', 'starter_code': 'def format_str(s):\n    return s', 'test_cases': [{'input': '', 'output': 'N/A'}], 'domain': 'strings'},
        {'title': 'Tax Calculation', 'description': 'Apply 5% tax.', 'starter_code': 'def tax(p):\n    return p + 5', 'test_cases': [{'input': 100, 'output': 105.0}], 'domain': 'finance'}
    ] * 4, # 20 entries
    'elementary': [
        {'title': 'Unique Sorted List', 'description': 'Return unique elements in order.', 'starter_code': 'def solve(l):\n    return list(set(l))', 'test_cases': [{'input': [3, 1, 2, 3], 'output': [1, 2, 3]}], 'domain': 'data'},
        {'title': 'Vowel Switch', 'description': 'Replace vowels with star.', 'starter_code': 'def solve(s):\n    return s', 'test_cases': [{'input': 'abc', 'output': '*bc'}], 'domain': 'strings'},
        {'title': 'Factorial Bug', 'description': 'Fix recursion base case.', 'starter_code': 'def solve(n):\n    if n == 0: return 0\n    return n * solve(n-1)', 'test_cases': [{'input': 3, 'output': 6}], 'domain': 'math'},
        {'title': 'Dict Key Filter', 'description': 'Filter by value threshold.', 'starter_code': 'def solve(d, t):\n    return d', 'test_cases': [{'input': [{'a': 10, 'b': 20}, 15], 'output': {'b': 20}}], 'domain': 'data'},
        {'title': 'Palindrome Ignore Case', 'description': 'Is pal (ignore case)?', 'starter_code': 'def solve(s):\n    return s == s[::-1]', 'test_cases': [{'input': 'Racecar', 'output': True}], 'domain': 'logic'}
    ] * 4,
    'intermediate': [
        {'title': 'Binary Search Midpoint', 'description': 'Find target index.', 'starter_code': 'def solve(nums, t):\n    l, r = 0, len(nums)\n    while l < r:\n        m = l + r // 2\n        if nums[m] == t: return m\n        l = m + 1\n    return -1', 'test_cases': [{'input': [[1, 2, 3], 2], 'output': 1}], 'domain': 'algorithms'},
        {'title': 'Nested Dict Flatten', 'description': 'Flatten one level depth.', 'starter_code': 'def solve(d):\n    return d', 'test_cases': [{'input': {'a': {'b': 1}}, 'output': {'a.b': 1}}], 'domain': 'data'},
        {'title': 'Regex Email Filter', 'description': 'Find valid emails.', 'starter_code': 'def solve(s):\n    return s.split()', 'test_cases': [{'input': 'a@b.com c@d', 'output': ['a@b.com']}], 'domain': 'strings'},
        {'title': 'Case-Insen Counter', 'description': 'Word frequency.', 'starter_code': 'def solve(s):\n    return {}', 'test_cases': [{'input': 'Apple apple', 'output': {'apple': 2}}], 'domain': 'data'},
        {'title': 'List Difference', 'description': 'A minus B.', 'starter_code': 'def solve(a, b):\n    return a', 'test_cases': [{'input': [[1, 2, 3], [2]], 'output': [1, 3]}], 'domain': 'logic'}
    ] * 4,
    'advanced': [
        {'title': 'Memoized Fibonacci', 'description': 'O(n) fibonacci with dict.', 'starter_code': 'memo = {}\ndef solve(n):\n    if n <= 1: return n\n    return solve(n-1) + solve(n-2)', 'test_cases': [{'input': 35, 'output': 9227465}], 'domain': 'algorithms'},
        {'title': 'BFS Path Finder', 'description': 'Shortest path in matrix.', 'starter_code': 'def solve(m):\n    return 0', 'test_cases': [{'input': [[0, 0], [1, 0]], 'output': 2}], 'domain': 'algorithms'},
        {'title': 'Decorator Timing', 'description': 'Fix the return of a decorator.', 'starter_code': 'def log(f):\n    def w(*a, **k):\n        f(*a, **k)\n    return w', 'test_cases': [{'input': 'test', 'output': 'test'}], 'domain': 'logic'},
        {'title': 'JSON Circularity', 'description': 'Filter objects with cyclic refs.', 'starter_code': 'def solve(o):\n    return o', 'test_cases': [{'input': {'id': 1}, 'output': {'id': 1}}], 'domain': 'data'},
        {'title': 'String Sliding Window', 'description': 'Find length of longest unique sub.', 'starter_code': 'def solve(s):\n    return 0', 'test_cases': [{'input': 'abcabcbb', 'output': 3}], 'domain': 'algorithms'}
    ] * 4,
    'expert': [
        {'title': 'Dijkstra Priority Queue', 'description': 'Graph shortest distance.', 'starter_code': 'import heapq\ndef solve(g, s):\n    q = [(0, s)]\n    d = {s: 0}\n    while q:\n        dist, u = heapq.heappop(q)\n        for v, w in g[u]:\n            if dist + w < d.get(v, 999):\n                d[v] = dist + w\n    return d', 'test_cases': [{'input': [{'A': [('B', 1)]}, 'A'], 'output': {'A': 0, 'B': 1}}], 'domain': 'algorithms'},
        {'title': 'Knapsack Dynamic', 'description': 'Max value in weight.', 'starter_code': 'def solve(w, v, c):\n    return 0', 'test_cases': [{'input': [[1, 2], [10, 20], 2], 'output': 20}], 'domain': 'algorithms'},
        {'title': 'Recursive Tree Depth', 'description': 'Find max depth of nested dict.', 'starter_code': 'def solve(t):\n    return 0', 'test_cases': [{'input': {'a': {'b': 1}}, 'output': 2}], 'domain': 'data'},
        {'title': 'Stock Spanner (Stack)', 'description': 'Consecutive days price <= current.', 'starter_code': 'def solve(p):\n    return [1] * len(p)', 'test_cases': [{'input': [100, 80, 60, 70], 'output': [1, 1, 1, 2]}], 'domain': 'finance'},
        {'title': 'Regex Multi-line Parse', 'description': 'Extract key=value from complex log.', 'starter_code': 'import re\ndef solve(l):\n    return re.findall(r"(\w+)=(\w+)", l)', 'test_cases': [{'input': "id=123 status=ok", 'output': [('id', '123'), ('status', 'ok')]}], 'domain': 'logs'}
    ] * 4
}