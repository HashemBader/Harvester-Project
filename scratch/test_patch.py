import re
import sys

_orig_re_compile = re.compile

def patched_re_compile(pattern, flags=0):
    if isinstance(pattern, str):
        if '(?i)' in pattern:
            # Move (?i) to the start if it's not there
            if not pattern.startswith('(?i)'):
                pattern = pattern.replace('(?i)', '')
                pattern = '(?i)' + pattern
    return _orig_re_compile(pattern, flags)

re.compile = patched_re_compile

try:
    from PyZ3950 import zoom
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
