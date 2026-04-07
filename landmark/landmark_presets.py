# -*- coding: utf-8 -*-

import json
from . import landmark_core


PRESET_VERSION = 1


def save_preset(filepath, obj, scene):
    if not obj or obj.type != 'MESH':
        return False

    groups_data = []
    for group in scene.intra10_landmark_groups:
        if group.obj_name != obj.name:
            continue
        indices = landmark_core.get_marked_edge_indices(obj, group.name)
        groups_data.append({
            "name": group.name,
            "color": list(group.color),
            "edge_indices": indices,
        })

    data = {
        "version": PRESET_VERSION,
        "groups": groups_data,
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return True


def load_preset(filepath, obj, scene):
    if not obj or obj.type != 'MESH':
        return False, "No mesh object selected"

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if "groups" not in data:
        return False, "Invalid preset format"

    loaded = 0
    for gdata in data["groups"]:
        name = gdata.get("name", "")
        color = gdata.get("color", [1.0, 1.0, 1.0, 1.0])
        indices = gdata.get("edge_indices", [])

        if not name:
            continue

        existing = None
        for g in scene.intra10_landmark_groups:
            if g.name == name and g.obj_name == obj.name:
                existing = g
                break

        if existing is None:
            existing = scene.intra10_landmark_groups.add()
            existing.name = name
            existing.obj_name = obj.name

        existing.color = color[:4]
        existing.visible = True

        landmark_core.set_marked_edge_indices(obj, name, indices)
        loaded += 1

    return True, f"Loaded {loaded} landmark groups"
