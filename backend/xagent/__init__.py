"""Compatibility package exposing modules from ``backend/app`` as ``xagent``."""

from pathlib import Path


_APP_DIR = Path(__file__).resolve().parent.parent / "app"
__path__ = [str(_APP_DIR)]
