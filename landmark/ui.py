# -*- coding: utf-8 -*-

import os
import bpy
import bmesh
from bpy.props import (
    StringProperty, BoolProperty, FloatVectorProperty, FloatProperty,
    IntProperty, EnumProperty, CollectionProperty,
)
from . import landmark_core
from . import landmark_draw
from . import landmark_presets
from .landmark_defs import (
    FACIAL_LANDMARKS, BODY_LANDMARKS, FINGER_LANDMARKS,
    DEFAULT_CUSTOM_COLOR,
)

PRESET_DIR = os.path.join(
    "C:\\Users\\USER\\Documents\\blender\\scripts",
    "intra10_toolkit", "landmarks",
)


def _redraw_viewports():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


# ======================================================================
# PropertyGroups
# ======================================================================

class INTRA10_PG_LandmarkGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", default="")
    color: FloatVectorProperty(
        name="Color", subtype='COLOR_GAMMA',
        size=4, min=0.0, max=1.0,
        default=(0.0, 1.0, 1.0, 1.0),
    )
    visible: BoolProperty(name="Visible", default=True)
    obj_name: StringProperty(name="Object", default="")


# ======================================================================
# UIList
# ======================================================================

class INTRA10_UL_LandmarkGroupList(bpy.types.UIList):
    bl_idname = "INTRA10_UL_landmark_group_list"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            row.prop(item, "color", text="", icon='COLOR')
            row.prop(item, "name", text="", emboss=False)
            vis_icon = 'HIDE_OFF' if item.visible else 'HIDE_ON'
            row.prop(item, "visible", text="", icon=vis_icon, emboss=False)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=item.name)


# ======================================================================
# Operators
# ======================================================================

class INTRA10_OT_ToggleLandmarkDraw(bpy.types.Operator):
    bl_idname = "intra10.toggle_landmark_draw"
    bl_label = "Toggle Landmark View"

    def execute(self, context):
        landmark_draw.toggle_draw()
        return {'FINISHED'}


class INTRA10_OT_MarkLandmark(bpy.types.Operator):
    """Add selected edges to the active landmark group"""
    bl_idname = "intra10.mark_landmark"
    bl_label = "Mark Landmark Edges"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        scene = context.scene
        idx = scene.intra10_landmark_active_index
        groups = scene.intra10_landmark_groups

        if idx < 0 or idx >= len(groups):
            self.report({'WARNING'}, "Select a landmark group first")
            return {'CANCELLED'}

        group = groups[idx]
        count = landmark_core.mark_edges(context, group.name)

        if scene.intra10_landmark_auto_mirror:
            landmark_core.auto_mirror_mark(context, group.name)

        _redraw_viewports()
        self.report({'INFO'}, f"Marked {count} edges in '{group.name}'")
        return {'FINISHED'}


class INTRA10_OT_SelectLandmarkEdges(bpy.types.Operator):
    bl_idname = "intra10.select_landmark_edges"
    bl_label = "Select Landmark Edges"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        scene = context.scene
        idx = scene.intra10_landmark_active_index
        groups = scene.intra10_landmark_groups

        if idx < 0 or idx >= len(groups):
            self.report({'WARNING'}, "Select a landmark group first")
            return {'CANCELLED'}

        group = groups[idx]
        count = landmark_core.select_edges(context, group.name)
        self.report({'INFO'}, f"Selected {count} edges in '{group.name}'")
        return {'FINISHED'}


class INTRA10_OT_AddLandmarkGroup(bpy.types.Operator):
    bl_idname = "intra10.add_landmark_group"
    bl_label = "Add Landmark Group"
    bl_options = {'REGISTER'}

    part_name: StringProperty(name="Part Name")
    part_color: FloatVectorProperty(
        name="Color", subtype='COLOR_GAMMA',
        size=4, min=0.0, max=1.0,
        default=(0.0, 1.0, 1.0, 1.0),
    )

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object")
            return {'CANCELLED'}

        for g in scene.intra10_landmark_groups:
            if g.name == self.part_name and g.obj_name == obj.name:
                scene.intra10_landmark_active_index = list(scene.intra10_landmark_groups).index(g)
                if context.mode == 'EDIT_MESH':
                    count = landmark_core.mark_edges(context, self.part_name)
                    if scene.intra10_landmark_auto_mirror:
                        landmark_core.auto_mirror_mark(context, self.part_name)
                    _redraw_viewports()
                    self.report({'INFO'}, f"Marked {count} edges in '{self.part_name}'")
                    return {'FINISHED'}
                self.report({'WARNING'}, f"'{self.part_name}' already exists")
                return {'CANCELLED'}

        group = scene.intra10_landmark_groups.add()
        group.name = self.part_name
        group.color = self.part_color
        group.visible = True
        group.obj_name = obj.name

        scene.intra10_landmark_active_index = len(scene.intra10_landmark_groups) - 1

        if context.mode == 'EDIT_MESH':
            count = landmark_core.mark_edges(context, self.part_name)
            if scene.intra10_landmark_auto_mirror:
                landmark_core.auto_mirror_mark(context, self.part_name)
            _redraw_viewports()
            self.report({'INFO'}, f"Added '{self.part_name}' and marked {count} edges")
        else:
            self.report({'INFO'}, f"Added landmark group '{self.part_name}'")
        return {'FINISHED'}


class INTRA10_OT_AddFingerLandmark(bpy.types.Operator):
    bl_idname = "intra10.add_finger_landmark"
    bl_label = "Add Finger/Toe Landmark"
    bl_options = {'REGISTER'}

    finger_name: StringProperty(name="Finger Name")
    finger_color: FloatVectorProperty(
        name="Color", subtype='COLOR_GAMMA',
        size=4, min=0.0, max=1.0,
        default=(1.0, 0.5, 0.2, 1.0),
    )
    range_start: IntProperty(name="Start", default=0, min=0, max=3)
    range_end: IntProperty(name="End", default=3, min=0, max=3)
    finger_number: EnumProperty(
        name="Number",
        items=[
            ('0', '00', ''),
            ('1', '01', ''),
            ('2', '02', ''),
            ('3', '03', ''),
        ],
        default='0',
    )

    def invoke(self, context, event):
        self.finger_number = str(self.range_start)
        return context.window_manager.invoke_props_dialog(self, width=200)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"{self.finger_name} Line")
        layout.prop(self, "finger_number", expand=True)

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object")
            return {'CANCELLED'}

        num = int(self.finger_number)
        if num < self.range_start or num > self.range_end:
            self.report({'WARNING'}, f"Number must be {self.range_start:02d}~{self.range_end:02d}")
            return {'CANCELLED'}

        name = f"{self.finger_name} {num:02d} Line"

        for g in scene.intra10_landmark_groups:
            if g.name == name and g.obj_name == obj.name:
                scene.intra10_landmark_active_index = list(scene.intra10_landmark_groups).index(g)
                if context.mode == 'EDIT_MESH':
                    count = landmark_core.mark_edges(context, name)
                    if scene.intra10_landmark_auto_mirror:
                        landmark_core.auto_mirror_mark(context, name)
                    _redraw_viewports()
                    self.report({'INFO'}, f"Marked {count} edges in '{name}'")
                    return {'FINISHED'}
                self.report({'WARNING'}, f"'{name}' already exists")
                return {'CANCELLED'}

        group = scene.intra10_landmark_groups.add()
        group.name = name
        group.color = self.finger_color
        group.visible = True
        group.obj_name = obj.name
        scene.intra10_landmark_active_index = len(scene.intra10_landmark_groups) - 1

        if context.mode == 'EDIT_MESH':
            count = landmark_core.mark_edges(context, name)
            if scene.intra10_landmark_auto_mirror:
                landmark_core.auto_mirror_mark(context, name)
            _redraw_viewports()
            self.report({'INFO'}, f"Added '{name}' and marked {count} edges")
        else:
            self.report({'INFO'}, f"Added '{name}'")

        return {'FINISHED'}


class INTRA10_OT_AddCustomLandmark(bpy.types.Operator):
    bl_idname = "intra10.add_custom_landmark"
    bl_label = "Add Custom Landmark"
    bl_options = {'REGISTER'}

    def _unique_name(self, base, obj_name, groups):
        existing = {g.name for g in groups if g.obj_name == obj_name}
        if base not in existing:
            return base
        idx = 1
        while True:
            candidate = f"{base}_{idx:03d}"
            if candidate not in existing:
                return candidate
            idx += 1

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object")
            return {'CANCELLED'}

        base_name = scene.intra10_landmark_custom_name.strip()
        if not base_name:
            self.report({'WARNING'}, "Enter a landmark name")
            return {'CANCELLED'}

        name = self._unique_name(base_name, obj.name, scene.intra10_landmark_groups)

        group = scene.intra10_landmark_groups.add()
        group.name = name
        group.color = scene.intra10_landmark_custom_color
        group.visible = True
        group.obj_name = obj.name

        scene.intra10_landmark_active_index = len(scene.intra10_landmark_groups) - 1

        if context.mode == 'EDIT_MESH':
            count = landmark_core.mark_edges(context, name)
            if scene.intra10_landmark_auto_mirror:
                landmark_core.auto_mirror_mark(context, name)
            _redraw_viewports()
            self.report({'INFO'}, f"Added custom landmark '{name}' and marked {count} edges")
        else:
            self.report({'INFO'}, f"Added custom landmark '{name}'")
        return {'FINISHED'}


class INTRA10_OT_UnmarkLandmark(bpy.types.Operator):
    """Remove selected edges from the active landmark group"""
    bl_idname = "intra10.unmark_landmark"
    bl_label = "Unmark Landmark Edges"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH'

    def execute(self, context):
        scene = context.scene
        idx = scene.intra10_landmark_active_index
        groups = scene.intra10_landmark_groups

        if idx < 0 or idx >= len(groups):
            self.report({'WARNING'}, "Select a landmark group first")
            return {'CANCELLED'}

        group = groups[idx]
        count = landmark_core.clear_edges(context, group.name)
        _redraw_viewports()
        self.report({'INFO'}, f"Unmarked {count} edges from '{group.name}'")
        return {'FINISHED'}


class INTRA10_OT_RemoveLandmarkGroup(bpy.types.Operator):
    bl_idname = "intra10.remove_landmark_group"
    bl_label = "Remove Landmark Group"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        idx = scene.intra10_landmark_active_index
        groups = scene.intra10_landmark_groups

        if idx < 0 or idx >= len(groups):
            self.report({'WARNING'}, "No group selected")
            return {'CANCELLED'}

        group = groups[idx]
        obj = context.active_object
        if obj and obj.type == 'MESH' and obj.name == group.obj_name:
            landmark_core.remove_attribute(obj, group.name)

        groups.remove(idx)
        scene.intra10_landmark_active_index = min(idx, len(groups) - 1)
        _redraw_viewports()
        return {'FINISHED'}


class INTRA10_OT_RemoveAllLandmarkGroups(bpy.types.Operator):
    """Remove all landmark groups and their edge data"""
    bl_idname = "intra10.remove_all_landmark_groups"
    bl_label = "Remove All Landmark Groups"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        groups = scene.intra10_landmark_groups

        if len(groups) == 0:
            self.report({'WARNING'}, "No groups to remove")
            return {'CANCELLED'}

        if obj and obj.type == 'MESH':
            for g in groups:
                if g.obj_name == obj.name:
                    landmark_core.remove_attribute(obj, g.name)

        groups.clear()
        scene.intra10_landmark_active_index = 0
        _redraw_viewports()
        self.report({'INFO'}, "Removed all landmark groups")
        return {'FINISHED'}


class INTRA10_MT_RemoveLandmarkMenu(bpy.types.Menu):
    bl_idname = "INTRA10_MT_remove_landmark_menu"
    bl_label = "Remove Landmark"

    def draw(self, context):
        layout = self.layout
        layout.operator("intra10.remove_landmark_group", text="Remove Selected", icon='REMOVE')
        layout.operator("intra10.remove_all_landmark_groups", text="Remove All", icon='TRASH')


class INTRA10_OT_MirrorLandmarkGroup(bpy.types.Operator):
    bl_idname = "intra10.mirror_landmark_group"
    bl_label = "Mirror Landmark Group"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object")
            return {'CANCELLED'}

        idx = scene.intra10_landmark_active_index
        groups = scene.intra10_landmark_groups
        if idx < 0 or idx >= len(groups):
            self.report({'WARNING'}, "No group selected")
            return {'CANCELLED'}

        src_group = groups[idx]
        dst_name = landmark_core.mirror_landmark_group(obj, src_group.name, scene)
        if not dst_name:
            self.report({'WARNING'}, "Mirror failed: no mirrored edges found")
            return {'CANCELLED'}

        if dst_name != src_group.name:
            existing = None
            for g in groups:
                if g.name == dst_name and g.obj_name == obj.name:
                    existing = g
                    break

            if existing is None:
                new_group = groups.add()
                new_group.name = dst_name
                new_group.color = src_group.color
                new_group.visible = True
                new_group.obj_name = obj.name
                scene.intra10_landmark_active_index = len(groups) - 1

        _redraw_viewports()
        self.report({'INFO'}, f"Mirrored to '{dst_name}'")
        return {'FINISHED'}


class INTRA10_OT_AddLRSuffix(bpy.types.Operator):
    bl_idname = "intra10.add_lr_suffix"
    bl_label = "Add .L/.R Suffix"
    bl_options = {'REGISTER'}

    suffix: StringProperty(name="Suffix", default=".L")

    def execute(self, context):
        scene = context.scene
        idx = scene.intra10_landmark_active_index
        groups = scene.intra10_landmark_groups
        if idx < 0 or idx >= len(groups):
            self.report({'WARNING'}, "No group selected")
            return {'CANCELLED'}

        group = groups[idx]
        old_name = group.name

        for suf in [".L", ".R", ".l", ".r", "_L", "_R", " L", " R",
                    ".Left", ".Right", ".left", ".right"]:
            if old_name.endswith(suf):
                old_name = old_name[:-len(suf)]
                break

        new_name = old_name + self.suffix

        obj = context.active_object
        if obj and obj.type == 'MESH' and obj.name == group.obj_name:
            old_aname = landmark_core.attr_name(group.name)
            new_aname = landmark_core.attr_name(new_name)
            me = obj.data
            if old_aname in me.attributes and old_aname != new_aname:
                if obj.mode == 'EDIT':
                    bm = bmesh.from_edit_mesh(me)
                    old_layer = bm.edges.layers.int.get(old_aname)
                    if old_layer:
                        if new_aname not in me.attributes:
                            me.attributes.new(name=new_aname, type='INT', domain='EDGE')
                        new_layer = bm.edges.layers.int.get(new_aname)
                        if not new_layer:
                            new_layer = bm.edges.layers.int.new(new_aname)
                        for e in bm.edges:
                            e[new_layer] = e[old_layer]
                        bm.edges.layers.int.remove(old_layer)
                    bmesh.update_edit_mesh(me)
                else:
                    old_attr = me.attributes[old_aname]
                    if new_aname not in me.attributes:
                        me.attributes.new(name=new_aname, type='INT', domain='EDGE')
                    new_attr = me.attributes[new_aname]
                    for i, d in enumerate(old_attr.data):
                        new_attr.data[i].value = d.value
                    me.attributes.remove(old_attr)

        group.name = new_name
        self.report({'INFO'}, f"Renamed to '{new_name}'")
        return {'FINISHED'}


class INTRA10_OT_SaveLandmarkPreset(bpy.types.Operator):
    bl_idname = "intra10.save_landmark_preset"
    bl_label = "Save Landmark Preset"
    bl_options = {'REGISTER'}

    preset_name: StringProperty(name="Preset Name", default="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "preset_name", text="Name")

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object")
            return {'CANCELLED'}

        name = self.preset_name.strip()
        if not name:
            self.report({'WARNING'}, "Enter a preset name")
            return {'CANCELLED'}

        os.makedirs(PRESET_DIR, exist_ok=True)

        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name)
        filepath = os.path.join(PRESET_DIR, f"{safe_name}.json")

        was_edit = (obj.mode == 'EDIT')
        if was_edit:
            bpy.ops.object.mode_set(mode='OBJECT')

        success = landmark_presets.save_preset(filepath, obj, context.scene)

        if was_edit:
            bpy.ops.object.mode_set(mode='EDIT')

        if success:
            self.report({'INFO'}, f"Preset saved: {name}")
        else:
            self.report({'ERROR'}, "Failed to save preset")
        return {'FINISHED'}


class INTRA10_OT_LoadLandmarkPreset(bpy.types.Operator):
    bl_idname = "intra10.load_landmark_preset"
    bl_label = "Load Landmark Preset"
    bl_options = {'REGISTER'}

    preset_file: EnumProperty(
        name="Preset",
        description="Select a preset to load",
        items=lambda self, context: INTRA10_OT_LoadLandmarkPreset._get_preset_items(),
    )

    @staticmethod
    def _get_preset_items():
        items = []
        if os.path.isdir(PRESET_DIR):
            for f in sorted(os.listdir(PRESET_DIR)):
                if f.lower().endswith('.json'):
                    display = f[:-5]
                    items.append((f, display, f"Load {display}"))
        if not items:
            items.append(('NONE', "(No presets found)", ""))
        return items

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "preset_file", text="Preset")

    def execute(self, context):
        if self.preset_file == 'NONE':
            self.report({'WARNING'}, "No presets available")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object")
            return {'CANCELLED'}

        filepath = os.path.join(PRESET_DIR, self.preset_file)
        if not os.path.isfile(filepath):
            self.report({'ERROR'}, f"Preset file not found: {self.preset_file}")
            return {'CANCELLED'}

        was_edit = (obj.mode == 'EDIT')
        if was_edit:
            bpy.ops.object.mode_set(mode='OBJECT')

        success, msg = landmark_presets.load_preset(filepath, obj, context.scene)

        if was_edit:
            bpy.ops.object.mode_set(mode='EDIT')

        _redraw_viewports()
        if success:
            self.report({'INFO'}, msg)
        else:
            self.report({'ERROR'}, msg)
        return {'FINISHED'}


# ======================================================================
# Panel
# ======================================================================

class INTRA10_PT_Landmarks(bpy.types.Panel):
    bl_label = "Landmarks"
    bl_idname = "INTRA10_PT_landmarks"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Intra10 ToolKit"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.active_object

        is_on = landmark_draw.is_drawing()
        row = layout.row(align=True)
        row.operator(
            "intra10.toggle_landmark_draw",
            text="View Landmarks" if not is_on else "Hide Landmarks",
            icon='HIDE_OFF' if is_on else 'HIDE_ON',
            depress=is_on,
        )
        if is_on:
            row.prop(scene, "intra10_landmark_xray", text="", icon='XRAY')

        row = layout.row(align=True)
        row.prop(scene, "intra10_landmark_auto_mirror", text="Auto Mirror", icon='MOD_MIRROR', toggle=True)

        layout.separator()

        if not obj or obj.type != 'MESH':
            layout.label(text="Select a Mesh Object", icon='ERROR')
            return

        # --- Landmark Group List ---
        row = layout.row()
        row.template_list(
            "INTRA10_UL_landmark_group_list", "",
            scene, "intra10_landmark_groups",
            scene, "intra10_landmark_active_index",
            rows=4,
        )

        col = row.column(align=True)
        if context.mode == 'EDIT_MESH':
            col.operator("intra10.mark_landmark", text="", icon='ADD')
            col.operator("intra10.unmark_landmark", text="", icon='REMOVE')
            col.operator("intra10.select_landmark_edges", text="", icon='RESTRICT_SELECT_OFF')
        col.operator("intra10.remove_landmark_group", text="", icon='TRASH')
        col.context_pointer_set("scene", context.scene)
        col.menu("INTRA10_MT_remove_landmark_menu", text="", icon='DOWNARROW_HLT')
        col.operator("intra10.mirror_landmark_group", text="", icon='MOD_MIRROR')

        # --- .L / .R suffix buttons ---
        row_lr = layout.row(align=True)
        op_l = row_lr.operator("intra10.add_lr_suffix", text=".L")
        op_l.suffix = ".L"
        op_r = row_lr.operator("intra10.add_lr_suffix", text=".R")
        op_r.suffix = ".R"

        # --- Custom landmark add ---
        box = layout.box()
        row = box.row(align=True)
        row.prop(scene, "intra10_landmark_custom_name", text="")
        row.prop(scene, "intra10_landmark_custom_color", text="")
        box.operator("intra10.add_custom_landmark", text="Add Landmark", icon='ADD')

        # --- Line width ---
        layout.prop(scene, "intra10_landmark_line_width", text="Line Width")

        layout.separator()


class INTRA10_PT_LandmarksFacial(bpy.types.Panel):
    bl_label = "Facial"
    bl_idname = "INTRA10_PT_landmarks_facial"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Intra10 ToolKit"
    bl_parent_id = "INTRA10_PT_landmarks"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        flow = col.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)

        for name, color in FACIAL_LANDMARKS:
            op = flow.operator("intra10.add_landmark_group", text=name)
            op.part_name = name
            op.part_color = color


class INTRA10_PT_LandmarksBody(bpy.types.Panel):
    bl_label = "Body"
    bl_idname = "INTRA10_PT_landmarks_body"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Intra10 ToolKit"
    bl_parent_id = "INTRA10_PT_landmarks"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        col = layout.column(align=True)
        flow = col.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)

        for name, color in BODY_LANDMARKS:
            op = flow.operator("intra10.add_landmark_group", text=name)
            op.part_name = name
            op.part_color = color

        layout.separator()
        layout.label(text="Fingers / Toes:")

        col = layout.column(align=True)
        flow = col.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)

        for fname, rstart, rend, fcolor in FINGER_LANDMARKS:
            op = flow.operator("intra10.add_finger_landmark", text=f"{fname} Line")
            op.finger_name = fname
            op.finger_color = fcolor
            op.range_start = rstart
            op.range_end = rend


class INTRA10_PT_LandmarksPreset(bpy.types.Panel):
    bl_label = "Preset"
    bl_idname = "INTRA10_PT_landmarks_preset"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Intra10 ToolKit"
    bl_parent_id = "INTRA10_PT_landmarks"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("intra10.save_landmark_preset", text="Save Preset", icon='EXPORT')
        row.operator("intra10.load_landmark_preset", text="Load Preset", icon='IMPORT')


# ======================================================================
# Registration
# ======================================================================

classes = [
    INTRA10_PG_LandmarkGroup,
    INTRA10_UL_LandmarkGroupList,
    INTRA10_OT_ToggleLandmarkDraw,
    INTRA10_OT_MarkLandmark,
    INTRA10_OT_UnmarkLandmark,
    INTRA10_OT_SelectLandmarkEdges,
    INTRA10_OT_AddLandmarkGroup,
    INTRA10_OT_AddFingerLandmark,
    INTRA10_OT_AddCustomLandmark,
    INTRA10_OT_RemoveLandmarkGroup,
    INTRA10_OT_RemoveAllLandmarkGroups,
    INTRA10_MT_RemoveLandmarkMenu,
    INTRA10_OT_MirrorLandmarkGroup,
    INTRA10_OT_AddLRSuffix,
    INTRA10_OT_SaveLandmarkPreset,
    INTRA10_OT_LoadLandmarkPreset,
    INTRA10_PT_Landmarks,
    INTRA10_PT_LandmarksFacial,
    INTRA10_PT_LandmarksBody,
    INTRA10_PT_LandmarksPreset,
]


def register_properties():
    bpy.types.Scene.intra10_landmark_groups = CollectionProperty(
        type=INTRA10_PG_LandmarkGroup,
    )
    bpy.types.Scene.intra10_landmark_active_index = IntProperty(
        name="Active Landmark Group",
        default=0,
    )
    bpy.types.Scene.intra10_landmark_xray = BoolProperty(
        name="X-Ray Landmark",
        description="Show landmarks through the model",
        default=False,
    )
    bpy.types.Scene.intra10_landmark_auto_mirror = BoolProperty(
        name="Auto Mirror",
        description="Automatically mirror edges when marking",
        default=False,
    )
    bpy.types.Scene.intra10_landmark_custom_name = StringProperty(
        name="Custom Name",
        default="Custom Line",
    )
    bpy.types.Scene.intra10_landmark_custom_color = FloatVectorProperty(
        name="Custom Color",
        subtype='COLOR_GAMMA',
        size=4, min=0.0, max=1.0,
        default=DEFAULT_CUSTOM_COLOR,
    )
    bpy.types.Scene.intra10_landmark_line_width = FloatProperty(
        name="Line Width",
        description="Landmark line thickness",
        default=3.0,
        min=1.0,
        max=10.0,
        step=10,
        precision=1,
    )


def unregister_properties():
    landmark_draw.remove_draw()

    props = [
        "intra10_landmark_groups",
        "intra10_landmark_active_index",
        "intra10_landmark_xray",
        "intra10_landmark_auto_mirror",
        "intra10_landmark_custom_name",
        "intra10_landmark_custom_color",
        "intra10_landmark_line_width",
    ]
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)
