"""
Helper Functions for Quadblock/Triblock List
Utility functions used by the block list UI
Unused functions `get_constant_material_names`, `get_navigation_points`,
`get_broken_navigation_points`, `count_navigation_points` removed.
"""

import bpy


def get_material_image_icon(material_name):
    """Get the actual image icon from a material's texture if it exists"""
    if material_name and material_name in bpy.data.materials:
        material = bpy.data.materials[material_name]

        if material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    image = node.image
                    if hasattr(image, 'preview') and image.preview:
                        return image.preview.icon_id
                    else:
                        image.preview_ensure()
                        if image.preview:
                            return image.preview.icon_id

            if material.texture_slots and material.active_texture:
                tex = material.active_texture
                if tex.type == 'IMAGE' and tex.image:
                    image = tex.image
                    if hasattr(image, 'preview') and image.preview:
                        return image.preview.icon_id

    return 'MATERIAL_DATA'


def get_block_material_name(obj, block_type, block_id):
    """Get the actual material name for a quadblock or triblock"""
    material_name = ""

    try:
        if block_type == "quadblock" and "quadblock_faces_map" in obj:
            if str(block_id) in obj["quadblock_faces_map"]:
                face_indices = obj["quadblock_faces_map"][str(block_id)]
                if face_indices and len(face_indices) > 0:
                    first_face_idx = face_indices[0]
                    if first_face_idx < len(obj.data.polygons):
                        face = obj.data.polygons[first_face_idx]
                        mat_index = face.material_index
                        if 0 <= mat_index < len(obj.material_slots):
                            material = obj.material_slots[mat_index].material
                            if material:
                                material_name = material.name

        elif block_type == "triblock" and "triblock_faces_map" in obj:
            if str(block_id) in obj["triblock_faces_map"]:
                face_indices = obj["triblock_faces_map"][str(block_id)]
                if face_indices and len(face_indices) > 0:
                    first_face_idx = face_indices[0]
                    if first_face_idx < len(obj.data.polygons):
                        face = obj.data.polygons[first_face_idx]
                        mat_index = face.material_index
                        if 0 <= mat_index < len(obj.material_slots):
                            material = obj.material_slots[mat_index].material
                            if material:
                                material_name = material.name
    except Exception:
        pass

    return material_name