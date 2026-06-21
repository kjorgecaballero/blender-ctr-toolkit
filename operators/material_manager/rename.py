import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ...utils.material_utils import (
    rename_material_if_unique,
    rename_base_material_family,
    is_constant_id_unique,
)


class MATERIAL_OT_RenameMaterial(Operator):
    """Rename the selected material.
    For constant materials, separate Base and ID fields.
    Prevents duplicate names and base name conflicts.
    Ensures all constant IDs are unique across the object.
    """
    bl_idname = "material.rename_material"
    bl_label = "Rename Material"
    bl_description = "Rename material (for constants: separate base name and ID)"
    bl_options = {'REGISTER', 'UNDO'}

    new_name: StringProperty(name="New Name", default="")
    new_base_name: StringProperty(name="Material", default="")
    new_id_value: StringProperty(name="ID", default="")

    @classmethod
    def poll(cls, context):
        props = context.scene.ctr_material_list
        return props.selected_index >= 0 and props.selected_index < len(props.items)

    def invoke(self, context, event):
        props = context.scene.ctr_material_list
        self.old_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(self.old_name)

        if not mat:
            self.report({'ERROR'}, f"Material '{self.old_name}' not found")
            return {'CANCELLED'}

        # Detect if it's a constant material
        if mat.get("ctr_block_type") is not None:
            self.is_constant = True
            # Extract current base and ID from name and properties
            if "_ID" in self.old_name:
                parts = self.old_name.split('_ID', 1)
                self.new_base_name = parts[0]
                self.new_id_value = parts[1]
            else:
                self.new_base_name = self.old_name
                self.new_id_value = ""
            # Use stored original base if available, else fallback to extracted
            stored_base = mat.get("ctr_original_material", "")
            if stored_base:
                self.new_base_name = stored_base
        else:
            self.is_constant = False
            self.new_name = self.old_name

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        if self.is_constant:
            layout.prop(self, "new_base_name", text="Material")
            layout.prop(self, "new_id_value", text="ID")
            layout.label(text=f"Result: {self.new_base_name}_ID{self.new_id_value}")
        else:
            layout.prop(self, "new_name", text="New Name")

    def execute(self, context):
        old_name = self.old_name
        obj = context.active_object
        mat = bpy.data.materials.get(old_name)
        if not mat:
            self.report({'ERROR'}, f"Material '{old_name}' not found")
            return {'CANCELLED'}

        # Case 1: Constant material
        if self.is_constant:
            new_base = self.new_base_name.strip()
            new_id = self.new_id_value.strip()
            if not new_base or not new_id:
                self.report({'ERROR'}, "Both Material and ID must be non-empty")
                return {'CANCELLED'}

            current_base = mat.get("ctr_original_material", "")
            # If original base is missing, derive from name
            if not current_base and "_ID" in old_name:
                current_base = old_name.split('_ID', 1)[0]
            if not current_base:
                current_base = old_name  # fallback

            # If the base name changes, we rename the whole family first.
            if new_base != current_base:
                # Check if the new base name is available
                if new_base in bpy.data.materials and new_base != current_base:
                    # rename_base_material_family will handle conflicts.
                    pass

                success, msg, updated = rename_base_material_family(obj, current_base, new_base)
                if not success:
                    self.report({'ERROR'}, msg)
                    return {'CANCELLED'}
                # Now all constants have been renamed to use new_base.
                # We need to find the specific constant (which now has new_base_ID_old_id)
                old_id = mat.get("ctr_block_id", "")
                if not old_id:
                    if "_ID" in old_name:
                        old_id = old_name.split('_ID', 1)[1]
                    else:
                        old_id = ""
                expected_old_const_name = f"{new_base}_ID{old_id}" if old_id else new_base
                const_mat = bpy.data.materials.get(expected_old_const_name)
                if not const_mat:
                    # Fallback: try to find it by scanning all constants with this base
                    for m in bpy.data.materials:
                        if m.get("ctr_original_material") == new_base and m.get("ctr_block_id") == old_id:
                            const_mat = m
                            break
                if not const_mat:
                    self.report({'WARNING'}, "Could not locate the renamed constant after base rename")
                    context.scene.ctr_material_list._update_items(context)
                    return {'FINISHED'}

                # Now if the ID also changed, rename that specific constant
                if new_id != old_id:
                    if not is_constant_id_unique(obj, new_id, exclude_material=const_mat):
                        self.report({'ERROR'}, f"ID '{new_id}' is already used by another constant on this object.")
                        return {'CANCELLED'}
                    new_const_name = f"{new_base}_ID{new_id}"
                    success, msg = rename_material_if_unique(const_mat, new_const_name)
                    if not success:
                        self.report({'ERROR'}, msg)
                        return {'CANCELLED'}
                    # Update its ctr_block_id to the new ID
                    const_mat["ctr_block_id"] = new_id
                    self.report({'INFO'}, f"Base renamed to '{new_base}', constant renamed to '{new_const_name}'")
                else:
                    self.report({'INFO'}, f"Base renamed to '{new_base}'")
            else:
                # Base name unchanged, only change ID
                current_id = mat.get("ctr_block_id", "")
                if not current_id and "_ID" in old_name:
                    current_id = old_name.split('_ID', 1)[1]
                if current_id == new_id:
                    self.report({'INFO'}, "No changes made")
                    return {'FINISHED'}

                if not is_constant_id_unique(obj, new_id, exclude_material=mat):
                    self.report({'ERROR'}, f"ID '{new_id}' is already used by another constant on this object.")
                    return {'CANCELLED'}

                new_const_name = f"{new_base}_ID{new_id}"
                success, msg = rename_material_if_unique(mat, new_const_name)
                if not success:
                    self.report({'ERROR'}, msg)
                    return {'CANCELLED'}
                mat["ctr_block_id"] = new_id
                self.report({'INFO'}, f"Renamed constant to '{new_const_name}'")

            context.scene.ctr_material_list._update_items(context)
            return {'FINISHED'}

        # Case 2: Base material (has constants) or normal material
        # Check if any constants reference this material as their base
        has_constants = False
        for m in bpy.data.materials:
            if m.get("ctr_original_material") == old_name:
                has_constants = True
                break

        new_name = self.new_name.strip()
        if not new_name:
            self.report({'ERROR'}, "Name cannot be empty")
            return {'CANCELLED'}

        if new_name == old_name:
            return {'CANCELLED'}

        if has_constants:
            # Rename base and all its constants
            success, msg, updated = rename_base_material_family(obj, old_name, new_name)
            if not success:
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}
            self.report({'INFO'}, f"Renamed base '{old_name}' → '{new_name}' and updated {updated} constant(s)")
        else:
            # Independent normal material
            success, msg = rename_material_if_unique(mat, new_name)
            if not success:
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}
            self.report({'INFO'}, f"Renamed material '{old_name}' → '{new_name}'")

        context.scene.ctr_material_list._update_items(context)
        return {'FINISHED'}


classes = [MATERIAL_OT_RenameMaterial]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)