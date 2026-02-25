"""speednik/debug.py — Debug flag from environment variable."""

import os

DEBUG = os.environ.get("SPEEDNIK_DEBUG", "") == "1"
