import sys
import os
import traceback

current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(os.path.join(base_dir, 'ai_engine'))

try:
    from services.ai_service import ai_service
    print("SUCCESS")
except Exception as e:
    with open('err.txt', 'w') as f:
        traceback.print_exc(file=f)
