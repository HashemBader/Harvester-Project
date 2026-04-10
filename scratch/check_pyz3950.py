import sys
try:
    from PyZ3950 import zoom
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
