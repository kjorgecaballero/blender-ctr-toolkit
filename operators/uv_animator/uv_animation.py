import bpy
import json
import time
from bpy.types import Operator
from ...utils.uv_animator.uv_animator_utils import (
    get_current_uvs_from_mesh,
    get_active_texture_path,
    apply_uvs_to_object,
    get_target_object,
    sync_texture_items,
    is_valid_for_uv_animation
)
from ...utils.uv_animator.uv_block_utils import (
    get_uvs_from_material_block,
    apply_uvs_to_material,
    get_active_texture_from_material,
    get_constant_materials_on_object,
    is_valid_block
)
from .uv_collapse import _get_expanded_dict, _set_expanded_dict

def _redraw_ui(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()

def get_active_block(context):
    scene = context.scene
    if scene.uv_animator_mode == 'LEGACY':
        obj = get_target_object(context)
        if obj and obj.is_uv_animated:
            return obj, None
        return None, None
    else:
        key = scene.active_uv_block_key
        if not key:
            return None, None
        parts = key.split(":", 1)
        if len(parts) != 2:
            return None, None
        obj_name, block_id = parts
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            return None, None
        for block in obj.uv_animated_blocks:
            if block.block_id == block_id:
                return obj, block
        return None, None

def _get_target_items_for_assign(context):
    scene = context.scene
    toggles = json.loads(scene.uv_animator_group_toggles)
    active_groups = [name for name, active in toggles.items() if active]
    if active_groups:
        groups_dict = json.loads(scene.uv_animator_groups)
        items = []
        for group_name in active_groups:
            if group_name not in groups_dict:
                continue
            for key in groups_dict[group_name]:
                if scene.uv_animator_mode == 'LEGACY':
                    obj = bpy.data.objects.get(key)
                    if obj and obj.type == 'MESH' and obj.is_uv_animated:
                        items.append((obj, None))
                else:
                    parts = key.split(":", 1)
                    if len(parts) == 2:
                        obj = bpy.data.objects.get(parts[0])
                        if obj:
                            for block in obj.uv_animated_blocks:
                                if block.block_id == parts[1] and block.is_animated:
                                    items.append((obj, block))
                                    break
        seen = set()
        unique_items = []
        for obj, block in items:
            if scene.uv_animator_mode == 'LEGACY':
                identifier = obj.name
            else:
                identifier = f"{obj.name}:{block.block_id}"
            if identifier not in seen:
                seen.add(identifier)
                unique_items.append((obj, block))
        return unique_items
    else:
        obj, block = get_active_block(context)
        return [(obj, block)] if obj else []

class UV_OT_NewAnimation(Operator):
    bl_idname = "uv_animator.new_animation"
    bl_label = "New UV Animation (Legacy)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if scene.uv_animator_mode != 'LEGACY':
            self.report({'WARNING'}, "Switch to 'Single Object' mode for this operator.")
            return {'CANCELLED'}
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "Select at least one mesh object")
            return {'CANCELLED'}
        valid_objects = [obj for obj in selected if is_valid_for_uv_animation(obj)]
        if not valid_objects:
            self.report({'ERROR'}, "None of the selected objects are valid quadblocks/triblocks.")
            return {'CANCELLED'}
        expanded = _get_expanded_dict(scene)
        for obj in valid_objects:
            obj.uv_animation_frames.clear()
            obj.uv_texture_items.clear()
            obj.is_uv_animated = True
            obj.uv_animator_playback_enabled = True
            obj.uv_start_frame = 0
            obj.uv_frame_duration = 0
            expanded[obj.name] = True
            if obj == valid_objects[0]:
                scene.active_uv_object_name = obj.name
        _set_expanded_dict(scene, expanded)
        _redraw_ui(context)
        self.report({'INFO'}, f"Created {len(valid_objects)} legacy animation(s)")
        return {'FINISHED'}

class UV_OT_NewAnimationFromConstants(Operator):
    bl_idname = "uv_animator.new_animation_from_constants"
    bl_label = "New UV Animation (Constant Blocks)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        if scene.uv_animator_mode != 'CONSTANT':
            self.report({'WARNING'}, "Switch to 'Constant Blocks' mode for this operator.")
            return {'CANCELLED'}
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "Select at least one mesh object")
            return {'CANCELLED'}
        created = 0
        expanded = _get_expanded_dict(scene)
        for obj in selected:
            const_mats = get_constant_materials_on_object(obj)
            if not const_mats:
                self.report({'WARNING'}, f"Object '{obj.name}' has no constant materials.")
                continue
            if "quadblock_faces_map" not in obj and "triblock_faces_map" not in obj:
                self.report({'WARNING'}, f"Object '{obj.name}' has no block maps. Run 'Navigate' first.")
                continue
            has_nav = False
            for slot in obj.material_slots:
                if slot.material and slot.material.get("ctr_is_navigation_point", False):
                    has_nav = True
                    break
            if not has_nav:
                self.report({'WARNING'}, f"Object '{obj.name}' has no navigation point. Mark one material as nav point.")
                continue
            obj.uv_animated_blocks.clear()
            for mat_name, block_type, block_id in const_mats:
                if not is_valid_block(obj, mat_name, block_type, block_id):
                    self.report({'WARNING'}, f"Block '{mat_name}' is not a valid block. Skipping.")
                    continue
                new_block = obj.uv_animated_blocks.add()
                new_block.block_id = str(block_id)
                new_block.block_type = block_type.upper()
                new_block.material_name = mat_name
                new_block.is_animated = True
                new_block.playback_enabled = True
                new_block.start_frame = 0
                new_block.frame_duration = 0
            if obj.uv_animated_blocks:
                obj.has_constant_materials = True
                obj.is_uv_animated = True
                first = obj.uv_animated_blocks[0]
                scene.active_uv_block_key = f"{obj.name}:{first.block_id}"
                expanded[first.block_id] = True
                created += 1
        _set_expanded_dict(scene, expanded)
        _redraw_ui(context)
        self.report({'INFO'}, f"Created animations for {created} object(s) with constant blocks.")
        return {'FINISHED'}

class UV_OT_AssignFrame(Operator):
    bl_idname = "uv_animator.assign_frame"
    bl_label = "Assign Frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        target_items = _get_target_items_for_assign(context)
        if not target_items:
            self.report({'WARNING'}, "No active object/block or active group items found.")
            return {'CANCELLED'}

        assigned_count = 0
        skipped_count = 0
        errors = []

        for obj, block in target_items:
            if scene.uv_animator_mode == 'LEGACY':
                if not is_valid_for_uv_animation(obj):
                    errors.append(f"Object '{obj.name}' is not a valid block.")
                    skipped_count += 1
                    continue
                uvs, error = get_current_uvs_from_mesh(obj)
                if uvs is None:
                    errors.append(f"Object '{obj.name}': {error}")
                    skipped_count += 1
                    continue
                tex_path = get_active_texture_path(obj)
                if not obj.is_uv_animated:
                    obj.is_uv_animated = True
                    obj.uv_animator_playback_enabled = True
                frame = obj.uv_animation_frames.add()
                frame.uv_data = json.dumps(uvs)
                frame.texture_path = tex_path
                assigned_count += 1
                if len(obj.uv_animation_frames) == 1:
                    obj.uv_start_frame = 0
                sync_texture_items(obj)
            else:  # CONSTANT
                if not block:
                    errors.append(f"Block not found for object '{obj.name}'")
                    skipped_count += 1
                    continue
                uvs, error = get_uvs_from_material_block(obj, block.material_name)
                if uvs is None:
                    errors.append(f"Block '{block.block_id}': {error}")
                    skipped_count += 1
                    continue
                mat = bpy.data.materials.get(block.material_name)
                tex_path = get_active_texture_from_material(mat)
                frame = block.frames.add()
                frame.uv_data = json.dumps(uvs)
                frame.texture_path = tex_path
                assigned_count += 1
                if len(block.frames) == 1:
                    block.start_frame = 0
                if tex_path:
                    existing = [it for it in block.texture_items if it.texture_path == tex_path]
                    if not existing:
                        item = block.texture_items.add()
                        item.texture_path = tex_path
                        item.blend_mode = "0"

        if assigned_count > 0:
            msg = f"Frame assigned to {assigned_count} item(s)"
            if skipped_count > 0:
                msg += f" (skipped {skipped_count})"
            if errors:
                msg += f". Errors: {'; '.join(errors[:3])}"
            self.report({'INFO'}, msg)
        else:
            self.report({'ERROR'}, f"No frames assigned. Errors: {'; '.join(errors)}")
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_DeleteFrame(Operator):
    bl_idname = "uv_animator.delete_frame"
    bl_label = "Delete Frame"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")
    frame_index: bpy.props.IntProperty()

    def execute(self, context):
        scene = context.scene
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}
        if scene.uv_animator_mode == 'LEGACY':
            frames = obj.uv_animation_frames
            if 0 <= self.frame_index < len(frames):
                frames.remove(self.frame_index)
                if len(frames) == 0:
                    obj.uv_start_frame = 0
                elif obj.uv_start_frame == self.frame_index:
                    obj.uv_start_frame = 0
                elif obj.uv_start_frame > self.frame_index:
                    obj.uv_start_frame -= 1
                sync_texture_items(obj)
        else:
            block = None
            for b in obj.uv_animated_blocks:
                if b.block_id == self.block_id:
                    block = b
                    break
            if not block:
                return {'CANCELLED'}
            frames = block.frames
            if 0 <= self.frame_index < len(frames):
                frames.remove(self.frame_index)
                if len(frames) == 0:
                    block.start_frame = 0
                elif block.start_frame == self.frame_index:
                    block.start_frame = 0
                elif block.start_frame > self.frame_index:
                    block.start_frame -= 1
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_PlayPreview(Operator):
    bl_idname = "uv_animator.play_preview"
    bl_label = "Play Preview"
    _timer = None
    _frame_indices = {}
    _last_update = {}
    _active_instance = None

    @classmethod
    def is_playing(cls):
        return cls._active_instance is not None

    @classmethod
    def stop_active(cls, context):
        if cls._active_instance:
            cls._active_instance.cancel(context)
            return True
        return False

    def execute(self, context):
        scene = context.scene
        if UV_OT_PlayPreview.is_playing():
            self.report({'WARNING'}, "Preview already running")
            return {'CANCELLED'}
        self._frame_indices.clear()
        self._last_update.clear()
        current_time = time.perf_counter()
        if scene.uv_animator_mode == 'LEGACY':
            play_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.is_uv_animated and obj.uv_animator_playback_enabled]
            if not play_objs:
                self.report({'WARNING'}, "No legacy objects with playback enabled")
                return {'CANCELLED'}
            for obj in play_objs:
                if len(obj.uv_animation_frames) == 0:
                    continue
                start = obj.uv_start_frame
                if start >= len(obj.uv_animation_frames):
                    start = 0
                self._frame_indices[obj.name] = start
                self._last_update[obj.name] = current_time
        else:
            blocks = []
            for obj in bpy.data.objects:
                if obj.type != 'MESH':
                    continue
                for block in obj.uv_animated_blocks:
                    if block.is_animated and block.playback_enabled and len(block.frames) > 0:
                        blocks.append((obj, block))
            if not blocks:
                self.report({'WARNING'}, "No blocks with frames and playback enabled")
                return {'CANCELLED'}
            for obj, block in blocks:
                key = f"{obj.name}:{block.block_id}"
                start = block.start_frame
                if start >= len(block.frames):
                    start = 0
                self._frame_indices[key] = start
                self._last_update[key] = current_time
        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0/60.0, window=context.window)
        wm.modal_handler_add(self)
        UV_OT_PlayPreview._active_instance = self
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            current_time = time.perf_counter()
            scene = context.scene
            for key, idx in list(self._frame_indices.items()):
                obj = None
                if scene.uv_animator_mode == 'LEGACY':
                    obj = bpy.data.objects.get(key)
                    if not obj or not obj.is_uv_animated or not obj.uv_animator_playback_enabled:
                        del self._frame_indices[key]
                        del self._last_update[key]
                        continue
                    frames = obj.uv_animation_frames
                    if not frames:
                        continue
                    duration_mult = obj.uv_frame_duration
                    frame_duration = (duration_mult + 1) * 0.033
                    if current_time - self._last_update[key] >= frame_duration:
                        self._last_update[key] = current_time
                        if idx >= len(frames):
                            idx = 0
                        frame = frames[idx]
                        uvs = json.loads(frame.uv_data)
                        tex = frame.texture_path
                        apply_uvs_to_object(obj, uvs, tex)
                        next_idx = (idx + 1) % len(frames)
                        self._frame_indices[key] = next_idx
                else:
                    parts = key.split(":", 1)
                    if len(parts) != 2:
                        del self._frame_indices[key]
                        del self._last_update[key]
                        continue
                    obj_name, block_id = parts
                    obj = bpy.data.objects.get(obj_name)
                    if not obj:
                        del self._frame_indices[key]
                        del self._last_update[key]
                        continue
                    block = None
                    for b in obj.uv_animated_blocks:
                        if b.block_id == block_id:
                            block = b
                            break
                    if not block or not block.is_animated or not block.playback_enabled:
                        del self._frame_indices[key]
                        del self._last_update[key]
                        continue
                    frames = block.frames
                    if not frames:
                        continue
                    duration_mult = block.frame_duration
                    frame_duration = (duration_mult + 1) * 0.033
                    if current_time - self._last_update[key] >= frame_duration:
                        self._last_update[key] = current_time
                        if idx >= len(frames):
                            idx = 0
                        frame = frames[idx]
                        uvs = json.loads(frame.uv_data)
                        apply_uvs_to_material(obj, block.material_name, uvs)
                        next_idx = (idx + 1) % len(frames)
                        self._frame_indices[key] = next_idx
            return {'PASS_THROUGH'}
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def cancel(self, context):
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        if UV_OT_PlayPreview._active_instance == self:
            UV_OT_PlayPreview._active_instance = None
        self._frame_indices.clear()
        self._last_update.clear()

class UV_OT_StopPreview(Operator):
    bl_idname = "uv_animator.stop_preview"
    bl_label = "Stop Preview"
    def execute(self, context):
        if UV_OT_PlayPreview.stop_active(context):
            self.report({'INFO'}, "Preview stopped")
        else:
            self.report({'WARNING'}, "No preview running")
        return {'FINISHED'}

class UV_OT_DeleteAnimation(Operator):
    bl_idname = "uv_animator.delete_animation"
    bl_label = "Delete Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj, block = get_active_block(context)
        if not obj:
            self.report({'WARNING'}, "No active object/block.")
            return {'CANCELLED'}
        if scene.uv_animator_mode == 'LEGACY':
            UV_OT_PlayPreview.stop_active(context)
            obj.uv_animation_frames.clear()
            obj.uv_texture_items.clear()
            obj.is_uv_animated = False
            obj.uv_start_frame = 0
            obj.uv_frame_duration = 0
            expanded = _get_expanded_dict(scene)
            if obj.name in expanded:
                del expanded[obj.name]
            _set_expanded_dict(scene, expanded)
        else:
            if not block:
                return {'CANCELLED'}
            UV_OT_PlayPreview.stop_active(context)
            for i, b in enumerate(obj.uv_animated_blocks):
                if b.block_id == block.block_id:
                    obj.uv_animated_blocks.remove(i)
                    break
            if len(obj.uv_animated_blocks) == 0:
                obj.is_uv_animated = False
                obj.has_constant_materials = False
                scene.active_uv_block_key = ""
        _redraw_ui(context)
        self.report({'INFO'}, "Deleted animation")
        return {'FINISHED'}