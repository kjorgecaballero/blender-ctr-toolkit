import bpy
import json
import os
from bpy.types import Operator


# SECTION COLLAPSE TOGGLES


class UV_OT_ToggleGroupSection(Operator):
    bl_idname = "uv_animator.toggle_group_section"
    bl_label = "Toggle Group Section"
    bl_options = {'REGISTER', 'UNDO'}
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        expanded = json.loads(scene.uv_animator_expanded)
        key = f"_group_{self.group_name}"
        expanded[key] = not expanded.get(key, True)
        scene.uv_animator_expanded = json.dumps(expanded)
        return {'FINISHED'}

class UV_OT_ToggleTextureSection(Operator):
    bl_idname = "uv_animator.toggle_texture_section"
    bl_label = "Toggle Texture Section"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        expanded = json.loads(scene.uv_animator_expanded)
        key = f"_textures_{self.object_name}"
        expanded[key] = not expanded.get(key, False)
        scene.uv_animator_expanded = json.dumps(expanded)
        return {'FINISHED'}

class UV_OT_ToggleTextureSubsection(Operator):
    bl_idname = "uv_animator.toggle_texture_subsection"
    bl_label = "Toggle Texture Subsection"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    texture_path: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        expanded = json.loads(scene.uv_animator_expanded)
        safe_path = self.texture_path.replace(os.sep, '_').replace(':', '_')
        key = f"_tex_sub_{self.object_name}_{safe_path}"
        expanded[key] = not expanded.get(key, False)
        scene.uv_animator_expanded = json.dumps(expanded)
        return {'FINISHED'}