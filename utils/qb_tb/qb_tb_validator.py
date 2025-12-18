import bpy
from math import isclose
from collections import defaultdict
from mathutils import Vector

def vertices_are_same(v1, v2, tolerance=0.001):
    """Check if two vertices have the same position within tolerance"""
    return (isclose(v1.x, v2.x, abs_tol=tolerance) and 
            isclose(v1.y, v2.y, abs_tol=tolerance) and 
            isclose(v1.z, v2.z, abs_tol=tolerance))

def analyze_quadblock_by_coordinates(obj, tolerance=0.001):
    """Analyze if an object is a valid Quadblock based on vertex coordinates"""
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    faces = list(mesh.polygons)
    
    # Must have exactly 4 faces
    if len(faces) != 4:
        return False
    
    # All faces must be quads
    if not all(len(face.vertices) == 4 for face in faces):
        return False
    
    # Collect all vertex positions
    all_vertex_positions = []
    for face in faces:
        face_vertices = []
        for vert_idx in face.vertices:
            face_vertices.append(mesh.vertices[vert_idx].co.copy())
        all_vertex_positions.append(face_vertices)
    
    # Count unique vertices and shared vertices between faces
    unique_vertices = []
    vertex_face_count = defaultdict(int)
    
    # First pass: identify unique vertices by position
    for i, face_verts in enumerate(all_vertex_positions):
        for vert_pos in face_verts:
            # Check if this vertex already exists in unique_vertices
            found = False
            for unique_vert in unique_vertices:
                if vertices_are_same(vert_pos, unique_vert, tolerance):
                    vertex_face_count[tuple(unique_vert)] += 1
                    found = True
                    break
            if not found:
                unique_vertices.append(vert_pos)
                vertex_face_count[tuple(vert_pos)] = 1
    
    # For a valid Quadblock, we must have exactly 9 unique vertices
    if len(unique_vertices) != 9:
        return False
    
    # Count how many vertices are shared by how many faces
    share_count = defaultdict(int)
    for count in vertex_face_count.values():
        share_count[count] += 1
    
    # In a valid Quadblock:
    # - 4 vertices shared by 1 face (corners)
    # - 4 vertices shared by 2 faces (edges)  
    # - 1 vertex shared by 4 faces (center)
    return (share_count.get(1, 0) == 4 and 
            share_count.get(2, 0) == 4 and 
            share_count.get(4, 0) == 1)

def analyze_triblock_by_coordinates(obj, tolerance=0.001):
    """Analyze if an object is a valid Triblock based on vertex coordinates"""
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    faces = list(mesh.polygons)
    
    # Must have exactly 4 faces
    if len(faces) != 4:
        return False
    
    # All faces must be triangles
    if not all(len(face.vertices) == 3 for face in faces):
        return False
    
    # Collect all vertex positions
    all_vertex_positions = []
    for face in faces:
        face_vertices = []
        for vert_idx in face.vertices:
            face_vertices.append(mesh.vertices[vert_idx].co.copy())
        all_vertex_positions.append(face_vertices)
    
    # Count unique vertices and shared vertices between faces
    unique_vertices = []
    vertex_face_count = defaultdict(int)
    
    for i, face_verts in enumerate(all_vertex_positions):
        for vert_pos in face_verts:
            found = False
            for unique_vert in unique_vertices:
                if vertices_are_same(vert_pos, unique_vert, tolerance):
                    vertex_face_count[tuple(unique_vert)] += 1
                    found = True
                    break
            if not found:
                unique_vertices.append(vert_pos)
                vertex_face_count[tuple(vert_pos)] = 1
    
    # For a valid Triblock, we must have exactly 6 unique vertices
    if len(unique_vertices) != 6:
        return False
    
    # Count how many vertices are shared by how many faces
    share_count = defaultdict(int)
    for count in vertex_face_count.values():
        share_count[count] += 1
    
    # In a valid Triblock:
    # - 3 vertices shared by 1 face (unique vertices)
    # - 3 vertices shared by 3 faces (shared vertices)
    return (share_count.get(1, 0) == 3 and 
            share_count.get(3, 0) == 3)

def are_uvs_degenerated(uv_layer, tolerance=0.0001):
    """Check if all UVs in a layer are at the same coordinate"""
    if not uv_layer.data:
        return False
    
    first_uv = uv_layer.data[0].uv.copy()
    
    for uv_data in uv_layer.data:
        current_uv = uv_data.uv
        if (abs(current_uv.x - first_uv.x) > tolerance or 
            abs(current_uv.y - first_uv.y) > tolerance):
            return False
    
    return True