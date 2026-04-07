# -*- coding: utf-8 -*-

import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from .landmark_defs import ATTR_PREFIX

_draw_handler = None


def _is_drawing():
    return _draw_handler is not None


def _draw_landmarks():
    context = bpy.context
    obj = context.active_object

    if not obj or obj.type != 'MESH':
        return

    scene = context.scene
    if not hasattr(scene, "intra10_landmark_groups"):
        return

    mesh = obj.data
    edges = mesh.edges
    verts = mesh.vertices
    mat = obj.matrix_world

    rv3d = context.region_data
    if not rv3d:
        return

    view_inv = rv3d.view_matrix.inverted()
    cam_pos = view_inv.translation
    view_dir = view_inv.col[2].xyz.normalized()
    is_persp = rv3d.is_perspective

    is_xray = getattr(scene, "intra10_landmark_xray", False)

    for group in scene.intra10_landmark_groups:
        if group.obj_name != obj.name:
            continue
        if not group.visible:
            continue

        aname = f"{ATTR_PREFIX}{group.name.replace(' ', '_').replace('.', '_')}"
        if aname not in mesh.attributes:
            continue

        attr = mesh.attributes[aname]
        coords = []

        for i, data in enumerate(attr.data):
            if data.value != 1:
                continue
            if i >= len(edges):
                continue

            e = edges[i]
            v1 = mat @ verts[e.vertices[0]].co
            v2 = mat @ verts[e.vertices[1]].co

            if not is_xray:
                dist1 = (cam_pos - v1).length if is_persp else 1.0
                dist2 = (cam_pos - v2).length if is_persp else 1.0
                offset1 = view_dir * (dist1 * 0.002 if is_persp else 0.002)
                offset2 = view_dir * (dist2 * 0.002 if is_persp else 0.002)
                v1 = v1 + offset1
                v2 = v2 + offset2

            coords.append(v1)
            coords.append(v2)

        if not coords:
            continue

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": coords})

        gpu.state.line_width_set(3.0)
        gpu.state.blend_set('ALPHA')

        if is_xray:
            gpu.state.depth_test_set('ALWAYS')
        else:
            gpu.state.depth_test_set('LESS_EQUAL')

        shader.bind()
        color = tuple(group.color)
        shader.uniform_float("color", color)
        batch.draw(shader)

    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def toggle_draw():
    global _draw_handler
    if _draw_handler is None:
        _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            _draw_landmarks, (), 'WINDOW', 'POST_VIEW'
        )
    else:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def remove_draw():
    global _draw_handler
    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, 'WINDOW')
        _draw_handler = None


def is_drawing():
    return _draw_handler is not None
