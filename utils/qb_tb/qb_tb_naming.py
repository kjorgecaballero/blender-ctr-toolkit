def build_object_name(base_name, mesh_type, issues):
    """Build an object name with multiple suffixes based on type and issues"""
    name_parts = [base_name]
    
    # Check for non-mesh objects first (they won't have a valid mesh_type)
    if "non_mesh" in issues:
        name_parts.append("nonmesh")
        return "_".join(name_parts)  # Return early for non-mesh objects
    
    # Then the geometry type if valid (only for mesh objects)
    if mesh_type == 'QUADBLOCK' and "invalid_geometry" not in issues:
        name_parts.append("quadblock")
    elif mesh_type == 'TRIBLOCK' and "invalid_geometry" not in issues:
        name_parts.append("triblock")
    
    # Then the problems (only for mesh objects)
    if "ngon" in issues:
        name_parts.append("ngon")
    if "invalid_geometry" in issues:
        name_parts.append("invalid_geo")
    if "invalid_uvs" in issues:
        name_parts.append("invalid_uvs")
    if "degenerated_uvs" in issues:
        name_parts.append("degenerated_uvs")
    
    return "_".join(name_parts)

def clean_object_name(name):
    """Clean all custom suffixes from object name"""
    suffixes = ["_quadblock", "_triblock", "_nonmesh", "_ngon", "_invalid_geo", "_invalid_uvs", "_degenerated_uvs"]
    
    clean_name = name
    for suffix in suffixes:
        clean_name = clean_name.replace(suffix, "")
    
    return clean_name