"""Tests that validate the web export can load correctly.

Pyxel's web player sets sys.path to only [os.path.dirname(startup_script)].
web_entry.py must live at the pyxapp root so that dirname resolves to the
directory containing the speednik/ package.

These tests simulate that restricted import environment and verify every
module imported during a normal gameplay session can be found.
"""

from __future__ import annotations

import importlib.util
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
WEB_ENTRY = REPO_ROOT / "web_entry.py"

# All submodules that main.py or its transitive imports pull in.
# Any module missing here would produce a ModuleNotFoundError in the browser.
REQUIRED_SUBMODULES = [
    "speednik.audio",
    "speednik.camera",
    "speednik.constants",
    "speednik.enemies",
    "speednik.level",
    "speednik.objects",
    "speednik.physics",
    "speednik.player",
    "speednik.renderer",
    "speednik.terrain",
    "speednik.stages.hillside",
    "speednik.stages.pipeworks",
    "speednik.stages.skybridge",
]


@contextmanager
def isolated_path(*extra_dirs: str):
    """Run with sys.path restricted to extra_dirs + stdlib only.

    Simulates Pyxel's web player which only appends dirname(startup_script)
    to sys.path — nothing else from the host environment.
    """
    stdlib_paths = [p for p in sys.path if "site-packages" not in p and p != ""]
    old_path = sys.path[:]
    old_modules = set(sys.modules)
    sys.path = list(extra_dirs) + stdlib_paths
    try:
        yield
    finally:
        sys.path = old_path
        for key in list(sys.modules):
            if key not in old_modules:
                del sys.modules[key]


class TestWebEntryPoint:
    def test_web_entry_exists_at_repo_root(self):
        """web_entry.py must be at repo root so Pyxel adds the right dir to sys.path."""
        assert WEB_ENTRY.exists(), (
            "web_entry.py missing from repo root. "
            "The web player only adds dirname(startup_script) to sys.path. "
            "web_entry.py must sit next to the speednik/ package."
        )

    def test_web_entry_not_inside_package(self):
        """web_entry.py must NOT be inside speednik/ or Pyxel's path setup breaks."""
        package_dir = REPO_ROOT / "speednik"
        assert not WEB_ENTRY.is_relative_to(package_dir), (
            "web_entry.py is inside speednik/ — move it to the repo root."
        )


class TestWebImportEnvironment:
    """Simulate Pyxel's web sys.path: only dirname(web_entry.py) is available."""

    def test_speednik_package_findable(self):
        """speednik package must be discoverable when only repo_root is in sys.path."""
        with isolated_path(str(REPO_ROOT)):
            spec = importlib.util.find_spec("speednik")
            assert spec is not None, (
                "speednik package not findable from repo root. "
                "Check that speednik/__init__.py exists."
            )

    @pytest.mark.parametrize("module", REQUIRED_SUBMODULES)
    def test_submodule_findable(self, module: str):
        """Each submodule must be findable in the restricted web sys.path."""
        with isolated_path(str(REPO_ROOT)):
            spec = importlib.util.find_spec(module)
            assert spec is not None, (
                f"{module} not findable from repo root — would cause "
                f"ModuleNotFoundError in the browser."
            )

    def test_stage_json_files_present(self):
        """Stage JSON data must be present so level.py can load levels at runtime."""
        stages = ["hillside", "pipeworks", "skybridge"]
        required_files = ["tile_map.json", "collision.json", "entities.json", "meta.json"]
        for stage in stages:
            for fname in required_files:
                path = REPO_ROOT / "speednik" / "stages" / stage / fname
                assert path.exists(), (
                    f"Missing stage data: speednik/stages/{stage}/{fname}. "
                    "Level loading will fail at runtime."
                )
