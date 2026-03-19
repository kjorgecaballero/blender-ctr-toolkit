import bpy
from math import isclose
from collections import defaultdict
from mathutils import Vector

# Check if two vertices are the same within tolerance
def vertices_are_same(v1, v2, tolerance=0.001):
    return (isclose(v1.x, v2.x, abs_tol=tolerance) and 
            isclose(v1.y, v2.y, abs_tol=tolerance) and 
            isclose(v1.z, v2.z, abs_tol=tolerance))

# Analyze vertex coordinates to check quadblock
def analyze_quadblock_by_coordinates(obj, tolerance=0.001):
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    faces = list(mesh.polygons)
    
    if len(faces) != 4:
        return False
    
    if not all(len(face.vertices) == 4 for face in faces):
        return False
    
    all_vertex_positions = []
    for face in faces:
        face_vertices = []
        for vert_idx in face.vertices:
            face_vertices.append(mesh.vertices[vert_idx].co.copy())
        all_vertex_positions.append(face_vertices)
    
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
    
    if len(unique_vertices) != 9:
        return False
    
    share_count = defaultdict(int)
    for count in vertex_face_count.values():
        share_count[count] += 1
    
    return (share_count.get(1, 0) == 4 and 
            share_count.get(2, 0) == 4 and 
            share_count.get(4, 0) == 1)

# Analyze vertex coordinates to check triblock
def analyze_triblock_by_coordinates(obj, tolerance=0.001):
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    faces = list(mesh.polygons)
    
    if len(faces) != 4:
        return False
    
    if not all(len(face.vertices) == 3 for face in faces):
        return False
    
    all_vertex_positions = []
    for face in faces:
        face_vertices = []
        for vert_idx in face.vertices:
            face_vertices.append(mesh.vertices[vert_idx].co.copy())
        all_vertex_positions.append(face_vertices)
    
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
    
    if len(unique_vertices) != 6:
        return False
    
    share_count = defaultdict(int)
    for count in vertex_face_count.values():
        share_count[count] += 1
    
    return (share_count.get(1, 0) == 3 and 
            share_count.get(3, 0) == 3)

# Check if all UVs are the same (degenerated)
def are_uvs_degenerated(uv_layer, tolerance=0.0001):
    if not uv_layer.data:
        return False
    
    first_uv = uv_layer.data[0].uv.copy()
    
    for uv_data in uv_layer.data:
        current_uv = uv_data.uv
        if (abs(current_uv.x - first_uv.x) > tolerance or 
            abs(current_uv.y - first_uv.y) > tolerance):
            return False
    
    return True

# Validate triblock UVs for an entire object (kept for compatibility)
def are_triblock_uvs_valid(obj, tolerance=0.0001):
    if obj.type != 'MESH':
        return False
    
    mesh = obj.data
    faces = list(mesh.polygons)
    if len(faces) != 4 or not all(len(face.vertices) == 3 for face in faces):
        return False
    
    if not mesh.uv_layers:
        return False
    
    uv_layer = mesh.uv_layers.active
    if not uv_layer or len(uv_layer.data) == 0:
        return False
    
    triangles_uvs = []
    for face in faces:
        face_uvs = []
        for loop_index in face.loop_indices:
            if loop_index < len(uv_layer.data):
                uv = uv_layer.data[loop_index].uv
                face_uvs.append({
                    'uv': uv,
                    'uv_key': (round(uv.x, 4), round(uv.y, 4))
                })
        if len(face_uvs) != 3:
            return False
        triangles_uvs.append(face_uvs)
    
    valid_pairs = []
    for i in range(4):
        for j in range(i + 1, 4):
            shared_uvs = []
            for uv1 in triangles_uvs[i]:
                for uv2 in triangles_uvs[j]:
                    if uv1['uv_key'] == uv2['uv_key']:
                        shared_uvs.append(uv1['uv'])
                        break
            if len(shared_uvs) >= 2:
                valid_pairs.append({
                    'tri1': i,
                    'tri2': j,
                    'shared_count': len(shared_uvs),
                    'shared_uvs': shared_uvs
                })
    
    return len(valid_pairs) > 0

# Get detailed triblock UV validation results (kept for compatibility)
def get_triblock_uv_validation_details(obj, tolerance=0.0001):
    if obj.type != 'MESH':
        return {'valid': False, 'reason': 'Not a mesh'}
    
    mesh = obj.data
    faces = list(mesh.polygons)
    if len(faces) != 4:
        return {'valid': False, 'reason': f'Expected 4 faces, found {len(faces)}'}
    
    if not all(len(face.vertices) == 3 for face in faces):
        return {'valid': False, 'reason': 'Not all faces are triangles'}
    
    if not mesh.uv_layers:
        return {'valid': False, 'reason': 'No UV layers'}
    
    uv_layer = mesh.uv_layers.active
    if not uv_layer or len(uv_layer.data) == 0:
        return {'valid': False, 'reason': 'No UV data in active layer'}
    
    triangles_uvs = []
    for face_idx, face in enumerate(faces):
        face_uvs = []
        for loop_index in face.loop_indices:
            if loop_index < len(uv_layer.data):
                uv = uv_layer.data[loop_index].uv
                face_uvs.append({
                    'uv': uv,
                    'uv_key': (round(uv.x, 4), round(uv.y, 4))
                })
        if len(face_uvs) != 3:
            return {'valid': False, 'reason': f'Triangle {face_idx} does not have 3 UVs'}
        triangles_uvs.append({
            'index': face_idx,
            'uvs': face_uvs
        })
    
    valid_pairs = []
    all_pairs = []
    for i in range(4):
        for j in range(i + 1, 4):
            shared_uvs = []
            shared_uv_keys = []
            for uv1 in triangles_uvs[i]['uvs']:
                for uv2 in triangles_uvs[j]['uvs']:
                    if uv1['uv_key'] == uv2['uv_key']:
                        shared_uvs.append(uv1['uv'])
                        shared_uv_keys.append(uv1['uv_key'])
                        break
            
            pair_info = {
                'triangles': (i, j),
                'shared_count': len(shared_uvs),
                'shared_uvs': shared_uvs,
                'shared_uv_keys': shared_uv_keys,
                'is_valid': len(shared_uvs) >= 2
            }
            
            all_pairs.append(pair_info)
            if pair_info['is_valid']:
                valid_pairs.append(pair_info)
    
    is_valid = len(valid_pairs) > 0
    return {
        'valid': is_valid,
        'valid_pairs': len(valid_pairs),
        'total_pairs': len(all_pairs),
        'pairs_details': all_pairs,
        'triangles_uvs': triangles_uvs,
        'reason': 'Valid' if is_valid else 'No triangle pair shares 2+ UVs'
    }


# Validate triblock UVs for a given set of face indices
def are_faces_triblock_uvs_valid(obj, face_indices, tolerance=0.0001):
    """Check if the given faces (must be 4 triangles) have valid triblock UV arrangement."""
    if obj.type != 'MESH':
        return False
    mesh = obj.data
    if len(face_indices) != 4:
        return False
    faces = [mesh.polygons[i] for i in face_indices]
    if not all(len(f.vertices) == 3 for f in faces):
        return False
    if not mesh.uv_layers:
        return False
    uv_layer = mesh.uv_layers.active
    if not uv_layer or len(uv_layer.data) == 0:
        return False

    triangles_uvs = []
    for fi in face_indices:
        face = mesh.polygons[fi]
        face_uvs = []
        for loop_index in face.loop_indices:
            uv = uv_layer.data[loop_index].uv
            face_uvs.append({
                'uv': uv,
                'uv_key': (round(uv.x, 4), round(uv.y, 4))
            })
        triangles_uvs.append(face_uvs)

    # Check for at least one pair sharing 2+ UVs
    for i in range(4):
        for j in range(i+1, 4):
            shared_keys = set(k['uv_key'] for k in triangles_uvs[i]) & set(k['uv_key'] for k in triangles_uvs[j])
            if len(shared_keys) >= 2:
                return True
    return False


# UV issue function 
def get_face_uv_issues(obj, face_indices):
    """Check UVs for the given faces and return a list of UV-related issues.
       Possible issues: 'invalid_uvs', 'degenerated_uvs'"""
    issues = []
    mesh = obj.data
    if not mesh.uv_layers:
        return issues
    uv_layer = mesh.uv_layers.active.data

    # Check for invalid UVs (out of 0-1 range)
    for fi in face_indices:
        face = mesh.polygons[fi]
        for loop_idx in face.loop_indices:
            uv = uv_layer[loop_idx].uv
            if uv.x < 0 or uv.x > 1 or uv.y < 0 or uv.y > 1:
                issues.append("invalid_uvs")
                break
        if "invalid_uvs" in issues:
            break

    # Check for degenerated UVs (all UVs identical)
    if face_indices:
        all_uvs = []
        for fi in face_indices:
            face = mesh.polygons[fi]
            for loop_idx in face.loop_indices:
                all_uvs.append(uv_layer[loop_idx].uv)
        if all_uvs:
            first_uv = all_uvs[0]
            degenerated = True
            for uv in all_uvs[1:]:
                if (abs(uv.x - first_uv.x) > 0.0001 or abs(uv.y - first_uv.y) > 0.0001):
                    degenerated = False
                    break
            if degenerated:
                issues.append("degenerated_uvs")

    return list(set(issues))


# Functions for vertex group validation

def get_faces_of_vertex_group(obj, vg_name):
    """
    Returns a list of face indices that are fully contained in the vertex group.
    A face is considered part of the group if all its vertices have weight > 0 in the group.
    """
    vg = obj.vertex_groups.get(vg_name)
    if not vg:
        return []
    # Collect vertices with weight > 0
    vert_indices = []
    for v in obj.data.vertices:
        try:
            if vg.weight(v.index) > 0:
                vert_indices.append(v.index)
        except RuntimeError:
            pass
    if not vert_indices:
        return []
    vert_set = set(vert_indices)
    # Find faces where all vertices are in the set
    face_indices = []
    for i, face in enumerate(obj.data.polygons):
        if all(v in vert_set for v in face.vertices):
            face_indices.append(i)
    return face_indices


def analyze_faces_for_quadblock(obj, face_indices, tolerance=0.001):
    """
    Given a list of face indices (supposedly 4 quads), analyze if they form a valid quadblock.
    Returns True if valid, False otherwise.
    """
    if len(face_indices) != 4:
        return False
    mesh = obj.data
    faces = [mesh.polygons[i] for i in face_indices]
    if not all(len(f.vertices) == 4 for f in faces):
        return False

    all_vertex_positions = []
    for face in faces:
        face_vertices = []
        for vert_idx in face.vertices:
            face_vertices.append(mesh.vertices[vert_idx].co.copy())
        all_vertex_positions.append(face_vertices)

    unique_vertices = []
    vertex_face_count = defaultdict(int)

    for face_verts in all_vertex_positions:
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

    if len(unique_vertices) != 9:
        return False

    share_count = defaultdict(int)
    for count in vertex_face_count.values():
        share_count[count] += 1

    return (share_count.get(1, 0) == 4 and
            share_count.get(2, 0) == 4 and
            share_count.get(4, 0) == 1)


def analyze_faces_for_triblock(obj, face_indices, tolerance=0.001):
    """
    Given a list of face indices (supposedly 4 triangles), analyze if they form a valid triblock.
    Returns True if valid, False otherwise.
    """
    if len(face_indices) != 4:
        return False
    mesh = obj.data
    faces = [mesh.polygons[i] for i in face_indices]
    if not all(len(f.vertices) == 3 for f in faces):
        return False

    all_vertex_positions = []
    for face in faces:
        face_vertices = []
        for vert_idx in face.vertices:
            face_vertices.append(mesh.vertices[vert_idx].co.copy())
        all_vertex_positions.append(face_vertices)

    unique_vertices = []
    vertex_face_count = defaultdict(int)

    for face_verts in all_vertex_positions:
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

    if len(unique_vertices) != 6:
        return False

    share_count = defaultdict(int)
    for count in vertex_face_count.values():
        share_count[count] += 1

    return (share_count.get(1, 0) == 3 and
            share_count.get(3, 0) == 3)


# Triblock-specific UV check ---
def analyze_faces_for_block(obj, face_indices):
    """
    Analyze the given faces (belonging to a potential quadblock or triblock)
    and return a list of issues.
    Possible issues: 'quadblock', 'triblock', 'invalid_geometry',
                     'invalid_uvs', 'degenerated_uvs', 'invalid_triblock_uvs'
    """
    issues = []
    if not face_indices:
        issues.append("invalid_geometry")
        return issues

    # Check if it's a valid quadblock
    is_quad = analyze_faces_for_quadblock(obj, face_indices)
    is_tri = False
    if is_quad:
        issues.append("quadblock")
    else:
        # Check if it's a valid triblock
        is_tri = analyze_faces_for_triblock(obj, face_indices)
        if is_tri:
            issues.append("triblock")
        else:
            issues.append("invalid_geometry")

    # Add general UV issues
    uv_issues = get_face_uv_issues(obj, face_indices)
    issues.extend(uv_issues)

    # If it's a triblock, check triblock-specific UV validity
    if is_tri:
        if not are_faces_triblock_uvs_valid(obj, face_indices):
            issues.append("invalid_triblock_uvs")

    return issues