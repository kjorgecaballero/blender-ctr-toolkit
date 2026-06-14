import bpy
import bmesh
from bpy.types import Operator
from ...utils.render import verify_attribute_for_active_object, PS1MaterialFactory


def expand_materials_by_scope(material_names, obj, scope):
    """
    Expand a set of material names based on the chosen scope.
    """
    if not obj or obj.type != 'MESH' or scope == 'SELECTED':
        return set(material_names)

    const_dict = obj.get("constant_materials", {})
    if not const_dict:
        return set(material_names)

    base_to_constants = {}
    for cname, cinfo in const_dict.items():
        base = cinfo.get("original_material", "")
        if base:
            base_to_constants.setdefault(base, set()).add(cname)

    result = set()
    for mat_name in material_names:
        if mat_name in const_dict:
            base = const_dict[mat_name].get("original_material", "")
            if not base:
                result.add(mat_name)
                continue
            if scope == 'FAMILY':
                result.add(base)
                result.update(base_to_constants.get(base, set()))
            elif scope == 'CONSTANTS_ONLY':
                result.update(base_to_constants.get(base, set()))
            elif scope == 'BASE_ONLY':
                result.add(base)
            else:
                result.add(mat_name)
        else:
            if mat_name in base_to_constants:
                if scope == 'FAMILY':
                    result.add(mat_name)
                    result.update(base_to_constants[mat_name])
                elif scope == 'CONSTANTS_ONLY':
                    result.update(base_to_constants[mat_name])
                elif scope == 'BASE_ONLY':
                    result.add(mat_name)
                else:
                    result.add(mat_name)
            else:
                result.add(mat_name)
    return result


class ApplyBlendMode(Operator):
    """Apply selected blend mode to material(s) of selected faces (Edit Mode) or selected materials (Object Mode)."""
    bl_idname = "psx.apply_blend_mode"
    bl_label = "Apply Blend Mode"
    bl_description = "In Edit Mode: applies to materials of selected faces. In Object Mode: applies to selected materials/objects."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        mode = scene.blend_mode
        obj = context.active_object
        scope = scene.blend_apply_scope

        # Collect originally selected material names ----
        selected_material_names = set()

        # Case 1: Edit Mode with active mesh object
        if context.mode == 'EDIT_MESH' and obj and obj.type == 'MESH':
            bm = bmesh.from_edit_mesh(obj.data)
            selected_faces = [f for f in bm.faces if f.select]
            if not selected_faces:
                self.report({'WARNING'}, "No faces selected. Select faces to apply blend mode.")
                return {'CANCELLED'}

            material_indices = set(f.material_index for f in selected_faces)
            for idx in material_indices:
                if idx < len(obj.material_slots):
                    mat = obj.material_slots[idx].material
                    if mat:
                        selected_material_names.add(mat.name)

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
                                selected_material_names.add(mat.name)

            if not selected_material_names:
                self.report({'WARNING'}, "Selected faces have no materials assigned.")
                return {'CANCELLED'}

        # Case 2: Object Mode
        else:
            for mat in bpy.data.materials:
                if hasattr(mat, 'select_get') and mat.select_get():
                    selected_material_names.add(mat.name)

            if not selected_material_names:
                for obj_sel in context.selected_objects:
                    if obj_sel.type == 'MESH' and obj_sel.active_material:
                        selected_material_names.add(obj_sel.active_material.name)

            if not selected_material_names and context.active_object and context.active_object.active_material:
                selected_material_names.add(context.active_object.active_material.name)

            if not selected_material_names:
                self.report({'WARNING'}, "No materials selected. Select materials in Outliner, select objects with materials, or enter Edit Mode and select faces.")
                return {'CANCELLED'}

        # Expand according to chosen scope
        final_names = expand_materials_by_scope(selected_material_names, obj, scope)

        # Apply blend mode
        applied_count = 0
        for mat_name in final_names:
            material = bpy.data.materials.get(mat_name)
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

        if context.active_object and context.active_object.type == 'MESH':
            verify_attribute_for_active_object(context, "VertexColor")

        context.view_layer.update()
        self.report({'INFO'}, f"Applied '{mode}' blend mode to {applied_count} material(s).")
        return {'FINISHED'}


classes = [ApplyBlendMode]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)