import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ...utils.material_utils import is_constant_id_unique, rename_material_if_unique, is_base_name_in_use


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
        const_dict = obj.get("constant_materials", {})

        if self.old_name in const_dict:
            if '_ID' in self.old_name:
                parts = self.old_name.split('_ID', 1)
                self.new_base_name = parts[0]
                self.new_id_value = parts[1]
            else:
                self.new_base_name = self.old_name
                self.new_id_value = ""
            self.is_constant = True
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
        const_dict = obj.get("constant_materials", {})

        # Constant material rename
        if self.is_constant:
            new_base = self.new_base_name.strip()
            new_id = self.new_id_value.strip()
            if not new_base or not new_id:
                self.report({'ERROR'}, "Both Material and ID must be non-empty")
                return {'CANCELLED'}
            new_full_name = f"{new_base}_ID{new_id}"

            if new_full_name == old_name:
                return {'CANCELLED'}

            if new_full_name in bpy.data.materials and new_full_name != old_name:
                self.report({'ERROR'}, f"Name '{new_full_name}' already exists. Choose a different name.")
                return {'CANCELLED'}

            if not is_constant_id_unique(obj, new_id, exclude_material=old_name):
                self.report({'ERROR'}, f"ID '{new_id}' is already used by another constant material. Please choose a unique ID.")
                return {'CANCELLED'}

            old_base_name = old_name.split('_ID')[0] if '_ID' in old_name else old_name
            const_info = const_dict.get(old_name)
            if not const_info:
                self.report({'ERROR'}, "Constant material not found in object data")
                return {'CANCELLED'}

            actual_base_name = const_info.get("original_material", old_base_name)
            base_mat = bpy.data.materials.get(actual_base_name)

            # Collect all constant materials that reference this base
            siblings = []
            for cname, cinfo in const_dict.items():
                if cinfo.get("original_material") == actual_base_name:
                    siblings.append((cname, cinfo))

            # Determine new base name
            new_base_final = None
            if base_mat:
                if new_base != base_mat.name:
                    if new_base in bpy.data.materials:
                        self.report({'ERROR'}, f"Base material name '{new_base}' already exists. Choose a different base name.")
                        return {'CANCELLED'}
                    if is_base_name_in_use(const_dict, new_base, exclude_material=None):
                        self.report({'ERROR'}, f"Name '{new_base}' is already used as a base name for other constant materials. Cannot rename.")
                        return {'CANCELLED'}
                new_base_final = new_base
            else:
                new_base_final = new_base

            # Rename plan
            rename_plan = []
            for cname, cinfo in siblings:
                if '_ID' in cname:
                    old_suffix = cname.split('_ID', 1)[1]
                else:
                    old_suffix = ""
                if cname == old_name:
                    desired = new_full_name
                else:
                    desired = f"{new_base_final}_ID{old_suffix}"
                if desired in bpy.data.materials and desired != cname:
                    self.report({'ERROR'}, f"Material name '{desired}' already exists. Cannot rename '{cname}'.")
                    return {'CANCELLED'}
                rename_plan.append((cname, desired, cinfo))

            # Perform renames (base first)
            if base_mat and new_base != base_mat.name:
                success, msg = rename_material_if_unique(base_mat, new_base, const_dict, exclude_material=None)
                if not success:
                    self.report({'ERROR'}, msg)
                    return {'CANCELLED'}

            for cname, desired, cinfo in rename_plan:
                const_mat = bpy.data.materials.get(cname)
                if const_mat and desired != const_mat.name:
                    success, msg = rename_material_if_unique(const_mat, desired, const_dict, exclude_material=cname)
                    if not success:
                        self.report({'ERROR'}, f"Failed to rename '{cname}': {msg}")
                        return {'CANCELLED'}
                # Update dict
                new_info = dict(cinfo)
                new_info["original_material"] = new_base_final
                const_dict[desired] = new_info
                if cname != desired:
                    del const_dict[cname]
                # Update object property
                block_type = cinfo.get("block_type")
                block_id = cinfo.get("block_id")
                if block_type and block_id is not None:
                    prop_name = f"constant_name_{block_type}_{block_id}"
                    if prop_name in obj and obj[prop_name] == cname:
                        obj[prop_name] = desired

            obj["constant_materials"] = const_dict
            self.report({'INFO'}, f"Renamed constant family: base → '{new_base_final}', selected constant → '{new_full_name}', updated {len(rename_plan)} constant(s)")
            context.scene.ctr_material_list._update_items(context)
            return {'FINISHED'}

        # Base material (has constants)
        elif any(info.get("original_material") == old_name for info in const_dict.values()):
            base_mat = bpy.data.materials.get(old_name)
            if not base_mat:
                self.report({'ERROR'}, f"Base material '{old_name}' not found")
                return {'CANCELLED'}
            new_base = self.new_name.strip()
            if not new_base:
                self.report({'ERROR'}, "Name cannot be empty")
                return {'CANCELLED'}
            if new_base == old_name:
                return {'CANCELLED'}

            if new_base in bpy.data.materials:
                self.report({'ERROR'}, f"Base material name '{new_base}' already exists. Choose a different name.")
                return {'CANCELLED'}
            if is_base_name_in_use(const_dict, new_base, exclude_material=None):
                self.report({'ERROR'}, f"Name '{new_base}' is already used as a base name for other constant materials. Cannot rename.")
                return {'CANCELLED'}

            # Collect constants that reference this base
            siblings = []
            for cname, cinfo in const_dict.items():
                if cinfo.get("original_material") == old_name:
                    siblings.append((cname, cinfo))

            # Check ID conflicts with other constants
            for cname, cinfo in siblings:
                if '_ID' in cname:
                    sid = cname.split('_ID', 1)[1]
                    for other_name, other_info in const_dict.items():
                        if other_name == cname:
                            continue
                        if '_ID' in other_name:
                            other_id = other_name.split('_ID', 1)[1]
                            if other_id == sid:
                                self.report({'ERROR'}, f"ID '{sid}' (from constant '{cname}') is already used by another constant '{other_name}'. Cannot rename base without changing IDs.")
                                return {'CANCELLED'}

            # Check each constant's new name
            for cname, cinfo in siblings:
                if '_ID' in cname:
                    suffix = cname.split('_ID', 1)[1]
                else:
                    suffix = ""
                desired = f"{new_base}_ID{suffix}"
                if desired in bpy.data.materials and desired != cname:
                    self.report({'ERROR'}, f"Constant material name '{desired}' already exists. Cannot rename '{cname}'.")
                    return {'CANCELLED'}

            # Rename base
            success, msg = rename_material_if_unique(base_mat, new_base, const_dict, exclude_material=None)
            if not success:
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}

            # Rename constants
            for cname, cinfo in siblings:
                if '_ID' in cname:
                    suffix = cname.split('_ID', 1)[1]
                else:
                    suffix = ""
                desired = f"{new_base}_ID{suffix}"
                const_mat = bpy.data.materials.get(cname)
                if const_mat and desired != const_mat.name:
                    success, msg = rename_material_if_unique(const_mat, desired, const_dict, exclude_material=cname)
                    if not success:
                        self.report({'ERROR'}, f"Failed to rename constant '{cname}': {msg}")
                        return {'CANCELLED'}
                # Update dict
                new_info = dict(cinfo)
                new_info["original_material"] = new_base
                const_dict[desired] = new_info
                del const_dict[cname]
                # Update object property
                block_type = cinfo.get("block_type")
                block_id = cinfo.get("block_id")
                if block_type and block_id is not None:
                    prop_name = f"constant_name_{block_type}_{block_id}"
                    if prop_name in obj and obj[prop_name] == cname:
                        obj[prop_name] = desired

            obj["constant_materials"] = const_dict
            self.report({'INFO'}, f"Renamed base '{old_name}' → '{new_base}' and updated {len(siblings)} constant(s)")
            context.scene.ctr_material_list._update_items(context)
            return {'FINISHED'}

        # Independent normal material 
        else:
            mat = bpy.data.materials.get(old_name)
            if not mat:
                self.report({'ERROR'}, f"Material '{old_name}' not found")
                return {'CANCELLED'}
            new_name = self.new_name.strip()
            if not new_name:
                self.report({'ERROR'}, "Name cannot be empty")
                return {'CANCELLED'}
            if new_name == old_name:
                return {'CANCELLED'}
            if is_base_name_in_use(const_dict, new_name, exclude_material=None):
                self.report({'ERROR'}, f"Name '{new_name}' is already used as a base name for constant materials. Cannot rename.")
                return {'CANCELLED'}
            success, msg = rename_material_if_unique(mat, new_name, const_dict, exclude_material=None)
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