"""
Utilities module initialization
Exporting functions from all utility modules
"""

from .compat import (
    get_blender_version,
    should_use_wm_obj_export,
    get_export_parameters,
    apply_scale_to_objects,
    restore_scale_to_objects,
    execute_obj_export,
    get_export_operator_name,
    has_vertex_colors_support,
    ensure_objects_in_view_layer,
    cleanup_temporarily_linked_objects,
)

from .qb_tb_navigator import (
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
    get_faces_by_material_name,
    is_valid_navigation_point,
    get_all_navigation_points,
)

from .material_utils import (
    update_derived_materials,
    is_constant_id_unique,
    get_material_categories,
    is_base_name_in_use,
    rename_material_if_unique,
    update_constant_material_base_reference,
    rename_base_material_family,
)


__all__ = [
    # Compatibility functions
    'get_blender_version',
    'should_use_wm_obj_export',
    'get_export_parameters',
    'apply_scale_to_objects',
    'restore_scale_to_objects',
    'execute_obj_export',
    'get_export_operator_name',
    'has_vertex_colors_support',
    'ensure_objects_in_view_layer',
    'cleanup_temporarily_linked_objects',
    
    # Navigation utilities
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
    
    # Constant material utilities
    'get_faces_by_material_name',
    'is_valid_navigation_point',
    'get_all_navigation_points',
    
    # Material manager utils
    'update_derived_materials',
    'is_constant_id_unique',
    'get_material_categories',
    'is_base_name_in_use',
    'rename_material_if_unique',
    'update_constant_material_base_reference',
    'rename_base_material_family',
]