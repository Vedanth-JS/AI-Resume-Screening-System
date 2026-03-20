import sys
import os
sys.path.append(os.getcwd())

print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

try:
    import app.main
    print("app.main imported successfully")
except Exception as e:
    print(f"Failed to import app.main: {e}")
    import traceback
    traceback.print_exc()

print("\n--- Loaded 'app' modules ---")
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("app"):
        print(f"{mod_name}: {sys.modules[mod_name]}")
