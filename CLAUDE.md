# CLAUDE.md

## Project

speednik — A Sonic 2 homage built with Pyxel, managed by uv.

### Build & Run

- **Install dependencies:** `uv sync`
- **Run the game:** `uv run python -m speednik.main`
- **Add a dependency:** `uv add <package>`

### Directory Conventions

```
docs/active/tickets/    # Ticket files (markdown with YAML frontmatter)
docs/active/stories/    # Story files (same frontmatter pattern)
docs/active/work/       # Work artifacts, one subdirectory per ticket ID
```

---

The RDSPI workflow definition is in docs/knowledge/rdspi-workflow.md and is injected into agent context by lisa automatically.
