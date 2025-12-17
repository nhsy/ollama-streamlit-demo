
import pypdf
import sys
import os

print("pypdf imported successfully")

try:
    with open("app.py", "r") as f:
        compile(f.read(), "app.py", "exec")
    print("app.py syntax check passed")
except Exception as e:
    print(f"app.py syntax check failed: {e}")
    sys.exit(1)
