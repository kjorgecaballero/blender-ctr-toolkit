import bpy
from bpy.types import Operator
from ...utils.render import PS1MaterialFactory
from ...utils.material_utils import get_family_materials


class ResetMaterialOverrides(Operator):
    bl_idname = "psx.reset_material_overrides"
    bl_label = "Default"
    bl_description = "Reset blend method override to automatic (Auto) for the active material and its family (scope controlled)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        material = obj.active_material if obj else None
        if not material:
            self.report({'ERROR'}, "No active material found")
            return {'CANCELLED'}

        scope = scene.blend_apply_scope
        family_names = get_family_materials(material, obj, scope)

        changed = 0
        for mat_name in family_names:
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                continue
            mat.ps1_blend_method_override = 'AUTO'
            if scene.ps1_render_active and mat.ps1_blend_mode != 'NONE':
                try:
                    setup = PS1MaterialFactory.get_material_setup(mat, mat.ps1_blend_mode)
                    setup.apply_setup()
                    changed += 1
                except Exception as e:
                    self.report({'WARNING'}, f"Material '{mat.name}': {e}")
            else:
                changed += 1
        self.report({'INFO'}, f"Reset blend method for {changed} material(s)")
        return {'FINISHED'}


class ResetOverlapDefault(Operator):
    bl_idname = "psx.reset_overlap_default"
    bl_label = "Default"
    bl_description = "Reset transparency overlap to automatic mode for the active material and its family (scope controlled)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        material = obj.active_material if obj else None
        if not material:
            self.report({'ERROR'}, "No active material found")
            return {'CANCELLED'}

        scope = scene.blend_apply_scope
        family_names = get_family_materials(material, obj, scope)

        changed = 0
        for mat_name in family_names:
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                continue
            mat.ps1_transparency_overlap_mode = 'DEFAULT'
            if scene.ps1_render_active and mat.ps1_blend_mode != 'NONE':
                try:
                    setup = PS1MaterialFactory.get_material_setup(mat, mat.ps1_blend_mode)
                    setup.apply_setup()
                    changed += 1
                except Exception as e:
                    self.report({'WARNING'}, f"Material '{mat.name}': {e}")
            else:
                changed += 1
        self.report({'INFO'}, f"Reset overlap for {changed} material(s)")
        return {'FINISHED'}


class ToggleOverlap(Operator):
    bl_idname = "psx.toggle_overlap"
    bl_label = "Overlap"
    bl_description = "Manually enable/disable transparency overlap for the active material and its family (scope controlled)"
    bl_options = {'REGISTER', 'UNDO'}

    value: bpy.props.BoolProperty(name="Overlap", default=False)

    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        material = obj.active_material if obj else None
        if not material:
            self.report({'ERROR'}, "No active material found")
            return {'CANCELLED'}

        scope = scene.blend_apply_scope
        family_names = get_family_materials(material, obj, scope)

        changed = 0
        for mat_name in family_names:
            mat = bpy.data.materials.get(mat_name)
            if not mat:
                continue
            mat.ps1_transparency_overlap_mode = 'MANUAL'
            mat.ps1_transparency_overlap_manual = self.value
            if scene.ps1_render_active and mat.ps1_blend_mode != 'NONE':
                try:
                    setup = PS1MaterialFactory.get_material_setup(mat, mat.ps1_blend_mode)
                    setup.apply_setup()
                    changed += 1
                except Exception as e:
                    self.report({'WARNING'}, f"Material '{mat.name}': {e}")
            else:
                changed += 1
        self.report({'INFO'}, f"Overlap set to {self.value} for {changed} material(s)")
        return {'FINISHED'}


classes = [
    ResetMaterialOverrides,
    ResetOverlapDefault,
    ToggleOverlap,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)