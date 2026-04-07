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

    print(f"[Intra10 ToolKit] DEBUG mark_edges: group='{group_name}' aname='{aname}' value={value} count={count}")
    print(f"[Intra10 ToolKit] DEBUG mark_edges: mesh.attrs={[a.name for a in me.attributes]}")

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


def _build_mirror_map_coords(verts_co):
    """Coordinate-based mirror map: X-flip with generous threshold."""
    import mathutils.kdtree

    n = len(verts_co)
    kd = mathutils.kdtree.KDTree(n)
    for i, co in enumerate(verts_co):
        kd.insert(co, i)
    kd.balance()

    mirror = {}
    for i, co in enumerate(verts_co):
        mirrored = co.copy()
        mirrored.x = -mirrored.x
        _, idx, dist = kd.find(mirrored)
        if dist < 0.001:
            mirror[i] = idx
    return mirror


def _build_mirror_map_topology(obj):
    """Topology-based mirror map using BFS from center vertices."""
    from mathutils import Vector

    me = obj.data
    verts = me.vertices
    n = len(verts)

    vert_edges = [[] for _ in range(n)]
    for e in me.edges:
        v0, v1 = e.vertices[0], e.vertices[1]
        vert_edges[v0].append((e.index, v1))
        vert_edges[v1].append((e.index, v0))

    verts_co = [v.co.copy() for v in verts]
    coord_mirror = _build_mirror_map_coords(verts_co)

    if len(coord_mirror) > n * 0.3:
        return coord_mirror

    center_threshold = 0.001
    center_verts = [i for i, co in enumerate(verts_co) if abs(co.x) < center_threshold]

    mirror = {}
    for cv in center_verts:
        mirror[cv] = cv

    visited = set(center_verts)
    queue = list(center_verts)

    while queue:
        current = queue.pop(0)
        m_current = mirror.get(current)
        if m_current is None:
            continue

        current_edges = sorted(vert_edges[current], key=lambda x: x[0])
        mirror_edges = sorted(vert_edges[m_current], key=lambda x: x[0])

        for (_, neighbor) in current_edges:
            if neighbor in visited:
                continue

            best_match = None
            best_dist = float('inf')
            target_co = verts_co[neighbor].copy()
            target_co.x = -target_co.x

            for (_, m_neighbor) in mirror_edges:
                if m_neighbor in mirror.values() and mirror.get(neighbor) != m_neighbor:
                    continue
                d = (verts_co[m_neighbor] - target_co).length
                if d < best_dist:
                    best_dist = d
                    best_match = m_neighbor

            if best_match is not None and best_dist < 0.01:
                mirror[neighbor] = best_match
                if best_match not in mirror:
                    mirror[best_match] = neighbor
                visited.add(neighbor)
                visited.add(best_match)
                queue.append(neighbor)

    return mirror


def _build_mirror_map(obj):
    """Build vertex mirror map. Tries topology first, falls back to coords."""
    me = obj.data
    verts_co = [v.co.copy() for v in me.vertices]

    topo_mirror = _build_mirror_map_topology(obj)
    if len(topo_mirror) > len(verts_co) * 0.3:
        return topo_mirror

    return _build_mirror_map_coords(verts_co)


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
        if was_edit:
            bpy.ops.object.mode_set(mode='EDIT')
        return None

    src_attr = me.attributes[src_aname]
    vert_mirror = _build_mirror_map(obj)

    edge_lookup = {}
    for i, e in enumerate(me.edges):
        key = tuple(sorted(e.vertices))
        edge_lookup[key] = i

    dst_aname = attr_name(dst_name)
    if dst_aname not in me.attributes:
        me.attributes.new(name=dst_aname, type='INT', domain='EDGE')
    dst_attr = me.attributes[dst_aname]

    for i in range(len(dst_attr.data)):
        dst_attr.data[i].value = 0

    mirrored_count = 0
    for i, d in enumerate(src_attr.data):
        if d.value != 1:
            continue
        e = me.edges[i]
        v0, v1 = e.vertices[0], e.vertices[1]
        mv0 = vert_mirror.get(v0)
        mv1 = vert_mirror.get(v1)
        if mv0 is not None and mv1 is not None:
            key = tuple(sorted((mv0, mv1)))
            dst_idx = edge_lookup.get(key)
            if dst_idx is not None:
                dst_attr.data[dst_idx].value = 1
                mirrored_count += 1

    if mirrored_count == 0:
        if dst_aname in me.attributes:
            me.attributes.remove(me.attributes[dst_aname])
        if was_edit:
            bpy.ops.object.mode_set(mode='EDIT')
        return None

    print(f"[Intra10 ToolKit] Mirror: {src_group_name} -> {dst_name}, {mirrored_count} edges, map size={len(vert_mirror)}")

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
