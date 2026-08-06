import math
import sys
import os

sys.path.insert(0, os.path.abspath('.'))
from speednik.grids import build_loop

# Let's reproduce the exact loop loop in grids.py
tiles = {}
two_pi = 2.0 * math.pi
radius = 48
cx = 304
cy = 252
loop_start = 304 - 48
loop_end = 304 + 48

arc_data = {}
circumference = int(two_pi * radius)
num_samples = max(circumference * 4, 1024)

for i in range(num_samples):
    theta = i * two_pi / num_samples
    px_f = cx + radius * math.sin(theta)
    py_f = cy + radius * math.cos(theta)
    
    px = int(px_f)
    py = int(py_f)
    if px < loop_start or px >= loop_end:
        continue
        
    tx = px // 16
    ty = py // 16
    local_x = px % 16
    if tx == 21 and ty == 17:
        print(f"th={theta:.3f} px={px_f:.2f} ({local_x}) py={py_f:.2f}")

