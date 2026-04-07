# -*- coding: utf-8 -*-

import bpy
import bmesh
from .landmark_defs import attr_name


def _ensure_attribute(mesh, group_name):
    """Ensure mesh attribute exists. Must be called before bmesh layer access."""
    aname = attr_name(group_name)
    if aname not in mesh.attributes:
        mesh.attributes.new(name=aname, type='INT', domain='EDGE')
    return aname


def _get_bmesh_layer(bm, aname):
    layer = bm.edges.layers.int.get(aname)
    if not layer:
        layer = bm.edges.layers.int.new(aname)
    return layer


def mark_edges(context, group_name, value=1):
    obj = context.edit_object
    if not obj or obj.type != 'MESH':
        return 0

    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    aname = attr_name(group_name)
    if aname not in me.attributes:
        me.attributes.new(name=aname, type='INT', domain='EDGE')

    layer = bm.edges.layers.int.get(aname)
    if not layer:
        layer = bm.edges.layers.int.new(aname)

    count = 0
    for e in bm.edges:
        if e.select:
            e[layer] = value
            count += 1

    bmesh.update_edit_mesh(me)
    return count


def clear_edges(context, group_name):
    return mark_edges(context, group_name, value=0)


def select_edges(context, group_name):
    obj = context.edit_object
    if not obj or obj.type != 'MESH':
        return 0

    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    aname = attr_name(group_name)
    layer = bm.edges.layers.int.get(aname)
    if not layer:
        return 0

    bpy.ops.mesh.select_all(action='DESELECT')
    count = 0
    for e in bm.edges:
        if e[layer] == 1:
            e.select = True
            count += 1

    bmesh.update_edit_mesh(me)
    return count


def get_marked_edge_indices(obj, group_name):
    if not obj or obj.type != 'MESH':
        return []

    me = obj.data
    aname = attr_name(group_name)

    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(me)
        layer = bm.edges.layers.int.get(aname)
        if not layer:
            return []
        return [e.index for e in bm.edges if e[layer] == 1]

    if aname not in me.attributes:
        return []
    attr = me.attributes[aname]
    return [i for i, d in enumerate(attr.data) if d.value == 1]


def set_marked_edge_indices(obj, group_name, indices):
    if not obj or obj.type != 'MESH':
        return

    me = obj.data
    aname = attr_name(group_name)
    if aname not in me.attributes:
        me.attributes.new(name=aname, type='INT', domain='EDGE')

    attr = me.attributes[aname]
    idx_set = set(indices)
    for i, d in enumerate(attr.data):
        d.value = 1 if i in idx_set else 0


def remove_attribute(obj, group_name):
    if not obj or obj.type != 'MESH':
        return

    me = obj.data
    aname = attr_name(group_name)

    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(me)
        layer = bm.edges.layers.int.get(aname)
        if layer:
            bm.edges.layers.int.remove(layer)
        bmesh.update_edit_mesh(me)
    else:
        if aname in me.attributes:
            me.attributes.remove(me.attributes[aname])


def _mirror_suffix(name):
    for l_suf, r_suf in [(".L", ".R"), (".l", ".r"), ("_L", "_R"), ("_l", "_r"),
                          (" L", " R"), (" l", " r"), (".Left", ".Right"), (".left", ".right")]:
        if name.endswith(l_suf):
            return name[:-len(l_suf)] + r_suf
        if name.endswith(r_suf):
            return name[:-len(r_suf)] + l_suf
    return None


def _build_mirror_map(obj):
    """Build vertex mirror map using X-axis symmetry with KDTree."""
    import mathutils.kdtree

    me = obj.data
    verts = me.vertices
    n = len(verts)

    kd = mathutils.kdtree.KDTree(n)
    for i, v in enumerate(verts):
        kd.insert(v.co, i)
    kd.balance()

    mirror = {}
    for i, v in enumerate(verts):
        mirrored = v.co.copy()
        mirrored.x = -mirrored.x
        _, idx, dist = kd.find(mirrored)
        if dist < 0.005:
            mirror[i] = idx
    return mirror


def mirror_landmark_group(obj, src_group_name, scene):
    if not obj or obj.type != 'MESH':
        return None

    dst_name = _mirror_suffix(src_group_name)
    if not dst_name:
        dst_name = src_group_name + ".R" if not src_group_name.endswith(".R") else src_group_name + ".L"

    me = obj.data
    src_aname = attr_name(src_group_name)

    was_edit = (obj.mode == 'EDIT')
    if was_edit:
        bpy.ops.object.mode_set(mode='OBJECT')

    if src_aname not in me.attributes:
        print(f"[Intra10 ToolKit] Mirror: source attribute '{src_aname}' not found. Available: {[a.name for a in me.attributes]}")
        if was_edit:
            bpy.ops.object.mode_set(mode='EDIT')
        return None

    src_attr = me.attributes[src_aname]

    src_edges = []
    for i, d in enumerate(src_attr.data):
        if d.value == 1:
            src_edges.append(i)

    if not src_edges:
        print(f"[Intra10 ToolKit] Mirror: no marked edges in '{src_group_name}'")
        if was_edit:
            bpy.ops.object.mode_set(mode='EDIT')
        return None

    vert_mirror = _build_mirror_map(obj)
    print(f"[Intra10 ToolKit] Mirror: mirror map size={len(vert_mirror)}/{len(me.vertices)}, src_edges={len(src_edges)}")

    edge_lookup = {}
    for i, e in enumerate(me.edges):
        key = frozenset((e.vertices[0], e.vertices[1]))
        edge_lookup[key] = i

    dst_aname = attr_name(dst_name)
    if dst_aname not in me.attributes:
        me.attributes.new(name=dst_aname, type='INT', domain='EDGE')
    dst_attr = me.attributes[dst_aname]

    for i in range(len(dst_attr.data)):
        dst_attr.data[i].value = 0

    mirrored_count = 0
    unmapped_verts = set()
    for i in src_edges:
        e = me.edges[i]
        v0, v1 = e.vertices[0], e.vertices[1]
        mv0 = vert_mirror.get(v0)
        mv1 = vert_mirror.get(v1)
        if mv0 is None:
            unmapped_verts.add(v0)
        if mv1 is None:
            unmapped_verts.add(v1)
        if mv0 is not None and mv1 is not None:
            key = frozenset((mv0, mv1))
            dst_idx = edge_lookup.get(key)
            if dst_idx is not None:
                dst_attr.data[dst_idx].value = 1
                mirrored_count += 1

    if unmapped_verts:
        print(f"[Intra10 ToolKit] Mirror: {len(unmapped_verts)} unmapped vertices (first 10: {list(unmapped_verts)[:10]})")

    if mirrored_count == 0:
        if dst_aname in me.attributes:
            me.attributes.remove(me.attributes[dst_aname])
        if was_edit:
            bpy.ops.object.mode_set(mode='EDIT')
        return None

    print(f"[Intra10 ToolKit] Mirror: {src_group_name} -> {dst_name}, {mirrored_count}/{len(src_edges)} edges mirrored")

    if was_edit:
        bpy.ops.object.mode_set(mode='EDIT')

    return dst_name


def auto_mirror_mark(context, group_name):
    obj = context.edit_object
    if not obj or obj.type != 'MESH':
        return

    me = obj.data
    bm = bmesh.from_edit_mesh(me)

    dst_name = _mirror_suffix(group_name)
    if not dst_name:
        dst_name = group_name

    aname = attr_name(dst_name)
    if aname not in me.attributes:
        me.attributes.new(name=aname, type='INT', domain='EDGE')

    layer = bm.edges.layers.int.get(aname)
    if not layer:
        layer = bm.edges.layers.int.new(aname)

    vert_mirror = _build_mirror_map(obj)

    edge_lookup = {}
    for e in bm.edges:
        key = frozenset((e.verts[0].index, e.verts[1].index))
        edge_lookup[key] = e

    src_aname = attr_name(group_name)
    src_layer = bm.edges.layers.int.get(src_aname)
    if not src_layer:
        return

    for e in bm.edges:
        if not e.select:
            continue
        v0 = e.verts[0].index
        v1 = e.verts[1].index
        mv0 = vert_mirror.get(v0)
        mv1 = vert_mirror.get(v1)
        if mv0 is not None and mv1 is not None:
            key = frozenset((mv0, mv1))
            mirror_edge = edge_lookup.get(key)
            if mirror_edge is not None:
                mirror_edge[layer] = 1

    bmesh.update_edit_mesh(me)
