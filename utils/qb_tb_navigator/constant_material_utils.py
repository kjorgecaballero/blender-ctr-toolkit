"""
Constant Material Utilities
Functions for validating and manipulating constant materials.
"""

import bpy
import bmesh
from .qb_tb_navigation_utils import detect_block_from_selection


def get_faces_by_material_name(obj, material_name):
    """
    Get face indices by material name (REINDEX-SAFE)
    """
    face_indices = []

    material_index = -1
    for i, slot in enumerate(obj.material_slots):
        if slot.material and slot.material.name == material_name:
            material_index = i
            break

    if material_index == -1:
        return []

    for poly in obj.data.polygons:
        if poly.material_index == material_index:
            face_indices.append(poly.index)

    return face_indices


def is_valid_navigation_point(obj, material_name, bm=None):
    """
    Check if a constant material is a valid navigation point.
    Checks the material's 'ctr_is_navigation_point' property.
    """
    mat = bpy.data.materials.get(material_name)
    if not mat:
        return False, "Material not found", None, None

    if mat.get("ctr_block_type") is None:
        return False, "Material is not a constant material", None, None

    if not mat.get("ctr_is_navigation_point", False):
        return False, f"Material '{material_name}' is not marked as navigation point", None, None

    face_indices = get_faces_by_material_name(obj, material_name)
    if not face_indices:
        return False, f"No faces found with material '{material_name}'", None, None

    if len(face_indices) != 4:
        return False, f"Has {len(face_indices)} faces, expected 4", None, None

    should_free_bmesh = False
    if bm is None:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        should_free_bmesh = True

    try:
        bm_faces = []
        for face_idx in face_indices:
            if face_idx < len(bm.faces):
                bm_faces.append(bm.faces[face_idx])
            else:
                if should_free_bmesh:
                    bm.free()
                return False, f"Face index {face_idx} out of range", None, None

        if len(bm_faces) != 4:
            if should_free_bmesh:
                bm.free()
            return False, f"Could not retrieve all 4 faces (got {len(bm_faces)})", None, None

        center, block_type = detect_block_from_selection(bm_faces)
        if not center:
            if should_free_bmesh:
                bm.free()
            return False, "Faces do not form a valid block", None, None

        return True, "Valid navigation point", center, block_type
    finally:
        if should_free_bmesh and bm:
            bm.free()


def _validate_block_by_material(obj, material_name, bm=None):
    """Validate that a material covers exactly 4 faces forming a valid block."""
    face_indices = get_faces_by_material_name(obj, material_name)
    if len(face_indices) != 4:
        return False, None, None

    should_free_bmesh = False
    if bm is None:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        should_free_bmesh = True

    try:
        bm_faces = []
        for idx in face_indices:
            if idx < len(bm.faces):
                bm_faces.append(bm.faces[idx])

        center, block_type = detect_block_from_selection(bm_faces)
        return (center is not None), center, block_type
    finally:
        if should_free_bmesh and bm:
            bm.free()


def get_all_navigation_points(obj, bm=None):
    """Gets all navigation points by scanning the object's material slots."""
    navigation_points = []
    if not obj or obj.type != 'MESH':
        return navigation_points

    for slot in obj.material_slots:
        mat = slot.material
        if not mat:
            continue
        if mat.get("ctr_block_type") is not None and mat.get("ctr_is_navigation_point", False):
            mat_name = mat.name
            is_valid, error_msg, center, block_type = is_valid_navigation_point(obj, mat_name, bm)
            if is_valid and center:
                navigation_points.append((mat_name, center, block_type))

    return navigation_points


def clear_all_constant_materials(obj, fallback_duplicate=True):
    """
    Clear all constant materials from the object by restoring original materials.
    Returns (cleared_with_original, restored_with_fallback, failed_materials)
    """
    if not obj or obj.type != 'MESH':
        return 0, 0, []

    # Collect names of constant materials used on this object
    mat_names = []
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.get("ctr_block_type") is not None:
            mat_names.append(mat.name)

    cleared_with_original = 0
    restored_with_fallback = 0
    failed_materials = []
    fallback_cache = {}

    for mat_name in mat_names:
        # Safely get the material object by name
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            # Material no longer exists (should not happen, but skip)
            continue

        face_indices = get_faces_by_material_name(obj, mat_name)
        if not face_indices:
            failed_materials.append(mat_name)
            continue

        original_mat_name = mat.get("ctr_original_material", "")
        original_mat = bpy.data.materials.get(original_mat_name) if original_mat_name else None

        if original_mat:
            # Restore original material
            if original_mat_name not in obj.data.materials:
                obj.data.materials.append(original_mat)
            orig_idx = obj.data.materials.find(original_mat_name)
            for idx in face_indices:
                if idx < len(obj.data.polygons):
                    obj.data.polygons[idx].material_index = orig_idx
            cleared_with_original += 1
        else:
            # Fallback: create a copy without constant metadata
            if fallback_duplicate:
                base_name = mat_name.rsplit('_ID', 1)[0] if '_ID' in mat_name else mat_name
                if base_name in fallback_cache:
                    new_mat_name, new_index = fallback_cache[base_name]
                else:
                    new_mat = mat.copy()
                    # Remove all constant metadata
                    new_mat.pop("ctr_block_type", None)
                    new_mat.pop("ctr_block_id", None)
                    new_mat.pop("ctr_original_material", None)
                    new_mat.pop("ctr_is_navigation_point", None)
                    new_mat.name = base_name
                    if new_mat.name not in obj.data.materials:
                        obj.data.materials.append(new_mat)
                    new_index = obj.data.materials.find(new_mat.name)
                    fallback_cache[base_name] = (new_mat.name, new_index)
                    new_mat_name = new_mat.name

                for idx in face_indices:
                    if idx < len(obj.data.polygons):
                        obj.data.polygons[idx].material_index = new_index
                restored_with_fallback += 1
            else:
                failed_materials.append(mat_name)
                continue

        # Remove the constant material if it has no users
        # Get it again by name to avoid stale references
        mat_to_remove = bpy.data.materials.get(mat_name)
        if mat_to_remove and mat_to_remove.users <= 1:
            bpy.data.materials.remove(mat_to_remove)

    # Clean up empty material slots
    try:
        bpy.ops.object.material_slot_remove_unused()
    except Exception:
        pass

    return cleared_with_original, restored_with_fallback, failed_materials