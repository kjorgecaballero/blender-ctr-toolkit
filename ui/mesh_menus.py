"""
Extend native Blender menus with CTR Toolkit operations
"""

import bpy

def menu_duplicate_block(self, context):
    """Add 'Duplicate Block with Constant' to Mesh menu"""
    if context.mode == 'EDIT_MESH' and context.edit_object:
        obj = context.edit_object
        # Only show if block data exists
        if "face_to_quadblock" in obj or "face_to_triblock" in obj:
            self.layout.operator(
                "list.duplicate_selection",
                text="Duplicate Block with Constant"
            )

def menu_toggle_block_seams(self, context):
    """Add 'Toggle Block Seams' to UV menu"""
    if context.mode == 'EDIT_MESH' and context.edit_object:
        obj = context.edit_object
        # Only show if block face maps exist
        if "quadblock_faces_map" in obj or "triblock_faces_map" in obj:
            self.layout.operator(
                "list.toggle_block_seams",
                text="Toggle Block Seams"
            )

def register():
    bpy.types.VIEW3D_MT_edit_mesh.append(menu_duplicate_block)
    bpy.types.VIEW3D_MT_uv_map.append(menu_toggle_block_seams)

def unregister():
    bpy.types.VIEW3D_MT_edit_mesh.remove(menu_duplicate_block)
    bpy.types.VIEW3D_MT_uv_map.remove(menu_toggle_block_seams)