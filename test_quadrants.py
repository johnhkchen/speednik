import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from speednik.terrain import get_quadrant

for a in [242, 249, 0, 14]:
    print(f"Angle {a:3d} => Quadrant {get_quadrant(a)}")
