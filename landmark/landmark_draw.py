# -*- coding: utf-8 -*-

import bpy
import bmesh
import gpu
from gpu_extras.batch import batch_for_shader
from .landmark_defs import attr_name

_draw_handler = None


def _draw_landmarks():
    context = bpy.context
    obj = context.active_object

    if not obj or obj.type != 'MESH':
        return

    scene = context.scene
    if not hasattr(scene, "intra10_landmark_groups"):
        return

    rv3d = context.region_data
    if not rv3d:
        return

    groups = scene.intra10_landmark_groups
    visible_groups = [g for g in groups if g.obj_name == obj.name and g.visible]
    if not visible_groups:
        return

    mat = obj.matrix_world
    view_inv = rv3d.view_matrix.inverted()
    cam_pos = view_inv.translation
    view_dir = view_inv.col[2].xyz.normalized()
    is_persp = rv3d.is_perspective
    is_xray = getattr(scene, "intra10_landmark_xray", False)
    is_edit = (obj.mode == 'EDIT')
    line_w = getattr(scene, "intra10_landmark_line_width", 3.0)

    me = obj.data
    bm = None
    if is_edit:
        bm = bmesh.from_edit_mesh(me)

    batches = []

    for group in visible_groups:
        aname = attr_name(group.name)
        coords = []

        if is_edit and bm is not None:
            layer = bm.edges.layers.int.get(aname)
            if layer:
                for e in bm.edges:
                    if e[layer] == 1:
                        coords.append(mat @ e.verts[0].co)
                        coords.append(mat @ e.verts[1].co)
        else:
            if aname in me.attributes:
                attr = me.attributes[aname]
                edges = me.edges
                verts = me.vertices
                n_edges = len(edges)
                for i, data in enumerate(attr.data):
                    if data.value == 1 and i < n_edges:
                        e = edges[i]
                        coords.append(mat @ verts[e.vertices[0]].co)
                        coords.append(mat @ verts[e.vertices[1]].co)

        if not coords:
            continue

        if not is_xray:
            offset_coords = []
            for v in coords:
                dist = (cam_pos - v).length if is_persp else 1.0
                offset = view_dir * (dist * 0.002 if is_persp else 0.002)
                offset_coords.append(v + offset)
            coords = offset_coords

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": coords})
        batches.append((shader, batch, tuple(group.color)))

    if not batches:
        return

    gpu.state.line_width_set(line_w)
    gpu.state.blend_set('ALPHA')
    if is_xray:
        gpu.state.depth_test_set('ALWAYS')
    else:
        gpu.state.depth_test_set('LESS_EQUAL')

    for shader, batch, color in batches:
        shader.bind()
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
