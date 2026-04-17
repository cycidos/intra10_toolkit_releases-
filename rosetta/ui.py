# -*- coding: utf-8 -*-
"""
Rosetta — Thin wrapper for intra10_toolkit addon.
Imports UI from the rosetta repository (wrappers/blender/ui_blender.py)
and registers panels under the addon's N-Panel category.
"""

import os
import sys

_ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BL_CATEGORY = "Intra10 ToolKit"

_ui_blender = None


def _find_rosetta_root():
    env = os.environ.get("ROSETTA_ROOT")
    if env and os.path.isdir(env):
        return env
    candidates = [
        os.path.normpath(os.path.join(
            _ADDON_DIR, "..", "..", "..", "other", "rosetta")),
        os.path.normpath(os.path.join(
            os.path.expanduser("~"), "Documents", "setting", "other", "rosetta")),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return ""


def _ensure_import():
    global _ui_blender
    if _ui_blender is not None:
        return _ui_blender

    root = _find_rosetta_root()
    if not root:
        raise RuntimeError(
            "Rosetta root not found. Set ROSETTA_ROOT environment variable "
            "or place the rosetta repository at "
            "~/Documents/setting/other/rosetta")

    blender_dir = os.path.join(root, "wrappers", "blender")
    common_dir = os.path.join(root, "wrappers", "common")

    for d in (blender_dir, common_dir):
        if d and os.path.isdir(d) and d not in sys.path:
            sys.path.insert(0, d)

    import importlib
    import ui_blender as _ub
    importlib.reload(_ub)
    _ui_blender = _ub
    return _ui_blender


# Public API used by intra10_toolkit __init__.py
classes = []  # empty — all classes are in ui_blender


def register_properties():
    """Register Rosetta panels under the addon's category."""
    try:
        ub = _ensure_import()
        ub.register(category=_BL_CATEGORY)
    except Exception as e:
        print(f"[Rosetta] UI registration deferred: {e}")


def unregister_properties():
    """Unregister Rosetta panels."""
    global _ui_blender
    if _ui_blender is not None:
        try:
            _ui_blender.unregister()
        except Exception:
            pass
    _ui_blender = None
