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

# Main Animation Operators

def get_target_objects(context):
    active_obj = get_target_object(context)
    return [active_obj] if active_obj else []

class UV_OT_NewAnimation(Operator):
    bl_idname = "uv_animator.new_animation"
    bl_label = "New UV Animation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not selected:
            self.report({'WARNING'}, "Select at least one mesh object")
            return {'CANCELLED'}

        # Filter objects that are valid for UV animation (Quadblock/Triblock with good UVs)
        valid_objects = [obj for obj in selected if is_valid_for_uv_animation(obj)]
        invalid_objects = [obj for obj in selected if obj not in valid_objects]

        if not valid_objects:
            self.report({'ERROR'}, "None of the selected objects are valid Quadblocks or Triblocks with valid UVs.")
            return {'CANCELLED'}

        if invalid_objects:
            self.report({'WARNING'}, f"Skipped {len(invalid_objects)} object(s) because they are not valid Quadblocks/Triblocks or have UV issues.")

        expanded = json.loads(context.scene.uv_animator_expanded)
        for obj in valid_objects:
            obj.uv_animation_frames.clear()
            obj.uv_texture_items.clear()
            obj.is_uv_animated = True
            obj.uv_animator_playback_enabled = True
            obj.uv_start_frame = 0
            obj.uv_frame_duration = 0
            expanded[obj.name] = True
            if obj == valid_objects[0]:
                context.scene.active_uv_object_name = obj.name

        context.scene.uv_animator_expanded = json.dumps(expanded)
        self.report({'INFO'}, f"Created animations for {len(valid_objects)} valid object(s)")
        return {'FINISHED'}

class UV_OT_AssignFrame(Operator):
    bl_idname = "uv_animator.assign_frame"
    bl_label = "Assign Frame"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        active_obj = get_target_object(context)
        if not active_obj:
            self.report({'WARNING'}, "No active target object")
            return {'CANCELLED'}

        target_objects = []
        toggles = json.loads(scene.uv_animator_group_toggles)
        groups_dict = json.loads(scene.uv_animator_groups)

        active_groups = [name for name, active in toggles.items() if active]

        if active_groups:
            obj_names_in_groups = set()
            for g_name in active_groups:
                if g_name in groups_dict:
                    obj_names_in_groups.update(groups_dict[g_name])

            for name in obj_names_in_groups:
                obj = bpy.data.objects.get(name)
                if obj and obj.type == 'MESH':
                    target_objects.append(obj)

            if active_obj not in target_objects:
                self.report({'WARNING'}, f"Active object '{active_obj.name}' is not in any active group. No frames assigned.")
                return {'CANCELLED'}
        else:
            target_objects = [active_obj]

        # Initial filter for valid objects (type + UVs)
        valid_targets = [obj for obj in target_objects if is_valid_for_uv_animation(obj)]
        invalid_targets = [obj for obj in target_objects if obj not in valid_targets]

        # If there are no valid objects, show the error first, then the warning (so warning is last)
        if not valid_targets:
            self.report({'ERROR'}, "No valid objects to assign frame.")
            if invalid_targets:
                self.report({'WARNING'}, f"Skipped {len(invalid_targets)} object(s) because they are not valid Quadblocks/Triblocks or have UV issues.")
            return {'CANCELLED'}

        # If there are valid objects, show the warning (if any) before the success message
        if invalid_targets:
            self.report({'WARNING'}, f"Skipped {len(invalid_targets)} object(s) because they are not valid Quadblocks/Triblocks or have UV issues.")

        assigned_count = 0
        for obj in valid_targets:
            # Re-validate at the moment of assignment to catch any UV changes made in Edit Mode
            if not is_valid_for_uv_animation(obj):
                self.report({'ERROR'}, f"Cannot assign frame to '{obj.name}' because UVs are invalid (out of range, degenerated, or triblock pattern incorrect).")
                continue

            uvs, error = get_current_uvs_from_mesh(obj)
            if uvs is None:
                self.report({'WARNING'}, f"Can't capture UVs from {obj.name}: {error}")
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

        self.report({'INFO'}, f"Frame assigned to {assigned_count} object(s)")
        return {'FINISHED'}

class UV_OT_DeleteFrame(Operator):
    bl_idname = "uv_animator.delete_frame"
    bl_label = "Delete Frame"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    frame_index: bpy.props.IntProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            self.report({'WARNING'}, "Object not found")
            return {'CANCELLED'}
        frames = obj.uv_animation_frames
        if 0 <= self.frame_index < len(frames):
            frames.remove(self.frame_index)
            
            if len(frames) == 0:
                obj.uv_start_frame = 0
            else:
                if obj.uv_start_frame == self.frame_index:
                    obj.uv_start_frame = 0
                elif obj.uv_start_frame > self.frame_index:
                    obj.uv_start_frame -= 1
                if obj.uv_start_frame >= len(frames):
                    obj.uv_start_frame = len(frames) - 1
            
            sync_texture_items(obj)
            self.report({'INFO'}, f"Frame {self.frame_index} deleted from '{obj.name}'")
        else:
            self.report({'WARNING'}, "Invalid frame index")
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
        play_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.is_uv_animated and obj.uv_animator_playback_enabled]
        if not play_objects:
            self.report({'WARNING'}, "No objects with playback enabled")
            return {'CANCELLED'}

        has_frames = any(len(obj.uv_animation_frames) > 0 for obj in play_objects)
        if not has_frames:
            self.report({'WARNING'}, "No frames to play")
            return {'CANCELLED'}

        if UV_OT_PlayPreview.is_playing():
            self.report({'WARNING'}, "Preview already running")
            return {'CANCELLED'}

        self._frame_indices = {}
        self._last_update = {}
        current_time = time.perf_counter()
        
        for obj in play_objects:
            frames = obj.uv_animation_frames
            if len(frames) == 0:
                continue
            start_idx = obj.uv_start_frame
            if start_idx >= len(frames):
                start_idx = 0
            self._frame_indices[obj.name] = start_idx
            self._last_update[obj.name] = current_time

        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0/60.0, window=context.window)
        wm.modal_handler_add(self)
        UV_OT_PlayPreview._active_instance = self
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'TIMER':
            current_time = time.perf_counter()
            
            for obj_name, idx in list(self._frame_indices.items()):
                obj = bpy.data.objects.get(obj_name)
                if not obj or not obj.is_uv_animated or not obj.uv_animator_playback_enabled:
                    del self._frame_indices[obj_name]
                    del self._last_update[obj_name]
                    continue
                
                frames = obj.uv_animation_frames
                if not frames:
                    continue
                
                duration_multiplier = obj.uv_frame_duration
                frame_duration = (duration_multiplier + 1) * 0.033
                
                if current_time - self._last_update[obj_name] >= frame_duration:
                    self._last_update[obj_name] = current_time
                    
                    if idx >= len(frames):
                        idx = 0
                    frame = frames[idx]
                    uvs = json.loads(frame.uv_data)
                    tex = frame.texture_path
                    apply_uvs_to_object(obj, uvs, tex)
                    
                    next_idx = (idx + 1) % len(frames)
                    self._frame_indices[obj_name] = next_idx
            
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
        obj = get_target_object(context)
        if not obj:
            self.report({'WARNING'}, "No target object")
            return {'CANCELLED'}
        UV_OT_PlayPreview.stop_active(context)
        obj.uv_animation_frames.clear()
        obj.uv_texture_items.clear()
        obj.is_uv_animated = False
        obj.uv_start_frame = 0
        obj.uv_frame_duration = 0
        expanded = json.loads(context.scene.uv_animator_expanded)
        if obj.name in expanded:
            del expanded[obj.name]
        context.scene.uv_animator_expanded = json.dumps(expanded)
        self.report({'INFO'}, f"Deleted animation from '{obj.name}'")
        return {'FINISHED'}