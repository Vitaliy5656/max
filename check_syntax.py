import sys
import os
import importlib

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

modules_to_check = [
    "src.core.cognitive.ensemble_types",
    "src.core.cognitive.ensemble_prompts",
    "src.core.cognitive.cpo_engine",
    "src.core.cognitive.ensemble_loop",
    "src.api.routers.chat",
]

print("Checking imports...")

for module_name in modules_to_check:
    try:
        print(f"Importing {module_name}...", end=" ")
        importlib.import_module(module_name)
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

print("Import check complete.")
