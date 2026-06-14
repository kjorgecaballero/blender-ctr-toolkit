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

# Validate triblock UVs for an entire object
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

    unique_verts, shared_verts = get_triblock_vertex_types(obj, face_indices, tolerance=0.001)
    if len(unique_verts) != 3 or len(shared_verts) != 3:
        return False

    vert_to_uvs = defaultdict(list)
    for fi in face_indices:
        face = mesh.polygons[fi]
        for loop_idx, vert_idx in zip(face.loop_indices, face.vertices):
            uv = uv_layer.data[loop_idx].uv
            vert_to_uvs[vert_idx].append(uv)

    central_face_index = None
    for fi in face_indices:
        face = mesh.polygons[fi]
        verts_in_face = set(face.vertices)
        if all(sv in verts_in_face for sv in shared_verts):
            central_face_index = fi
            break

    if central_face_index is None:
        return False

    central_uvs = {}
    face = mesh.polygons[central_face_index]
    for loop_idx, vert_idx in zip(face.loop_indices, face.vertices):
        if vert_idx in shared_verts:
            central_uvs[vert_idx] = uv_layer.data[loop_idx].uv

    if len(central_uvs) != 3:
        return False

    for fi in face_indices:
        if fi == central_face_index:
            continue
        face = mesh.polygons[fi]
        adj_shared_uvs = {}
        for loop_idx, vert_idx in zip(face.loop_indices, face.vertices):
            if vert_idx in shared_verts:
                adj_shared_uvs[vert_idx] = uv_layer.data[loop_idx].uv
        if len(adj_shared_uvs) != 2:
            continue
        matches = 0
        for sv, uv in adj_shared_uvs.items():
            central_uv = central_uvs.get(sv)
            if central_uv is None:
                continue
            if (abs(uv.x - central_uv.x) <= 1e-5 and abs(uv.y - central_uv.y) <= 1e-5):
                matches += 1
        if matches == 2:
            return True
    return False

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

def get_face_uv_issues(obj, face_indices):
    """Check UVs for the given faces and return a list of UV-related issues."""
    issues = []
    mesh = obj.data
    if not mesh.uv_layers:
        issues.append("missing_uvs")
        return issues
    uv_layer = mesh.uv_layers.active
    if not uv_layer or len(uv_layer.data) == 0:
        issues.append("missing_uvs")
        return issues

    uv_data = uv_layer.data
    for fi in face_indices:
        face = mesh.polygons[fi]
        for loop_idx in face.loop_indices:
            if loop_idx >= len(uv_data):
                continue
            uv = uv_data[loop_idx].uv
            if uv.x < 0 or uv.x > 1 or uv.y < 0 or uv.y > 1:
                issues.append("invalid_uvs")
                break
        if "invalid_uvs" in issues:
            break

    if face_indices:
        all_uvs = []
        for fi in face_indices:
            face = mesh.polygons[fi]
            for loop_idx in face.loop_indices:
                if loop_idx >= len(uv_data):
                    continue
                all_uvs.append(uv_data[loop_idx].uv)
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

def get_faces_of_vertex_group(obj, vg_name):
    vg = obj.vertex_groups.get(vg_name)
    if not vg:
        return []
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
    face_indices = []
    for i, face in enumerate(obj.data.polygons):
        if all(v in vert_set for v in face.vertices):
            face_indices.append(i)
    return face_indices

def analyze_faces_for_quadblock(obj, face_indices, tolerance=0.001):
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

# Main validation function for a set of faces belonging to a potential block
def analyze_faces_for_block(obj, face_indices):
    """
    Analyze the given faces (belonging to a potential quadblock or triblock)
    and return a list of issues.
    Possible issues: 'quadblock', 'triblock', 'invalid_geometry',
                     'invalid_uvs', 'degenerated_uvs', 'invalid_triblock_uvs',
                     'multiple_materials', 'missing_uvs'
    """
    issues = []
    if not face_indices:
        issues.append("invalid_geometry")
        return issues

    # Check material consistency
    unique_materials = set()
    for fi in face_indices:
        face = obj.data.polygons[fi]
        mat_idx = face.material_index
        if 0 <= mat_idx < len(obj.material_slots):
            mat = obj.material_slots[mat_idx].material
            unique_materials.add(mat.name if mat else None)
        else:
            unique_materials.add(None)
        if len(unique_materials) > 1:
            issues.append("multiple_materials")
            break

    # Check geometry type
    is_quad = analyze_faces_for_quadblock(obj, face_indices)
    is_tri = False
    if is_quad:
        issues.append("quadblock")
    else:
        is_tri = analyze_faces_for_triblock(obj, face_indices)
        if is_tri:
            issues.append("triblock")
        else:
            issues.append("invalid_geometry")

    # Add general UV issues
    uv_issues = get_face_uv_issues(obj, face_indices)
    issues.extend(uv_issues)

    # Triblock-specific UV check
    if is_tri:
        if not are_faces_triblock_uvs_valid(obj, face_indices):
            issues.append("invalid_triblock_uvs")

    return issues