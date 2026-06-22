import bpy
import json
import os
from bpy.types import Operator

def _get_expanded_dict(scene):
    if scene.uv_animator_mode == 'LEGACY':
        return json.loads(scene.uv_animator_expanded)
    else:
        return json.loads(scene.uv_animator_expanded_blocks)

def _set_expanded_dict(scene, expanded):
    if scene.uv_animator_mode == 'LEGACY':
        scene.uv_animator_expanded = json.dumps(expanded)
    else:
        scene.uv_animator_expanded_blocks = json.dumps(expanded)

class UV_OT_ToggleGroupSection(Operator):
    bl_idname = "uv_animator.toggle_group_section"
    bl_label = "Toggle Group Section"
    bl_options = {'REGISTER', 'UNDO'}
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        expanded = _get_expanded_dict(scene)
        key = f"_group_{self.group_name}"
        expanded[key] = not expanded.get(key, True)
        _set_expanded_dict(scene, expanded)
        return {'FINISHED'}

class UV_OT_ToggleTextureSection(Operator):
    bl_idname = "uv_animator.toggle_texture_section"
    bl_label = "Toggle Texture Section"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")

    def execute(self, context):
        scene = context.scene
        expanded = _get_expanded_dict(scene)
        if self.block_id:
            key = f"_textures_{self.object_name}_{self.block_id}"
        else:
            key = f"_textures_{self.object_name}"
        expanded[key] = not expanded.get(key, False)
        _set_expanded_dict(scene, expanded)
        return {'FINISHED'}

class UV_OT_ToggleTextureSubsection(Operator):
    bl_idname = "uv_animator.toggle_texture_subsection"
    bl_label = "Toggle Texture Subsection"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")
    texture_path: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        expanded = _get_expanded_dict(scene)
        safe_path = self.texture_path.replace(os.sep, '_').replace(':', '_')
        if self.block_id:
            key = f"_tex_sub_{self.object_name}_{self.block_id}_{safe_path}"
        else:
            key = f"_tex_sub_{self.object_name}_{safe_path}"
        expanded[key] = not expanded.get(key, False)
        _set_expanded_dict(scene, expanded)
        return {'FINISHED'}