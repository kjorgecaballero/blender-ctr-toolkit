import bpy
import bmesh
from bpy.types import Operator
from bpy.props import BoolProperty
from ...utils.material_utils import get_family_materials


class SetBackfaceVisibility(Operator):
    """Unified operator to set backface visibility on materials, respecting scope."""
    bl_idname = "psx.set_backface"
    bl_label = "Set Backface Visibility"
    bl_description = "Show or hide backfaces on selected materials (scope controlled in Advanced settings)"
    bl_options = {'REGISTER', 'UNDO'}

    show: BoolProperty(
        name="Show Backfaces",
        default=True,
        description="When True, show backfaces; when False, hide them"
    )

    def execute(self, context):
        scene = context.scene
        scope = scene.blend_apply_scope
        processed_materials = set()

        if context.mode == 'EDIT_MESH' and context.tool_settings.mesh_select_mode[2]:
            has_selected = False
            for edit_obj in context.objects_in_mode:
                if edit_obj.type != 'MESH':
                    continue
                bm = bmesh.from_edit_mesh(edit_obj.data)
                selected_faces = [f for f in bm.faces if f.select]
                if selected_faces:
                    has_selected = True
                    material_indices = set(f.material_index for f in selected_faces)
                    for idx in material_indices:
                        if idx < len(edit_obj.material_slots):
                            mat = edit_obj.material_slots[idx].material
                            if mat and mat not in processed_materials:
                                family_names = get_family_materials(mat, edit_obj, scope)
                                for fname in family_names:
                                    family_mat = bpy.data.materials.get(fname)
                                    if family_mat:
                                        family_mat.ps1_show_backface = self.show
                                        family_mat.use_backface_culling = not self.show
                                        processed_materials.add(family_mat)
            if not has_selected:
                self.report({'INFO'}, "No faces selected in edit mode")
                return {'CANCELLED'}
        else:
            for sel_obj in context.selected_objects:
                if sel_obj.type != 'MESH':
                    continue
                for slot in sel_obj.material_slots:
                    if slot.material and slot.material not in processed_materials:
                        family_names = get_family_materials(slot.material, sel_obj, scope)
                        for fname in family_names:
                            family_mat = bpy.data.materials.get(fname)
                            if family_mat:
                                family_mat.ps1_show_backface = self.show
                                family_mat.use_backface_culling = not self.show
                                processed_materials.add(family_mat)

        context.view_layer.update()
        count = len(processed_materials)
        self.report({'INFO'}, f"Backfaces {'visible' if self.show else 'hidden'} on {count} material(s)")
        return {'FINISHED'}


classes = [SetBackfaceVisibility]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)