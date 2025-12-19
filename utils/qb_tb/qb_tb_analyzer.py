import bpy
from .qb_tb_validator import (
    analyze_quadblock_by_coordinates,
    analyze_triblock_by_coordinates,
    are_uvs_degenerated
)

def get_mesh_type(obj):
    """Determine mesh type based on vertex coordinates"""
    if obj.type != 'MESH':
        return None
    
    # Check for NGons
    if any(len(poly.vertices) > 4 for poly in obj.data.polygons):
        return None
    
    # Check Quadblock
    if analyze_quadblock_by_coordinates(obj):
        return 'QUADBLOCK'
    
    # Check Triblock
    if analyze_triblock_by_coordinates(obj):
        return 'TRIBLOCK'
    
    return None

def get_object_issues(obj):
    """Analyze an object and return a list of all detected problems"""
    issues = []
    
    if obj.type != 'MESH':
        issues.append("non_mesh")
        return issues
    
    # Check NGons
    if any(len(poly.vertices) > 4 for poly in obj.data.polygons):
        issues.append("ngon")
    
    # Check geometry
    mesh_type = get_mesh_type(obj)
    if mesh_type is None:
        issues.append("invalid_geometry")
    
    # Check UVs
    if obj.data.uv_layers:
        has_invalid_uvs = False
        has_degenerated_uvs = False
        
        for uv_layer in obj.data.uv_layers:
            # Check UVs out of range
            for uv_data in uv_layer.data:
                u, v = uv_data.uv.x, uv_data.uv.y
                if u < 0 or u > 1 or v < 0 or v > 1:
                    has_invalid_uvs = True
                    break
            
            # Check degenerated UVs
            if are_uvs_degenerated(uv_layer):
                has_degenerated_uvs = True
        
        if has_invalid_uvs:
            issues.append("invalid_uvs")
        if has_degenerated_uvs:
            issues.append("degenerated_uvs")
    
    return issues