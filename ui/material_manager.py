"""
CTR Material Manager – Custom scrollable list with preview icons,
top action buttons, filter bar, search, and pagination.
Uses checkboxes for single selection.
Includes operators for remapping (texture sync) and renaming materials,
with bidirectional base/constant handling and separate Base/ID fields for constants.
Prevents duplicate material names and base name conflicts.
Ensures all constant IDs are unique across the object.
"""

import bpy
import bmesh
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import StringProperty, IntProperty, EnumProperty, CollectionProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

from .qb_tb_list.list_helpers import get_material_image_icon
from ..utils.material_utils import update_derived_materials, is_constant_id_unique


# Material categories (global – used only for 'ALL' filter)
def get_material_categories():
    """Return three sets: normal, constant, nav_point (global)."""
    const_names = set()
    nav_names = set()
    for obj in bpy.data.objects:
        if "constant_materials" in obj:
            for mat_name, info in obj["constant_materials"].items():
                const_names.add(mat_name)
                if info.get("is_navigation_point", False):
                    nav_names.add(mat_name)

    normal = set()
    constant = set()
    nav_point = set()
    for mat in bpy.data.materials:
        if mat.name in const_names:
            if mat.name in nav_names:
                nav_point.add(mat.name)
            else:
                constant.add(mat.name)
        else:
            normal.add(mat.name)
    return normal, constant, nav_point


# Properties for the material list
class CTR_MaterialListItem(PropertyGroup):
    name: StringProperty()


class CTR_MaterialListProps(PropertyGroup):
    filter_type: EnumProperty(
        name="Filter",
        items=[
            ('ALL', "All", "Show all materials in the scene"),
            ('NORMAL', "Normal", "Materials of the active object that are NOT constant/nav points"),
            ('CONSTANT', "Constant", "Constant materials of the active object (not nav points)"),
            ('NAV_POINT', "Nav Point", "Navigation point materials of the active object"),
        ],
        default='ALL',
        update=lambda self, ctx: self._update_items(ctx)
    )
    search_text: StringProperty(
        name="Search", default="",
        update=lambda self, ctx: self._update_items(ctx)
    )
    items: CollectionProperty(type=CTR_MaterialListItem)
    selected_index: IntProperty(default=-1, options={'SKIP_SAVE'})
    scroll: IntProperty(default=0, min=0)

    def _update_items(self, context):
        """Rebuild the items collection from current filter & search."""
        self.items.clear()
        obj = context.active_object
        search = self.search_text.lower()

        if self.filter_type == 'ALL':
            # Global materials
            normal, constant, nav_point = get_material_categories()
            raw = normal | constant | nav_point
            for name in sorted(raw):
                if search and search not in name.lower():
                    continue
                item = self.items.add()
                item.name = name
        else:
            # Object‑scoped filters – require a valid mesh object
            if not obj or obj.type != 'MESH':
                self.selected_index = -1
                self.scroll = 0
                return

            const_dict = obj.get("constant_materials", {})
            # Determine which material names belong to which category
            normal_mats = []
            constant_mats = []
            nav_point_mats = []

            for slot in obj.material_slots:
                if not slot.material:
                    continue
                mat_name = slot.material.name
                if mat_name in const_dict:
                    if const_dict[mat_name].get("is_navigation_point", False):
                        nav_point_mats.append(mat_name)
                    else:
                        constant_mats.append(mat_name)
                else:
                    normal_mats.append(mat_name)

            # Remove duplicates (though material slots are unique per object)
            normal_mats = list(dict.fromkeys(normal_mats))
            constant_mats = list(dict.fromkeys(constant_mats))
            nav_point_mats = list(dict.fromkeys(nav_point_mats))

            if self.filter_type == 'NORMAL':
                raw = normal_mats
            elif self.filter_type == 'CONSTANT':
                raw = constant_mats
            else:  # NAV_POINT
                raw = nav_point_mats

            for name in sorted(raw):
                if search and search not in name.lower():
                    continue
                item = self.items.add()
                item.name = name

        self.selected_index = -1
        self.scroll = 0


def is_base_name_in_use(const_dict, name, exclude_material=None):
    """
    Check if 'name' is used as original_material in any constant material.
    exclude_material: if provided, ignore constants with that name (used when renaming a constant itself).
    Returns True if name is already a base name for any constant (excluding the one being renamed).
    """
    for cname, cinfo in const_dict.items():
        if exclude_material and cname == exclude_material:
            continue
        if cinfo.get("original_material") == name:
            return True
    return False


# Helper to rename a material only if the new name is unique and not a used base name
def rename_material_if_unique(mat, new_name, const_dict=None, exclude_material=None):
    """
    Rename material to new_name if:
      - new_name is not already a material name
      - new_name is not already used as original_material in any constant (if const_dict provided)
    Returns (success, error_message)
    """
    if not mat:
        return False, "Material not found"
    if new_name == mat.name:
        return True, ""
    if new_name in bpy.data.materials:
        return False, f"Name '{new_name}' already exists. Choose a different name."
    if const_dict is not None:
        if is_base_name_in_use(const_dict, new_name, exclude_material):
            return False, f"Name '{new_name}' is already used as a base name for constant materials. Cannot rename."
    mat.name = new_name
    return True, ""


# RENAME OPERATOR with Base/ID fields for constants
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

    # Common property
    new_name: StringProperty(name="New Name", default="")  # for normal materials
    # For constant materials
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

        # Check if it's a constant material
        if self.old_name in const_dict:
            # Parse base and ID from the constant name (expected format: Base_IDValue)
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

            # Check if the new full name already exists (and it's not the current material)
            if new_full_name in bpy.data.materials and new_full_name != old_name:
                self.report({'ERROR'}, f"Name '{new_full_name}' already exists. Choose a different name.")
                return {'CANCELLED'}

            # Check ID uniqueness (excluding current constant)
            if not is_constant_id_unique(obj, new_id, exclude_material=old_name):
                self.report({'ERROR'}, f"ID '{new_id}' is already used by another constant material. Please choose a unique ID.")
                return {'CANCELLED'}

            # Find the base material and all siblings (constants sharing same base)
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

            # Step 1: Check all desired new names for uniqueness and base name conflicts
            new_base_final = None
            if base_mat:
                if new_base != base_mat.name:
                    # Check if new_base is already a material name
                    if new_base in bpy.data.materials:
                        self.report({'ERROR'}, f"Base material name '{new_base}' already exists. Choose a different base name.")
                        return {'CANCELLED'}
                    # Check if new_base is already a base name for other constants (excluding our family)
                    if is_base_name_in_use(const_dict, new_base, exclude_material=None):
                        self.report({'ERROR'}, f"Name '{new_base}' is already used as a base name for other constant materials. Cannot rename.")
                        return {'CANCELLED'}
                new_base_final = new_base
            else:
                new_base_final = new_base

            # For each sibling, compute desired name and check conflicts
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

            # Step 2: Perform renames (base first, then constants)
            if base_mat and new_base != base_mat.name:
                success, msg = rename_material_if_unique(base_mat, new_base, const_dict, exclude_material=None)
                if not success:
                    self.report({'ERROR'}, msg)
                    return {'CANCELLED'}

            # Rename constants
            for cname, desired, cinfo in rename_plan:
                const_mat = bpy.data.materials.get(cname)
                if const_mat and desired != const_mat.name:
                    # For constants, we pass const_dict and exclude the current constant being renamed to avoid self-conflict
                    success, msg = rename_material_if_unique(const_mat, desired, const_dict, exclude_material=cname)
                    if not success:
                        self.report({'ERROR'}, f"Failed to rename '{cname}': {msg}")
                        return {'CANCELLED'}
                # Update dictionary and properties
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

        # Base material rename (non-constant but has constants)
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

            # Check if new_base is already a material name
            if new_base in bpy.data.materials:
                self.report({'ERROR'}, f"Base material name '{new_base}' already exists. Choose a different name.")
                return {'CANCELLED'}
            # Check if new_base is already used as a base name for constants (excluding the ones we're about to rename)
            if is_base_name_in_use(const_dict, new_base, exclude_material=None):
                self.report({'ERROR'}, f"Name '{new_base}' is already used as a base name for other constant materials. Cannot rename.")
                return {'CANCELLED'}

            # Collect all constants that reference this base
            siblings = []
            for cname, cinfo in const_dict.items():
                if cinfo.get("original_material") == old_name:
                    siblings.append((cname, cinfo))

            # Check that none of the IDs of these siblings conflict with constants outside the group 
            for cname, cinfo in siblings:
                if '_ID' in cname:
                    sid = cname.split('_ID', 1)[1]
                    # Verify ID uniqueness against all constants except this sibling itself
                    for other_name, other_info in const_dict.items():
                        if other_name == cname:
                            continue
                        if '_ID' in other_name:
                            other_id = other_name.split('_ID', 1)[1]
                            if other_id == sid:
                                self.report({'ERROR'}, f"ID '{sid}' (from constant '{cname}') is already used by another constant '{other_name}'. Cannot rename base without changing IDs.")
                                return {'CANCELLED'}

            # Check each constant's new name (they will keep the same ID but new base)
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
            # For a normal material, we must also prevent it from taking a name that is a base name of any constant
            if is_base_name_in_use(const_dict, new_name, exclude_material=None):
                self.report({'ERROR'}, f"Name '{new_name}' is already used as a base name for constant materials. Cannot rename.")
                return {'CANCELLED'}
            success, msg = rename_material_if_unique(mat, new_name, const_dict, exclude_material=None)
            if not success:
                self.report({'ERROR'}, msg)
                return {'CANCELLED'}
            self.report({'INFO'}, f"Renamed material '{old_name}' → '{new_name}'")

        # Refresh the list
        context.scene.ctr_material_list._update_items(context)
        return {'FINISHED'}


#REMAP OPERATOR (always updates base + constants)
class MATERIAL_OT_RemapMaterial(Operator):
    """Remap texture image for the selected material and all linked materials (base + constants)."""
    bl_idname = "material.remap_material"
    bl_label = "Remap"
    bl_description = "Change the texture image for this material and all derived/linked materials"
    bl_options = {'REGISTER', 'UNDO'}

    new_image_name: StringProperty(name="New Image", default="")

    @classmethod
    def poll(cls, context):
        props = context.scene.ctr_material_list
        return props.selected_index >= 0 and props.selected_index < len(props.items)

    def invoke(self, context, event):
        props = context.scene.ctr_material_list
        self.selected_mat_name = props.items[props.selected_index].name
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Material: {self.selected_mat_name}")
        layout.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        op = layout.operator("material.remap_from_file", text="", icon='FILE_FOLDER')

    def execute(self, context):
        obj = context.active_object
        new_image = bpy.data.images.get(self.new_image_name)
        if not new_image:
            self.report({'ERROR'}, "Please select an image")
            return {'CANCELLED'}

        const_dict = obj.get("constant_materials", {}) if obj else {}
        base_materials = set()

        # Determine if selected is constant or base
        if self.selected_mat_name in const_dict:
            base = const_dict[self.selected_mat_name].get("original_material", "")
            if base:
                base_materials.add(base)
        else:
            for info in const_dict.values():
                if info.get("original_material") == self.selected_mat_name:
                    base_materials.add(self.selected_mat_name)
                    break

        if base_materials:
            updated = update_derived_materials(
                obj, list(base_materials), new_image, update_base_material=True
            )
            self.report({'INFO'}, f"Remapped {updated} materials (base + constants)")
        else:
            mat = bpy.data.materials.get(self.selected_mat_name)
            if not mat:
                self.report({'ERROR'}, f"Material '{self.selected_mat_name}' not found")
                return {'CANCELLED'}
            if mat.use_nodes:
                found = False
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        node.image = new_image
                        found = True
                if found:
                    self.report({'INFO'}, f"Remapped texture for '{mat.name}'")
                else:
                    self.report({'WARNING'}, "No texture image node found")
            else:
                self.report({'WARNING'}, "Material does not use nodes")
        return {'FINISHED'}


class MATERIAL_OT_RemapFromFile(Operator, ImportHelper):
    """Load an image from disk and remap the material(s)."""
    bl_idname = "material.remap_from_file"
    bl_label = "Remap from Image File"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.tga",
        options={'HIDDEN'}
    )

    def execute(self, context):
        filepath = self.filepath
        if not filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}

        image = None
        for img in bpy.data.images:
            if img.filepath == filepath or (img.filepath and img.filepath == bpy.path.relpath(filepath)):
                image = img
                break
        if image is None:
            try:
                image = bpy.data.images.load(filepath)
                self.report({'INFO'}, f"Loaded: {image.name}")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to load: {str(e)}")
                return {'CANCELLED'}

        props = context.scene.ctr_material_list
        if props.selected_index < 0:
            return {'CANCELLED'}
        selected_mat_name = props.items[props.selected_index].name
        obj = context.active_object
        const_dict = obj.get("constant_materials", {}) if obj else {}

        base_materials = set()
        if selected_mat_name in const_dict:
            base = const_dict[selected_mat_name].get("original_material", "")
            if base:
                base_materials.add(base)
        else:
            for info in const_dict.values():
                if info.get("original_material") == selected_mat_name:
                    base_materials.add(selected_mat_name)
                    break

        if base_materials:
            updated = update_derived_materials(
                obj, list(base_materials), image, update_base_material=True
            )
            self.report({'INFO'}, f"Remapped {updated} materials")
        else:
            mat = bpy.data.materials.get(selected_mat_name)
            if mat and mat.use_nodes:
                found = False
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        node.image = image
                        found = True
                if found:
                    self.report({'INFO'}, f"Remapped texture for '{mat.name}'")
                else:
                    self.report({'WARNING'}, "No texture image node found")
            else:
                self.report({'WARNING'}, "Material not found or does not use nodes")
        return {'FINISHED'}


# ASSIGN, SELECT, DESELECT, REFRESH, SCROLL
class MATERIAL_OT_AssignSelected(Operator):
    """Assign the selected material to selected faces (whole blocks if any face belongs to a block)"""
    bl_idname = "material.assign_selected"
    bl_label = "Assign"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            self.report({'ERROR'}, f"Material '{mat_name}' not found")
            return {'CANCELLED'}

        if "constant_materials" in obj and mat_name in obj["constant_materials"]:
            self.report({'ERROR'}, f"Cannot assign constant/navigation material '{mat_name}' using this button. Use the 'Assign' button inside the Block List (Constant Materials mode) instead.")
            return {'CANCELLED'}

        if mat.name not in obj.data.materials:
            obj.data.materials.append(mat)
        mat_index = obj.data.materials.find(mat.name)

        has_block_data = ("face_to_quadblock" in obj and "quadblock_faces_map" in obj) or \
                         ("face_to_triblock" in obj and "triblock_faces_map" in obj)

        if not has_block_data:
            bm = bmesh.from_edit_mesh(obj.data)
            for face in bm.faces:
                if face.select:
                    face.material_index = mat_index
            bmesh.update_edit_mesh(obj.data)
            self.report({'INFO'}, f"Assigned {mat.name} to selected faces")
            return {'FINISHED'}

        bm = bmesh.from_edit_mesh(obj.data)
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        face_to_quad = obj.get("face_to_quadblock", {})
        face_to_tri = obj.get("face_to_triblock", {})
        quad_maps = obj.get("quadblock_faces_map", {})
        tri_maps = obj.get("triblock_faces_map", {})

        blocks_to_assign = set()
        individual_faces = set()

        for face in selected_faces:
            idx_str = str(face.index)
            if idx_str in face_to_quad:
                block_id = int(face_to_quad[idx_str])
                blocks_to_assign.add(('quadblock', block_id))
            elif idx_str in face_to_tri:
                block_id = int(face_to_tri[idx_str])
                blocks_to_assign.add(('triblock', block_id))
            else:
                individual_faces.add(face.index)

        faces_to_assign = set(individual_faces)
        for block_type, block_id in blocks_to_assign:
            if block_type == 'quadblock':
                block_faces = quad_maps.get(str(block_id), [])
            else:
                block_faces = tri_maps.get(str(block_id), [])
            faces_to_assign.update(block_faces)

        for face in bm.faces:
            if face.index in faces_to_assign:
                face.material_index = mat_index

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Assigned {mat.name} to {len(faces_to_assign)} faces ({len(blocks_to_assign)} blocks + {len(individual_faces)} standalone faces)")
        return {'FINISHED'}


class MATERIAL_OT_SelectByMaterial(Operator):
    """Select all faces using the selected material"""
    bl_idname = "material.select_by_material"
    bl_label = "Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat or mat.name not in obj.data.materials:
            self.report({'WARNING'}, f"Material '{mat_name}' not used by object")
            return {'CANCELLED'}

        mat_index = obj.data.materials.find(mat.name)
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            face.select = False
        for face in bm.faces:
            if face.material_index == mat_index:
                face.select = True
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected faces with {mat.name}")
        return {'FINISHED'}


class MATERIAL_OT_DeselectByMaterial(Operator):
    """Deselect all faces using the selected material"""
    bl_idname = "material.deselect_by_material"
    bl_label = "Deselect"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat or mat.name not in obj.data.materials:
            return {'CANCELLED'}

        mat_index = obj.data.materials.find(mat.name)
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            if face.material_index == mat_index:
                face.select = False
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Deselected faces with {mat.name}")
        return {'FINISHED'}


class MATERIAL_OT_RefreshList(Operator):
    """Rebuild the material list (after adding/renaming materials) and optionally purge unused data blocks"""
    bl_idname = "material.refresh_list"
    bl_label = "Refresh"
    bl_description = "Rebuild the material list (after adding/renaming materials)"
    bl_options = {'REGISTER'}

    purge_unused: BoolProperty(
        name="Purge unused",
        description="Delete all unused materials, textures, and images",
        default=False
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.prop(self, "purge_unused")

    def execute(self, context):
        if self.purge_unused:
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
            self.report({'INFO'}, "Purged unused data blocks")
        context.scene.ctr_material_list._update_items(context)
        self.report({'INFO'}, "Material list refreshed")
        return {'FINISHED'}


class MATERIAL_OT_VerticalScroll(Operator):
    bl_idname = "material.vertical_scroll"
    bl_label = "Scroll"
    direction: EnumProperty(items=[('UP', 'Up', ''), ('DOWN', 'Down', '')])

    def execute(self, context):
        props = context.scene.ctr_material_list
        total = len(props.items)
        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total - ITEMS_PER_PAGE)
        if self.direction == 'UP':
            props.scroll = max(0, props.scroll - 1)
        else:
            props.scroll = min(max_scroll, props.scroll + 1)
        return {'FINISHED'}


class MATERIAL_OT_JumpToPage(Operator):
    bl_idname = "material.jump_to_page"
    bl_label = "Jump to Page"
    page: IntProperty(default=1, min=1)

    def execute(self, context):
        props = context.scene.ctr_material_list
        total = len(props.items)
        ITEMS_PER_PAGE = 10
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        safe_page = max(1, min(self.page, total_pages))
        props.scroll = (safe_page - 1) * ITEMS_PER_PAGE
        return {'FINISHED'}


class MATERIAL_OT_ToggleSelection(Operator):
    bl_idname = "material.toggle_selection"
    bl_label = "Select Material"
    index: IntProperty()

    def execute(self, context):
        props = context.scene.ctr_material_list
        if self.index < 0 or self.index >= len(props.items):
            return {'CANCELLED'}
        if props.selected_index == self.index:
            props.selected_index = -1
        else:
            props.selected_index = self.index
        return {'FINISHED'}


# Main Panel
class CTR_PT_MaterialManager(Panel):
    bl_label = "CTR Material Manager"
    bl_idname = "CTR_PT_material_manager"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        props = context.scene.ctr_material_list
        obj = context.active_object

        # Filter row
        row = layout.row(align=True)
        row.prop(props, "filter_type", expand=True)

        # Search bar only (refresh button removed from here)
        row = layout.row(align=True)
        row.prop(props, "search_text", text="", icon='VIEWZOOM')

        # First row: Assign, Select, Deselect
        row1 = layout.row(align=True)

        # Assign button (disabled if constant material selected)
        assign_disabled = False
        if props.selected_index >= 0 and props.selected_index < len(props.items):
            selected_mat_name = props.items[props.selected_index].name
            if obj and "constant_materials" in obj and selected_mat_name in obj["constant_materials"]:
                assign_disabled = True

        assign_row = row1.row(align=True)
        assign_row.enabled = not assign_disabled
        assign_row.operator("material.assign_selected", text="Assign", icon='CHECKMARK')

        row1.operator("material.select_by_material", text="Select", icon='RESTRICT_SELECT_OFF')
        row1.operator("material.deselect_by_material", text="Deselect", icon='RESTRICT_SELECT_ON')

        # Second row: Rename, Remap, Refresh
        row2 = layout.row(align=True)

        # Rename button (disabled if no selection)
        rename_row = row2.row(align=True)
        rename_row.enabled = (props.selected_index >= 0 and props.selected_index < len(props.items))
        rename_row.operator("material.rename_material", text="Rename", icon='OUTLINER_DATA_FONT')

        # Remap button (disabled if no selection)
        remap_row = row2.row(align=True)
        remap_row.enabled = (props.selected_index >= 0 and props.selected_index < len(props.items))
        remap_row.operator("material.remap_material", text="Remap", icon='FILE_REFRESH')

        # Refresh button (always enabled)
        row2.operator("material.refresh_list", text="Refresh", icon='FILE_REFRESH')

        # List area
        total = len(props.items)
        if total == 0:
            layout.box().label(text="No materials match the filter", icon='INFO')
            return

        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total - ITEMS_PER_PAGE)
        safe_scroll = min(props.scroll, max_scroll)
        start = safe_scroll
        end = min(start + ITEMS_PER_PAGE, total)

        box = layout.box()
        count_row = box.row()
        count_row.alignment = 'CENTER'
        count_row.label(text=f"Materials: {total}  (page {(safe_scroll // ITEMS_PER_PAGE) + 1} of {max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)})")

        for idx in range(start, end):
            item = props.items[idx]
            mat_name = item.name
            row = box.row(align=True)

            is_sel = (idx == props.selected_index)
            icon = 'CHECKBOX_HLT' if is_sel else 'CHECKBOX_DEHLT'
            op = row.operator("material.toggle_selection", text="", icon=icon, emboss=False)
            op.index = idx

            icon_id = get_material_image_icon(mat_name)
            if isinstance(icon_id, int) and icon_id != 0:
                row.label(text=mat_name, icon_value=icon_id)
            else:
                row.label(text=mat_name, icon='MATERIAL')

            if is_sel:
                row.alert = True

        if total > ITEMS_PER_PAGE:
            pagination_row = box.row(align=True)
            pagination_row.alignment = 'CENTER'
            current_page = (safe_scroll // ITEMS_PER_PAGE) + 1
            total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

            up = pagination_row.operator("material.vertical_scroll", text="", icon='TRIA_UP')
            up.direction = 'UP'
            first = pagination_row.operator("material.jump_to_page", text="<<", icon='REW')
            first.page = 1
            prev = pagination_row.operator("material.jump_to_page", text="<", icon='PREV_KEYFRAME')
            prev.page = current_page - 1 if current_page > 1 else 1
            pagination_row.label(text=f"[{current_page}/{total_pages}]")
            nxt = pagination_row.operator("material.jump_to_page", text=">", icon='NEXT_KEYFRAME')
            nxt.page = current_page + 1 if current_page < total_pages else total_pages
            last = pagination_row.operator("material.jump_to_page", text=">>", icon='FF')
            last.page = total_pages
            down = pagination_row.operator("material.vertical_scroll", text="", icon='TRIA_DOWN')
            down.direction = 'DOWN'


# Registration
classes = [
    CTR_MaterialListItem,
    CTR_MaterialListProps,
    MATERIAL_OT_AssignSelected,
    MATERIAL_OT_SelectByMaterial,
    MATERIAL_OT_DeselectByMaterial,
    MATERIAL_OT_RefreshList,
    MATERIAL_OT_VerticalScroll,
    MATERIAL_OT_JumpToPage,
    MATERIAL_OT_ToggleSelection,
    MATERIAL_OT_RenameMaterial,
    MATERIAL_OT_RemapMaterial,
    MATERIAL_OT_RemapFromFile,
    CTR_PT_MaterialManager,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ctr_material_list = bpy.props.PointerProperty(type=CTR_MaterialListProps)

def unregister():
    del bpy.types.Scene.ctr_material_list
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)