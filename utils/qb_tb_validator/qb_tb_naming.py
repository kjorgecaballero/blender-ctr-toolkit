def build_object_name(base_name, mesh_type, issues):
    name_parts = [base_name]
    
    if "non_mesh" in issues:
        name_parts.append("nonmesh")
        return "_".join(name_parts)
    
    if mesh_type == 'QUADBLOCK' and "invalid_geometry" not in issues:
        name_parts.append("quadblock")
    elif mesh_type == 'TRIBLOCK' and "invalid_geometry" not in issues:
        name_parts.append("triblock")
    
    if "ngon" in issues:
        name_parts.append("ngon")
    if "invalid_geometry" in issues:
        name_parts.append("invalid_geo")
    if "invalid_uvs" in issues:
        name_parts.append("invalid_uvs")
    if "degenerated_uvs" in issues:
        name_parts.append("degenerated_uvs")
    if "invalid_triblock_uvs" in issues:
        name_parts.append("invalid_triblock_uvs")
    if "out_of_range" in issues:
        name_parts.append("out_of_range")
    if "multiple_materials" in issues:
        name_parts.append("multi_mat")
    
    return "_".join(name_parts)

def clean_object_name(name):
    suffixes = ["_quadblock", "_triblock", "_nonmesh", "_ngon", "_invalid_geo", 
                "_invalid_uvs", "_degenerated_uvs", "_invalid_triblock_uvs", "_out_of_range",
                "_multi_mat"]
    clean_name = name
    for suffix in suffixes:
        clean_name = clean_name.replace(suffix, "")
    return clean_name