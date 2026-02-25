"""Web entry point for speednik.

Pyxel's web player only adds os.path.dirname(startup_script) to sys.path.
This file lives at the pyxapp root so that dirname resolves to the directory
that *contains* the speednik/ package — making all package imports work.
"""
import os
import sys

# dirname(__file__) == pyxapp root == the directory that contains speednik/
_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from speednik.main import App  # noqa: E402

App()
