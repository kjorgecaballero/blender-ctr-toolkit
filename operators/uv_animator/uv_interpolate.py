import bpy
import bpy_extras.io_utils
import json
import re
import os
from bpy.types import Operator, Menu
from ...utils.uv_animator.uv_animator_utils import get_current_uvs_from_mesh, get_active_texture_path, sync_texture_items

# Helper to redraw UI
def _redraw_ui(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()

# GROUP COLLECTIONS

class UV_OT_AutoGroupCollections(Operator):
    """Organize selected objects into numbered collections"""
    bl_idname = "uv_animator.auto_group_collections"
    bl_label = "Group Collections"
    bl_options = {'REGISTER', 'UNDO'}

    base_name: bpy.props.StringProperty(
        name="Base Name",
        description="Base name for the animation sequence",
        default="Animation"
    )

    group_by_material: bpy.props.BoolProperty(
        name="Group by Material",
        description="Group objects based on their active material name (pattern: *_frameXXX) instead of object names",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.enabled = not self.group_by_material
        row.prop(self, "base_name")
        layout.prop(self, "group_by_material")
        
        if self.group_by_material:
            box = layout.box()
            box.label(text="Material Pattern: *_frameXXX", icon='INFO')
            box.label(text="Example: 'texrex_frame01', 'texrex_frame02'", icon='BLANK1')

    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "No MESH objects selected")
            return {'CANCELLED'}

        # MODE 1: GROUP BY OBJECT NAME
        if not self.group_by_material:
            selected.sort(key=lambda o: o.name)
            parent = bpy.data.collections.get(self.base_name)
            if not parent:
                parent = bpy.data.collections.new(self.base_name)
                context.scene.collection.children.link(parent)

            for idx, obj in enumerate(selected, 1):
                coll_name = f"{self.base_name}_AnimSeqTex_Frame{idx:03d}"
                coll = bpy.data.collections.get(coll_name)
                if not coll:
                    coll = bpy.data.collections.new(coll_name)
                    parent.children.link(coll)

                for old_coll in obj.users_collection:
                    old_coll.objects.unlink(obj)
                coll.objects.link(obj)

            self.report({'INFO'}, f"Grouped {len(selected)} objects by name into '{self.base_name}'")
            return {'FINISHED'}

        # MODE 2: GROUP BY MATERIAL NAME
        pattern = re.compile(r'^(.*?)_frame(\d+)$', re.IGNORECASE)
        material_groups = {}

        for obj in selected:
            mat = obj.active_material
            if not mat:
                self.report({'WARNING'}, f"Object '{obj.name}' has no active material. Skipping.")
                continue

            match = pattern.match(mat.name)
            if not match:
                self.report({'WARNING'}, f"Object '{obj.name}' material '{mat.name}' doesn't match pattern '*_frameXXX'. Skipping.")
                continue

            base = match.group(1)
            frame_num = int(match.group(2))
            key = (base, frame_num)
            material_groups.setdefault(key, []).append(obj)

        if not material_groups:
            self.report({'WARNING'}, "No objects matched the material pattern. Check your material names.")
            return {'CANCELLED'}

        processed_count = 0
        for (base, frame_num), objects in material_groups.items():
            parent = bpy.data.collections.get(base)
            if not parent:
                parent = bpy.data.collections.new(base)
                context.scene.collection.children.link(parent)

            coll_name = f"{base}_AnimSeqTex_Frame{frame_num:03d}"
            coll = bpy.data.collections.get(coll_name)
            if not coll:
                coll = bpy.data.collections.new(coll_name)
                parent.children.link(coll)

            for obj in objects:
                for old_coll in obj.users_collection:
                    old_coll.objects.unlink(obj)
                coll.objects.link(obj)
                processed_count += 1

        base_animations = json.loads(context.scene.uv_animator_base_animations)
        for (base, frame_num), objects in material_groups.items():
            if base not in base_animations:
                all_frames = []
                for (b, f), objs in material_groups.items():
                    if b == base:
                        all_frames.append(f)
                all_frames.sort()
                collections = [f"{base}_AnimSeqTex_Frame{num:03d}" for num in all_frames]
                base_animations[base] = {
                    "collections": collections,
                    "frame_count": len(collections),
                    "expanded": False
                }
        context.scene.uv_animator_base_animations = json.dumps(base_animations)

        self.report({'INFO'}, f"Grouped {processed_count} objects by material into {len(material_groups)} frame(s).")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=350)



# FIND COLLECTIONS

class UV_OT_AutoFindCollections(Operator):
    """Find collections matching the pattern and register them as base animations"""
    bl_idname = "uv_animator.auto_find_collections"
    bl_label = "Find Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        pattern = re.compile(r"^(.*)_AnimSeqTex_Frame(\d+)$")
        found = {}

        for coll in bpy.data.collections:
            match = pattern.match(coll.name)
            if match:
                base = match.group(1)
                frame_num = int(match.group(2))
                found.setdefault(base, []).append(frame_num)

        base_animations = {}
        for base, frames in found.items():
            frames.sort()
            collections = [f"{base}_AnimSeqTex_Frame{num:03d}" for num in frames]
            base_animations[base] = {
                "collections": collections,
                "frame_count": len(collections),
                "expanded": False
            }

        context.scene.uv_animator_base_animations = json.dumps(base_animations)

        if base_animations:
            self.report({'INFO'}, f"Found {len(base_animations)} base animation(s)")
        else:
            self.report({'WARNING'}, "No valid collections found")

        return {'FINISHED'}



# SELECT SECONDARY TEXTURE

class UV_OT_AutoSelectSecondaryTexture(Operator, bpy_extras.io_utils.ImportHelper):
    """Select a secondary texture for interpolation"""
    bl_idname = "uv_animator.auto_select_secondary_texture"
    bl_label = "Select Secondary Texture"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: bpy.props.StringProperty(
        default="*.png;*.jpg;*.jpeg;*.bmp;*.tga",
        options={'HIDDEN'}
    )

    def execute(self, context):
        context.scene.uv_animator_secondary_texture = bpy.path.abspath(self.filepath)
        self.report({'INFO'}, f"Secondary texture set to: {os.path.basename(self.filepath)}")
        return {'FINISHED'}



# MENU FOR ANIMATION SELECTION

class UV_MT_AutoAnimationMenu(Menu):
    bl_label = "Select Animation"
    bl_idname = "UV_MT_AutoAnimationMenu"

    def draw(self, context):
        layout = self.layout
        base_animations = json.loads(context.scene.uv_animator_base_animations)
        for name in base_animations.keys():
            op = layout.operator("uv_animator.auto_select_animation", text=name)
            op.anim_name = name


class UV_OT_AutoSelectAnimation(Operator):
    """Select an animation to process"""
    bl_idname = "uv_animator.auto_select_animation"
    bl_label = "Select Animation"
    bl_options = {'REGISTER', 'UNDO'}

    anim_name: bpy.props.StringProperty()

    def execute(self, context):
        context.scene.uv_animator_selected_animation = self.anim_name
        self.report({'INFO'}, f"Selected animation: {self.anim_name}")
        return {'FINISHED'}



# GENERATE OPERATOR (WITH POPUP FOR REVERT)

class UV_OT_AutoAssignInterpolation(Operator):
    """Generate UV animation by interpolating textures between keyframes"""
    bl_idname = "uv_animator.auto_assign_interpolation"
    bl_label = "Generate"
    bl_options = {'REGISTER', 'UNDO'}

    # This property will be shown in the popup
    revert: bpy.props.BoolProperty(
        name="Revert",
        description="Add reverse sequence after the forward sequence",
        default=False
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "revert")
        
        box = layout.box()
        box.label(text="This will generate animation frames for all objects", icon='INFO')
        box.label(text="in the selected animation, using the secondary texture", icon='BLANK1')
        box.label(text="for non-keyframes. Objects will be auto-grouped.", icon='BLANK1')

    def invoke(self, context, event):
        # Load current revert state from scene
        self.revert = context.scene.uv_animator_revert_interpolation
        return context.window_manager.invoke_props_dialog(self, width=350)

    def execute(self, context):
        scene = context.scene
        
        # Save revert state back to scene (so it persists)
        scene.uv_animator_revert_interpolation = self.revert
        
        secondary_tex = scene.uv_animator_secondary_texture
        if not secondary_tex:
            self.report({'WARNING'}, "No secondary texture selected")
            return {'CANCELLED'}

        base_animations = json.loads(scene.uv_animator_base_animations)
        selected_anim = scene.uv_animator_selected_animation
        if not selected_anim or selected_anim not in base_animations:
            self.report({'WARNING'}, "No base animation selected")
            return {'CANCELLED'}

        anim_data = base_animations[selected_anim]
        collections = anim_data["collections"]
        total_frames = len(collections)
        revert = self.revert
        total_animation_frames = total_frames * 2 if revert else total_frames

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        processed_objects = []

        for idx, coll_name in enumerate(collections):
            coll = bpy.data.collections.get(coll_name)
            if not coll:
                continue

            for obj in coll.objects:
                if obj.type != 'MESH':
                    continue

                if not obj.is_uv_animated:
                    obj.is_uv_animated = True
                    obj.uv_animator_playback_enabled = True
                    obj.uv_start_frame = 0
                    obj.uv_frame_duration = 0
                    obj.uv_animation_frames.clear()
                    obj.uv_texture_items.clear()

                uvs, error = get_current_uvs_from_mesh(obj)
                if uvs is None:
                    self.report({'WARNING'}, f"Object '{obj.name}': {error}")
                    continue

                primary_tex = get_active_texture_path(obj)
                if not primary_tex:
                    self.report({'WARNING'}, f"Object '{obj.name}' has no active texture")
                    continue

                for frame_idx in range(total_animation_frames):
                    if revert and frame_idx >= total_frames:
                        effective = total_animation_frames - frame_idx - 1
                    else:
                        effective = frame_idx

                    is_keyframe = (effective == idx)

                    frame = obj.uv_animation_frames.add()
                    frame.uv_data = json.dumps(uvs)
                    frame.texture_path = primary_tex if is_keyframe else secondary_tex

                sync_texture_items(obj)
                processed_objects.append(obj.name)

        if not processed_objects:
            self.report({'WARNING'}, "No objects were processed")
            return {'CANCELLED'}

        # Auto-group
        groups = json.loads(scene.uv_animator_groups)

        for group_name, members in list(groups.items()):
            groups[group_name] = [key for key in members if key not in processed_objects]
            if not groups[group_name]:
                del groups[group_name]

        if selected_anim not in groups:
            groups[selected_anim] = []
        for obj_name in processed_objects:
            if obj_name not in groups[selected_anim]:
                groups[selected_anim].append(obj_name)

        scene.uv_animator_groups = json.dumps(groups)
        scene.uv_animator_active_group = selected_anim

        _redraw_ui(context)

        self.report({'INFO'}, f"Generated {total_animation_frames} frames for '{selected_anim}' (Revert: {'ON' if revert else 'OFF'}) on {len(processed_objects)} object(s). Grouped as '{selected_anim}'.")
        return {'FINISHED'}



# SCAN TIMELINE

class UV_OT_ScanTimeline(Operator):
    """Scan the timeline and assign UV frames for each selected object across all frames"""
    bl_idname = "uv_animator.scan_timeline"
    bl_label = "Scan Timeline"
    bl_description = "Scan the timeline and capture UVs for selected objects at each frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        start_frame = scene.frame_start
        end_frame = scene.frame_end

        mesh_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objs:
            self.report({'WARNING'}, "No mesh objects selected.")
            return {'CANCELLED'}

        mesh_objs.sort(key=lambda o: o.name)
        group_name = f"Timeline_{start_frame}_{end_frame}"

        for obj in mesh_objs:
            obj.is_uv_animated = True
            obj.uv_animator_playback_enabled = True
            obj.uv_start_frame = 0
            obj.uv_frame_duration = 0
            obj.uv_animation_frames.clear()
            obj.uv_texture_items.clear()

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        total_frames = end_frame - start_frame + 1
        progress = 0

        for frame in range(start_frame, end_frame + 1):
            context.scene.frame_set(frame)

            for obj in mesh_objs:
                uvs, error = get_current_uvs_from_mesh(obj)
                if uvs is None:
                    self.report({'WARNING'}, f"Frame {frame}: {error} for {obj.name}")
                    continue

                tex_path = get_active_texture_path(obj)

                frame_data = obj.uv_animation_frames.add()
                frame_data.uv_data = json.dumps(uvs)
                frame_data.texture_path = tex_path

            progress += 1
            if progress % 10 == 0:
                print(f"Scanning timeline: {progress}/{total_frames}")

        for obj in mesh_objs:
            sync_texture_items(obj)

        groups = json.loads(scene.uv_animator_groups)
        obj_names = [o.name for o in mesh_objs]

        for group_name_existing, members in list(groups.items()):
            groups[group_name_existing] = [key for key in members if key not in obj_names]
            if not groups[group_name_existing]:
                del groups[group_name_existing]

        if group_name not in groups:
            groups[group_name] = []
        for name in obj_names:
            if name not in groups[group_name]:
                groups[group_name].append(name)

        scene.uv_animator_groups = json.dumps(groups)
        scene.uv_animator_active_group = group_name

        _redraw_ui(context)

        self.report({'INFO'}, f"Scanned timeline from {start_frame} to {end_frame}. Captured {total_frames} frames for {len(mesh_objs)} object(s). Grouped as '{group_name}'.")
        return {'FINISHED'}