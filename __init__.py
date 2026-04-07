# -*- coding: utf-8 -*-

bl_info = {
    "name": "Intra10 ToolKit",
    "author": "kimhwan",
    "version": (0, 1, 9),
    "blender": (5, 0, 0),
    "location": "View3D > N-Panel > Intra10 ToolKit",
    "description": "Collection of tools for Blender workflow",
    "category": "3D View",
}

import bpy

from . import landmark

FEATURE_MODULES = {
    "landmark": landmark,
}


def register():
    for name, module in FEATURE_MODULES.items():
        if hasattr(module, 'ui') and hasattr(module.ui, 'classes'):
            for cls in module.ui.classes:
                try:
                    bpy.utils.register_class(cls)
                except Exception as e:
                    print(f"[Intra10 ToolKit] Failed to register {cls.__name__}: {e}")

        if hasattr(module, 'ui') and hasattr(module.ui, 'register_properties'):
            try:
                module.ui.register_properties()
            except Exception as e:
                print(f"[Intra10 ToolKit] Failed to register properties for {name}: {e}")

    print(f"[Intra10 ToolKit] Registered {len(FEATURE_MODULES)} feature modules")


def unregister():
    for name, module in reversed(list(FEATURE_MODULES.items())):
        if hasattr(module, 'ui') and hasattr(module.ui, 'unregister_properties'):
            try:
                module.ui.unregister_properties()
            except Exception as e:
                print(f"[Intra10 ToolKit] Failed to unregister properties for {name}: {e}")

        if hasattr(module, 'ui') and hasattr(module.ui, 'classes'):
            for cls in reversed(module.ui.classes):
                try:
                    bpy.utils.unregister_class(cls)
                except Exception as e:
                    print(f"[Intra10 ToolKit] Failed to unregister {cls.__name__}: {e}")


if __name__ == "__main__":
    register()
