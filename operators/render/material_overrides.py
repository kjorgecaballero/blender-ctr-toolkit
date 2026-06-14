import bpy
from bpy.types import Operator
from ...utils.render import PS1MaterialFactory

class ResetMaterialOverrides(Operator):
    bl_idname = "psx.reset_material_overrides"
    bl_label = "Default"
    bl_description = "Reset blend method override to automatic (Auto) for the active material"
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
                self.report({'INFO'}, f"Blend method reset to Auto for '{material.name}'")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to reset: {e}")
                return {'CANCELLED'}
        else:
            self.report({'INFO'}, "Blend method reset to Auto (PS1 render inactive)")
        return {'FINISHED'}

class ResetOverlapDefault(Operator):
    bl_idname = "psx.reset_overlap_default"
    bl_label = "Default"
    bl_description = "Reset transparency overlap to automatic mode for the active material"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        material = context.active_object.active_material if context.active_object else None
        if not material:
            self.report({'ERROR'}, "No active material found")
            return {'CANCELLED'}

        material.ps1_transparency_overlap_mode = 'DEFAULT'
        if context.scene.ps1_render_active and material.ps1_blend_mode != 'NONE':
            try:
                setup = PS1MaterialFactory.get_material_setup(material, material.ps1_blend_mode)
                setup.apply_setup()
            except Exception as e:
                print(f"Warning: could not reapply material setup: {e}")
        self.report({'INFO'}, f"Overlap reset to default for '{material.name}'")
        return {'FINISHED'}

class ToggleOverlap(Operator):
    bl_idname = "psx.toggle_overlap"
    bl_label = "Overlap"
    bl_description = "Manually enable/disable transparency overlap for the active material"
    bl_options = {'REGISTER', 'UNDO'}

    value: bpy.props.BoolProperty(name="Overlap", default=False)

    def execute(self, context):
        material = context.active_object.active_material if context.active_object else None
        if not material:
            self.report({'ERROR'}, "No active material found")
            return {'CANCELLED'}

        material.ps1_transparency_overlap_mode = 'MANUAL'
        material.ps1_transparency_overlap_manual = self.value
        if context.scene.ps1_render_active and material.ps1_blend_mode != 'NONE':
            try:
                setup = PS1MaterialFactory.get_material_setup(material, material.ps1_blend_mode)
                setup.apply_setup()
            except Exception as e:
                print(f"Warning: could not reapply material setup: {e}")
        self.report({'INFO'}, f"Overlap set to {self.value} for '{material.name}'")
        return {'FINISHED'}