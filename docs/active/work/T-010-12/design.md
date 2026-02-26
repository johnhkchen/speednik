# T-010-12 Design: Trajectory Serialization & Metrics

## Decision 1: Where to add velocity_profile

### Option A: Add to runner.py alongside other metrics (Chosen)
All metric functions live in `runner.py` lines 106-187. Adding `_metric_velocity_profile`
there keeps the single-location pattern. The dispatch dict stays as the canonical
registry. Simple, consistent.

### Option B: Separate metrics.py module
The ticket suggests `speednik/scenarios/metrics.py`. However, all metric functions
are already in runner.py and tightly coupled to FrameRecord and SimState from the
same module. Extracting to a separate file adds a module boundary with no benefit —
the functions are small (2-5 lines each) and the dispatch dict needs to reference
them. **Rejected**: unnecessary indirection.

### Decision
Add `_metric_velocity_profile` to runner.py, following the existing pattern. The
ticket's suggested file layout is advisory; the code is already well-organized.

---

## Decision 2: Unknown metric error handling

### Option A: ValueError immediately on unknown name (Chosen)
Change `compute_metrics` to raise `ValueError` when a name isn't in `_METRIC_DISPATCH`.
This is explicitly required by acceptance criteria. Fail-fast catches typos in YAML
scenario files during development.

### Option B: Collect unknown names, raise at end
Slightly more user-friendly (shows all bad names at once). But unnecessary complexity
— YAML files are validated at load time in practice, and the error message from a
single unknown name is clear enough.

### Option C: Keep silent skip
Violates acceptance criteria. Rejected.

### Decision
Option A. Change the `if func is not None` guard to `if func is None: raise ValueError(...)`.
Update `test_unknown_metric_ignored` to `test_unknown_metric_raises`.

---

## Decision 3: velocity_profile and --trajectory coupling

The spec says velocity_profile "returns the full list of x_vel values (large — only
included with --trajectory)". However, the current architecture has metrics computed
by the runner and trajectory inclusion controlled by the output layer.

### Option A: Always compute, let output layer handle size concerns
velocity_profile is a list[float] in the metrics dict. It gets serialized normally.
The `--trajectory` flag controls whether the full FrameRecord list is included, but
metrics are always included. This means velocity_profile always appears in JSON.
This is the simplest approach and matches how compute_metrics works.

### Option B: Special-case velocity_profile in output layer
Strip velocity_profile from metrics when --trajectory is not set. Adds coupling
between the output layer and specific metric names. **Rejected**: breaks
separation of concerns.

### Decision
Option A. velocity_profile is just another metric. If a scenario requests it, it
appears in the metrics dict regardless of --trajectory. The distinction is:
--trajectory controls the full frame-by-frame trajectory array, not individual
metric values. This matches the spec's intent ("velocity_profile metric returns
the full x_vel list") without special-casing.

---

## Decision 4: Test strategy

### New tests needed

1. **_metric_death_count** — Not currently tested. Verify it reads `sim.deaths`.
2. **_metric_stuck_at** — Not currently tested. Two cases: stuck (spread < 2.0)
   and not stuck (spread >= 2.0). Also test with short trajectory (< 120 frames).
3. **_metric_velocity_profile** — New metric, needs test.
4. **Unknown metric ValueError** — Replace `test_unknown_metric_ignored` with
   `test_unknown_metric_raises_valueerror`.
5. **Round-trip serialization** — Save outcomes to JSON, load back, verify all
   top-level fields and metric values match. Use a trajectory with at least one
   FrameRecord to test trajectory round-trip too.
6. **Empty trajectory edge cases** — Verify metrics handle `trajectory=[]`
   gracefully (most return 0.0 or None).

### Test fixtures
Reuse the existing `_make_trajectory()` helper in TestComputeMetrics and `_make_sim()`
helper. For stuck_at, build trajectories with controlled x positions.

---

## Decision 5: Ticket-suggested output.py changes

The ticket mentions extending `save_results` with serialization logic. However,
`save_results` is already complete — it calls `_outcome_to_dict` → `dataclasses.asdict`
→ `json.dumps`. The JSON format already matches the spec exactly:

```json
{
  "name": "...",
  "success": true,
  "reason": "...",
  "frames_elapsed": 1847,
  "wall_time_ms": 42.3,
  "metrics": {...},
  "trajectory": [...]
}
```

No changes needed to output.py.

---

## Summary of Changes

| Change | File | Impact |
|--------|------|--------|
| Add `_metric_velocity_profile` + dispatch entry | runner.py | +6 lines |
| ValueError in `compute_metrics` for unknown names | runner.py | ~3 lines changed |
| Add death_count test | test_scenarios.py | +8 lines |
| Add stuck_at tests (stuck, not stuck, short traj) | test_scenarios.py | +30 lines |
| Add velocity_profile test | test_scenarios.py | +8 lines |
| Fix unknown metric test to expect ValueError | test_scenarios.py | ~5 lines changed |
| Add round-trip serialization test | test_scenarios.py | +25 lines |
| Add empty trajectory edge case tests | test_scenarios.py | +15 lines |
| **Total** | | ~100 lines |
