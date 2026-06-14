"""
Material utilities for updating derived (constant) materials.
"""

import bpy


def update_derived_materials(obj, base_material_names, image, update_base_material, ensure_node_callback=None):
    """
    Synchronize the image texture across all materials linked to the specified base materials
    defined in the object's custom properties.
    
    Args:
        obj: The mesh object
        base_material_names: List of base material names
        image: The new image to assign
        update_base_material: Whether to update the base material itself
        ensure_node_callback: Optional function to ensure texture node exists (takes material, image)
    
    Returns:
        Number of materials updated
    """
    if not image:
        return 0

    const_dict = obj.get("constant_materials", {})
    updated_count = 0

    for base_mat_name in base_material_names:
        # Update all constant materials derived from this base
        for const_name, info in const_dict.items():
            if info.get("original_material") == base_mat_name:
                mat = bpy.data.materials.get(const_name)
                if mat:
                    if ensure_node_callback:
                        ensure_node_callback(mat, image)
                    else:
                        # Fallback to old method: just replace existing image node
                        if mat.use_nodes:
                            for node in mat.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image is not None:
                                    node.image = image
                                    updated_count += 1
                                    break
                    updated_count += 1

        # Update the base material itself if requested
        if update_base_material:
            base_mat = bpy.data.materials.get(base_mat_name)
            if base_mat:
                if ensure_node_callback:
                    ensure_node_callback(base_mat, image)
                else:
                    if base_mat.use_nodes:
                        for node in base_mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image is not None:
                                node.image = image
                                updated_count += 1
                                break
                updated_count += 1

    return updated_count


def is_constant_id_unique(obj, id_value, exclude_material=None):
    """
    Check if the ID (suffix after '_ID') is already used by any other constant material on the object.
    Args:
        obj: The mesh object containing constant_materials dict.
        id_value: The ID string to check (e.g., "xd").
        exclude_material: Name of a constant material to ignore (used during renaming).
    Returns:
        True if ID is unique, False if another constant already uses the same ID.
    """
    const_dict = obj.get("constant_materials", {})
    for mat_name, info in const_dict.items():
        if exclude_material and mat_name == exclude_material:
            continue
        if '_ID' in mat_name:
            existing_id = mat_name.split('_ID', 1)[1]
            if existing_id == id_value:
                return False
    return True


# Material Manager helpers

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


def is_base_name_in_use(const_dict, name, exclude_material=None):
    """Check if 'name' is used as original_material in any constant material."""
    for cname, cinfo in const_dict.items():
        if exclude_material and cname == exclude_material:
            continue
        if cinfo.get("original_material") == name:
            return True
    return False


def rename_material_if_unique(mat, new_name, const_dict=None, exclude_material=None):
    """Rename material if new_name is unique and not a used base name."""
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


def update_constant_material_base_reference(old_base_name, new_base_name):
    """
    Update the 'original_material' field in all constant_materials dictionaries
    of all mesh objects in the scene from old_base_name to new_base_name.
    
    Args:
        old_base_name: Current name of the base material
        new_base_name: New name of the base material
    
    Returns:
        int: Number of constant material entries updated
    """
    if old_base_name == new_base_name:
        return 0
    
    updated_count = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH' or "constant_materials" not in obj:
            continue
        
        const_dict = obj["constant_materials"]
        modified = False
        
        # Iterate over a list of keys because we might modify the dict
        for mat_name, info in list(const_dict.items()):
            if info.get("original_material") == old_base_name:
                info["original_material"] = new_base_name
                modified = True
                updated_count += 1
        
        if modified:
            obj["constant_materials"] = const_dict
    
    return updated_count


def rename_base_material_family(obj, old_base_name, new_base_name):
    """
    Rename a base material and all its constant materials (including navigation points)
    on the given object, using the same logic as MATERIAL_OT_RenameMaterial.
    
    Args:
        obj: The mesh object that contains the constant_materials dict.
        old_base_name: Current name of the base material.
        new_base_name: Desired new name for the base material.
    
    Returns:
        tuple: (success: bool, message: str, updated_count: int)
    """
    if not obj or obj.type != 'MESH':
        return False, "Object is not a valid mesh", 0
    if old_base_name == new_base_name:
        return True, "No change needed", 0
    
    const_dict = obj.get("constant_materials", {})
    base_mat = bpy.data.materials.get(old_base_name)
    if not base_mat:
        return False, f"Base material '{old_base_name}' not found", 0
    
    # Check if new_base_name is already used by another material
    if new_base_name in bpy.data.materials and new_base_name != old_base_name:
        return False, f"Name '{new_base_name}' already exists. Choose a different name.", 0
    
    # Check if new_base_name is already used as original_material by any constant (excluding current family)
    if is_base_name_in_use(const_dict, new_base_name, exclude_material=None):
        return False, f"Name '{new_base_name}' is already used as a base name for other constant materials. Cannot rename.", 0
    
    # Collect constants that reference this base
    siblings = []
    for cname, cinfo in const_dict.items():
        if cinfo.get("original_material") == old_base_name:
            siblings.append((cname, cinfo))
    
    # Check ID conflicts with other constants (to avoid ID collision after rename)
    for cname, cinfo in siblings:
        if '_ID' in cname:
            suffix = cname.split('_ID', 1)[1]
            for other_name, other_info in const_dict.items():
                if other_name == cname:
                    continue
                if '_ID' in other_name:
                    other_id = other_name.split('_ID', 1)[1]
                    if other_id == suffix:
                        return False, f"ID '{suffix}' (from constant '{cname}') is already used by another constant '{other_name}'. Cannot rename base without changing IDs.", 0
    
    # Check each constant's new name availability
    for cname, cinfo in siblings:
        if '_ID' in cname:
            suffix = cname.split('_ID', 1)[1]
        else:
            suffix = ""
        desired = f"{new_base_name}_ID{suffix}"
        if desired in bpy.data.materials and desired != cname:
            return False, f"Constant material name '{desired}' already exists. Cannot rename '{cname}'.", 0
    
    # Rename the base material
    base_mat.name = new_base_name
    
    # Rename all constant materials and update const_dict
    updated = 0
    for cname, cinfo in siblings:
        if '_ID' in cname:
            suffix = cname.split('_ID', 1)[1]
        else:
            suffix = ""
        desired = f"{new_base_name}_ID{suffix}"
        const_mat = bpy.data.materials.get(cname)
        if const_mat and desired != const_mat.name:
            const_mat.name = desired
        # Update const_dict entry
        new_info = dict(cinfo)
        new_info["original_material"] = new_base_name
        const_dict[desired] = new_info
        if cname != desired:
            del const_dict[cname]
        # Update object property constant_name_{block_type}_{block_id}
        block_type = cinfo.get("block_type")
        block_id = cinfo.get("block_id")
        if block_type and block_id is not None:
            prop_name = f"constant_name_{block_type}_{block_id}"
            if prop_name in obj and obj[prop_name] == cname:
                obj[prop_name] = desired
        updated += 1
    
    obj["constant_materials"] = const_dict
    return True, f"Renamed base '{old_base_name}' → '{new_base_name}' and updated {updated} constant(s)", updated



def get_family_materials(material, obj, scope):
    """
    Given a starting material and a scope setting, return a set of material names
    that should be affected.

    Args:
        material: bpy.types.Material (the source material)
        obj: bpy.types.Object (mesh object containing constant_materials dict)
        scope: string from scene.blend_apply_scope ('SELECTED', 'FAMILY', 'CONSTANTS_ONLY', 'BASE_ONLY')

    Returns:
        set of material names
    """
    if scope == 'SELECTED' or not obj or obj.type != 'MESH':
        return {material.name}

    const_dict = obj.get("constant_materials", {})
    if not const_dict:
        return {material.name}

    # Build reverse mapping: base -> set of constants
    base_to_constants = {}
    for cname, cinfo in const_dict.items():
        base = cinfo.get("original_material", "")
        if base:
            base_to_constants.setdefault(base, set()).add(cname)

    mat_name = material.name
    result = set()

    # Case: material is a constant
    if mat_name in const_dict:
        base = const_dict[mat_name].get("original_material", "")
        if not base:
            return {mat_name}
        if scope == 'FAMILY':
            result.add(base)
            result.update(base_to_constants.get(base, set()))
        elif scope == 'CONSTANTS_ONLY':
            result.update(base_to_constants.get(base, set()))
        elif scope == 'BASE_ONLY':
            result.add(base)
        else:
            result.add(mat_name)
    # Case: material is normal (possibly a base)
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