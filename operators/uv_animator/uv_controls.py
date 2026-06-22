import bpy
import json
from bpy.types import Operator
from ...utils.uv_animator.uv_animator_utils import apply_uvs_to_object
from ...utils.uv_animator.uv_block_utils import (
    apply_uvs_to_material,
    get_faces_with_material,
    get_uvs_from_material_block
)
from .uv_animation import get_active_block
from .uv_collapse import _get_expanded_dict, _set_expanded_dict

def _redraw_ui(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()

class UV_OT_ToggleExpand(Operator):
    bl_idname = "uv_animator.toggle_expand"
    bl_label = "Toggle Expand"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")

    def execute(self, context):
        scene = context.scene
        expanded = _get_expanded_dict(scene)
        if self.block_id:
            key = f"{self.object_name}:{self.block_id}"
        else:
            key = self.object_name
        expanded[key] = not expanded.get(key, False)
        _set_expanded_dict(scene, expanded)
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_TogglePlayback(Operator):
    bl_idname = "uv_animator.toggle_playback"
    bl_label = "Toggle Playback"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")

    def execute(self, context):
        scene = context.scene
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}
        if scene.uv_animator_mode == 'LEGACY':
            obj.uv_animator_playback_enabled = not obj.uv_animator_playback_enabled
        else:
            for block in obj.uv_animated_blocks:
                if block.block_id == self.block_id:
                    block.playback_enabled = not block.playback_enabled
                    break
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_ToggleGroupSelection(Operator):
    bl_idname = "uv_animator.toggle_group_selection"
    bl_label = "Toggle Group Selection"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")

    def execute(self, context):
        scene = context.scene
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}
        if scene.uv_animator_mode == 'LEGACY':
            obj.uv_selected_for_group = not obj.uv_selected_for_group
        else:
            for block in obj.uv_animated_blocks:
                if block.block_id == self.block_id:
                    block.selected_for_group = not block.selected_for_group
                    break
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_SetActiveUVObject(Operator):
    bl_idname = "uv_animator.set_active_uv_object"
    bl_label = "Set Active UV Object/Block"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")

    def execute(self, context):
        scene = context.scene
        if scene.uv_animator_mode == 'LEGACY':
            scene.active_uv_object_name = self.object_name
        else:
            scene.active_uv_block_key = f"{self.object_name}:{self.block_id}"
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_SetStartFrame(Operator):
    bl_idname = "uv_animator.set_start_frame"
    bl_label = "Set Start Frame"
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
            if not frames:
                return {'CANCELLED'}
            obj.uv_start_frame = self.frame_index
            if self.frame_index < len(frames):
                frame = frames[self.frame_index]
                uvs = json.loads(frame.uv_data)
                tex = frame.texture_path
                apply_uvs_to_object(obj, uvs, tex)
        else:
            block = None
            for b in obj.uv_animated_blocks:
                if b.block_id == self.block_id:
                    block = b
                    break
            if not block:
                return {'CANCELLED'}
            frames = block.frames
            if not frames:
                return {'CANCELLED'}
            block.start_frame = self.frame_index
            if self.frame_index < len(frames):
                frame = frames[self.frame_index]
                uvs = json.loads(frame.uv_data)
                apply_uvs_to_material(obj, block.material_name, uvs)
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_SetFrameDuration(Operator):
    bl_idname = "uv_animator.set_frame_duration"
    bl_label = "Set Frame Duration"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")
    duration: bpy.props.IntProperty(default=0, min=0, max=30)

    def invoke(self, context, event):
        scene = context.scene
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}
        if scene.uv_animator_mode == 'LEGACY':
            self.duration = obj.uv_frame_duration
        else:
            for block in obj.uv_animated_blocks:
                if block.block_id == self.block_id:
                    self.duration = block.frame_duration
                    break
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "duration")
        real_duration = (self.duration + 1) * 0.033
        layout.label(text=f"Duration: {real_duration:.3f}s")

    def execute(self, context):
        scene = context.scene
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}
        if scene.uv_animator_mode == 'LEGACY':
            obj.uv_frame_duration = self.duration
        else:
            for block in obj.uv_animated_blocks:
                if block.block_id == self.block_id:
                    block.frame_duration = self.duration
                    break
        _redraw_ui(context)
        return {'FINISHED'}