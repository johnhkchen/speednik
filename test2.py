import sys
import os

sys.path.insert(0, os.path.abspath('.'))
import speednik.grids

# monkey patch
orig_build_loop = speednik.grids.build_loop

def patched(*args, **kwargs):
    tiles, wrap = orig_build_loop(*args, **kwargs)
    return tiles, wrap

# actually wait, I can just modify grids.py locally to print arc_data
