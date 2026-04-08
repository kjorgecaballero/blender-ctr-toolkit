"""
Constant Material Utilities
Functions for validating and manipulating constant materials, especially navigation points, clear_all_constant_materials() for bulk cleanup with fallback duplication.
"""

import bpy
import bmesh
from .qb_tb_navigation_utils import detect_block_from_selection


def get_faces_by_material_name(obj, material_name):
    """
    Get face indices by material name (REINDEX-SAFE)

    Args:
        obj: Blender object
        material_name: Name of the material to find

    Returns:
        List of face indices that use this material
    """
    face_indices = []

    # Find material index
    material_index = -1
    for i, slot in enumerate(obj.material_slots):
        if slot.material and slot.material.name == material_name:
            material_index = i
            break

    if material_index == -1:
        return []

    # Collect faces with this material
    for poly in obj.data.polygons:
        if poly.material_index == material_index:
            face_indices.append(poly.index)

    return face_indices


def is_valid_navigation_point(obj, material_name, bm=None):
    """
    Check if a constant material is a valid navigation point

    Args:
        obj: Blender object
        material_name: Name of the constant material
        bm: Optional existing BMesh (will create if None)

    Returns:
        Tuple: (is_valid, error_message, center_element, block_type)
    """
    # Validation 1: Check if object has constant materials
    if "constant_materials" not in obj:
        return False, "No constant materials found on object", None, None

    # Convert IDPropertyGroup to dict
    constant_materials = dict(obj["constant_materials"])

    # Validation 2: Check if material exists in constant materials
    if material_name not in constant_materials:
        return False, f"Material '{material_name}' not in constant materials", None, None

    # Validation 3: Check if marked as navigation point
    block_info = constant_materials[material_name]
    if not block_info.get("is_navigation_point", False):
        return False, f"Material '{material_name}' is not marked as navigation point", None, None

    # Validation 4: Get faces by material name (reindex-safe)
    face_indices = get_faces_by_material_name(obj, material_name)

    if not face_indices:
        return False, f"No faces found with material '{material_name}'", None, None

    # Validation 5: Must have exactly 4 faces
    if len(face_indices) != 4:
        return False, f"Has {len(face_indices)} faces, expected 4", None, None

    # Get or create BMesh
    should_free_bmesh = False
    if bm is None:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        should_free_bmesh = True

    try:
        # Get BMesh faces
        bm_faces = []
        for face_idx in face_indices:
            if face_idx < len(bm.faces):
                bm_faces.append(bm.faces[face_idx])
            else:
                if should_free_bmesh:
                    bm.free()
                return False, f"Face index {face_idx} out of range", None, None

        # Validation 6: Must have exactly 4 BMesh faces
        if len(bm_faces) != 4:
            if should_free_bmesh:
                bm.free()
            return False, f"Could not retrieve all 4 faces from BMesh (got {len(bm_faces)})", None, None

        # Validation 7: The 4 faces must form a valid block
        center, block_type = detect_block_from_selection(bm_faces)

        if not center:
            quad_count = sum(1 for f in bm_faces if len(f.verts) == 4)
            tri_count = sum(1 for f in bm_faces if len(f.verts) == 3)
            error_msg = f"Faces do not form a valid block (quads: {quad_count}, triangles: {tri_count})"

            if should_free_bmesh:
                bm.free()
            return False, error_msg, None, None

        # SUCCESS: Valid navigation point
        return True, "Valid navigation point", center, block_type

    finally:
        if should_free_bmesh and bm:
            bm.free()


def get_all_navigation_points(obj, bm=None):
    """
    Get all valid navigation points from an object

    Args:
        obj: Blender object
        bm: Optional existing BMesh

    Returns:
        List of tuples: (material_name, center_element, block_type)
    """
    navigation_points = []

    if "constant_materials" not in obj:
        return navigation_points

    # Convert IDPropertyGroup to dict
    constant_materials = dict(obj["constant_materials"])

    for mat_name, block_info in constant_materials.items():
        if block_info.get("is_navigation_point", False):
            is_valid, error_msg, center, block_type = is_valid_navigation_point(obj, mat_name, bm)

            if is_valid and center:
                navigation_points.append((mat_name, center, block_type))

    return navigation_points



# UTILITIES FOR CLEARING ALL CONSTANT MATERIALS WITH FALLBACK


def _create_base_material_from_constant(obj, const_mat_name):
    """
    Create a new base material by duplicating the constant material and stripping '_ID' suffix.
    Returns (new_material_name, new_material_index) or (None, -1) on failure.
    """
    if '_ID' in const_mat_name:
        base_name = const_mat_name.rsplit('_ID', 1)[0]
    else:
        base_name = const_mat_name

    const_mat = bpy.data.materials.get(const_mat_name)
    if not const_mat:
        return None, -1

    new_mat = const_mat.copy()
    new_mat.name = base_name

    if new_mat.name not in obj.data.materials:
        obj.data.materials.append(new_mat)
    new_index = obj.data.materials.find(new_mat.name)
    return new_mat.name, new_index


def clear_all_constant_materials(obj, fallback_duplicate=True):
    """
    Clear all constant materials from the object.
    For each constant material, try to restore the original material.
    If the original material is missing and fallback_duplicate is True,
    create a new base material from the constant material (strip '_ID' suffix)
    and assign it to the block's faces.

    Args:
        obj: Blender object (must be in OBJECT mode for safe material ops)
        fallback_duplicate: If True, create fallback base material when original missing

    Returns:
        tuple: (cleared_with_original, restored_with_fallback, failed_materials)
    """
    if "constant_materials" not in obj:
        return 0, 0, []

    constant_materials_dict = dict(obj["constant_materials"])
    fallback_cache = {}
    restored_with_fallback = 0
    cleared_with_original = 0
    failed_materials = []

    for mat_name, block_info in constant_materials_dict.items():
        block_type = block_info.get("block_type", "")
        block_id = block_info.get("block_id", 0)
        original_material_name = block_info.get("original_material", "")

        # Get all faces that use this constant material
        face_indices = get_faces_by_material_name(obj, mat_name)
        if not face_indices:
            failed_materials.append(mat_name)
            continue

        original_material = None
        if original_material_name and original_material_name in bpy.data.materials:
            original_material = bpy.data.materials[original_material_name]

        if not original_material:
            if fallback_duplicate:
                const_mat = bpy.data.materials.get(mat_name)
                if const_mat:
                    base_name = mat_name.rsplit('_ID', 1)[0] if '_ID' in mat_name else mat_name
                    if base_name in fallback_cache:
                        new_mat_name, new_index = fallback_cache[base_name]
                    else:
                        new_mat_name, new_index = _create_base_material_from_constant(obj, mat_name)
                        if new_mat_name:
                            fallback_cache[base_name] = (new_mat_name, new_index)
                        else:
                            failed_materials.append(mat_name)
                            continue

                    for idx in face_indices:
                        if idx < len(obj.data.polygons):
                            obj.data.polygons[idx].material_index = new_index
                    restored_with_fallback += 1
                else:
                    failed_materials.append(mat_name)
                    continue
            else:
                failed_materials.append(mat_name)
                continue
        else:
            # Restore original material
            if original_material_name not in obj.data.materials:
                obj.data.materials.append(original_material)
            original_mat_index = obj.data.materials.find(original_material_name)
            for idx in face_indices:
                if idx < len(obj.data.polygons):
                    obj.data.polygons[idx].material_index = original_mat_index
            cleared_with_original += 1

        # Remove constant material from dictionaries
        if mat_name in obj["constant_materials"]:
            del obj["constant_materials"][mat_name]
        const_prop_name = f"constant_name_{block_type}_{block_id}"
        if const_prop_name in obj:
            del obj[const_prop_name]

        # Delete the constant material if no users
        if mat_name in bpy.data.materials:
            mat = bpy.data.materials[mat_name]
            if mat.users == 0:
                bpy.data.materials.remove(mat)

    # Remove any orphaned constant_name_* properties
    for prop in list(obj.keys()):
        if prop.startswith("constant_name_"):
            del obj[prop]

    # Clean up unused material slots
    try:
        bpy.ops.object.material_slot_remove_unused()
    except Exception:
        pass

    return cleared_with_original, restored_with_fallback, failed_materials