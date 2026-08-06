# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "Pillow",
#     "numpy",
#     "scipy",
#     "opencv-python",
#     "rembg[cpu]",
# ]
# ///

import os
import sys
import numpy as np
import cv2
from PIL import Image
from scipy.spatial.distance import cdist
import rembg
import argparse

# Pyxel strict 16-color palette
PYXEL_PALETTE = [
    (0, 0, 0),        # 0: Black
    (29, 43, 83),     # 1: Dark Blue
    (126, 37, 83),    # 2: Dark Purple
    (0, 135, 81),     # 3: Dark Green
    (171, 82, 54),    # 4: Brown
    (95, 87, 79),     # 5: Dark Gray
    (194, 195, 199),  # 6: Light Gray
    (255, 241, 232),  # 7: White
    (255, 0, 77),     # 8: Red
    (255, 163, 0),    # 9: Orange
    (255, 236, 39),   # 10: Yellow
    (0, 228, 54),     # 11: Green
    (41, 173, 255),   # 12: Blue
    (131, 118, 156),  # 13: Indigo
    (255, 119, 168),  # 14: Pink
    (255, 204, 170)   # 15: Peach
]

def map_to_palette(img_array: np.ndarray) -> np.ndarray:
    """Takes an RGBA numpy array, quantizes RGB channels to the nearest Pyxel palette color."""
    h, w, c = img_array.shape
    if c != 4:
        raise ValueError("Image must have 4 channels (RGBA)")
    
    pixels = img_array[:, :, :3].reshape(-1, 3)
    palette = np.array(PYXEL_PALETTE)
    
    # Calculate nearest palette color
    dists = cdist(pixels, palette)
    nearest_idx = np.argmin(dists, axis=1)
    
    quantized_pixels = palette[nearest_idx]
    quantized_img = quantized_pixels.reshape((h, w, 3))
    
    # Put alpha back
    out = np.zeros_like(img_array)
    out[:, :, :3] = quantized_img
    
    # Threshold alpha
    out[:, :, 3] = np.where(img_array[:, :, 3] > 128, 255, 0)
    
    # Pyxel convention: if transparent, set RGB to black so it doesn't bleed during scaling
    out[out[:, :, 3] == 0, :3] = 0
    
    return out

def process_spritesheet(input_path, output_dir, target_size=24, padding=4):
    print(f"Loading {input_path}...")
    img = Image.open(input_path).convert("RGBA")
    
    print("Removing background with rembg...")
    no_bg_img = rembg.remove(img)
    
    arr = np.array(no_bg_img)
    
    # Get alpha mask
    alpha = arr[:, :, 3]
    _, mask = cv2.threshold(alpha, 128, 255, cv2.THRESH_BINARY)
    
    print("Finding individual sprites...")
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    bboxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 15 and h > 15:  # Ignore small noise
            bboxes.append((x, y, w, h))
            
    # Sort bounding boxes top to bottom, then left to right
    # AI spritesheets usually contain rows of sprites.
    # Group by rows of arbitrary pixel height (e.g. 100 px) to sort them well.
    if bboxes:
        avg_h = sum(b[3] for b in bboxes) / len(bboxes)
        row_height = max(10, avg_h * 0.8)
        bboxes.sort(key=lambda b: (int(b[1] / row_height), b[0]))
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Found {len(bboxes)} sprites. Processing & resizing to {target_size}x{target_size}...")
    
    frames = []
    
    for i, (x, y, w, h) in enumerate(bboxes):
        sprite = arr[y:y+h, x:x+w]
        
        # We need to pad it to square to maintain aspect ratio perfectly when resizing
        size = max(w, h) + padding * 2
        padded = np.zeros((size, size, 4), dtype=np.uint8)
        
        # Center horizontally, anchor to bottom vertically so feet align
        off_x = (size - w) // 2
        off_y = size - padding - h
        
        padded[off_y:off_y+h, off_x:off_x+w] = sprite
        
        # Resize to Pyxel size (nearest neighbor to keep crisp)
        resized = cv2.resize(padded, (target_size, target_size), interpolation=cv2.INTER_NEAREST)
        
        # Quantize Colors
        quantized = map_to_palette(resized)
        
        out_img = Image.fromarray(quantized, 'RGBA')
        frame_name = f"frame_{i:02d}.png"
        out_path = os.path.join(output_dir, frame_name)
        out_img.save(out_path)
        frames.append(frame_name)
        
    print(f"Saved {len(frames)} frames to {output_dir}/")
    
    html_path = os.path.join(output_dir, "review.html")
    with open(html_path, "w") as f:
        f.write("<html><head><style>")
        f.write("body { background: #222; color: #eee; font-family: monospace; }")
        f.write(".grid { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 20px; }")
        f.write(".grid img { image-rendering: pixelated; width: 64px; height: 64px; border: 1px solid #444; background: #333; }")
        f.write("#anim { image-rendering: pixelated; width: 128px; height: 128px; border: 2px solid #fff; background: #333; }")
        f.write("</style></head><body>")
        
        f.write("<h2>Animation Preview</h2>")
        f.write("<img id='anim' src=''>")
        f.write("<br><br>")
        f.write("<button onclick='play()'>Play</button> <button onclick='pause()'>Pause</button> ")
        f.write("Speed (ms): <input type='range' id='speed' min='20' max='300' value='100' onchange='updateSpeed()'>")
        f.write(" | Frame: <span id='framenum'>0</span>")
        
        f.write("<h2>Individual Frames</h2>")
        f.write("<div class='grid'>")
        for i, frame in enumerate(frames):
            f.write(f"<div><img src='{frame}' title='{frame}' onclick='setFrame({i})'><br>{frame}</div>")
        f.write("</div>")
        
        f.write("<script>")
        # Convert frames list to valid JS array
        frames_js = "[" + ",".join([f"'{fr}'" for fr in frames]) + "]"
        f.write(f"const frames = {frames_js};")
        f.write("""
        let currentFrame = 0;
        let interval = null;
        let speed = 100;
        
        function updateAnim() {
            if (frames.length > 0) {
                document.getElementById('anim').src = frames[currentFrame];
                document.getElementById('framenum').innerText = currentFrame;
                currentFrame = (currentFrame + 1) % frames.length;
            }
        }
        function setFrame(i) {
            pause();
            currentFrame = i;
            document.getElementById('anim').src = frames[currentFrame];
            document.getElementById('framenum').innerText = currentFrame;
        }
        function play() {
            if (!interval) interval = setInterval(updateAnim, speed);
        }
        function pause() {
            if (interval) { clearInterval(interval); interval = null; }
        }
        function updateSpeed() {
            speed = parseInt(document.getElementById('speed').value);
            if (interval) { pause(); play(); }
        }
        
        if (frames.length > 0) {
            document.getElementById('anim').src = frames[0];
            play();
        }
        """)
        f.write("</script></body></html>")
        
    print(f"Generated playback review page at {html_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert AI Spritesheets to Pyxel Frames")
    parser.add_argument("input", help="Path to input AI spritesheet PNG")
    parser.add_argument("output_dir", help="Directory to save the extracted frames")
    parser.add_argument("--size", type=int, default=32, help="Target uniform Pyxel sprite size (default: 32)")
    parser.add_argument("--pad", type=int, default=4, help="Internal padding before resizing (default: 4)")
    
    args = parser.parse_args()
    process_spritesheet(args.input, args.output_dir, args.size, args.pad)
