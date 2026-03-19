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

# Get unique and shared vertex indices from a triblock (given face indices)
def get_triblock_vertex_types(obj, face_indices, tolerance=0.001):
    """Returns (list_of_unique_vert_indices, list_of_shared_vert_indices) for a triblock."""
    mesh = obj.data
    faces = [mesh.polygons[i] for i in face_indices]
    if len(faces) != 4 or not all(len(f.vertices) == 3 for f in faces):
        return [], []

    # Build vertex position -> count and store one vertex index per position
    pos_to_count = defaultdict(int)
    vert_index_by_pos = {}
    for face in faces:
        for vert_idx in face.vertices:
            co = mesh.vertices[vert_idx].co
            found = False
            for existing_pos in list(pos_to_count.keys()):
                if vertices_are_same(co, Vector(existing_pos), tolerance):
                    pos_to_count[existing_pos] += 1
                    # Keep any valid vertex index for this position
                    vert_index_by_pos[existing_pos] = vert_idx
                    found = True
                    break
            if not found:
                key = tuple(co)
                pos_to_count[key] = 1
                vert_index_by_pos[key] = vert_idx

    unique_verts = []
    shared_verts = []
    for pos, count in pos_to_count.items():
        if count == 1:
            unique_verts.append(vert_index_by_pos[pos])
        elif count == 3:
            shared_verts.append(vert_index_by_pos[pos])
    return unique_verts, shared_verts

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
    face_indices = list(range(len(faces)))
    return are_faces_triblock_uvs_valid(obj, face_indices, tolerance)

# Triblock UV validation
# It checks that at least one adjacent triangle shares its two shared vertices
# with the same UVs as in the central triangle.
def are_faces_triblock_uvs_valid(obj, face_indices, tolerance=0.0001):
    """Check if the given faces (must be 4 triangles) have valid triblock UV arrangement.
       Valid means there exists at least one adjacent triangle whose two shared vertices
       have the same UVs as in the central triangle.
    """
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

    # Get unique and shared vertex indices
    unique_verts, shared_verts = get_triblock_vertex_types(obj, face_indices, tolerance=0.001)
    if len(unique_verts) != 3 or len(shared_verts) != 3:
        return False

    # Build a mapping from vertex index to its UV(s) across faces
    vert_to_uvs = defaultdict(list)
    for fi in face_indices:
        face = mesh.polygons[fi]
        for loop_idx, vert_idx in zip(face.loop_indices, face.vertices):
            uv = uv_layer.data[loop_idx].uv
            vert_to_uvs[vert_idx].append(uv)

    # For shared vertices, they should appear in multiple faces.
    # We need to know which triangle is the central one.
    # The central triangle is the one that contains all three shared vertices.
    central_face_index = None
    for fi in face_indices:
        face = mesh.polygons[fi]
        verts_in_face = set(face.vertices)
        if all(sv in verts_in_face for sv in shared_verts):
            central_face_index = fi
            break

    if central_face_index is None:
        return False  # No triangle contains all shared vertices (should not happen if topology is correct)

    # Get UVs of shared vertices in the central triangle
    central_uvs = {}
    face = mesh.polygons[central_face_index]
    for loop_idx, vert_idx in zip(face.loop_indices, face.vertices):
        if vert_idx in shared_verts:
            central_uvs[vert_idx] = uv_layer.data[loop_idx].uv

    if len(central_uvs) != 3:
        return False

    # Now check each adjacent triangle (the ones that are not central)
    for fi in face_indices:
        if fi == central_face_index:
            continue
        face = mesh.polygons[fi]
        # Collect UVs of shared vertices in this triangle
        adj_shared_uvs = {}
        for loop_idx, vert_idx in zip(face.loop_indices, face.vertices):
            if vert_idx in shared_verts:
                adj_shared_uvs[vert_idx] = uv_layer.data[loop_idx].uv

        if len(adj_shared_uvs) != 2:
            continue  # An adjacent triangle should have exactly 2 shared vertices

        # Check if both shared vertices have the same UV as in the central triangle
        matches = 0
        for sv, uv in adj_shared_uvs.items():
            central_uv = central_uvs.get(sv)
            if central_uv is None:
                continue
            # Compare with tolerance 
            if (abs(uv.x - central_uv.x) <= 1e-5 and abs(uv.y - central_uv.y) <= 1e-5):
                matches += 1
        if matches == 2:
            return True

    return False

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

    face_indices = list(range(len(faces)))
    valid = are_faces_triblock_uvs_valid(obj, face_indices, tolerance)
    reason = 'Valid' if valid else 'No adjacent triangle shares both shared UVs with central triangle'
    return {'valid': valid, 'reason': reason}

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


# Triblock-specific UV check 
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