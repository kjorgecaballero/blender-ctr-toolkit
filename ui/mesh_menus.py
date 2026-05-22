"""
Extend native Blender menus with CTR Toolkit operations
"""

import bpy
from ..icons import get_icon

def _icon(name, fallback):
    ico = get_icon(name)
    return {'icon_value': ico} if ico else {'icon': fallback}

def menu_duplicate_block(self, context):
    if context.mode == 'EDIT_MESH' and context.edit_object:
        obj = context.edit_object
        if "face_to_quadblock" in obj or "face_to_triblock" in obj:
            self.layout.operator(
                "list.duplicate_selection",
                text="Duplicate Constant",
                **_icon("duplicate_constant_icon", 'DUPLICATE')
            )

def menu_toggle_block_seams(self, context):
    if context.mode == 'EDIT_MESH' and context.edit_object:
        obj = context.edit_object
        if "quadblock_faces_map" in obj or "triblock_faces_map" in obj:
            self.layout.operator(
                "list.toggle_block_seams",
                text="Toggle QB/TB Seams",
                **_icon("seams_icon", 'UV_SYNC_SELECT')
            )

def register():
    bpy.types.VIEW3D_MT_edit_mesh.append(menu_duplicate_block)
    bpy.types.VIEW3D_MT_edit_mesh_edges.append(menu_toggle_block_seams)
    bpy.types.VIEW3D_MT_uv_map.append(menu_toggle_block_seams)

def unregister():
    bpy.types.VIEW3D_MT_uv_map.remove(menu_toggle_block_seams)
    bpy.types.VIEW3D_MT_edit_mesh_edges.remove(menu_toggle_block_seams)
    bpy.types.VIEW3D_MT_edit_mesh.remove(menu_duplicate_block)