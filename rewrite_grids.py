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
    
    # We ignore ramp_radius for physical offset and just use it to generate smooth 
    # flat approach tiles that safely "feed" the player by retaining straight physics.
    
    approach_px = approach_tiles * TILE_SIZE
    r_ramp = ramp_radius if ramp_radius else 0
    loop_start = approach_px + r_ramp
    loop_end = loop_start + 2 * radius
    ramp_exit_end = loop_end + r_ramp
    cx = loop_start + radius

    # Flat approach & entry area (all the way to cx, because left wall is pass-through)
    # We extend flat ground under the left half of the loop so the player doesn't fall.
    for tx in range(approach_tiles + r_ramp // TILE_SIZE + radius // TILE_SIZE):
        if (tx, ground_row) not in tiles:
            tiles[(tx, ground_row)] = _flat_tile()
        _fill_below(tiles, tx, ground_row)

    # Exit area flat ground (from cx to the end)
    # The player will exit at cx and run right.
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
        
        # Upper half of loop should not block upward jumps (TOP_ONLY)
        # speednik logic: if it's the upper arc, make it TOP_ONLY or let surface loop rules handle it.
        # Original test expects TOP_ONLY for upper arc? LoopSolidity test says:
        # "upper loop tiles have FULL solidity" in synthetic tests, so we use FULL.
        tile.solidity = FULL
        tile.tile_type = SURFACE_LOOP
        
        for local_x, surface_y, _angle in pixels:
            h = max(0, min(TILE_SIZE, round(tile_bottom_y - surface_y)))
            tile.height_array[local_x] = max(tile.height_array[local_x], h)
            
        mid = pixels[len(pixels) // 2]
        tile.angle = mid[2]

    # Fill below the loop's bottom-most arc tiles to prevent sensor fall-through
    for tx in range(loop_start // TILE_SIZE, loop_end // TILE_SIZE + 1):
        _fill_below(tiles, tx, ground_row)

    return tiles, _wrap(tiles)
'''

with open("speednik/grids.py", "w") as f:
    text = re.sub(r'def build_loop\((.*?)\) -> .*?return tiles, _wrap\(tiles\)', replace_loop, text, flags=re.DOTALL)
    f.write(text)
