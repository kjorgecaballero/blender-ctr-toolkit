"""
Helper Functions for Quadblock/Triblock List
Utility functions used by the block list UI
"""

import bpy


def get_material_image_icon(material_name):
    """Get the actual image icon from a material's texture if it exists (Blender 3.3+ compatible)."""
    if not material_name or material_name not in bpy.data.materials:
        return 'MATERIAL_DATA'

    material = bpy.data.materials[material_name]

    # Only use node trees (texture slots are deprecated and removed in Blender 3.0+)
    if material.use_nodes and material.node_tree:
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                image = node.image
                # Ensure preview is generated
                if not hasattr(image, 'preview') or not image.preview:
                    image.preview_ensure()
                if image.preview:
                    return image.preview.icon_id

    # Fallback to generic material icon
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