"""
Material utilities for updating derived (constant) materials.
"""

import bpy


def update_derived_materials(obj, base_material_names, image, update_base_material):
    """
    Synchronize the image texture across all materials linked to the specified base materials
    defined in the object's custom properties.
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
                if mat and mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image is not None:
                            node.image = image
                            updated_count += 1
                            break

        # Update the base material itself if requested
        if update_base_material:
            base_mat = bpy.data.materials.get(base_mat_name)
            if base_mat and base_mat.use_nodes:
                for node in base_mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        node.image = image
                        updated_count += 1
                        break

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