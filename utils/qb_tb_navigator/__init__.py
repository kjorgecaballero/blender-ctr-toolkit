"""
QB/TB Navigation Utilities
Export utility functions for use in operators
Now includes constant material utilities
Only keep actually used functions.
"""

from .qb_tb_navigation_utils import (
    QbTbBlockResult,
    is_quadblock_center,
    validate_quadblock_topology,
    is_triangle_face,
    is_quad_face,
    central_face_has_quad_edge,
    get_quadblock_vertices,
    get_quadblock_faces,
    find_adjacent_triangular_faces,
    is_valid_triblock,
    get_triblock_faces,
    get_triblock_vertices,
    find_qb_tb_with_groups,
    assign_groups_with_vertex_separation_quads,
    assign_groups_with_vertex_separation_tris,
    detect_quadblock_from_faces,
    detect_triblock_from_faces,
    detect_block_from_selection,
)

from .constant_material_utils import (
    get_faces_by_material_name,
    is_valid_navigation_point,
    get_all_navigation_points,
)


__all__ = [
    'QbTbBlockResult',
    'is_quadblock_center',
    'validate_quadblock_topology',
    'is_triangle_face',
    'is_quad_face',
    'central_face_has_quad_edge',
    'get_quadblock_vertices',
    'get_quadblock_faces',
    'find_adjacent_triangular_faces',
    'is_valid_triblock',
    'get_triblock_faces',
    'get_triblock_vertices',
    'find_qb_tb_with_groups',
    'assign_groups_with_vertex_separation_quads',
    'assign_groups_with_vertex_separation_tris',
    'detect_quadblock_from_faces',
    'detect_triblock_from_faces',
    'detect_block_from_selection',
    'get_faces_by_material_name',
    'is_valid_navigation_point',
    'get_all_navigation_points',
]