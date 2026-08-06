import math
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
    if px < loop_start or px >= loop_end: continue
    tx = px // 16
    ty = py // 16
    local_x = px % 16
    arc_data.setdefault((tx, ty), []).append((local_x, py_f, 0))

pixels = arc_data.get((21, 17), [])

harr = [0]*16
tile_bottom_y = 18 * 16

for local_x, surface_y, _angle in pixels:
    h = max(0, min(16, round(tile_bottom_y - surface_y)))
    harr[local_x] = max(harr[local_x], h)

print("pixels:", len(pixels))
print("harr:", harr)
