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