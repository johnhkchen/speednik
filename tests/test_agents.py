"""Tests for speednik/agents — Agent protocol, action space, and programmed agents."""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

from speednik.agents import (
    ACTION_DOWN,
    ACTION_DOWN_JUMP,
    ACTION_JUMP,
    ACTION_LEFT,
    ACTION_LEFT_JUMP,
    ACTION_MAP,
    ACTION_NOOP,
    ACTION_RIGHT,
    ACTION_RIGHT_JUMP,
    AGENT_REGISTRY,
    NUM_ACTIONS,
    Agent,
    HoldRightAgent,
    IdleAgent,
    JumpRunnerAgent,
    ScriptedAgent,
    SpindashAgent,
    action_to_input,
    resolve_agent,
)
from speednik.observation import extract_observation
from speednik.physics import InputState
from speednik.simulation import create_sim, sim_step


# ---------------------------------------------------------------------------
# Agent protocol
# ---------------------------------------------------------------------------

class _GoodAgent:
    def act(self, obs: np.ndarray) -> int:
        return 0

    def reset(self) -> None:
        pass


class _BadAgent:
    def reset(self) -> None:
        pass


def test_agent_protocol_conformance():
    agent = _GoodAgent()
    assert isinstance(agent, Agent)


def test_agent_protocol_rejects_incomplete():
    agent = _BadAgent()
    assert not isinstance(agent, Agent)


# ---------------------------------------------------------------------------
# Action constants
# ---------------------------------------------------------------------------

def test_action_constants_range():
    actions = [
        ACTION_NOOP, ACTION_LEFT, ACTION_RIGHT, ACTION_JUMP,
        ACTION_LEFT_JUMP, ACTION_RIGHT_JUMP, ACTION_DOWN, ACTION_DOWN_JUMP,
    ]
    assert sorted(actions) == list(range(8))


def test_num_actions_matches_map():
    assert NUM_ACTIONS == len(ACTION_MAP)
    assert NUM_ACTIONS == 8


# ---------------------------------------------------------------------------
# ACTION_MAP
# ---------------------------------------------------------------------------

def test_action_map_completeness():
    for i in range(NUM_ACTIONS):
        assert i in ACTION_MAP
        assert isinstance(ACTION_MAP[i], InputState)


def test_action_map_noop():
    inp = ACTION_MAP[ACTION_NOOP]
    assert not inp.left
    assert not inp.right
    assert not inp.jump_pressed
    assert not inp.jump_held
    assert not inp.down_held
    assert not inp.up_held


def test_action_map_directional():
    left = ACTION_MAP[ACTION_LEFT]
    assert left.left and not left.right and not left.jump_held

    right = ACTION_MAP[ACTION_RIGHT]
    assert right.right and not right.left and not right.jump_held

    down = ACTION_MAP[ACTION_DOWN]
    assert down.down_held and not down.left and not down.right and not down.jump_held


def test_action_map_jump_actions():
    for action in [ACTION_JUMP, ACTION_LEFT_JUMP, ACTION_RIGHT_JUMP, ACTION_DOWN_JUMP]:
        inp = ACTION_MAP[action]
        assert inp.jump_pressed, f"action {action} template should have jump_pressed"
        assert inp.jump_held, f"action {action} template should have jump_held"


# ---------------------------------------------------------------------------
# action_to_input
# ---------------------------------------------------------------------------

def test_action_to_input_noop():
    inp, prev = action_to_input(ACTION_NOOP, False)
    assert not inp.left
    assert not inp.right
    assert not inp.jump_pressed
    assert not inp.jump_held
    assert not inp.down_held
    assert prev is False


def test_action_to_input_jump_first_frame():
    inp, prev = action_to_input(ACTION_JUMP, False)
    assert inp.jump_pressed is True, "First frame of jump should set jump_pressed"
    assert inp.jump_held is True
    assert prev is True


def test_action_to_input_jump_held_frame():
    inp, prev = action_to_input(ACTION_JUMP, True)
    assert inp.jump_pressed is False, "Held frame should NOT set jump_pressed"
    assert inp.jump_held is True
    assert prev is True


def test_action_to_input_jump_release():
    # Frame 1: jump
    _, prev = action_to_input(ACTION_JUMP, False)
    assert prev is True

    # Frame 2: noop (release)
    inp, prev = action_to_input(ACTION_NOOP, prev)
    assert not inp.jump_held
    assert not inp.jump_pressed
    assert prev is False

    # Frame 3: jump again (should be pressed)
    inp, prev = action_to_input(ACTION_JUMP, prev)
    assert inp.jump_pressed is True
    assert prev is True


def test_action_to_input_directional_jump():
    inp, prev = action_to_input(ACTION_LEFT_JUMP, False)
    assert inp.left is True
    assert inp.jump_pressed is True
    assert inp.jump_held is True
    assert prev is True

    inp, prev = action_to_input(ACTION_RIGHT_JUMP, False)
    assert inp.right is True
    assert inp.jump_pressed is True
    assert inp.jump_held is True

    inp, prev = action_to_input(ACTION_DOWN_JUMP, False)
    assert inp.down_held is True
    assert inp.jump_pressed is True
    assert inp.jump_held is True


def test_action_to_input_right():
    inp, prev = action_to_input(ACTION_RIGHT, False)
    assert inp.right is True
    assert not inp.left
    assert not inp.jump_held
    assert prev is False


# ---------------------------------------------------------------------------
# No Pyxel imports (existing modules)
# ---------------------------------------------------------------------------

def test_no_pyxel_import_base():
    from speednik.agents import base
    source = Path(inspect.getfile(base)).read_text()
    assert "import pyxel" not in source
    assert "from pyxel" not in source


def test_no_pyxel_import_actions():
    from speednik.agents import actions
    source = Path(inspect.getfile(actions)).read_text()
    assert "import pyxel" not in source
    assert "from pyxel" not in source


# ===========================================================================
# T-010-05: Programmed agents
# ===========================================================================

# ---------------------------------------------------------------------------
# Protocol conformance — all 5 agents pass isinstance(agent, Agent)
# ---------------------------------------------------------------------------

def test_idle_agent_protocol():
    agent = IdleAgent()
    assert isinstance(agent, Agent)


def test_hold_right_agent_protocol():
    agent = HoldRightAgent()
    assert isinstance(agent, Agent)


def test_jump_runner_agent_protocol():
    agent = JumpRunnerAgent()
    assert isinstance(agent, Agent)


def test_spindash_agent_protocol():
    agent = SpindashAgent()
    assert isinstance(agent, Agent)


def test_scripted_agent_protocol():
    agent = ScriptedAgent(timeline=[])
    assert isinstance(agent, Agent)


# ---------------------------------------------------------------------------
# Behavioral correctness
# ---------------------------------------------------------------------------

def _make_obs(**overrides) -> np.ndarray:
    """Build a 12-dim obs vector with sensible defaults and overrides."""
    obs = np.zeros(12, dtype=np.float32)
    obs[4] = 1.0   # on_ground
    obs[7] = 1.0   # facing_right
    for key, val in overrides.items():
        obs[int(key)] = val
    return obs


def test_idle_agent_always_noop():
    agent = IdleAgent()
    obs = _make_obs()
    for _ in range(10):
        assert agent.act(obs) == ACTION_NOOP


def test_hold_right_agent_always_right():
    agent = HoldRightAgent()
    obs = _make_obs()
    for _ in range(10):
        assert agent.act(obs) == ACTION_RIGHT


def test_jump_runner_agent_jumps_on_first_call():
    agent = JumpRunnerAgent()
    obs = _make_obs()  # on_ground=1.0
    assert agent.act(obs) == ACTION_RIGHT_JUMP


def test_jump_runner_agent_runs_when_airborne():
    agent = JumpRunnerAgent()
    obs_ground = _make_obs()
    obs_air = _make_obs(**{"4": 0.0})

    # First call: jump
    agent.act(obs_ground)
    # Now airborne
    assert agent.act(obs_air) == ACTION_RIGHT
    assert agent.act(obs_air) == ACTION_RIGHT


def test_jump_runner_agent_jumps_on_landing():
    agent = JumpRunnerAgent()
    obs_ground = _make_obs()
    obs_air = _make_obs(**{"4": 0.0})

    # First call: jump
    agent.act(obs_ground)
    # Go airborne for a few frames
    agent.act(obs_air)
    agent.act(obs_air)
    # Land
    assert agent.act(obs_ground) == ACTION_RIGHT_JUMP


def test_jump_runner_reset():
    agent = JumpRunnerAgent()
    obs_ground = _make_obs()
    agent.act(obs_ground)  # consume first call
    agent.reset()
    # After reset, first call should jump again
    assert agent.act(obs_ground) == ACTION_RIGHT_JUMP


def test_spindash_agent_phase_sequence():
    agent = SpindashAgent(charge_frames=2, redash_speed=0.125)
    obs = _make_obs()

    # Phase 1: CROUCH → ACTION_DOWN
    assert agent.act(obs) == ACTION_DOWN
    # Phase 2: CHARGE (frame 1) → ACTION_DOWN_JUMP
    assert agent.act(obs) == ACTION_DOWN_JUMP
    # Phase 2: CHARGE (frame 2, hits charge_frames) → ACTION_DOWN_JUMP
    assert agent.act(obs) == ACTION_DOWN_JUMP
    # Phase 3: RELEASE → ACTION_RIGHT
    assert agent.act(obs) == ACTION_RIGHT
    # Phase 4: RUN — on_ground=True, ground_speed=0, not rolling → re-dash
    assert agent.act(obs) == ACTION_DOWN


def test_spindash_agent_runs_at_speed():
    agent = SpindashAgent(charge_frames=1, redash_speed=0.125)
    # Fast obs: ground_speed above threshold
    obs_fast = _make_obs(**{"5": 0.5})

    # Burn through CROUCH → CHARGE → RELEASE
    agent.act(obs_fast)  # CROUCH
    agent.act(obs_fast)  # CHARGE (1 frame, hits limit)
    agent.act(obs_fast)  # RELEASE
    # Now RUN with high speed — should stay running
    assert agent.act(obs_fast) == ACTION_RIGHT
    assert agent.act(obs_fast) == ACTION_RIGHT


def test_spindash_agent_no_redash_while_rolling():
    agent = SpindashAgent(charge_frames=1, redash_speed=0.125)
    # Slow but rolling
    obs_rolling = _make_obs(**{"5": 0.0, "6": 1.0})

    # Burn through to RUN
    agent.act(obs_rolling)  # CROUCH
    agent.act(obs_rolling)  # CHARGE
    agent.act(obs_rolling)  # RELEASE
    # RUN: slow + rolling → should NOT re-dash
    assert agent.act(obs_rolling) == ACTION_RIGHT


def test_spindash_agent_reset():
    agent = SpindashAgent(charge_frames=1)
    obs = _make_obs()
    agent.act(obs)  # CROUCH
    agent.act(obs)  # CHARGE
    agent.reset()
    # After reset, should start at CROUCH again
    assert agent.act(obs) == ACTION_DOWN


def test_spindash_agent_custom_params():
    agent = SpindashAgent(charge_frames=5, redash_speed=0.5)
    assert agent.charge_frames == 5
    assert agent.redash_speed == 0.5


def test_scripted_agent_timeline_playback():
    timeline = [
        (0, 5, ACTION_RIGHT),
        (5, 10, ACTION_RIGHT_JUMP),
        (15, 20, ACTION_DOWN),
    ]
    agent = ScriptedAgent(timeline=timeline)

    # Frames 0-4: RIGHT
    for _ in range(5):
        assert agent.act(_make_obs()) == ACTION_RIGHT

    # Frames 5-9: RIGHT_JUMP
    for _ in range(5):
        assert agent.act(_make_obs()) == ACTION_RIGHT_JUMP

    # Frames 10-14: no matching window → NOOP
    for _ in range(5):
        assert agent.act(_make_obs()) == ACTION_NOOP

    # Frames 15-19: DOWN
    for _ in range(5):
        assert agent.act(_make_obs()) == ACTION_DOWN


def test_scripted_agent_reset():
    timeline = [(0, 3, ACTION_RIGHT)]
    agent = ScriptedAgent(timeline=timeline)

    for _ in range(3):
        agent.act(_make_obs())
    # Frame 3: past the window
    assert agent.act(_make_obs()) == ACTION_NOOP

    agent.reset()
    # After reset: frame 0 again
    assert agent.act(_make_obs()) == ACTION_RIGHT


def test_scripted_agent_empty_timeline():
    agent = ScriptedAgent(timeline=[])
    assert agent.act(_make_obs()) == ACTION_NOOP


# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------

def test_registry_contains_all_agents():
    expected = {"idle", "hold_right", "jump_runner", "spindash", "scripted"}
    actual = set(AGENT_REGISTRY.keys())
    # "ppo" is present only when torch is installed
    assert actual - {"ppo"} == expected
    if "ppo" in actual:
        import torch  # noqa: F401 — confirms torch is available when ppo is registered


def test_resolve_agent_hold_right():
    agent = resolve_agent("hold_right")
    assert isinstance(agent, HoldRightAgent)
    assert isinstance(agent, Agent)


def test_resolve_agent_with_params():
    agent = resolve_agent("spindash", {"charge_frames": 5})
    assert isinstance(agent, SpindashAgent)
    assert agent.charge_frames == 5


def test_resolve_agent_scripted_with_timeline():
    timeline = [(0, 10, ACTION_RIGHT)]
    agent = resolve_agent("scripted", {"timeline": timeline})
    assert isinstance(agent, ScriptedAgent)
    assert agent.act(_make_obs()) == ACTION_RIGHT


def test_resolve_agent_unknown_raises():
    import pytest
    with pytest.raises(KeyError):
        resolve_agent("nonexistent_agent")


# ---------------------------------------------------------------------------
# Smoke tests: agents driving real simulation
# ---------------------------------------------------------------------------

def _run_agent(agent, frames: int = 300) -> float:
    """Run an agent on hillside for N frames, return final x position."""
    sim = create_sim("hillside")
    agent.reset()
    prev_jump_held = False

    for _ in range(frames):
        obs = extract_observation(sim)
        action = agent.act(obs)
        inp, prev_jump_held = action_to_input(action, prev_jump_held)
        sim_step(sim, inp)

    return sim.player.physics.x


def test_smoke_hold_right_moves_right():
    agent = HoldRightAgent()
    sim = create_sim("hillside")
    start_x = sim.player.physics.x
    final_x = _run_agent(agent, frames=300)
    assert final_x > start_x, f"HoldRightAgent should move right: {start_x} → {final_x}"


def test_smoke_spindash_beats_hold_right():
    hold_right_x = _run_agent(HoldRightAgent(), frames=300)
    spindash_x = _run_agent(SpindashAgent(), frames=300)
    assert spindash_x > hold_right_x, (
        f"SpindashAgent should reach further than HoldRightAgent: "
        f"{spindash_x:.1f} vs {hold_right_x:.1f}"
    )


def test_smoke_idle_stays_put():
    agent = IdleAgent()
    sim = create_sim("hillside")
    start_x = sim.player.physics.x
    final_x = _run_agent(agent, frames=300)
    # Idle agent should not move significantly (small drift from gravity is ok)
    assert abs(final_x - start_x) < 50, f"IdleAgent moved too far: {start_x} → {final_x}"


def test_smoke_jump_runner_moves_right():
    agent = JumpRunnerAgent()
    sim = create_sim("hillside")
    start_x = sim.player.physics.x
    final_x = _run_agent(agent, frames=300)
    assert final_x > start_x, f"JumpRunnerAgent should move right: {start_x} → {final_x}"


# ---------------------------------------------------------------------------
# No Pyxel imports (new modules)
# ---------------------------------------------------------------------------

def _assert_no_pyxel(module_name: str) -> None:
    import importlib
    mod = importlib.import_module(f"speednik.agents.{module_name}")
    source = Path(inspect.getfile(mod)).read_text()
    assert "import pyxel" not in source, f"{module_name} imports pyxel"
    assert "from pyxel" not in source, f"{module_name} imports from pyxel"


def test_no_pyxel_import_idle():
    _assert_no_pyxel("idle")


def test_no_pyxel_import_hold_right():
    _assert_no_pyxel("hold_right")


def test_no_pyxel_import_jump_runner():
    _assert_no_pyxel("jump_runner")


def test_no_pyxel_import_spindash():
    _assert_no_pyxel("spindash")


def test_no_pyxel_import_scripted():
    _assert_no_pyxel("scripted")


def test_no_pyxel_import_registry():
    _assert_no_pyxel("registry")


# ===========================================================================
# T-010-15: PPOAgent (requires torch)
# ===========================================================================

def _make_ppo_checkpoint(tmp_path, obs_dim=26, num_actions=8):
    """Create a temporary PPO checkpoint for testing."""
    torch = __import__("torch")
    from speednik.agents.ppo_agent import _PPONetwork

    net = _PPONetwork(obs_dim, num_actions)
    path = str(tmp_path / "test_model.pt")
    torch.save(net.state_dict(), path)
    return path


class TestPPOAgent:
    """PPOAgent tests — all skip if torch is not installed."""

    def setup_method(self):
        import pytest
        pytest.importorskip("torch")

    def test_protocol_conformance(self, tmp_path):
        from speednik.agents.ppo_agent import PPOAgent

        path = _make_ppo_checkpoint(tmp_path)
        agent = PPOAgent(model_path=path)
        assert isinstance(agent, Agent)

    def test_no_pyxel_import(self):
        _assert_no_pyxel("ppo_agent")

    def test_deterministic_actions(self, tmp_path):
        """Same observation should produce the same action every time."""
        from speednik.agents.ppo_agent import PPOAgent

        path = _make_ppo_checkpoint(tmp_path)
        agent = PPOAgent(model_path=path)
        obs = np.zeros(26, dtype=np.float32)
        obs[4] = 1.0  # on_ground

        actions = [agent.act(obs) for _ in range(10)]
        assert len(set(actions)) == 1, f"Expected deterministic actions, got {actions}"

    def test_action_range(self, tmp_path):
        """Actions should be valid integers in [0, num_actions)."""
        from speednik.agents.ppo_agent import PPOAgent

        path = _make_ppo_checkpoint(tmp_path)
        agent = PPOAgent(model_path=path)

        rng = np.random.default_rng(42)
        for _ in range(20):
            obs = rng.standard_normal(26).astype(np.float32)
            action = agent.act(obs)
            assert isinstance(action, int)
            assert 0 <= action < 8

    def test_reset_is_noop(self, tmp_path):
        from speednik.agents.ppo_agent import PPOAgent

        path = _make_ppo_checkpoint(tmp_path)
        agent = PPOAgent(model_path=path)
        obs = np.zeros(26, dtype=np.float32)
        action_before = agent.act(obs)
        agent.reset()
        action_after = agent.act(obs)
        assert action_before == action_after

    def test_custom_dims(self, tmp_path):
        """PPOAgent should work with non-default obs_dim and num_actions."""
        from speednik.agents.ppo_agent import PPOAgent

        path = _make_ppo_checkpoint(tmp_path, obs_dim=12, num_actions=4)
        agent = PPOAgent(model_path=path, obs_dim=12, num_actions=4)
        obs = np.zeros(12, dtype=np.float32)
        action = agent.act(obs)
        assert 0 <= action < 4

    def test_registry_has_ppo(self):
        assert "ppo" in AGENT_REGISTRY

    def test_resolve_agent_ppo(self, tmp_path):
        path = _make_ppo_checkpoint(tmp_path)
        agent = resolve_agent("ppo", {"model_path": path})
        assert isinstance(agent, Agent)
        obs = np.zeros(26, dtype=np.float32)
        action = agent.act(obs)
        assert isinstance(action, int)

    def test_file_not_found(self, tmp_path):
        import pytest
        from speednik.agents.ppo_agent import PPOAgent

        with pytest.raises(FileNotFoundError):
            PPOAgent(model_path=str(tmp_path / "nonexistent.pt"))
