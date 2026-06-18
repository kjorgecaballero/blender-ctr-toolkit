import bpy
import json
from bpy.types import Operator


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