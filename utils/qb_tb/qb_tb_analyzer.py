import bpy
from .qb_tb_validator import (
    analyze_quadblock_by_coordinates,
    analyze_triblock_by_coordinates,
    are_uvs_degenerated,
    are_triblock_uvs_valid
)

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
    
    if obj.data.uv_layers:
        has_invalid_uvs = False
        has_degenerated_uvs = False
        
        for uv_layer in obj.data.uv_layers:
            if len(uv_layer.data) == 0:
                continue
                
            for uv_data in uv_layer.data:
                u, v = uv_data.uv.x, uv_data.uv.y
                if u < 0 or u > 1 or v < 0 or v > 1:
                    has_invalid_uvs = True
                    break
            
            if are_uvs_degenerated(uv_layer):
                has_degenerated_uvs = True
        
        if has_invalid_uvs:
            issues.append("invalid_uvs")
        if has_degenerated_uvs:
            issues.append("degenerated_uvs")
        
        if mesh_type == 'TRIBLOCK':
            try:
                if not are_triblock_uvs_valid(obj):
                    issues.append("invalid_triblock_uvs")
            except Exception as e:
                print(f"Error checking triblock UVs for {obj.name}: {e}")
    
    return issues