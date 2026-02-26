"""speednik/agents/actions.py — Action space and input mapping.

8 discrete actions covering all meaningful button combinations.
The action_to_input helper handles jump_pressed edge detection.
"""

from __future__ import annotations

from speednik.physics import InputState

# Action constants
ACTION_NOOP = 0
ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_JUMP = 3
ACTION_LEFT_JUMP = 4
ACTION_RIGHT_JUMP = 5
ACTION_DOWN = 6
ACTION_DOWN_JUMP = 7

NUM_ACTIONS = 8

# Maps action int to template InputState.
# Jump actions use jump_pressed=True as a marker; action_to_input
# overrides jump_pressed with edge detection.
ACTION_MAP: dict[int, InputState] = {
    ACTION_NOOP: InputState(),
    ACTION_LEFT: InputState(left=True),
    ACTION_RIGHT: InputState(right=True),
    ACTION_JUMP: InputState(jump_pressed=True, jump_held=True),
    ACTION_LEFT_JUMP: InputState(left=True, jump_pressed=True, jump_held=True),
    ACTION_RIGHT_JUMP: InputState(right=True, jump_pressed=True, jump_held=True),
    ACTION_DOWN: InputState(down_held=True),
    ACTION_DOWN_JUMP: InputState(down_held=True, jump_pressed=True, jump_held=True),
}


def action_to_input(action: int, prev_jump_held: bool) -> tuple[InputState, bool]:
    """Convert an action int to InputState with jump edge detection.

    Args:
        action: Discrete action index (0-7).
        prev_jump_held: Whether jump was held on the previous frame.

    Returns:
        (input_state, new_prev_jump_held) — the caller stores the second
        element and passes it back on the next call.
    """
    base = ACTION_MAP[action]
    jump_in_action = base.jump_held
    inp = InputState(
        left=base.left,
        right=base.right,
        jump_pressed=jump_in_action and not prev_jump_held,
        jump_held=jump_in_action,
        down_held=base.down_held,
        up_held=base.up_held,
    )
    return inp, jump_in_action
