# T-011-02 Design: physics-invariant-checker

## Decision: FrameSnapshot import strategy

### Options

1. **Import from tests.harness** — `from tests.harness import FrameSnapshot`
   - Pro: Zero duplication, exact same type.
   - Con: Production code importing from tests/ is a code smell. Works only when
     tests/ is on sys.path (true in pytest, may break in other contexts).

2. **Define a Protocol in speednik/invariants.py** — duck-type the snapshot
   - Pro: Clean boundary. No import from tests. Works with any snapshot-like object
     (FrameSnapshot, FrameRecord, etc.).
   - Con: Slightly more code. Users see Protocol in signatures rather than concrete type.

3. **Move FrameSnapshot to speednik/** — relocate the canonical definition
   - Pro: Clean imports everywhere.
   - Con: Large refactor touching many files. Out of scope for this ticket.

**Decision: Option 2 — Protocol.** Define `SnapshotLike` with the required attributes.
The function accepts `Sequence[SnapshotLike]`. Both `FrameSnapshot` and `FrameRecord`
satisfy the protocol automatically. This keeps the import boundary clean and makes the
checker maximally reusable.

## Decision: Checker architecture

### Options

A. **Single monolithic function** — one `check_invariants()` that loops over snapshots
   and checks everything inline.
   - Pro: Simple, easy to read.
   - Con: Hard to extend, long function body.

B. **Registry of individual check functions** — each invariant is a small function,
   a dispatcher calls all of them.
   - Pro: Extensible, each check is independently testable.
   - Con: Heavier abstraction for a handful of checks.

C. **List of checker functions, called sequentially** — middle ground. Each check is a
   standalone function, `check_invariants` calls them all and aggregates results.
   - Pro: Clean separation without over-engineering. Easy to add/remove checks.
   - Con: Slightly more boilerplate than monolithic.

**Decision: Option C.** Each invariant category (position, velocity, state) is a
private function that returns `list[Violation]`. `check_invariants` calls all of them
and concatenates. No registry — just explicit calls. This keeps it simple while
maintaining separation.

## Decision: Velocity spike threshold

The ticket says "no single-frame velocity spike" unless spring/spindash occurred.
Need to define what counts:
- Springs set vel to ±10.0
- Spindash sets ground_speed up to 12.0
- Normal acceleration is ~0.05-0.5 per frame

A `|delta_vel|` threshold of 12.0 (magnitude of velocity change vector) is generous
enough to allow springs and spindashes without triggering, but catches teleportation
bugs. The ticket only mentions `SpringEvent` for excusal — we'll also check for
spindash state transitions (state was "spindash" on previous frame and isn't now =
spindash release).

**Decision: delta_vel threshold = 12.0 per axis. Excused by SpringEvent or spindash
release (prev state == "spindash" and current != "spindash").**

## Decision: on_ground validation depth

Full sensor cast validation would require reimplementing terrain.py logic. That's
fragile and duplicative.

**Decision: Lightweight check.** When `on_ground=True`, verify the tile at
`(x, y + height_radius)` is not `None` or `NOT_SOLID`. This catches floating-in-air
bugs without reimplementing sensor logic. Use STANDING_HEIGHT_RADIUS (20) as the
offset. This is a warning, not an error, since edge cases exist (slope transitions,
etc.).

## Decision: Dead state validation

Ticket says "DEAD only if rings were 0 at time of damage OR fell out of bounds."
FrameSnapshot doesn't carry `rings` count. SimState has it but only at the current
frame. We can't retroactively check what rings were at the damage frame from the
snapshot list alone.

**Decision: Skip the rings-at-damage check.** The snapshot doesn't carry ring count.
We can still check the "fell out of bounds" case: if state == "dead" and the last
non-dead position was within bounds, flag it as a warning (informational, not
necessarily a bug since damage could have occurred). This is a known limitation.

## Invariants summary

| Invariant | Severity | Excusal |
|-----------|----------|---------|
| x < 0 | error | none |
| y > level_height + 64 | error | none |
| x > level_width + 64 | error | none |
| inside solid tile | error | none |
| \|x_vel\| > 20.0 | error | none |
| \|y_vel\| > 20.0 | error | none |
| velocity spike > 12.0/axis | warning | SpringEvent, spindash release |
| on_ground with no surface | warning | none |
| quadrant diagonal jump | warning | none |
