"""Where AIR is, for MM-Air's Python tests.

MM-Air is its own repository beside AIR. AIR_ROOT overrides the default sibling
checkout (../AIR on Linux, C:\\AIR next to C:\\MM-Air\\src on Windows).
"""
import os
from pathlib import Path

APP = Path(__file__).resolve().parents[1]


def air_root() -> Path:
    named = os.environ.get("AIR_ROOT")
    candidates = [Path(named)] if named else [APP.parent / "AIR", APP.parents[1] / "AIR"]
    for candidate in candidates:
        if (candidate / "toolkits/desktop").is_dir():
            return candidate.resolve()
    tried = ", ".join(str(c) for c in candidates)
    raise SystemExit(f"AIR checkout not found ({tried}); set AIR_ROOT")
