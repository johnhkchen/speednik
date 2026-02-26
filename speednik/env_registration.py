"""speednik/env_registration.py — Register Speednik envs with Gymnasium.

Import this module to register all environments::

    import speednik.env_registration
    env = gymnasium.make("speednik/Hillside-v0")
"""

import gymnasium as gym

gym.register(
    id="speednik/Hillside-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "hillside", "max_steps": 3600},
    max_episode_steps=3600,
)

gym.register(
    id="speednik/Pipeworks-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "pipeworks", "max_steps": 5400},
    max_episode_steps=5400,
)

gym.register(
    id="speednik/Skybridge-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "skybridge", "max_steps": 7200},
    max_episode_steps=7200,
)

# NoRay variants (12-dim observations, no terrain raycasts)
gym.register(
    id="speednik/Hillside-NoRay-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "hillside", "max_steps": 3600, "use_raycasts": False},
    max_episode_steps=3600,
)

gym.register(
    id="speednik/Pipeworks-NoRay-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "pipeworks", "max_steps": 5400, "use_raycasts": False},
    max_episode_steps=5400,
)

gym.register(
    id="speednik/Skybridge-NoRay-v0",
    entry_point="speednik.env:SpeednikEnv",
    kwargs={"stage": "skybridge", "max_steps": 7200, "use_raycasts": False},
    max_episode_steps=7200,
)
