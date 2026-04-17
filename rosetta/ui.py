# -*- coding: utf-8 -*-
"""
Rosetta — Blender N-Panel UI.
Maya UI(ui_maya.py) 구조를 미러링한다.
비즈니스 로직은 Controller에 위임, 이 파일은 View만 담당한다.
"""

import os
import sys
import traceback

import bpy
from bpy.props import (
    StringProperty, BoolProperty, FloatProperty,
    IntProperty, EnumProperty, CollectionProperty, PointerProperty,
)

_ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _find_rosetta_root():
    env = os.environ.get("ROSETTA_ROOT")
    if env and os.path.isdir(env):
        return env
    candidates = [
        os.path.normpath(os.path.join(_ADDON_DIR, "..", "..", "..", "other", "rosetta")),
        os.path.normpath(os.path.join(os.path.expanduser("~"), "Documents", "setting", "other", "rosetta")),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return ""

_ROSETTA_ROOT = _find_rosetta_root()
_WRAPPER_DIR = os.path.join(_ROSETTA_ROOT, "wrappers", "blender") if _ROSETTA_ROOT else ""
_COMMON_DIR = os.path.join(_ROSETTA_ROOT, "wrappers", "common") if _ROSETTA_ROOT else ""

for d in (_WRAPPER_DIR, _COMMON_DIR):
    if d not in sys.path:
        sys.path.insert(0, d)

SET_PREFIX_SRC = "rosetta_src_"
SET_PREFIX_TGT = "rosetta_tgt_"
_BL_CATEGORY = "Intra10 ToolKit"


def _import_rosetta():
    import importlib
    import adapter_blender as _ab
    import controller as _ctrl
    import model as _mdl
    importlib.reload(_ab)
    importlib.reload(_ctrl)
    importlib.reload(_mdl)
    return _ab.BlenderAdapter, _ctrl.RetargetController, _ctrl.AILandmarkController, _mdl.RetargetParams, _mdl.LandmarkPair


def _import_landmark_vp():
    import landmark_viewport as _lvp
    return _lvp


def _get_mesh_objects(self, context):
    return [(o.name, o.name, "") for o in bpy.data.objects if o.type == 'MESH']


# ══════════════════════════════════════════════════════════════
#  PropertyGroup
# ══════════════════════════════════════════════════════════════

class ROSETTA_PG_LandmarkEntry(bpy.types.PropertyGroup):
    name: StringProperty(name="Name")
    src_count: IntProperty(name="Src Vtx", default=0)
    tgt_count: IntProperty(name="Tgt Vtx", default=0)
    status: StringProperty(name="Status", default="")


class ROSETTA_PG_LandmarkGroup(bpy.types.PropertyGroup):
    name: StringProperty(name="Joint")
    label: StringProperty(name="Label")
    color: bpy.props.FloatVectorProperty(
        name="Color", subtype='COLOR', size=3,
        min=0.0, max=1.0, default=(0.8, 0.8, 0.8),
    )
    vtx_count: IntProperty(name="Vtx", default=0)
    mesh_count: IntProperty(name="Meshes", default=0)
    visible: BoolProperty(name="Visible", default=True)


class ROSETTA_PG_Settings(bpy.types.PropertyGroup):
    mode: EnumProperty(
        name="Mode",
        items=[
            ('SAME', "Same Topology", ""),
            ('DIFF', "Different Topology", ""),
        ],
        default='SAME',
    )
    source_body: StringProperty(name="Source Body")
    target_body: StringProperty(name="Target Body")

    landmark_mode: EnumProperty(
        name="Landmark Mode",
        items=[
            ('MANUAL', "Manual", ""),
            ('AI', "AI Auto", ""),
        ],
        default='MANUAL',
    )

    ai_mesh: StringProperty(name="AI Mesh")
    ai_gender: EnumProperty(
        name="Gender",
        items=[
            ('neutral', "Neutral", ""),
            ('male', "Male", ""),
            ('female', "Female", ""),
        ],
        default='neutral',
    )
    ai_include_fingers: BoolProperty(
        name="Include Fingers",
        default=False,
        description="손가락 관절도 포함",
    )
    ai_mirror: BoolProperty(
        name="Mirror (L→R)",
        default=False,
        description="왼쪽만 감지 후 오른쪽 대칭 생성",
    )
    ai_status: StringProperty(name="AI Status", default="")

    smoothing_lambda: FloatProperty(
        name="Smoothing Lambda", default=0.15,
        min=0.0, max=2.0, step=5,
    )
    collision_pushout: FloatProperty(
        name="Collision Pushout", default=0.003,
        min=0.0, max=0.05, step=1, precision=4,
    )
    collision_margin: FloatProperty(
        name="Collision Margin", default=0.002,
        min=0.0, max=0.05, step=1, precision=4,
    )
    num_control_points: IntProperty(
        name="Control Points", default=500,
        min=50, max=5000, step=100,
    )
    max_iterations: IntProperty(
        name="Max Iterations", default=10,
        min=1, max=100,
    )
    enable_proximity: BoolProperty(
        name="Enable Proximity / Collision", default=True,
        description="OFF: RBF + Laplacian only. ON: collision resolve + proximity",
    )

    set_name: StringProperty(name="Set Name", default="")
    log_text: StringProperty(name="Log", default="")


# ══════════════════════════════════════════════════════════════
#  UIList
# ══════════════════════════════════════════════════════════════

class ROSETTA_UL_LandmarkList(bpy.types.UIList):
    bl_idname = "ROSETTA_UL_landmark_list"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        row.label(text=item.name)
        row.label(text=str(item.src_count))
        row.label(text=str(item.tgt_count))
        row.label(text=item.status)


class ROSETTA_UL_AILandmarkGroups(bpy.types.UIList):
    bl_idname = "ROSETTA_UL_ai_lm_groups"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        row = layout.row(align=True)
        sub = row.row(align=True)
        sub.scale_x = 0.15
        ico = 'HIDE_OFF' if item.visible else 'HIDE_ON'
        op = sub.operator("rosetta.ai_lm_toggle_single", text="", icon=ico, emboss=False)
        op.group_name = item.name
        sub = row.row(align=True)
        sub.scale_x = 0.1
        sub.prop(item, "color", text="")
        row.label(text=item.label)
        sub = row.row(align=True)
        sub.alignment = 'RIGHT'
        sub.label(text=f"{item.vtx_count}v")


# ══════════════════════════════════════════════════════════════
#  Operators
# ══════════════════════════════════════════════════════════════

class ROSETTA_OT_PickMesh(bpy.types.Operator):
    bl_idname = "rosetta.pick_mesh"
    bl_label = "Pick Mesh"
    bl_options = {'REGISTER'}

    target_prop: StringProperty()

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select a mesh object")
            return {'CANCELLED'}
        settings = context.scene.rosetta_settings
        setattr(settings, self.target_prop, obj.name)
        return {'FINISHED'}


class ROSETTA_OT_AddGarment(bpy.types.Operator):
    bl_idname = "rosetta.add_garment"
    bl_label = "Add Selected as Garment"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        existing = {g.name for g in scene.rosetta_garments}
        added = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.name not in existing:
                item = scene.rosetta_garments.add()
                item.name = obj.name
                existing.add(obj.name)
                added += 1
        if added == 0:
            self.report({'WARNING'}, "No new mesh objects selected")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Added {added} garments")
        return {'FINISHED'}


class ROSETTA_OT_RemoveGarment(bpy.types.Operator):
    bl_idname = "rosetta.remove_garment"
    bl_label = "Remove Garment"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        idx = scene.rosetta_garment_index
        if 0 <= idx < len(scene.rosetta_garments):
            scene.rosetta_garments.remove(idx)
            scene.rosetta_garment_index = min(idx, len(scene.rosetta_garments) - 1)
        return {'FINISHED'}


class ROSETTA_OT_AddTarget(bpy.types.Operator):
    bl_idname = "rosetta.add_target"
    bl_label = "Add Selected as Target"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        existing = {t.name for t in scene.rosetta_targets}
        added = 0
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.name not in existing:
                item = scene.rosetta_targets.add()
                item.name = obj.name
                existing.add(obj.name)
                added += 1
        if added == 0:
            self.report({'WARNING'}, "No new mesh objects selected")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Added {added} targets")
        return {'FINISHED'}


class ROSETTA_OT_RemoveTarget(bpy.types.Operator):
    bl_idname = "rosetta.remove_target"
    bl_label = "Remove Target"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        idx = scene.rosetta_target_index
        if 0 <= idx < len(scene.rosetta_targets):
            scene.rosetta_targets.remove(idx)
            scene.rosetta_target_index = min(idx, len(scene.rosetta_targets) - 1)
        return {'FINISHED'}


class ROSETTA_OT_CreateLandmarkSet(bpy.types.Operator):
    """Create landmark vertex group from selection"""
    bl_idname = "rosetta.create_landmark_set"
    bl_label = "Create Set from Selection"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        settings = scene.rosetta_settings
        name = settings.set_name.strip()
        if not name:
            self.report({'WARNING'}, "Enter a set name")
            return {'CANCELLED'}

        src_obj = bpy.data.objects.get(settings.source_body)
        tgt_obj = bpy.data.objects.get(settings.target_body)
        if not src_obj or not tgt_obj:
            self.report({'WARNING'}, "Set Source Body and Target Body first")
            return {'CANCELLED'}

        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "Select vertices on a mesh")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Enter Edit Mode and select vertices")
            return {'CANCELLED'}

        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        selected_verts = [v.index for v in bm.verts if v.select]

        if not selected_verts:
            self.report({'WARNING'}, "No vertices selected")
            return {'CANCELLED'}

        if obj.name == src_obj.name:
            vg_name = f"{SET_PREFIX_SRC}{name}"
        elif obj.name == tgt_obj.name:
            vg_name = f"{SET_PREFIX_TGT}{name}"
        else:
            self.report({'WARNING'}, "Selection must be on Source or Target body")
            return {'CANCELLED'}

        vg = obj.vertex_groups.get(vg_name)
        if vg:
            obj.vertex_groups.remove(vg)
        vg = obj.vertex_groups.new(name=vg_name)
        vg.add(selected_verts, 1.0, 'REPLACE')

        settings.set_name = ""
        self.report({'INFO'}, f"Created '{vg_name}' ({len(selected_verts)} vertices)")
        return {'FINISHED'}


class ROSETTA_OT_ScanLandmarkSets(bpy.types.Operator):
    bl_idname = "rosetta.scan_landmark_sets"
    bl_label = "Scan Scene"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.rosetta_landmark_entries.clear()

        src_sets = {}
        tgt_sets = {}

        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            for vg in obj.vertex_groups:
                if vg.name.startswith(SET_PREFIX_SRC):
                    lm_name = vg.name[len(SET_PREFIX_SRC):]
                    count = sum(1 for v in obj.data.vertices
                                if any(g.group == vg.index for g in v.groups))
                    src_sets[lm_name] = count
                elif vg.name.startswith(SET_PREFIX_TGT):
                    lm_name = vg.name[len(SET_PREFIX_TGT):]
                    count = sum(1 for v in obj.data.vertices
                                if any(g.group == vg.index for g in v.groups))
                    tgt_sets[lm_name] = count

        all_names = sorted(set(src_sets) | set(tgt_sets))
        for name in all_names:
            entry = scene.rosetta_landmark_entries.add()
            entry.name = name
            entry.src_count = src_sets.get(name, 0)
            entry.tgt_count = tgt_sets.get(name, 0)
            if name in src_sets and name in tgt_sets:
                entry.status = "Matched"
            elif name in src_sets:
                entry.status = "Source only"
            else:
                entry.status = "Target only"

        self.report({'INFO'}, f"Found {len(all_names)} landmark sets")
        return {'FINISHED'}


class ROSETTA_OT_AIDetect(bpy.types.Operator):
    """Auto detect landmarks using AI (SMPL-X fitting) on a single mesh"""
    bl_idname = "rosetta.ai_detect"
    bl_label = "AI Detect"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        settings = scene.rosetta_settings

        mesh_name = settings.ai_mesh
        if not mesh_name:
            self.report({'WARNING'}, "Set AI Mesh first")
            return {'CANCELLED'}

        if not bpy.data.objects.get(mesh_name):
            self.report({'WARNING'}, f"Mesh '{mesh_name}' not found")
            return {'CANCELLED'}

        settings.ai_status = "Detecting..."

        try:
            BlenderAdapter, _, AILandmarkController, _, _ = _import_rosetta()
            adapter = BlenderAdapter()
            ai_ctrl = AILandmarkController(adapter=adapter, on_log=lambda m: print(f"[Rosetta AI] {m}"))
            landmarks, meta = ai_ctrl.detect_single(
                mesh_name=mesh_name,
                gender=settings.ai_gender,
                dcc_type="blender",
                include_fingers=settings.ai_include_fingers,
                mirror=settings.ai_mirror,
            )

            n_joints = len(set(lm.get('name') for lm in landmarks)) if landmarks else 0
            fit_time = meta.get('total_time_sec', 0)

            if landmarks:
                settings.ai_status = f"OK: {n_joints}j, {len(landmarks)}lm ({fit_time:.1f}s)"
                self.report({'INFO'}, settings.ai_status)

                try:
                    lvp = _import_landmark_vp()
                    joints = meta.get('joints', {})
                    lvp.store_landmarks_single(mesh_name, landmarks, joints=joints)
                    if joints:
                        lvp.create_joint_armatures()
                except Exception as ve:
                    print(f"[Rosetta AI] Viewport viz error: {ve}")
            else:
                settings.ai_status = "FAIL: no landmarks"
                self.report({'WARNING'}, settings.ai_status)

        except Exception as e:
            settings.ai_status = f"ERROR: {e}"
            self.report({'ERROR'}, str(e))

        return {'FINISHED'}


class ROSETTA_OT_AILandmarkSelect(bpy.types.Operator):
    """Select vertices of the active landmark group"""
    bl_idname = "rosetta.ai_lm_select"
    bl_label = "Select Group Vertices"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        idx = scene.rosetta_lm_group_index
        if idx < 0 or idx >= len(scene.rosetta_lm_groups):
            return {'CANCELLED'}
        group = scene.rosetta_lm_groups[idx]
        try:
            lvp = _import_landmark_vp()
            lvp.select_group_vertices(group.name)
            self.report({'INFO'}, f"Selected: {group.label}")
        except Exception as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}


class ROSETTA_OT_AILandmarkToggleSingle(bpy.types.Operator):
    """Toggle visibility of a specific landmark group"""
    bl_idname = "rosetta.ai_lm_toggle_single"
    bl_label = "Toggle"
    bl_options = {'REGISTER'}

    group_name: StringProperty()

    def execute(self, context):
        scene = context.scene
        for item in scene.rosetta_lm_groups:
            if item.name == self.group_name:
                item.visible = not item.visible
                try:
                    lvp = _import_landmark_vp()
                    lvp.set_group_visible(item.name, item.visible)
                except Exception:
                    pass
                break
        return {'FINISHED'}


class ROSETTA_OT_AILandmarkToggleAll(bpy.types.Operator):
    """Toggle all landmark groups visibility"""
    bl_idname = "rosetta.ai_lm_toggle_all"
    bl_label = "Toggle All"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            lvp = _import_landmark_vp()
            show = lvp.toggle_all_visibility()
            self.report({'INFO'}, f"All landmarks {'visible' if show else 'hidden'}")
        except Exception as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}


class ROSETTA_OT_AILandmarkClear(bpy.types.Operator):
    """Clear AI landmark markers (bones are preserved)"""
    bl_idname = "rosetta.ai_lm_clear"
    bl_label = "Clear Landmarks"
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            lvp = _import_landmark_vp()
            lvp.clear_landmarks()
        except Exception:
            pass
        context.scene.rosetta_settings.ai_status = ""
        self.report({'INFO'}, "AI landmarks cleared (bones kept)")
        return {'FINISHED'}


class ROSETTA_OT_AICreateArmatures(bpy.types.Operator):
    """Create temporary armatures showing SMPL-X joint positions"""
    bl_idname = "rosetta.ai_create_armatures"
    bl_label = "Show Joints"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            lvp = _import_landmark_vp()
            if not lvp.has_joint_data():
                self.report({'WARNING'}, "Run AI Detect first")
                return {'CANCELLED'}
            names = lvp.create_joint_armatures()
            self.report({'INFO'}, f"Created: {', '.join(names)}")
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        return {'FINISHED'}


class ROSETTA_OT_AIRemoveArmatures(bpy.types.Operator):
    """Remove Rosetta joint armatures"""
    bl_idname = "rosetta.ai_remove_armatures"
    bl_label = "Remove Joints"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            lvp = _import_landmark_vp()
            lvp.remove_joint_armatures()
            self.report({'INFO'}, "Joint armatures removed")
        except Exception as e:
            self.report({'ERROR'}, str(e))
        return {'FINISHED'}


class ROSETTA_OT_Execute(bpy.types.Operator):
    """Execute retarget pipeline"""
    bl_idname = "rosetta.execute"
    bl_label = "Execute Retarget"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        settings = scene.rosetta_settings
        log_lines = []

        def on_log(msg):
            log_lines.append(msg)
            print(f"[Rosetta] {msg}")

        src_body = settings.source_body
        if not src_body:
            self.report({'WARNING'}, "Set Source Body")
            return {'CANCELLED'}

        garments = [g.name for g in scene.rosetta_garments]
        if not garments:
            self.report({'WARNING'}, "Add at least one Garment")
            return {'CANCELLED'}

        try:
            BlenderAdapter, RetargetController, _, RetargetParams, LandmarkPair = _import_rosetta()
        except Exception as e:
            self.report({'ERROR'}, f"Failed to import Rosetta: {e}")
            return {'CANCELLED'}

        adapter = BlenderAdapter()
        ctrl = RetargetController(adapter=adapter, on_log=on_log)

        params = RetargetParams(
            same_topology=(settings.mode == 'SAME'),
            rbf_radius=0.0,
            rbf_strength=1.0,
            smoothing_lambda=settings.smoothing_lambda,
            collision_pushout=settings.collision_pushout,
            collision_margin=settings.collision_margin,
            max_iterations=settings.max_iterations,
            convergence_epsilon=1e-4,
            num_control_points=settings.num_control_points,
            enable_proximity=settings.enable_proximity,
        )

        if settings.mode == 'SAME':
            targets = [t.name for t in scene.rosetta_targets]
            if not targets:
                self.report({'WARNING'}, "Add at least one Target Body")
                return {'CANCELLED'}
            jobs = ctrl.build_batch_jobs(src_body, targets, garments, params)
        else:
            tgt_body = settings.target_body
            if not tgt_body:
                self.report({'WARNING'}, "Set Target Body")
                return {'CANCELLED'}

            landmarks = []
            if settings.landmark_mode == 'AI':
                landmarks = self._collect_ai_landmarks(scene, settings, src_body, tgt_body, LandmarkPair, on_log)
                if not landmarks:
                    self.report({'WARNING'}, "Run AI Detect on Source and Target meshes first")
                    return {'CANCELLED'}
            else:
                landmarks = self._collect_manual_landmarks(scene, settings)
                if not landmarks:
                    self.report({'WARNING'}, "No matched landmark sets found")
                    return {'CANCELLED'}
                on_log(f"[INFO] {len(landmarks)} pairs from manual sets")

            jobs = ctrl.build_single_jobs(src_body, tgt_body, garments, landmarks, params)

        errors = ctrl.validate(jobs)
        if errors:
            for e in errors:
                on_log(f"[VALIDATION] {e}")
            self.report({'WARNING'}, "Validation failed. Check console.")
            settings.log_text = "\n".join(log_lines)
            return {'CANCELLED'}

        try:
            results = ctrl.run_batch(jobs)
            success = sum(1 for r in results if r.success)
            fail = len(results) - success
            settings.log_text = "\n".join(log_lines)
            self.report({'INFO'}, f"Done: {success} success, {fail} fail")
        except Exception:
            on_log(f"[ERROR] {traceback.format_exc()}")
            settings.log_text = "\n".join(log_lines)
            self.report({'ERROR'}, "Execution failed. Check console.")
            return {'CANCELLED'}

        return {'FINISHED'}

    def _collect_ai_landmarks(self, scene, settings, src_body, tgt_body, LandmarkPair, on_log):
        """AI detect 결과를 src/tgt 메쉬별로 조회하여 joint name으로 페어링."""
        try:
            lvp = _import_landmark_vp()
        except Exception:
            return []

        meshes_data = lvp._landmark_data.get("meshes", {})
        src_data = meshes_data.get(src_body)
        tgt_data = meshes_data.get(tgt_body)
        if not src_data or not tgt_data:
            return []

        pairs = []
        src_groups = src_data["groups"]
        tgt_groups = tgt_data["groups"]

        for joint_name in src_groups:
            if joint_name not in tgt_groups:
                continue
            src_vids = src_groups[joint_name]
            tgt_vids = tgt_groups[joint_name]
            n = min(len(src_vids), len(tgt_vids))
            for i in range(n):
                pairs.append(LandmarkPair(
                    source_vertex_id=src_vids[i],
                    target_vertex_id=tgt_vids[i],
                    weight=1.0 if i == 0 else 0.6,
                ))

        on_log(f"[INFO] {len(pairs)} pairs from AI detection (src={src_body}, tgt={tgt_body})")
        return pairs

    def _collect_manual_landmarks(self, scene, settings):
        from model import LandmarkPair
        src_obj = bpy.data.objects.get(settings.source_body)
        tgt_obj = bpy.data.objects.get(settings.target_body)
        if not src_obj or not tgt_obj:
            return []

        src_groups = {}
        for vg in src_obj.vertex_groups:
            if vg.name.startswith(SET_PREFIX_SRC):
                lm_name = vg.name[len(SET_PREFIX_SRC):]
                vids = sorted(v.index for v in src_obj.data.vertices
                              if any(g.group == vg.index for g in v.groups))
                if vids:
                    src_groups[lm_name] = vids

        tgt_groups = {}
        for vg in tgt_obj.vertex_groups:
            if vg.name.startswith(SET_PREFIX_TGT):
                lm_name = vg.name[len(SET_PREFIX_TGT):]
                vids = sorted(v.index for v in tgt_obj.data.vertices
                              if any(g.group == vg.index for g in v.groups))
                if vids:
                    tgt_groups[lm_name] = vids

        pairs = []
        for name in sorted(set(src_groups) & set(tgt_groups)):
            s_ids = src_groups[name]
            t_ids = tgt_groups[name]
            n = min(len(s_ids), len(t_ids))
            for i in range(n):
                pairs.append(LandmarkPair(
                    source_vertex_id=s_ids[i],
                    target_vertex_id=t_ids[i],
                    weight=1.0,
                ))
        return pairs


# ══════════════════════════════════════════════════════════════
#  Panels
# ══════════════════════════════════════════════════════════════

class ROSETTA_PT_Main(bpy.types.Panel):
    bl_label = "Rosetta"
    bl_idname = "ROSETTA_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _BL_CATEGORY

    def draw(self, context):
        layout = self.layout
        settings = context.scene.rosetta_settings

        layout.prop(settings, "mode", expand=True)


class ROSETTA_PT_MeshSelection(bpy.types.Panel):
    bl_label = "Mesh Selection"
    bl_idname = "ROSETTA_PT_mesh_selection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _BL_CATEGORY
    bl_parent_id = "ROSETTA_PT_main"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.rosetta_settings

        row = layout.row(align=True)
        row.prop_search(settings, "source_body", bpy.data, "objects",
                        text="Source Body", icon='MESH_DATA')
        op = row.operator("rosetta.pick_mesh", text="", icon='EYEDROPPER')
        op.target_prop = "source_body"

        if settings.mode == 'SAME':
            layout.label(text="Target Bodies:")
            row = layout.row()
            row.template_list("UI_UL_list", "rosetta_targets",
                              scene, "rosetta_targets",
                              scene, "rosetta_target_index", rows=3)
            col = row.column(align=True)
            col.operator("rosetta.add_target", text="", icon='ADD')
            col.operator("rosetta.remove_target", text="", icon='REMOVE')
        else:
            row = layout.row(align=True)
            row.prop_search(settings, "target_body", bpy.data, "objects",
                            text="Target Body", icon='MESH_DATA')
            op = row.operator("rosetta.pick_mesh", text="", icon='EYEDROPPER')
            op.target_prop = "target_body"

        if settings.mode == 'DIFF':
            layout.separator()
            layout.prop(settings, "landmark_mode", text="Landmark Source", expand=True)

        layout.separator()
        layout.label(text="Garments:")
        row = layout.row()
        row.template_list("UI_UL_list", "rosetta_garments",
                          scene, "rosetta_garments",
                          scene, "rosetta_garment_index", rows=3)
        col = row.column(align=True)
        col.operator("rosetta.add_garment", text="", icon='ADD')
        col.operator("rosetta.remove_garment", text="", icon='REMOVE')


class ROSETTA_PT_Landmarks(bpy.types.Panel):
    """AI Landmark detection — independent from retarget workflow"""
    bl_label = "Rosetta Landmarks"
    bl_idname = "ROSETTA_PT_landmarks"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _BL_CATEGORY
    bl_order = 100

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        settings = scene.rosetta_settings

        box = layout.box()
        box.label(text="AI Auto Detect", icon='AUTO')
        row = box.row(align=True)
        row.prop_search(settings, "ai_mesh", bpy.data, "objects",
                        text="Mesh", icon='MESH_DATA')
        op = row.operator("rosetta.pick_mesh", text="", icon='EYEDROPPER')
        op.target_prop = "ai_mesh"

        box.prop(settings, "ai_gender", text="Gender")

        row = box.row(align=True)
        row.prop(settings, "ai_include_fingers", toggle=True)
        row.prop(settings, "ai_mirror", toggle=True)

        box.operator("rosetta.ai_detect", icon='PLAY')

        if settings.ai_status:
            status_box = layout.box()
            if settings.ai_status.startswith("OK"):
                status_box.label(text=settings.ai_status, icon='CHECKMARK')
            elif settings.ai_status.startswith("FAIL") or settings.ai_status.startswith("ERROR"):
                status_box.label(text=settings.ai_status, icon='ERROR')
            else:
                status_box.label(text=settings.ai_status, icon='TIME')

        if len(scene.rosetta_lm_groups) > 0:
            layout.separator()
            row = layout.row(align=True)
            row.label(text="Landmark Groups:", icon='GROUP_VERTEX')
            row.operator("rosetta.ai_lm_toggle_all", text="", icon='HIDE_OFF')

            layout.template_list(
                "ROSETTA_UL_ai_lm_groups", "",
                scene, "rosetta_lm_groups",
                scene, "rosetta_lm_group_index",
                rows=5,
            )
            row = layout.row(align=True)
            row.operator("rosetta.ai_lm_select", text="Select", icon='RESTRICT_SELECT_OFF')
            row.operator("rosetta.ai_lm_clear", text="Clear Landmarks", icon='X')

        layout.separator()
        row = layout.row(align=True)
        row.operator("rosetta.ai_create_armatures", text="Show Joints", icon='ARMATURE_DATA')
        row.operator("rosetta.ai_remove_armatures", text="Remove Joints", icon='TRASH')

        if settings.mode == 'DIFF':
            layout.separator()
            box = layout.box()
            box.label(text="Manual Landmarks", icon='VERTEXSEL')
            box.prop(settings, "set_name", text="Set Name")
            row = box.row(align=True)
            row.operator("rosetta.create_landmark_set", icon='ADD')
            row.operator("rosetta.scan_landmark_sets", icon='FILE_REFRESH')

            if len(scene.rosetta_landmark_entries) > 0:
                layout.template_list(
                    "ROSETTA_UL_landmark_list", "",
                    scene, "rosetta_landmark_entries",
                    scene, "rosetta_landmark_entry_index",
                    rows=4,
                )


class ROSETTA_PT_Parameters(bpy.types.Panel):
    bl_label = "Parameters"
    bl_idname = "ROSETTA_PT_parameters"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _BL_CATEGORY
    bl_parent_id = "ROSETTA_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.rosetta_settings

        layout.prop(settings, "smoothing_lambda")
        layout.prop(settings, "collision_pushout")
        layout.prop(settings, "collision_margin")
        layout.prop(settings, "num_control_points")
        layout.prop(settings, "max_iterations")
        layout.separator()
        layout.prop(settings, "enable_proximity")


class ROSETTA_PT_Execute(bpy.types.Panel):
    bl_label = "Execute"
    bl_idname = "ROSETTA_PT_execute"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = _BL_CATEGORY
    bl_parent_id = "ROSETTA_PT_main"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.rosetta_settings

        layout.operator("rosetta.execute", text="Execute Retarget", icon='PLAY')

        if settings.log_text:
            box = layout.box()
            box.label(text="Log:", icon='TEXT')
            lines = settings.log_text.split('\n')
            for line in lines[-10:]:
                box.label(text=line[:80])


# ══════════════════════════════════════════════════════════════
#  Registration
# ══════════════════════════════════════════════════════════════

classes = [
    ROSETTA_PG_LandmarkEntry,
    ROSETTA_PG_LandmarkGroup,
    ROSETTA_PG_Settings,
    ROSETTA_UL_LandmarkList,
    ROSETTA_UL_AILandmarkGroups,
    ROSETTA_OT_PickMesh,
    ROSETTA_OT_AddGarment,
    ROSETTA_OT_RemoveGarment,
    ROSETTA_OT_AddTarget,
    ROSETTA_OT_RemoveTarget,
    ROSETTA_OT_CreateLandmarkSet,
    ROSETTA_OT_ScanLandmarkSets,
    ROSETTA_OT_AIDetect,
    ROSETTA_OT_AILandmarkSelect,
    ROSETTA_OT_AILandmarkToggleSingle,
    ROSETTA_OT_AILandmarkToggleAll,
    ROSETTA_OT_AILandmarkClear,
    ROSETTA_OT_AICreateArmatures,
    ROSETTA_OT_AIRemoveArmatures,
    ROSETTA_OT_Execute,
    ROSETTA_PT_Main,
    ROSETTA_PT_MeshSelection,
    ROSETTA_PT_Landmarks,
    ROSETTA_PT_Parameters,
    ROSETTA_PT_Execute,
]


def register_properties():
    bpy.types.Scene.rosetta_settings = PointerProperty(type=ROSETTA_PG_Settings)
    bpy.types.Scene.rosetta_garments = CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.rosetta_garment_index = IntProperty(default=0)
    bpy.types.Scene.rosetta_targets = CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.rosetta_target_index = IntProperty(default=0)
    bpy.types.Scene.rosetta_landmark_entries = CollectionProperty(type=ROSETTA_PG_LandmarkEntry)
    bpy.types.Scene.rosetta_landmark_entry_index = IntProperty(default=0)
    bpy.types.Scene.rosetta_lm_groups = CollectionProperty(type=ROSETTA_PG_LandmarkGroup)
    bpy.types.Scene.rosetta_lm_group_index = IntProperty(default=0)


def unregister_properties():
    try:
        from landmark_viewport import remove_draw_handler
        remove_draw_handler()
    except Exception:
        pass
    props = [
        "rosetta_settings",
        "rosetta_garments",
        "rosetta_garment_index",
        "rosetta_targets",
        "rosetta_target_index",
        "rosetta_landmark_entries",
        "rosetta_landmark_entry_index",
        "rosetta_lm_groups",
        "rosetta_lm_group_index",
    ]
    for prop in props:
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)
