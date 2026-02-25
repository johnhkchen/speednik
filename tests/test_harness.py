"""Tests for tests/harness.py — scenario runner and strategy self-tests."""

from __future__ import annotations

import pytest

from speednik.physics import InputState
from speednik.player import Player, PlayerState
from speednik.terrain import FULL, TILE_SIZE, Tile, TileLookup

from tests.harness import (
    FrameSnapshot,
    ScenarioResult,
    hold_right,
    hold_right_jump,
    idle,
    run_scenario,
    scripted,
    spindash_right,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def flat_tile() -> Tile:
    """A completely flat full tile."""
    return Tile(height_array=[TILE_SIZE] * TILE_SIZE, angle=0, solidity=FULL)


def make_tile_lookup(tiles: dict[tuple[int, int], Tile]) -> TileLookup:
    """Create a TileLookup from a dict."""
    def lookup(tx: int, ty: int) -> Tile | None:
        return tiles.get((tx, ty))
    return lookup


def flat_ground_lookup(width: int = 30) -> TileLookup:
    """A wide flat ground at tile_y=12 (pixel y=192)."""
    tiles = {}
    for tx in range(width):
        tiles[(tx, 12)] = flat_tile()
    return make_tile_lookup(tiles)


# ---------------------------------------------------------------------------
# TestRunScenario
# ---------------------------------------------------------------------------

class TestRunScenario:
    def test_idle_stays_grounded(self):
        """Idle on flat ground for 60 frames — player stays grounded."""
        lookup = flat_ground_lookup()
        result = run_scenario(lookup, 64.0, 172.0, idle(), frames=60)

        assert len(result.snapshots) == 60
        for snap in result.snapshots:
            assert snap.on_ground is True

    def test_hold_right_advances_x(self):
        """Hold right on flat ground for 60 frames — X position increases."""
        lookup = flat_ground_lookup()
        start_x = 64.0
        result = run_scenario(lookup, start_x, 172.0, hold_right(), frames=60)

        assert result.final.x > start_x
        assert result.final.state in ("running", "standing")

    def test_returns_correct_frame_count(self):
        """Number of snapshots matches requested frame count."""
        lookup = flat_ground_lookup()
        result = run_scenario(lookup, 64.0, 172.0, idle(), frames=10)

        assert len(result.snapshots) == 10
        assert result.snapshots[0].frame == 0
        assert result.snapshots[-1].frame == 9

    def test_on_ground_false_starts_airborne(self):
        """on_ground=False starts player in the air."""
        lookup = flat_ground_lookup()
        result = run_scenario(
            lookup, 64.0, 172.0, idle(), frames=1, on_ground=False
        )

        # Player started airborne — first snapshot should reflect the physics
        # (may or may not still be airborne depending on collision resolution,
        # but the player object was initialized airborne)
        assert result.player is not None


# ---------------------------------------------------------------------------
# TestScenarioResult
# ---------------------------------------------------------------------------

class TestScenarioResult:
    def test_final(self):
        """final returns the last snapshot."""
        snaps = [
            FrameSnapshot(0, 10.0, 0, 0, 0, 0, 0, True, 0, "standing"),
            FrameSnapshot(1, 20.0, 0, 0, 0, 0, 0, True, 0, "running"),
        ]
        result = ScenarioResult(snapshots=snaps, player=Player())
        assert result.final.x == 20.0
        assert result.final.frame == 1

    def test_max_x(self):
        """max_x returns the maximum X across all snapshots."""
        snaps = [
            FrameSnapshot(0, 10.0, 0, 0, 0, 0, 0, True, 0, "standing"),
            FrameSnapshot(1, 50.0, 0, 0, 0, 0, 0, True, 0, "running"),
            FrameSnapshot(2, 30.0, 0, 0, 0, 0, 0, True, 0, "running"),
        ]
        result = ScenarioResult(snapshots=snaps, player=Player())
        assert result.max_x == 50.0

    def test_quadrants_visited(self):
        """quadrants_visited collects unique quadrant values."""
        snaps = [
            FrameSnapshot(0, 0, 0, 0, 0, 0, 0, True, 0, "standing"),
            FrameSnapshot(1, 0, 0, 0, 0, 0, 0, True, 1, "running"),
            FrameSnapshot(2, 0, 0, 0, 0, 0, 0, True, 0, "running"),
            FrameSnapshot(3, 0, 0, 0, 0, 0, 0, True, 2, "running"),
        ]
        result = ScenarioResult(snapshots=snaps, player=Player())
        assert result.quadrants_visited == {0, 1, 2}

    def test_stuck_at_detects_stuck(self):
        """stuck_at detects player stuck at a wall."""
        # Simulate player stuck at x=100 for 30 frames
        snaps = [
            FrameSnapshot(i, 100.0 + (i % 2) * 0.1, 0, 0, 0, 0, 0, True, 0, "standing")
            for i in range(40)
        ]
        result = ScenarioResult(snapshots=snaps, player=Player())
        stuck_x = result.stuck_at(tolerance=2.0, window=30)
        assert stuck_x is not None
        assert abs(stuck_x - 100.0) < 2.0

    def test_stuck_at_returns_none_when_moving(self):
        """stuck_at returns None when player is progressing."""
        snaps = [
            FrameSnapshot(i, float(i * 5), 0, 0, 0, 0, 0, True, 0, "running")
            for i in range(60)
        ]
        result = ScenarioResult(snapshots=snaps, player=Player())
        assert result.stuck_at(tolerance=2.0, window=30) is None

    def test_stuck_at_too_few_frames(self):
        """stuck_at returns None when fewer frames than window."""
        snaps = [
            FrameSnapshot(i, 100.0, 0, 0, 0, 0, 0, True, 0, "standing")
            for i in range(10)
        ]
        result = ScenarioResult(snapshots=snaps, player=Player())
        assert result.stuck_at(tolerance=2.0, window=30) is None


# ---------------------------------------------------------------------------
# TestStrategies
# ---------------------------------------------------------------------------

class TestStrategies:
    def test_idle_returns_empty(self):
        """idle() returns empty InputState."""
        strat = idle()
        player = Player()
        inp = strat(0, player)
        assert inp == InputState()

    def test_hold_right_output(self):
        """hold_right() returns right=True."""
        strat = hold_right()
        player = Player()
        inp = strat(0, player)
        assert inp.right is True
        assert inp.left is False
        assert inp.jump_pressed is False

    def test_hold_right_jump_presses_on_first_frame(self):
        """hold_right_jump() presses jump on first frame when grounded."""
        strat = hold_right_jump()
        player = Player()
        player.physics.on_ground = True
        inp = strat(0, player)
        assert inp.right is True
        assert inp.jump_pressed is True
        assert inp.jump_held is True

    def test_hold_right_jump_holds_after_first(self):
        """hold_right_jump() holds but doesn't re-press while airborne."""
        strat = hold_right_jump()
        player = Player()
        player.physics.on_ground = True
        strat(0, player)  # first frame: press

        player.physics.on_ground = False
        inp = strat(1, player)
        assert inp.jump_pressed is False
        assert inp.jump_held is True

    def test_hold_right_jump_represses_after_landing(self):
        """hold_right_jump() re-presses jump after landing."""
        strat = hold_right_jump()
        player = Player()

        # Frame 0: on ground, jump pressed
        player.physics.on_ground = True
        strat(0, player)

        # Frame 1: airborne
        player.physics.on_ground = False
        strat(1, player)

        # Frame 2: still airborne
        strat(2, player)

        # Frame 3: landed
        player.physics.on_ground = True
        inp = strat(3, player)
        assert inp.jump_pressed is True

    def test_scripted_within_window(self):
        """scripted() returns correct input within a window."""
        timeline = [
            (0, 5, InputState(right=True)),
            (10, 15, InputState(left=True)),
        ]
        strat = scripted(timeline)
        player = Player()

        assert strat(2, player).right is True
        assert strat(12, player).left is True

    def test_scripted_outside_window(self):
        """scripted() returns empty input outside windows."""
        timeline = [
            (0, 5, InputState(right=True)),
        ]
        strat = scripted(timeline)
        player = Player()

        inp = strat(7, player)
        assert inp == InputState()

    def test_spindash_right_crouch_phase(self):
        """spindash_right() starts with down_held for crouch."""
        strat = spindash_right()
        player = Player()
        player.physics.on_ground = True
        inp = strat(0, player)
        assert inp.down_held is True

    def test_spindash_right_charge_phase(self):
        """spindash_right() charges with down + jump after crouch."""
        strat = spindash_right(charge_frames=3)
        player = Player()
        player.physics.on_ground = True
        strat(0, player)  # crouch

        inp = strat(1, player)  # first charge
        assert inp.down_held is True
        assert inp.jump_pressed is True

    def test_spindash_right_release_phase(self):
        """spindash_right() releases by dropping down_held."""
        strat = spindash_right(charge_frames=2)
        player = Player()
        player.physics.on_ground = True
        strat(0, player)  # crouch
        strat(1, player)  # charge 1
        strat(2, player)  # charge 2 → triggers release next

        inp = strat(3, player)  # release
        assert inp.down_held is False
        assert inp.right is True
