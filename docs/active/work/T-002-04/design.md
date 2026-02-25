# Design — T-002-04: Skybridge Gauntlet SVG Layout

## Decision: Terrain Representation Strategy

### Option A: All solid ground (`#00AA00`)

Use solid ground polygons for everything, including elevated bridges. Fill everything
below each polygon with solid tiles.

**Rejected.** Elevated platforms over empty pits would fill the entire column below,
creating solid walls where pits should exist. This breaks the stage concept fundamentally.

### Option B: Top-only platforms (`#0000FF`) for bridges, solid for ground

Use top-only platforms for all elevated bridge segments. Use solid ground for the
ramp bases and arena floor only.

**Rejected partially.** Top-only platforms ignore collision when the player moves upward,
which is correct for jump-through behavior but may interfere with ramp launches where
the player needs solid footing during acceleration.

### Option C (Chosen): Hybrid — solid ground for bases + top-only for elevated platforms

- **Solid ground (`#00AA00`):** Ramp structures (sections 2–4), arena floor (section 6),
  low detour path (section 5). These have terrain below them extending to the world bottom.
- **Top-only (`#0000FF`):** Bridge segments (section 1), landing platforms (sections 2–4),
  elevated bridge in path split (section 5). These float above empty space.

**Rationale:** Solid ground provides reliable physics for acceleration and ramp launches.
Top-only platforms enable the "floating bridges over pits" aesthetic without filling columns.
The player only needs to land on these from above, matching top-only semantics exactly.

## Decision: Vertical Layout

### Ground Levels

The 896px height allows vertical layering:

| Level | Y coordinate | Purpose |
|-------|-------------|---------|
| Sky | 0–200 | Empty (visual sky) |
| High platforms | 300–400 | Ascend targets, upper path |
| Main bridge | 480–520 | Primary elevation for sections 1–5 |
| Ramp bases | 520–700 | Solid ground supporting ramp structures |
| Pit floor | 750–800 | Low detour platforms |
| Death zone | 800–896 | Below visible area, not drawn (fall = death in engine) |

**Main bridge surface at y=500.** This leaves 500px of sky above (ample) and 396px
below for pits, detours, and visual depth. Ground fill extends from polygons to y=896.

### Player Start

Place at x=64, y=490 (10px above main bridge surface at y=500). Matches the
hillside pattern of placing the player slightly above ground.

## Decision: Ramp Geometry

### Approach: Separate polygons per ramp

Each ramp is a polygon connecting the main bridge level to the launch angle.
The ramp polygon has its own slope defined by the point positions.

**Ramp geometry formula:**
- Ramp length (horizontal): 160px (10 tiles of acceleration space)
- Rise for 30° ramp: 160 × tan(30°) ≈ 92px → launch point at y ≈ 408
- Rise for 35° ramp: 160 × tan(35°) ≈ 112px → launch point at y ≈ 388
- Rise for 40° ramp: 160 × tan(40°) ≈ 134px → launch point at y ≈ 366

**Landing platforms:** Top-only platforms at the main bridge height (y=500) positioned
after the gap. The player arc from the ramp peak must land on these.

### Approach: Continuous ramp polygons (rejected)

Build ramps as part of the bridge polygon. Rejected because this complicates the
polygon geometry and makes the bridge/ramp/gap boundary harder to control.

## Decision: Section 1 Bridge Design

Narrow bridge segments with gaps between them. All as top-only platforms.

**Layout:**
- Bridge width: 96px per segment (6 tiles)
- Gap widths: 32px, 48px, 64px (escalating)
- Total: 4 bridge segments + 3 gaps = 4×96 + 32 + 48 + 64 = 528px
- Remaining 272px: starting platform (solid, 160px) + final transition (112px)

**Springs:** Place spring_up under each gap for safety recovery.

## Decision: Rhythm Section Structure

Each rhythm section (2, 3, 4) follows the same four-phase pattern:

1. **BUILD zone (200px):** Downhill slope from bridge level to ramp base
2. **LAUNCH (160px):** Ramp ascending at the section's angle
3. **GAP (80/112/144px):** Empty air
4. **CLEAR + ASCEND (remaining):** Landing platform with enemies, bounce platform above

The landing platform is at main bridge level (y=500). The "ascend" target is a
higher platform at y=400, reached by bouncing off the last enemy.

## Decision: Path Split (Section 5)

Two-layer design:

**Upper bridge (y=500):** Main bridge continues. Guardian enemy rect at mid-point.
The guardian blocks passage unless player has spindash speed ≥ 8.

**Lower detour (y=700):** Series of narrow top-only platforms over the pit.
Accessed by dropping off the bridge before the guardian. Reconnects to main
level via spring_up at the end of the detour.

## Decision: Boss Arena (Section 6)

Flat enclosed area. Solid ground polygon from x=4000 to x=5200, y=500 to y=896.
Walls on both sides (solid polygons at x=4000 and x=5200 from y=200 to y=500)
to create the enclosed feel.

20 rings placed in the arena. Goal post at x=5150, y=464.

## Decision: Entity Distribution

| Section | Rings | Enemies | Springs | Checkpoints |
|---------|-------|---------|---------|-------------|
| 1 | 40 | 3 crabs + 1 buzzer | 3 (under gaps) | 0 |
| 2 | 45 | 2 crabs | 1 (under gap) | 1 (at x=780) |
| 3 | 45 | 2 crabs + 1 buzzer | 1 (under gap) | 0 |
| 4 | 50 | 3 crabs + 1 buzzer | 1 (under gap) | 0 |
| 5 | 30 | 1 guardian (crab) + 2 crabs (detour) | 1 (detour exit) | 0 |
| 6 | 20 | 0 (boss is engine entity) | 0 | 1 (at x=3980) |
| **Total** | **230** | **13 + guardian** | **7** | **2** |

Target ~250 rings. Add 20 more distributed across section transitions to reach ~250.

## Decision: Loader Module

Follow `hillside.py` exactly. Only differences:
- Module: `speednik/stages/skybridge.py`
- Data dir: `Path(__file__).parent / "skybridge"`
- Function signature and StageData class remain identical

Reuse the same `StageData` dataclass from hillside.py. Both stages share the
identical return type — only the data differs.

**Alternative considered:** Shared `StageData` in a common module. Rejected for now
because hillside.py defines StageData locally and changing it would modify an existing
file unnecessarily. Can be refactored later if a third stage needs it.

## Decision: Test Strategy

Follow `test_hillside.py` pattern with stage-specific adjustments:

- **TestLoadReturnsStageData** — Same structural checks
- **TestTileLookup** — Check bridge tile at section 1 (known coordinate)
- **TestEntities** — ~250 rings, 2 checkpoints, enemies present, springs present, goal
- **TestPlayerStart** — x=64, y=490
- **TestLevelDimensions** — 5200×896
- **TestBridgeGeometry** — Verify top-only tiles exist at bridge elevation
- **TestRampAngles** — Spot-check that ramp region tiles have non-zero angles
