# -*- coding: utf-8 -*-

import bpy
import bmesh
import gpu
from gpu_extras.batch import batch_for_shader
from .landmark_defs import attr_name

_draw_handler = None
_debug_counter = 0


def _collect_coords_object_mode(obj, group_name, mat):
    mesh = obj.data
    aname = attr_name(group_name)
    if aname not in mesh.attributes:
        return [], aname, "attr_not_found"

    attr = mesh.attributes[aname]
    edges = mesh.edges
    verts = mesh.vertices
    coords = []
    marked = 0

    for i, data in enumerate(attr.data):
        if data.value != 1:
            continue
        marked += 1
        if i >= len(edges):
            continue
        e = edges[i]
        coords.append(mat @ verts[e.vertices[0]].co)
        coords.append(mat @ verts[e.vertices[1]].co)

    return coords, aname, f"marked={marked}"


def _collect_coords_edit_mode(obj, group_name, mat):
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    aname = attr_name(group_name)

    layer = bm.edges.layers.int.get(aname)
    if not layer:
        all_layers = [l.name for l in bm.edges.layers.int.values()]
        return [], aname, f"layer_not_found(available={all_layers})"

    coords = []
    marked = 0
    for e in bm.edges:
        if e[layer] == 1:
            marked += 1
            coords.append(mat @ e.verts[0].co)
            coords.append(mat @ e.verts[1].co)

    return coords, aname, f"marked={marked}"


def _draw_landmarks():
    global _debug_counter
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

    mat = obj.matrix_world
    view_inv = rv3d.view_matrix.inverted()
    cam_pos = view_inv.translation
    view_dir = view_inv.col[2].xyz.normalized()
    is_persp = rv3d.is_perspective
    is_xray = getattr(scene, "intra10_landmark_xray", False)
    is_edit = (obj.mode == 'EDIT')

    should_debug = (_debug_counter % 120 == 0)
    _debug_counter += 1

    for group in scene.intra10_landmark_groups:
        if group.obj_name != obj.name:
            continue
        if not group.visible:
            continue

        group_name = group.name

        if is_edit:
            coords, aname, info = _collect_coords_edit_mode(obj, group_name, mat)
        else:
            coords, aname, info = _collect_coords_object_mode(obj, group_name, mat)

        if should_debug:
            mode = 'EDIT' if is_edit else 'OBJECT'
            mesh_attrs = [a.name for a in obj.data.attributes]
            print(f"[Intra10 ToolKit] draw: group='{group_name}' aname='{aname}' {mode} coords={len(coords)} {info} attrs={mesh_attrs}")

        if not coords:
            continue

        if not is_xray:
            offset_coords = []
            for idx, v in enumerate(coords):
                dist = (cam_pos - v).length if is_persp else 1.0
                offset = view_dir * (dist * 0.002 if is_persp else 0.002)
                offset_coords.append(v + offset)
            coords = offset_coords

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": coords})

        line_w = getattr(scene, "intra10_landmark_line_width", 3.0)
        gpu.state.line_width_set(line_w)
        gpu.state.blend_set('ALPHA')

        if is_xray:
            gpu.state.depth_test_set('ALWAYS')
        else:
            gpu.state.depth_test_set('LESS_EQUAL')

        shader.bind()
        shader.uniform_float("color", tuple(group.color))
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
