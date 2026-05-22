import bpy
import bmesh
from bpy.types import Operator
from bpy.props import BoolProperty

class SetBackfaceVisibility(Operator):
    """Unified operator to set backface visibility on materials"""
    bl_idname = "psx.set_backface"
    bl_label = "Set Backface Visibility"
    bl_description = "Show or hide backfaces on selected materials (global or per selected faces)"
    bl_options = {'REGISTER', 'UNDO'}

    show: BoolProperty(
        name="Show Backfaces",
        default=True,
        description="When True, show backfaces; when False, hide them"
    )

    def execute(self, context):
        scene = context.scene
        scene.show_backfaces = self.show
        processed_materials = set()

        if context.mode == 'EDIT_MESH' and context.tool_settings.mesh_select_mode[2]:
            has_selected = False
            for obj in context.objects_in_mode:
                if obj.type != 'MESH':
                    continue
                bm = bmesh.from_edit_mesh(obj.data)
                selected_faces = [f for f in bm.faces if f.select]
                if selected_faces:
                    has_selected = True
                    material_indices = set(f.material_index for f in selected_faces)
                    for idx in material_indices:
                        if idx < len(obj.material_slots) and obj.material_slots[idx].material:
                            mat = obj.material_slots[idx].material
                            if mat not in processed_materials:
                                mat.ps1_show_backface = self.show
                                mat.use_backface_culling = not self.show
                                processed_materials.add(mat)
            if not has_selected:
                self.report({'INFO'}, "No faces selected in edit mode")
                return {'CANCELLED'}
        else:
            for obj in context.selected_objects:
                if obj.type != 'MESH':
                    continue
                for slot in obj.material_slots:
                    if slot.material and slot.material not in processed_materials:
                        slot.material.ps1_show_backface = self.show
                        slot.material.use_backface_culling = not self.show
                        processed_materials.add(slot.material)

        context.view_layer.update()
        count = len(processed_materials)
        if self.show:
            self.report({'INFO'}, f"Backfaces visible on {count} materials")
        else:
            self.report({'INFO'}, f"Backfaces hidden on {count} materials")
        return {'FINISHED'}