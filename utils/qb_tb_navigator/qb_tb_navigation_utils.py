"""
QB/TB Navigation Utilities
Core algorithms for quadblock and triblock detection and analysis
Now with optional group calculation for performance optimization
Added functions for detecting block centers from complete face selection
"""

import bpy
import bmesh
from mathutils import Vector
from collections import defaultdict, deque


class QbTbBlockResult:
    """Container for quadblock and triblock detection results"""
    def __init__(self):
        self.quadblock_centers = []
        self.triblock_centers = []
        self.used_faces = set()
        self.visited_verts = set()
        self.visited_faces = set()
        self.quadblock_groups = {}
        self.triblock_groups = {}
        self.quad_group_members = defaultdict(list)
        self.tri_group_members = defaultdict(list)

        # Fast lookup structures
        self.face_to_quadblock = {}
        self.face_to_triblock = {}
        self.quadblock_faces_map = defaultdict(list)
        self.triblock_faces_map = defaultdict(list)



# CORE VALIDATION FUNCTIONS FOR QUADBLOCKS AND TRIBLOCKS


def is_quadblock_center(center_vert):
    """Validate if a vertex is a valid quadblock center"""
    if len(center_vert.link_faces) != 4:
        return False

    for face in center_vert.link_faces:
        if len(face.verts) != 4:
            return False

    all_vertices = set()
    for face in center_vert.link_faces:
        for vert in face.verts:
            all_vertices.add(vert)

    all_vertices.discard(center_vert)

    if len(all_vertices) != 8:
        return False

    direct_connected = set()
    for edge in center_vert.link_edges:
        other_vert = edge.other_vert(center_vert)
        direct_connected.add(other_vert)

    if len(direct_connected) != 4:
        return False

    for vert in direct_connected:
        face_count = 0
        for face in center_vert.link_faces:
            if vert in face.verts:
                face_count += 1
        if face_count != 2:
            return False

    return True


def validate_quadblock_topology(center_vert):
    """Complete validation of quadblock topology"""
    if not is_quadblock_center(center_vert):
        return False, "Not a quadblock center"

    if len(center_vert.link_edges) != 4:
        return False, f"Expected 4 edges, found {len(center_vert.link_edges)}"

    intermediate_vertices = []
    for edge in center_vert.link_edges:
        intermediate = edge.other_vert(center_vert)
        intermediate_vertices.append(intermediate)

        if len(intermediate.link_edges) < 3:
            return False, f"Intermediate vertex has only {len(intermediate.link_edges)} edges"

    face_vertices = set()
    for face in center_vert.link_faces:
        if len(face.verts) != 4:
            return False, "Face is not a quad"

        for vert in face.verts:
            face_vertices.add(vert)

    face_vertices.discard(center_vert)

    if len(face_vertices) != 8:
        return False, f"Expected 8 unique vertices, found {len(face_vertices)}"

    return True, "Valid quadblock topology"


def is_triangle_face(face):
    """Check if face has exactly 3 vertices"""
    return len(face.verts) == 3


def is_quad_face(face):
    """Check if face has exactly 4 vertices"""
    return len(face.verts) == 4


def central_face_has_quad_edge(central_face):
    """Check if triblock center face borders a quad face"""
    for edge in central_face.edges:
        quad_count = 0
        for face in edge.link_faces:
            if face != central_face and is_quad_face(face):
                quad_count += 1

        if quad_count > 0:
            return True

    return False


def find_adjacent_triangular_faces(central_face):
    """Find 3 triangular faces adjacent to central face"""
    if not is_triangle_face(central_face):
        return []

    adjacent_faces = []

    for edge in central_face.edges:
        for face in edge.link_faces:
            if (face != central_face and
                is_triangle_face(face) and
                face not in adjacent_faces):
                adjacent_faces.append(face)

    return adjacent_faces


def is_valid_triblock(central_face, adjacent_faces):
    """Validate if faces form a valid triblock with quad edge restriction"""
    if len(adjacent_faces) != 3:
        return False

    for face in adjacent_faces:
        if not is_triangle_face(face):
            return False

    for adj_face in adjacent_faces:
        shared_edges = 0
        for edge in adj_face.edges:
            if edge in central_face.edges:
                shared_edges += 1
        if shared_edges != 1:
            return False

    if central_face_has_quad_edge(central_face):
        return False

    return True



# FUNCTIONS FOR RETRIEVING QUADBLOCKS AND TRIBLOCKS


def get_quadblock_vertices(center_vert):
    """Get ALL vertices of a quadblock (center + 8 adjacent)"""
    vertices = set([center_vert])
    # Note: the 8 adjacent vertices come from the 4 faces
    for face in center_vert.link_faces:
        for vert in face.verts:
            if vert != center_vert:
                vertices.add(vert)
    return vertices


def get_quadblock_faces(center_vert):
    """Get the 4 unique faces forming this quadblock"""
    if not is_quadblock_center(center_vert):
        return set()
    return set(center_vert.link_faces)


def get_triblock_faces(central_face):
    """Get the 4 faces forming this triblock"""
    adjacent_faces = find_adjacent_triangular_faces(central_face)
    return set([central_face] + adjacent_faces)


def get_triblock_vertices(center_face):
    """Get ALL vertices of a triblock (6 vertices from 4 triangles)"""
    vertices = set()
    adjacent_faces = find_adjacent_triangular_faces(center_face)
    if not is_valid_triblock(center_face, adjacent_faces):
        return vertices

    for vert in center_face.verts:
        vertices.add(vert)

    for face in adjacent_faces:
        for vert in face.verts:
            vertices.add(vert)

    return vertices



# DETECT QUADBLOCK OR TRIBLOCK FROM COMPLETE SELECTION


def detect_quadblock_from_faces(selected_faces):
    """
    Detect if 4 selected faces form a complete quadblock
    Returns the center vertex if valid, None otherwise
    """
    if len(selected_faces) != 4:
        return None

    for face in selected_faces:
        if not is_quad_face(face):
            return None

    common_vertices = None
    for face in selected_faces:
        face_vertices = set(face.verts)
        if common_vertices is None:
            common_vertices = face_vertices
        else:
            common_vertices = common_vertices.intersection(face_vertices)

    if len(common_vertices) != 1:
        return None

    center = list(common_vertices)[0]

    if not is_quadblock_center(center):
        return None

    center_faces = set(center.link_faces)
    if center_faces != set(selected_faces):
        return None

    return center


def detect_triblock_from_faces(selected_faces):
    """
    Detect if 4 selected faces form a complete triblock
    Returns the center face if valid, None otherwise
    """
    if len(selected_faces) != 4:
        return None

    for face in selected_faces:
        if not is_triangle_face(face):
            return None

    for candidate_face in selected_faces:
        adjacent_faces = find_adjacent_triangular_faces(candidate_face)

        if set(adjacent_faces).issubset(selected_faces):
            if is_valid_triblock(candidate_face, adjacent_faces):
                triblock_faces = set([candidate_face] + adjacent_faces)
                if triblock_faces == set(selected_faces):
                    return candidate_face

    return None


def detect_block_from_selection(selected_faces):
    """
    Detect if selected faces form a complete quadblock or triblock
    Returns tuple: (center_element, block_type) or (None, None)
    """
    if not selected_faces or len(selected_faces) != 4:
        return None, None

    quad_center = detect_quadblock_from_faces(selected_faces)
    if quad_center:
        return quad_center, 'QUADBLOCK'

    tri_center = detect_triblock_from_faces(selected_faces)
    if tri_center:
        return tri_center, 'TRIBLOCK'

    return None, None



# GRAPH AND GROUPING FUNCTIONS FOR QUADBLOCKS AND TRIBLOCKS


def build_adjacency_graph_quads(quadblock_centers):
    """Build adjacency graph where quadblocks are connected if they share at least one vertex"""
    adjacency = defaultdict(set)

    quadblock_data = []
    for center in quadblock_centers:
        vertices = get_quadblock_vertices(center)
        quadblock_data.append((center, vertices))

    n = len(quadblock_data)
    for i in range(n):
        center_i, vertices_i = quadblock_data[i]
        for j in range(i + 1, n):
            center_j, vertices_j = quadblock_data[j]

            if vertices_i.intersection(vertices_j):
                adjacency[center_i].add(center_j)
                adjacency[center_j].add(center_i)

    return adjacency


def build_adjacency_graph_tris(triblock_centers):
    """Build adjacency graph where triblocks are connected if they share at least one vertex"""
    adjacency = defaultdict(set)

    triblock_data = []
    for center in triblock_centers:
        vertices = get_triblock_vertices(center)
        triblock_data.append((center, vertices))

    n = len(triblock_data)
    for i in range(n):
        center_i, vertices_i = triblock_data[i]
        for j in range(i + 1, n):
            center_j, vertices_j = triblock_data[j]

            if vertices_i.intersection(vertices_j):
                adjacency[center_i].add(center_j)
                adjacency[center_j].add(center_i)

    return adjacency


def greedy_coloring_with_adjacency(centers, adjacency, max_colors=8):
    """Greedy coloring algorithm optimized for 3D grid structure"""
    sorted_centers = sorted(centers,
                           key=lambda c: len(adjacency[c]),
                           reverse=True)

    colors = {}
    available_colors = set(range(1, max_colors + 1))

    for center in sorted_centers:
        used_colors = set()
        for neighbor in adjacency[center]:
            if neighbor in colors:
                used_colors.add(colors[neighbor])

        for color in available_colors:
            if color not in used_colors:
                colors[center] = color
                break
        else:
            colors[center] = max(available_colors) + 1

    return colors


def assign_groups_with_vertex_separation_quads(quadblock_centers):
    """Assign groups ensuring no quadblocks in same group share any vertices"""
    adjacency = build_adjacency_graph_quads(quadblock_centers)
    colors = greedy_coloring_with_adjacency(quadblock_centers, adjacency, max_colors=8)

    result_groups = {}
    group_members = defaultdict(list)

    for center, color in colors.items():
        result_groups[center] = color
        group_members[color].append(center)

    return result_groups, group_members


def assign_groups_with_vertex_separation_tris(triblock_centers):
    """Assign groups ensuring no triblocks in same group share any vertices"""
    adjacency = build_adjacency_graph_tris(triblock_centers)
    colors = greedy_coloring_with_adjacency(triblock_centers, adjacency, max_colors=8)

    result_groups = {}
    group_members = defaultdict(list)

    for center, color in colors.items():
        result_groups[center] = color
        group_members[color].append(center)

    return result_groups, group_members



# BFS DETECTION FOR QUADBLOCKS AND TRIBLOCKS


def find_adjacent_quadblock_centers(center_vert, used_faces):
    """Find all adjacent quadblock centers with isolation handling"""
    if not is_quadblock_center(center_vert):
        return []

    adjacent_centers = []

    for edge in center_vert.link_edges:
        intermediate = edge.other_vert(center_vert)

        for next_edge in intermediate.link_edges:
            if next_edge == edge:
                continue

            candidate = next_edge.other_vert(intermediate)

            if (is_quadblock_center(candidate) and
                candidate not in adjacent_centers and
                candidate != center_vert):

                candidate_faces = set(candidate.link_faces)
                if not candidate_faces.intersection(used_faces):
                    adjacent_centers.append(candidate)

    return adjacent_centers


def get_all_vertices_from_edges(face):
    """Get all vertices from face edges"""
    vertices = set()
    for edge in face.edges:
        for vert in edge.verts:
            vertices.add(vert)
    return vertices


def find_triangular_faces_through_vertices(central_face, used_faces):
    """Find triangular faces connected through vertices for new triblocks"""
    potential_centers = []

    all_vertices = get_all_vertices_from_edges(central_face)

    for vertex in all_vertices:
        for face in vertex.link_faces:
            if (is_triangle_face(face) and
                face != central_face and
                face not in used_faces):

                adjacent_faces = find_adjacent_triangular_faces(face)
                if is_valid_triblock(face, adjacent_faces):
                    triblock_faces = set([face] + adjacent_faces)
                    if not triblock_faces.intersection(used_faces):
                        potential_centers.append(face)

    return potential_centers


def find_triblocks_from_quadblock_edges(quad_center, used_faces, bm):
    """Find triblocks connected to quadblock edge vertices"""
    potential_triblocks = []

    if not is_quadblock_center(quad_center):
        return potential_triblocks

    for edge in quad_center.link_edges:
        edge_vertex = edge.other_vert(quad_center)

        for face in edge_vertex.link_faces:
            if not is_triangle_face(face) or face in used_faces:
                continue

            adjacent_faces = find_adjacent_triangular_faces(face)
            if is_valid_triblock(face, adjacent_faces):
                triblock_faces = set([face] + adjacent_faces)

                if not triblock_faces.intersection(used_faces):
                    potential_triblocks.append(face)

    return potential_triblocks


def find_quadblocks_from_triblock_vertices(tri_center, used_faces, bm):
    """Find quadblocks connected to triblock vertices"""
    potential_quadblocks = []

    for vertex in tri_center.verts:
        for edge in vertex.link_edges:
            other_vertex = edge.other_vert(vertex)

            if is_quadblock_center(other_vertex):
                quad_faces = get_quadblock_faces(other_vertex)

                if not quad_faces.intersection(used_faces):
                    potential_quadblocks.append(other_vertex)

    return potential_quadblocks


def find_qb_tb_with_groups(start_element, bm, used_faces_initial=None, skip_grouping=False):
    """
    Find both quadblocks and triblocks and intelligently group them
    If skip_grouping=True, group calculation is skipped (for multi-navigation point optimization)
    """
    result = QbTbBlockResult()
    used_faces = used_faces_initial.copy() if used_faces_initial else set()

    quad_queue = deque()
    tri_queue = deque()

    # Initialize with start element
    if isinstance(start_element, bmesh.types.BMVert) and is_quadblock_center(start_element):
        quad_queue.append(start_element)
        result.visited_verts.add(start_element)
        initial_faces = get_quadblock_faces(start_element)
        used_faces.update(initial_faces)
        result.used_faces.update(initial_faces)
        result.quadblock_centers.append(start_element)

        for face in initial_faces:
            result.face_to_quadblock[face.index] = start_element.index
            result.quadblock_faces_map[start_element.index].append(face.index)

    elif isinstance(start_element, bmesh.types.BMFace) and is_triangle_face(start_element):
        adjacent_faces = find_adjacent_triangular_faces(start_element)
        if is_valid_triblock(start_element, adjacent_faces):
            tri_queue.append(start_element)
            result.visited_faces.add(start_element)
            initial_faces = get_triblock_faces(start_element)
            used_faces.update(initial_faces)
            result.used_faces.update(initial_faces)
            result.triblock_centers.append(start_element)

            for face in initial_faces:
                result.face_to_triblock[face.index] = start_element.index
                result.triblock_faces_map[start_element.index].append(face.index)
    else:
        return result

    # BFS process to find all connected blocks
    while quad_queue or tri_queue:
        while quad_queue:
            current_quad = quad_queue.popleft()

            adjacent_quads = find_adjacent_quadblock_centers(current_quad, used_faces)
            for next_quad in adjacent_quads:
                if next_quad not in result.visited_verts:
                    new_faces = get_quadblock_faces(next_quad)
                    if not new_faces.intersection(used_faces):
                        used_faces.update(new_faces)
                        result.used_faces.update(new_faces)
                        result.visited_verts.add(next_quad)
                        result.quadblock_centers.append(next_quad)

                        for face in new_faces:
                            result.face_to_quadblock[face.index] = next_quad.index
                            result.quadblock_faces_map[next_quad.index].append(face.index)

                        quad_queue.append(next_quad)

            adjacent_tris = find_triblocks_from_quadblock_edges(current_quad, used_faces, bm)
            for tri_center in adjacent_tris:
                if tri_center not in result.visited_faces:
                    adjacent_faces = find_adjacent_triangular_faces(tri_center)
                    if is_valid_triblock(tri_center, adjacent_faces):
                        tri_faces = set([tri_center] + adjacent_faces)
                        if not tri_faces.intersection(used_faces):
                            used_faces.update(tri_faces)
                            result.used_faces.update(tri_faces)
                            result.visited_faces.add(tri_center)
                            result.triblock_centers.append(tri_center)

                            for face in tri_faces:
                                result.face_to_triblock[face.index] = tri_center.index
                                result.triblock_faces_map[tri_center.index].append(face.index)

                            tri_queue.append(tri_center)

        while tri_queue:
            current_tri = tri_queue.popleft()

            connected_tris = find_triangular_faces_through_vertices(current_tri, used_faces)
            for next_tri in connected_tris:
                if next_tri not in result.visited_faces:
                    adjacent_faces = find_adjacent_triangular_faces(next_tri)
                    if is_valid_triblock(next_tri, adjacent_faces):
                        tri_faces = set([next_tri] + adjacent_faces)
                        if not tri_faces.intersection(used_faces):
                            used_faces.update(tri_faces)
                            result.used_faces.update(tri_faces)
                            result.visited_faces.add(next_tri)
                            result.triblock_centers.append(next_tri)

                            for face in tri_faces:
                                result.face_to_triblock[face.index] = next_tri.index
                                result.triblock_faces_map[next_tri.index].append(face.index)

                            tri_queue.append(next_tri)

            connected_quads = find_quadblocks_from_triblock_vertices(current_tri, used_faces, bm)
            for quad_center in connected_quads:
                if quad_center not in result.visited_verts:
                    new_faces = get_quadblock_faces(quad_center)
                    if not new_faces.intersection(used_faces):
                        used_faces.update(new_faces)
                        result.used_faces.update(new_faces)
                        result.visited_verts.add(quad_center)
                        result.quadblock_centers.append(quad_center)

                        for face in new_faces:
                            result.face_to_quadblock[face.index] = quad_center.index
                            result.quadblock_faces_map[quad_center.index].append(face.index)

                        quad_queue.append(quad_center)

    # Apply grouping algorithm only if not skipped
    if not skip_grouping:
        if result.quadblock_centers:
            result.quadblock_groups, result.quad_group_members = assign_groups_with_vertex_separation_quads(result.quadblock_centers)

        if result.triblock_centers:
            result.triblock_groups, result.tri_group_members = assign_groups_with_vertex_separation_tris(result.triblock_centers)

    return result