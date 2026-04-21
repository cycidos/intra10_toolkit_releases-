# -*- coding: utf-8 -*-
"""
Rosetta — Thin wrapper for intra10_toolkit addon.
Imports UI from the rosetta repository (wrappers/blender/ui_blender.py)
and registers panels under the addon's N-Panel category.

Also owns the "Reload Rosetta UI" operator: this lives in intra10_toolkit
(not in rosetta) so that even if a server-side rosetta update breaks the
import, the user can still trigger a recovery from the host addon.
See: docs/Security_Design.md §9 / §9.1 in the rosetta repository.
"""

import os
import sys
import importlib
import traceback

import bpy

_ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BL_CATEGORY = "Intra10 ToolKit"

_ui_blender = None

_ROSETTA_ROOT_CANDIDATES = (
    os.environ.get("ROSETTA_ROOT", ""),
    r"C:\server\extensions\rosetta",          # primary (intra10_pipeline symlink)
    r"H:\공유 드라이브\extensions\rosetta",   # direct shared-drive fallback
    os.path.normpath(os.path.join(_ADDON_DIR, "..", "..", "..", "other", "rosetta")),
    os.path.normpath(os.path.join(
        os.path.expanduser("~"), "Documents", "setting", "other", "rosetta")),
)

_ROSETTA_MODULE_NAMES = (
    "ui_blender", "adapter_blender", "controller", "model", "binary_io",
    "landmark_preset", "landmark_mirror", "landmark_draw",
    "landmark_viewport", "landmark_cache", "landmark_utils",
    "retarget_preset",
    "bone_blender", "bone_controller", "rig_utils",
    "collision_resolver", "garment_layer",
    "part_aware_rbf", "body_part_segmentation",
    "license",
)


def _resolve_rosetta_root():
    for p in _ROSETTA_ROOT_CANDIDATES:
        if p and os.path.isdir(p):
            return p
    return ""


def _ensure_sys_path(root):
    for sub in ("wrappers/blender", "wrappers/common"):
        p = os.path.join(root, sub)
        if p and os.path.isdir(p) and p not in sys.path:
            sys.path.insert(0, p)


def _ensure_import(force_reload=False):
    """Resolve rosetta deploy root and import (or re-import) ui_blender."""
    global _ui_blender

    if _ui_blender is not None and not force_reload:
        return _ui_blender

    root = _resolve_rosetta_root()
    if not root:
        raise RuntimeError(
            "Rosetta deploy root not found. Set ROSETTA_ROOT env or ensure "
            r"intra10_pipeline created C:\server\extensions symlink.")

    _ensure_sys_path(root)

    if force_reload:
        for name in _ROSETTA_MODULE_NAMES:
            sys.modules.pop(name, None)

    import ui_blender as _ub
    if force_reload:
        _ub = importlib.reload(_ub)
    _ui_blender = _ub
    return _ui_blender


def _draw_reload_button(self, _context):
    """Appended to ROSETTA_PT_main.draw() — adds a refresh icon next to the title.

    Lives in intra10_toolkit so that hot-reloading rosetta itself is safe.
    """
    row = self.layout.row(align=True)
    row.alignment = 'RIGHT'
    row.operator("intra10.rosetta_reload", text="", icon='FILE_REFRESH')


class INTRA10_OT_RosettaReload(bpy.types.Operator):
    """Hot-reload Rosetta UI / wrapper modules from the server deploy root.

    Use this after a server-side Rosetta update (e.g. C:\\server\\rosetta) to
    apply changes without restarting Blender.
    """
    bl_idname = "intra10.rosetta_reload"
    bl_label = "Reload Rosetta UI"
    bl_description = ("Reload Rosetta UI / wrapper modules from "
                      "C:\\server\\extensions\\rosetta")

    def execute(self, context):
        # Defer to next tick so the current panel draw / event loop unwinds first.
        bpy.app.timers.register(_perform_reload, first_interval=0.05)
        self.report({'INFO'}, "Rosetta reload scheduled")
        return {'FINISHED'}


def _perform_reload():
    global _ui_blender

    # 1) Try to gracefully unregister current rosetta UI.
    try:
        if _ui_blender is not None:
            _ui_blender.unregister()
    except Exception as exc:
        print(f"[Intra10 ToolKit] Rosetta unregister warning: {exc}")

    # 2) Detach our panel-append hook so the new register can re-attach cleanly.
    _detach_panel_hook()

    # 3) Drop cached wrapper modules and re-import + register.
    _ui_blender = None
    try:
        ub = _ensure_import(force_reload=True)
        ub.register(category=_BL_CATEGORY)
        _attach_panel_hook()
        print(f"[Intra10 ToolKit] Reloaded Rosetta UI from "
              f"{_resolve_rosetta_root()!r}")
    except Exception as exc:
        traceback.print_exc()
        print(f"[Intra10 ToolKit] Rosetta reload FAILED: {exc}")
    return None  # one-shot timer


def _attach_panel_hook():
    """Append our refresh button to rosetta's main panel header (best-effort)."""
    main_panel = getattr(bpy.types, "ROSETTA_PT_main", None)
    if main_panel is None:
        return
    try:
        main_panel.append(_draw_reload_button)
    except Exception as exc:
        print(f"[Intra10 ToolKit] Could not append reload button: {exc}")


def _detach_panel_hook():
    main_panel = getattr(bpy.types, "ROSETTA_PT_main", None)
    if main_panel is None:
        return
    try:
        main_panel.remove(_draw_reload_button)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public API used by intra10_toolkit/__init__.py
# ---------------------------------------------------------------------------

# The reload operator is owned by THIS addon — register it via the addon's
# class loop. ui_blender's own classes are registered by ui_blender.register().
classes = (INTRA10_OT_RosettaReload,)


def register_properties():
    """Register Rosetta panels under the addon's category and attach hooks."""
    try:
        ub = _ensure_import()
        ub.register(category=_BL_CATEGORY)
        _attach_panel_hook()
    except Exception as e:
        print(f"[Rosetta] UI registration deferred: {e}")


def unregister_properties():
    """Unregister Rosetta panels and detach hooks."""
    global _ui_blender
    _detach_panel_hook()
    if _ui_blender is not None:
        try:
            _ui_blender.unregister()
        except Exception:
            pass
    _ui_blender = None
