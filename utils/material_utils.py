"""
Material utilities for updating derived (constant) materials.
"""

import bpy


def get_constant_materials_from_object(obj):
    """
    Return a list of materials assigned to the object that have
    the 'ctr_block_type' property (i.e., constant materials).
    """
    result = []
    if not obj or obj.type != 'MESH':
        return result
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.get("ctr_block_type") is not None:
            result.append(mat)
    return result


def get_constant_material_info(mat):
    """Safely retrieve constant material metadata from a material."""
    if not mat:
        return None
    block_type = mat.get("ctr_block_type")
    if block_type is None:
        return None
    return {
        "block_type": block_type,
        "block_id": mat.get("ctr_block_id", 0),
        "original_material": mat.get("ctr_original_material", ""),
        "is_navigation_point": mat.get("ctr_is_navigation_point", False),
    }


def update_derived_materials(obj, base_material_names, image, update_base_material, ensure_node_callback=None):
    """
    Synchronize the image texture across all materials linked to the specified base materials.
    Scans all materials in the blend file for those that have
    'ctr_original_material' matching the given base names.
    """
    if not image:
        return 0

    updated_count = 0

    # Look at all materials in the blend file (names are unique)
    for mat in bpy.data.materials:
        if mat.get("ctr_original_material") in base_material_names:
            # This is a constant material derived from one of our bases
            if ensure_node_callback:
                ensure_node_callback(mat, image)
            else:
                if mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image is not None:
                            node.image = image
                            updated_count += 1
                            break

        # Also update the base material itself if requested
        if update_base_material and mat.name in base_material_names:
            if ensure_node_callback:
                ensure_node_callback(mat, image)
            else:
                if mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image is not None:
                            node.image = image
                            updated_count += 1
                            break
            updated_count += 1

    return updated_count


def is_constant_id_unique(obj, id_value, exclude_material=None):
    """
    Check if the ID (suffix after '_ID') is already used by another constant material
    *on the same object*. exclude_material can be a Material object or its name.
    """
    # Convert exclude_material to a Material object if it's a string
    exclude_mat = None
    if isinstance(exclude_material, str):
        exclude_mat = bpy.data.materials.get(exclude_material)
    elif isinstance(exclude_material, bpy.types.Material):
        exclude_mat = exclude_material

    for slot in obj.material_slots:
        mat = slot.material
        if not mat:
            continue
        # Skip the excluded material (compare by object identity)
        if exclude_mat and mat == exclude_mat:
            continue
        if "_ID" in mat.name:
            existing_id = mat.name.split('_ID', 1)[1]
            if existing_id == id_value:
                return False
    return True


def get_material_categories():
    """
    Return three sets: normal, constant, nav_point (global).
    Scans all materials in the blend file.
    """
    normal = set()
    constant = set()
    nav_point = set()

    for mat in bpy.data.materials:
        block_type = mat.get("ctr_block_type")
        if block_type is not None:
            if mat.get("ctr_is_navigation_point", False):
                nav_point.add(mat.name)
            else:
                constant.add(mat.name)
        else:
            normal.add(mat.name)

    return normal, constant, nav_point


def is_base_name_in_use(base_name, exclude_material=None):
    """
    Check if 'base_name' is used as original_material in any constant material globally.
    """
    for mat in bpy.data.materials:
        if mat == exclude_material:
            continue
        if mat.get("ctr_original_material") == base_name:
            return True
    return False


def rename_material_if_unique(mat, new_name, exclude_material=None):
    """Rename material if new_name is unique and not a used base name."""
    if not mat:
        return False, "Material not found"
    if new_name == mat.name:
        return True, ""

    if new_name in bpy.data.materials:
        return False, f"Name '{new_name}' already exists."

    if is_base_name_in_use(new_name, exclude_material):
        return False, f"Name '{new_name}' is already used as a base name for constant materials."

    mat.name = new_name
    return True, ""


def update_constant_material_base_reference(old_base_name, new_base_name):
    """
    Update the 'ctr_original_material' property in all constant materials
    from old_base_name to new_base_name.
    """
    if old_base_name == new_base_name:
        return 0

    updated_count = 0
    for mat in bpy.data.materials:
        if mat.get("ctr_original_material") == old_base_name:
            mat["ctr_original_material"] = new_base_name
            updated_count += 1

    return updated_count


def rename_base_material_family(obj, old_base_name, new_base_name):
    """
    Rename a base material and all its constant materials.
    Works entirely by renaming materials and updating their properties.
    """
    if not obj or obj.type != 'MESH':
        return False, "Object is not a valid mesh", 0
    if old_base_name == new_base_name:
        return True, "No change needed", 0

    base_mat = bpy.data.materials.get(old_base_name)
    if not base_mat:
        return False, f"Base material '{old_base_name}' not found", 0

    if new_base_name in bpy.data.materials and new_base_name != old_base_name:
        return False, f"Name '{new_base_name}' already exists.", 0

    # Collect constants that reference this base
    const_mats = []
    for mat in bpy.data.materials:
        if mat.get("ctr_original_material") == old_base_name:
            const_mats.append(mat)

    # Check ID conflicts on the same object
    for mat in const_mats:
        if "_ID" in mat.name:
            suffix = mat.name.split('_ID', 1)[1]
            for other_slot in obj.material_slots:
                other = other_slot.material
                if other and other != mat and "_ID" in other.name:
                    other_id = other.name.split('_ID', 1)[1]
                    if other_id == suffix:
                        return False, f"ID '{suffix}' is used by another constant on this object."

    # Rename base
    base_mat.name = new_base_name

    # Rename constants
    updated = 0
    for mat in const_mats:
        if "_ID" in mat.name:
            suffix = mat.name.split('_ID', 1)[1]
            desired = f"{new_base_name}_ID{suffix}"
            if desired in bpy.data.materials and desired != mat.name:
                return False, f"Constant name '{desired}' already exists."
            mat.name = desired
            updated += 1
            # Ensure the block_id property is updated to match the new suffix
            mat["ctr_block_id"] = suffix
        else:
            desired = new_base_name
            if desired in bpy.data.materials and desired != mat.name:
                return False, f"Name '{desired}' already exists."
            mat.name = desired
            updated += 1
        # Update its original_material reference
        mat["ctr_original_material"] = new_base_name

    return True, f"Renamed base '{old_base_name}' → '{new_base_name}' and updated {updated} constant(s)", updated


def get_family_materials(material, obj, scope):
    """
    Given a starting material and a scope setting, return a set of material names
    that should be affected, based on material properties.
    Scopes: SELECTED, FULL, CONSTANTS, NAV, BASE_ONLY
    """
    if scope == 'SELECTED' or not obj or obj.type != 'MESH':
        return {material.name}

    mat_name = material.name
    result = set()

    # If it's a constant, get its base
    if material.get("ctr_block_type") is not None:
        base = material.get("ctr_original_material", "")
        if not base:
            return {mat_name}

        if scope == 'FULL':
            if base in bpy.data.materials:
                result.add(base)
            for m in bpy.data.materials:
                if m.get("ctr_original_material") == base:
                    result.add(m.name)   # includes nav points too
        elif scope == 'CONSTANTS':
            for m in bpy.data.materials:
                if m.get("ctr_original_material") == base:
                    if not m.get("ctr_is_navigation_point", False):
                        result.add(m.name)
        elif scope == 'NAV':
            for m in bpy.data.materials:
                if m.get("ctr_original_material") == base:
                    if m.get("ctr_is_navigation_point", False):
                        result.add(m.name)
        elif scope == 'BASE_ONLY':
            if base in bpy.data.materials:
                result.add(base)
        else:
            result.add(mat_name)
    else:
        # Normal material (possibly a base)
        children = [m for m in bpy.data.materials if m.get("ctr_original_material") == mat_name]
        if children:
            if scope == 'FULL':
                result.add(mat_name)
                result.update([m.name for m in children])   # all constants (incl. nav)
            elif scope == 'CONSTANTS':
                for m in children:
                    if not m.get("ctr_is_navigation_point", False):
                        result.add(m.name)
            elif scope == 'NAV':
                for m in children:
                    if m.get("ctr_is_navigation_point", False):
                        result.add(m.name)
            elif scope == 'BASE_ONLY':
                result.add(mat_name)
            else:
                result.add(mat_name)
        else:
            result.add(mat_name)

    return result