tailscale := "/Applications/Tailscale.app/Contents/MacOS/Tailscale"

# Rebuild the game and serve it on 0.0.0.0:8000
up:
    uv run pyxel package . web_entry.py
    zip -d speednik.pyxapp 'speednik/docs/*' 'speednik/CLAUDE.md' 'speednik/justfile' 'speednik/uv.lock'
    uv run pyxel app2html speednik.pyxapp
    @echo "Serving at http://$({{tailscale}} ip -4):8000/speednik.html"
    uv run python -m http.server 8000 --bind 0.0.0.0
