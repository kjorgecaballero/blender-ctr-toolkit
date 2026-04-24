import bpy
from bpy.types import Operator
from ...utils.render import verify_attribute_for_active_object, PS1MaterialFactory

class ApplyBlendMode(Operator):
    bl_idname = "psx.apply_blend_mode"
    bl_label = "Apply Blend Mode"
    bl_description = "Apply selected blend mode to active material"
    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if not obj:
            self.report({'ERROR'}, "No object selected")
            return {'CANCELLED'}
        if not obj.data.materials:
            self.report({'ERROR'}, "Selected object has no materials")
            return {'CANCELLED'}
        material = obj.active_material
        if not material:
            self.report({'ERROR'}, "No active material found")
            return {'CANCELLED'}
        current_backface = getattr(material, 'ps1_show_backface', False)
        success, message = verify_attribute_for_active_object(context, "VertexColor")
        if not success:
            self.report({'WARNING'}, message)
        else:
            self.report({'INFO'}, message)
        if obj.type == 'MESH':
            mesh = obj.data
            if hasattr(mesh, "color_attributes") and mesh.color_attributes:
                target_index = -1
                for i, attr in enumerate(mesh.color_attributes):
                    if attr.name == "VertexColor":
                        target_index = i
                        break
                if target_index != -1:
                    mesh.color_attributes.active_color_index = target_index
                    mesh.update()
                    context.view_layer.update()
                    obj.update_tag()
                    for area in context.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
        mode = scene.blend_mode
        material.ps1_blend_mode = mode
        material.ps1_show_backface = current_backface
        context.view_layer.update()
        self.report({'INFO'}, f"{mode} blend mode applied successfully! Backface: {'Show' if current_backface else 'Hide'}")
        return {'FINISHED'}