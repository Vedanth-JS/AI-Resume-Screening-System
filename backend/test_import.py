import sys
import os
sys.path.append(os.getcwd())

try:
    from app.api.routes import router
    print("Import successful!")
    print(f"Router: {router}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
