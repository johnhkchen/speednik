import math

r = 48
cx = 304
cy = 252

for theta_deg in range(0, 181, 10):
    theta = theta_deg * math.pi / 180.0
    px = cx + r * math.sin(theta)
    py = cy + r * math.cos(theta)
    print(f"th={theta_deg:3d}  px={px:6.2f} (tx={int(px)//16} lx={int(px)%16}) py={py:6.2f} (ty={int(py)//16} ly={int(py)%16})")
    
