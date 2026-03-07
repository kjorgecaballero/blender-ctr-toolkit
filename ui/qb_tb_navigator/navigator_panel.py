"""
Block Navigator Panel
Main UI panel for the QB/TB Block Navigator tools
Simple UI with all functionality in the main "Navigate" operator
"""

import bpy
from bpy.types import Panel


class NAVIGATOR_PT_BlockToolsPanel(Panel):
    bl_label = "Block Navigator"
    bl_idname = "NAVIGATOR_PT_block_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'CTR'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        obj = context.edit_object
        
        is_edit_mode = (context.mode == 'EDIT_MESH')
        
        box = layout.box()
        box.label(text="Selection", icon='RESTRICT_SELECT_OFF')
        
        # First row: Navigate, Clear
        row = box.row(align=True)
        row.operator("navigator.find_blocks", 
                     text="Navigate", 
                     icon='ZOOM_ALL')
        row.operator("navigator.clear_block_cache", text="Clear", icon='TRASH')
        
        # Second row: Quadblock, Triblock
        row = box.row(align=True)
        row.operator("navigator.select_quadblocks_only", text="Quadblock", icon='VERTEXSEL')
        row.operator("navigator.select_triblocks_only", text="Triblock", icon='FACESEL')
        
        # Third row: Duplicate, Invalid
        row = box.row(align=True)
        row.operator("navigator.duplicate_all_blocks_by_group", 
                     text="Duplicate", 
                     icon='DUPLICATE')
        row.operator("navigator.select_invalid_faces", text="Invalid", icon='ERROR')
        
        # Collapsible group selection panel
        if obj and (("quad_group_members" in obj and obj["quad_group_members"]) or 
                    ("tri_group_members" in obj and obj["tri_group_members"])):
            group_box = box.box()
            row = group_box.row(align=True)
            
            # Toggle for collapsing/expanding
            row.prop(scene, "navigator_show_group_selection", 
                     icon="TRIA_DOWN" if scene.navigator_show_group_selection else "TRIA_RIGHT",
                     icon_only=True, 
                     emboss=False)
            row.label(text="Group Selection", icon='GROUP')
            
            # Expanded content
            if scene.navigator_show_group_selection:
                inner_box = group_box.box()
                
                if "quad_group_members" in obj:
                    quad_group_members = obj["quad_group_members"]
                    inner_box.label(text="Select Quadblocks by Group:", icon='GROUP_VERTEX')
                    row = inner_box.row(align=True)
                    
                    sorted_groups = []
                    for group_str in quad_group_members.keys():
                        try:
                            group_num = int(group_str)
                            sorted_groups.append(group_num)
                        except ValueError:
                            continue
                    
                    sorted_groups.sort()
                    for group_num in sorted_groups:
                        if group_num <= 12:
                            op = row.operator("navigator.select_quadblock_group", text=str(group_num))
                            op.group_number = group_num
                
                if "tri_group_members" in obj:
                    tri_group_members = obj["tri_group_members"]
                    inner_box.label(text="Select Triblocks by Group:", icon='MENU_PANEL')
                    row = inner_box.row(align=True)
                    
                    sorted_groups = []
                    for group_str in tri_group_members.keys():
                        try:
                            group_num = int(group_str)
                            sorted_groups.append(group_num)
                        except ValueError:
                            continue
                    
                    sorted_groups.sort()
                    for group_num in sorted_groups:
                        if group_num <= 12:
                            op = row.operator("navigator.select_triblock_group", text=str(group_num))
                            op.group_number = group_num
        
        if not is_edit_mode:
            layout.label(text="Enter Edit Mode to use tools", icon='ERROR')