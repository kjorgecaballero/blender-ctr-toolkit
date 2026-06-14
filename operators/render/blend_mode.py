import bpy
import bmesh
from bpy.types import Operator
from ...utils.render import verify_attribute_for_active_object, PS1MaterialFactory


class ApplyBlendMode(Operator):
    """Apply selected blend mode to material(s) of selected faces (Edit Mode) or selected materials (Object Mode)"""
    bl_idname = "psx.apply_blend_mode"
    bl_label = "Apply Blend Mode"
    bl_description = "In Edit Mode: applies to materials of selected faces. In Object Mode: applies to selected materials/objects."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        mode = scene.blend_mode
        obj = context.active_object
        materials_to_apply = set()

        # Case 1: Edit Mode with active mesh object
        if context.mode == 'EDIT_MESH' and obj and obj.type == 'MESH':
            bm = bmesh.from_edit_mesh(obj.data)
            selected_faces = [f for f in bm.faces if f.select]
            if not selected_faces:
                self.report({'WARNING'}, "No faces selected. Select faces to apply blend mode.")
                return {'CANCELLED'}

            # Collect unique material indices from selected faces
            material_indices = set(f.material_index for f in selected_faces)
            for idx in material_indices:
                if idx < len(obj.material_slots):
                    mat = obj.material_slots[idx].material
                    if mat:
                        materials_to_apply.add(mat)

            # Also check other objects in multi-object edit mode
            for edit_obj in context.objects_in_mode:
                if edit_obj == obj or edit_obj.type != 'MESH':
                    continue
                bm_other = bmesh.from_edit_mesh(edit_obj.data)
                sel_faces = [f for f in bm_other.faces if f.select]
                if sel_faces:
                    mat_indices = set(f.material_index for f in sel_faces)
                    for idx in mat_indices:
                        if idx < len(edit_obj.material_slots):
                            mat = edit_obj.material_slots[idx].material
                            if mat:
                                materials_to_apply.add(mat)

            if not materials_to_apply:
                self.report({'WARNING'}, "Selected faces have no materials assigned.")
                return {'CANCELLED'}

        # Case 2: Object Mode – try Outliner selection, then selected objects' active materials
        else:
            # Check Outliner selection
            for mat in bpy.data.materials:
                if hasattr(mat, 'select_get') and mat.select_get():
                    materials_to_apply.add(mat)

            # If no Outliner selection, use active materials of selected objects
            if not materials_to_apply:
                for obj_sel in context.selected_objects:
                    if obj_sel.type == 'MESH' and obj_sel.active_material:
                        materials_to_apply.add(obj_sel.active_material)

            # Final fallback: active material of active object
            if not materials_to_apply and context.active_object and context.active_object.active_material:
                materials_to_apply.add(context.active_object.active_material)

            if not materials_to_apply:
                self.report({'WARNING'}, "No materials selected. Select materials in Outliner, select objects with materials, or enter Edit Mode and select faces.")
                return {'CANCELLED'}

        # Apply blend mode to all collected materials
        applied_count = 0
        for material in materials_to_apply:
            if not material or not material.use_nodes:
                continue

            current_backface = getattr(material, 'ps1_show_backface', False)
            material.ps1_blend_mode = mode
            material.ps1_show_backface = current_backface

            if scene.ps1_render_active:
                try:
                    setup = PS1MaterialFactory.get_material_setup(material, mode)
                    setup.apply_setup()
                except Exception as e:
                    self.report({'WARNING'}, f"Material '{material.name}': {e}")
                    continue

            applied_count += 1

        # Ensure vertex color attributes exist (for active object only)
        if context.active_object and context.active_object.type == 'MESH':
            verify_attribute_for_active_object(context, "VertexColor")

        context.view_layer.update()
        self.report({'INFO'}, f"Applied '{mode}' blend mode to {applied_count} material(s) from selected faces/objects.")
        return {'FINISHED'}


# Registration
classes = [ApplyBlendMode]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)