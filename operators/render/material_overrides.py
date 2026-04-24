import bpy
from bpy.types import Operator
from ...utils.render import PS1MaterialFactory

class ApplyMaterialOverrides(Operator):
    bl_idname = "psx.apply_material_overrides"
    bl_label = "Apply"
    bl_description = "Apply the current override settings to the active material"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        material = context.active_object.active_material if context.active_object else None
        if not material:
            self.report({'ERROR'}, "No active material found")
            return {'CANCELLED'}

        if context.scene.ps1_render_active and material.ps1_blend_mode != 'NONE':
            try:
                setup = PS1MaterialFactory.get_material_setup(material, material.ps1_blend_mode)
                setup.apply_setup()
                self.report({'INFO'}, f"Overrides applied to material '{material.name}'")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to apply overrides: {e}")
                return {'CANCELLED'}
        else:
            self.report({'INFO'}, "Overrides saved (PS1 render inactive, will apply when activated)")
        return {'FINISHED'}

class ResetMaterialOverrides(Operator):
    bl_idname = "psx.reset_material_overrides"
    bl_label = "Reset Material Overrides"
    bl_description = "Reset overrides to AUTO and restore automatic behaviour"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        material = context.active_object.active_material if context.active_object else None
        if not material:
            self.report({'ERROR'}, "No active material found")
            return {'CANCELLED'}

        material.ps1_blend_method_override = 'AUTO'

        if context.scene.ps1_render_active and material.ps1_blend_mode != 'NONE':
            try:
                setup = PS1MaterialFactory.get_material_setup(material, material.ps1_blend_mode)
                setup.apply_setup()
                self.report({'INFO'}, f"Overrides reset for material '{material.name}', auto mode restored")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to reset overrides: {e}")
                return {'CANCELLED'}
        else:
            self.report({'INFO'}, "Overrides reset (PS1 render inactive)")
        return {'FINISHED'}