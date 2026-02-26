# T-010-17 Design: full-observation-vector

## Decision 1: How to parameterize observation dimensionality

### Option A: Two separate functions

`extract_observation_12(sim)` and `extract_observation_26(sim)`. Env picks which to call.

- Pro: No branching, clear contracts.
- Con: Code duplication for the shared 12-dim base. Two public functions to maintain.

### Option B: Single function with boolean parameter

`extract_observation(sim, use_raycasts=True)`. When True, appends raycast data.

- Pro: Single function, shared base logic, clean interface.
- Con: Caller must know the parameter. Slight branch cost.

### Option C: Single function, OBS_DIM determines behavior

OBS_DIM is set globally; function checks it.

- Con: Global mutable state. Two environments in the same process would conflict.

**Decision: Option B.** Single function with `use_raycasts` parameter. The base 12 dims
are always computed; raycast dims are appended conditionally. The `OBS_DIM` constant
becomes a function of `use_raycasts`, so we export two constants or a helper. Simplest:
export `OBS_DIM_FULL = 26` and `OBS_DIM_BASE = 12`, keep `OBS_DIM = 26` as the default.

Actually, simpler: make OBS_DIM remain the single constant but set it to 26 (the new
default). The env computes `obs_dim = 26 if use_raycasts else 12` locally. Tests that
import OBS_DIM will see 26, which is the new default.

## Decision 2: How the env passes use_raycasts to extract_observation

### Option A: Pass use_raycasts to extract_observation

Env stores `self.use_raycasts` and calls `extract_observation(self.sim, use_raycasts=self.use_raycasts)`.

### Option B: Two observation functions

Env picks which function to call based on `self.use_raycasts`.

**Decision: Option A.** Cleanest — single call site, parameter propagates naturally.

## Decision 3: extract_observation signature change

The function currently takes only `sim: SimState`. With raycasts, it needs `tile_lookup`
for `cast_terrain_ray`. But `sim.tile_lookup` is already accessible from the SimState.
So no additional parameter is needed — the function extracts `tile_lookup` from `sim`.

The only new parameter is `use_raycasts: bool = True`.

## Decision 4: Raycast implementation in extract_observation

The ticket provides the exact code. Key points:

- 7 rays at angles `[-45, -30, -15, 0, 15, 30, 45]`.
- Ray origin: `(p.x, p.y - 8)` — player center (half-height offset).
- Facing-left flip: `effective_angle = 180 - angle_deg`.
- Max range: 128.0 (local constant, not exported).
- Distance normalized by 128.0, surface angle by 255.0.
- Fill indices 12-25.

This is a direct translation of the ticket pseudocode. No design ambiguity.

## Decision 5: OBS_DIM constant

Change `OBS_DIM = 12` to `OBS_DIM = 26`. This is the new default. The env uses
`obs_dim = OBS_DIM if self.use_raycasts else 12` for observation_space shape.

We also export `OBS_DIM_BASE = 12` for backward compat assertions.

## Decision 6: NoRay registration variants

Add `-NoRay-v0` for each stage: `speednik/Hillside-NoRay-v0`, `speednik/Pipeworks-NoRay-v0`,
`speednik/Skybridge-NoRay-v0`. These pass `use_raycasts=False`.

## Decision 7: Test updates

- Existing `test_obs_dim_constant` → assert OBS_DIM == 26.
- Existing `test_observation_shape_and_dtype` → assert shape == (26,).
- Existing tests that check indices 0-11 remain valid (values don't change).
- Add tests: raycast indices 12-25 produce finite values, correct range.
- Add test: use_raycasts=False produces 12-dim.
- Add test: facing_left flips ray direction.
- Add env tests: NoRay variant, check_env with 26-dim, observations finite 1000 steps.

## Decision 8: What NOT to do

- Baseline regeneration (mentioned in ticket) is informational, not gated. We skip it
  since there's no baseline infrastructure to re-run.
- PPO smoke test (10K steps): if the training script exists, run it; otherwise document
  as manual verification.
- Learning curve comparison: informational only, skip.

## Rejected Approaches

- **DDA raycasting**: Already rejected in T-010-16. Step-based is sufficient.
- **Separate raycast observation module**: Over-engineering. Raycasts are 15 lines inside
  `extract_observation`.
- **Lazy raycast computation**: Not worth the complexity. 7 rays at 128 steps is <1ms.
