import sys
import os

sys.path.insert(0, os.path.abspath('.'))

import speednik.grids
import math

r = 48
cx = 304
cy = 252

two_pi = 2.0 * math.pi
circumference = int(two_pi * r)
num_samples = max(circumference * 4, 1024)

for i in range(num_samples):
    theta = i * two_pi / num_samples
    px_f = cx + r * math.sin(theta)
    py_f = cy + r * math.cos(theta)
    traversal_angle = round(theta * 256 / two_pi) % 256
    
    px = int(px_f)
    if px >= 348 and px <= 352:
        print(f"px={px} py={int(py_f)} angle={traversal_angle}")

