import bpy
from .qb_tb_validation import (
    analyze_quadblock_by_coordinates,
    analyze_triblock_by_coordinates,
    analyze_faces_for_block   # added import
)
from ...utils.range_box import is_object_in_range, get_out_of_range_objects

def get_mesh_type(obj):
    if obj.type != 'MESH':
        return None
    
    if any(len(poly.vertices) > 4 for poly in obj.data.polygons):
        return None
    
    if analyze_quadblock_by_coordinates(obj):
        return 'QUADBLOCK'
    
    if analyze_triblock_by_coordinates(obj):
        return 'TRIBLOCK'
    
    return None

def get_object_issues(obj):
    issues = []
    
    if obj.type != 'MESH':
        issues.append("non_mesh")
        return issues
    
    if any(len(poly.vertices) > 4 for poly in obj.data.polygons):
        issues.append("ngon")
    
    mesh_type = get_mesh_type(obj)
    if mesh_type is None:
        issues.append("invalid_geometry")
    
    # --- UNIFIED UV VALIDATION using analyze_faces_for_block ---
    # Get all face indices of the object
    all_face_indices = list(range(len(obj.data.polygons)))
    uv_issues = analyze_faces_for_block(obj, all_face_indices)
    
    # Map the issues returned by analyze_faces_for_block to the expected labels
    if "invalid_uvs" in uv_issues:
        issues.append("invalid_uvs")
    if "degenerated_uvs" in uv_issues:
        issues.append("degenerated_uvs")
    if "invalid_triblock_uvs" in uv_issues:
        issues.append("invalid_triblock_uvs")
    # Note: analyze_faces_for_block may also return 'quadblock' or 'triblock',
    # but those are not treated as issues in this context.
    # ------------------------------------------------------------
    
    if not is_object_in_range(obj):
        issues.append("out_of_range")
    
    return issues

def get_range_statistics():
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    in_range, out_of_range = get_out_of_range_objects(mesh_objects)
    
    return {
        'total_meshes': len(mesh_objects),
        'in_range': len(in_range),
        'out_of_range': len(out_of_range),
        'in_range_objects': in_range,
        'out_of_range_objects': out_of_range,
        'range_box_exists': bpy.data.objects.get("Range") is not None
    }