# -*- coding: utf-8 -*-

import os

def _find_rosetta_root():
    env = os.environ.get("ROSETTA_ROOT")
    if env and os.path.isdir(env):
        return env
    _addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.normpath(os.path.join(_addon_dir, "..", "..", "..", "other", "rosetta")),
        os.path.normpath(os.path.join(os.path.expanduser("~"), "Documents", "setting", "other", "rosetta")),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return ""

_rosetta_root = _find_rosetta_root()

if _rosetta_root:
    from . import ui
else:
    ui = None
    print("[Intra10 ToolKit] Rosetta: external project not found, skipping UI registration")
