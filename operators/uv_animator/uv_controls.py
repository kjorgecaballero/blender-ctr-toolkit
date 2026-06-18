import bpy
import json
from bpy.types import Operator
from ...utils.uv_animator.uv_animator_utils import apply_uvs_to_object

# Toggle / Selection Operators

class UV_OT_ToggleExpand(Operator):
    bl_idname = "uv_animator.toggle_expand"
    bl_label = "Toggle Expand"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        expanded = json.loads(scene.uv_animator_expanded)
        expanded[self.object_name] = not expanded.get(self.object_name, False)
        scene.uv_animator_expanded = json.dumps(expanded)
        return {'FINISHED'}

class UV_OT_TogglePlayback(Operator):
    bl_idname = "uv_animator.toggle_playback"
    bl_label = "Toggle Playback"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if obj:
            obj.uv_animator_playback_enabled = not obj.uv_animator_playback_enabled
            state = "enabled" if obj.uv_animator_playback_enabled else "disabled"
            self.report({'INFO'}, f"Playback {state} for '{obj.name}'")
        return {'FINISHED'}

class UV_OT_ToggleGroupSelection(Operator):
    bl_idname = "uv_animator.toggle_group_selection"
    bl_label = "Toggle Group Selection"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if obj:
            obj.uv_selected_for_group = not obj.uv_selected_for_group
            state = "selected" if obj.uv_selected_for_group else "deselected"
            self.report({'INFO'}, f"{obj.name} {state} for grouping")
        return {'FINISHED'}

class UV_OT_SetActiveUVObject(Operator):
    bl_idname = "uv_animator.set_active_uv_object"
    bl_label = "Set Active UV Object"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        context.scene.active_uv_object_name = self.object_name
        self.report({'INFO'}, f"Active: {self.object_name}")
        return {'FINISHED'}

# Set Start Frame (with immediate preview)

class UV_OT_SetStartFrame(Operator):
    bl_idname = "uv_animator.set_start_frame"
    bl_label = "Set Start Frame"
    bl_description = "Set this frame as the start frame for playback (toggle off to disable)"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    frame_index: bpy.props.IntProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}
        
        if obj.uv_start_frame == self.frame_index:
            obj.uv_start_frame = -1
        else:
            obj.uv_start_frame = self.frame_index
        
        # Apply the selected frame immediately so the user sees the result
        frames = obj.uv_animation_frames
        if self.frame_index < len(frames):
            frame = frames[self.frame_index]
            uvs = json.loads(frame.uv_data)
            tex = frame.texture_path
            apply_uvs_to_object(obj, uvs, tex)
        
        return {'FINISHED'}