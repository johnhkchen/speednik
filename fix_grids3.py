import re
with open("speednik/grids.py", "r") as f:
    text = f.read()

def replace_loop(match):
    return '''def build_loop(
    approach_tiles: int,
    radius: int,
    ground_row: int,
    ramp_radius: int | None = None,
) -> tuple[dict[tuple[int, int], Tile], TileLookup]:
    tiles: dict[tuple[int, int], Tile] = {}
    two_pi = 2.0 * math.pi

    ground_y = ground_row * TILE_SIZE
    cy = ground_y - radius
    
    approach_px = approach_tiles * TILE_SIZE
    r_ramp = ramp_radius if ramp_radius else 0
    loop_start = approach_px + r_ramp
    loop_end = loop_start + 2 * radius
    ramp_exit_end = loop_end + r_ramp
    cx = loop_start + radius

    # Flat approach & entry area 
    for tx in range(approach_tiles + r_ramp // TILE_SIZE + radius // TILE_SIZE):
        if (tx, ground_row) not in tiles:
            tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # Exit area flat ground 
    exit_start_tx = cx // TILE_SIZE
    total_tx = (ramp_exit_end + approach_px) // TILE_SIZE + 5
    for tx in range(exit_start_tx, total_tx + 5):
        if (tx, ground_row) not in tiles:
            tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # Loop circle - precise physical placement
    arc_data: dict[tuple[int, int], list[tuple[int, float, int]]] = {}
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
            
        tx = px // TILE_SIZE
        ty = py // TILE_SIZE
        local_x = px % TILE_SIZE
        
        # Physics engine defines tile.angle as surface angle.
        traversal_angle = round(theta * 256 / two_pi) % 256
        arc_data.setdefault((tx, ty), []).append((local_x, py_f, traversal_angle))

    for key, pixels in arc_data.items():
        tx, ty = key
        tile_bottom_y = (ty + 1) * TILE_SIZE
        
        if key not in tiles:
            tiles[key] = Tile(
                height_array=[0] * TILE_SIZE, angle=0,
                solidity=FULL, tile_type=SURFACE_LOOP,
            )
        tile = tiles[key]
        tile.solidity = FULL
        tile.tile_type = SURFACE_LOOP
        
        for local_x, surface_y, _angle in pixels:
            h = max(0, min(TILE_SIZE, round(tile_bottom_y - surface_y)))
            tile.height_array[local_x] = max(tile.height_array[local_x], h)
            
        # Fix 1-pixel walls using horizontal fill outward from the circle center
        px_mid = tx * TILE_SIZE + 8
        if px_mid > cx:
            min_lx = min(p[0] for p in pixels)
            h = tile.height_array[min_lx]
            for lx in range(min_lx, TILE_SIZE):
                tile.height_array[lx] = max(tile.height_array[lx], h)
        else:
            max_lx = max(p[0] for p in pixels)
            h = tile.height_array[max_lx]
            for lx in range(0, max_lx + 1):
                tile.height_array[lx] = max(tile.height_array[lx], h)

        # Average the angle properly over the sampled arc, 
        # protecting against wrapping (0 and 255)
        sin_sum = 0.0
        cos_sum = 0.0
        for _, _, ang in pixels:
            rad = ang * two_pi / 256.0
            sin_sum += math.sin(rad)
            cos_sum += math.cos(rad)
        avg_rad = math.atan2(sin_sum, cos_sum)
        tile.angle = round(avg_rad * 256 / two_pi) % 256

    # Fill external columns entirely so they block horizontal clipping completely
    for ty in range((cy - radius) // TILE_SIZE, (cy + radius) // TILE_SIZE + 1):
        # Left wall fill
        l_tx = loop_start // TILE_SIZE
        if (l_tx, ty) in tiles:
            h = tiles[l_tx, ty].height_array[0]
            for fill_tx in range(l_tx - FILL_DEPTH, l_tx):
                if (fill_tx, ty) not in tiles:
                    tiles[fill_tx, ty] = Tile([h]*16, 0, FULL, SURFACE_LOOP)
        # Right wall fill
        r_tx = loop_end // TILE_SIZE - 1
        if (r_tx, ty) in tiles:
            h = tiles[r_tx, ty].height_array[15]
            for fill_tx in range(r_tx + 1, r_tx + 1 + FILL_DEPTH):
                if (fill_tx, ty) not in tiles:
                    tiles[fill_tx, ty] = Tile([h]*16, 0, FULL, SURFACE_LOOP)

    return tiles, _wrap(tiles)
'''

with open("speednik/grids.py", "w") as f:
    text = re.sub(r'def build_loop\((.*?)\) -> .*?return tiles, _wrap\(tiles\)', replace_loop, text, flags=re.DOTALL)
    f.write(text)
