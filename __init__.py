# -*- coding: utf-8 -*-

bl_info = {
    "name": "Intra10 ToolKit",
    "author": "kimhwan",
    "version": (0, 2, 1),
    "blender": (5, 0, 0),
    "location": "View3D > N-Panel > Intra10 ToolKit",
    "description": "Collection of tools for Blender workflow",
    "category": "3D View",
}

import bpy

from . import landmark
from . import rosetta

FEATURE_MODULES = {
    "landmark": landmark,
    "rosetta": rosetta,
}


def _get_ui(module):
    ui = getattr(module, 'ui', None)
    return ui if ui is not None else None


def register():
    registered = 0
    for name, module in FEATURE_MODULES.items():
        ui = _get_ui(module)
        if ui is None:
            continue

        if hasattr(ui, 'classes'):
            for cls in ui.classes:
                try:
                    bpy.utils.register_class(cls)
                except Exception as e:
                    print(f"[Intra10 ToolKit] Failed to register {cls.__name__}: {e}")

        if hasattr(ui, 'register_properties'):
            try:
                ui.register_properties()
            except Exception as e:
                print(f"[Intra10 ToolKit] Failed to register properties for {name}: {e}")

        registered += 1

    print(f"[Intra10 ToolKit] Registered {registered}/{len(FEATURE_MODULES)} feature modules")


def unregister():
    for name, module in reversed(list(FEATURE_MODULES.items())):
        ui = _get_ui(module)
        if ui is None:
            continue

        if hasattr(ui, 'unregister_properties'):
            try:
                ui.unregister_properties()
            except Exception as e:
                print(f"[Intra10 ToolKit] Failed to unregister properties for {name}: {e}")

        if hasattr(ui, 'classes'):
            for cls in reversed(ui.classes):
                try:
                    bpy.utils.unregister_class(cls)
                except Exception as e:
                    print(f"[Intra10 ToolKit] Failed to unregister {cls.__name__}: {e}")


if __name__ == "__main__":
    register()
