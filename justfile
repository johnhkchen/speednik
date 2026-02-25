tailscale := "/Applications/Tailscale.app/Contents/MacOS/Tailscale"

# Rebuild the game and serve it on 0.0.0.0:8000
up:
    uv run pyxel package . web_entry.py
    zip -d speednik.pyxapp 'speednik/docs/*' 'speednik/CLAUDE.md' 'speednik/justfile' 'speednik/uv.lock'
    uv run pyxel app2html speednik.pyxapp
    @echo "Serving at http://$({{tailscale}} ip -4):8080/speednik.html"
    uv run python -m http.server 8080 --bind 0.0.0.0

# Run the game locally with debug HUD and dev park enabled
debug:
    SPEEDNIK_DEBUG=1 uv run python -m speednik.main
