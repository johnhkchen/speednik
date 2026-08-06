import math

with open("speednik/grids.py") as f:
    text = f.read()
    
print("Found arc_data loop:")
import re
match = re.search(r'arc_data: dict.*?\n\s+for i in range.*?return tiles', text, re.DOTALL)
if match:
    print(match.group(0))
else:
    print("Not found")
