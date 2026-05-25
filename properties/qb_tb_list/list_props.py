"""
QB/TB List Properties
Property definitions for the block list system.
"""

import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty, StringProperty

# Update functions for VERTEX GROUPS mode 
def update_qb_vertex_groups(self, context):
    # If user unchecks QB and TB is already unchecked, activate TB
    if not self.list_filter_show_qb and not self.list_filter_show_tb:
        self.list_filter_show_tb = True

def update_tb_vertex_groups(self, context):
    # If user unchecks TB and QB is already unchecked, activate QB
    if not self.list_filter_show_tb and not self.list_filter_show_qb:
        self.list_filter_show_qb = True

# Update functions for CONSTANT MATERIALS mode
def update_qb_constant_materials(self, context):
    if not self.list_filter_cm_qb and not self.list_filter_cm_tb:
        self.list_filter_cm_tb = True

def update_tb_constant_materials(self, context):
    if not self.list_filter_cm_tb and not self.list_filter_cm_qb:
        self.list_filter_cm_qb = True

def register():
    # Display type selector
    bpy.types.Scene.list_display_type = EnumProperty(
        name="Display Type",
        items=[
            ('VERTEX_GROUPS', 'Vertex Groups', 'Show block vertex groups (QB/TB)'),
            ('CONSTANT_MATERIALS', 'Constant Mat', 'Show constant materials'),
        ],
        default='VERTEX_GROUPS'
    )
    
    # Vertex Groups filters
    bpy.types.Scene.list_filter_show_qb = BoolProperty(
        name="Show Quadblocks",
        default=True,
        update=update_qb_vertex_groups
    )
    
    bpy.types.Scene.list_filter_show_tb = BoolProperty(
        name="Show Triblocks",
        default=True,
        update=update_tb_vertex_groups
    )
    
    # Constant Materials filters
    bpy.types.Scene.list_filter_cm_qb = BoolProperty(
        name="Show Quadblocks",
        default=True,
        update=update_qb_constant_materials
    )
    
    bpy.types.Scene.list_filter_cm_tb = BoolProperty(
        name="Show Triblocks",
        default=True,
        update=update_tb_constant_materials
    )
    
    bpy.types.Scene.list_navigation_filter = EnumProperty(
        name="Navigation Filter",
        items=[
            ('ALL', 'All', 'Show all constant materials'),
            ('NAVIGATION_POINTS', 'Navigation Points', 'Show only materials marked as navigation points'),
            ('NON_NAVIGATION', 'Constant Materials', 'Show only materials NOT marked as navigation points'),
        ],
        default='ALL'
    )
    
    bpy.types.Scene.list_material_filter_vg = StringProperty(
        name="Material Filter (Vertex Groups)",
        default=""
    )
    
    bpy.types.Scene.list_material_filter_cm = StringProperty(
        name="Material Filter (Constant Materials)",
        default=""
    )
    
    bpy.types.Scene.list_issue_filter = EnumProperty(
        name="Issue Filter",
        items=[
            ('ALL', 'All', 'Show all blocks (valid and invalid)'),
            ('VALID', 'Valid', 'Show only valid blocks'),
            ('INVALID', 'Invalid', 'Show only blocks with any issue'),
            ('INVALID_GEOMETRY', 'Invalid Geometry', 'Show blocks with invalid geometry'),
            ('INVALID_UVS', 'Invalid UVs', 'Show blocks with UVs outside 0-1 range'),
            ('INVALID_TRIBLOCK_UVS', 'Invalid Triblock UVs', 'Show triblocks with incorrect UV arrangement'),
            ('DEGENERATED_UVS', 'Degenerated UVs', 'Show blocks with all UVs identical'),
            ('OUT_OF_RANGE', 'Out of Range', 'Show blocks with vertices outside the range box'),
            ('MULTIPLE_MATERIALS', 'Multiple Materials', 'Show blocks with more than one material'),
        ],
        default='ALL'
    )
    
    bpy.types.Scene.list_active_group = StringProperty(
        name="Active Group",
        default=""
    )
    
    bpy.types.Scene.list_show_group_section = BoolProperty(
        name="Show Group Section",
        default=False
    )
    
    bpy.types.Scene.list_show_items = BoolProperty(
        name="Show Block List",
        default=True
    )
    
    bpy.types.Scene.list_search_text = StringProperty(
        name="Search",
        default="",
        update=lambda self, context: setattr(self, 'list_scroll_position', 0)
    )
    
    bpy.types.Scene.list_sort_name_direction = EnumProperty(
        name="Name Sort Direction",
        items=[
            ('ASC', 'A-Z', 'Sort by name ascending'),
            ('DESC', 'Z-A', 'Sort by name descending'),
        ],
        default='ASC'
    )
    
    bpy.types.Scene.list_sort_type_direction = EnumProperty(
        name="Type Sort Direction",
        items=[
            ('ASC', 'QB/TB', 'Sort by block type (QB then TB)'),
            ('DESC', 'TB/QB', 'Sort by block type (TB then QB)'),
        ],
        default='ASC'
    )
    
    bpy.types.Scene.list_list_index = IntProperty(
        name="List Index",
        default=0
    )
    
    bpy.types.Scene.list_scroll_position = IntProperty(
        name="Scroll Position",
        default=0,
        min=0
    )
    
    bpy.types.Scene.list_vertical_scroll = IntProperty(
        name="Vertical Stack",
        default=0,
        min=0
    )

def unregister():
    del bpy.types.Scene.list_display_type
    del bpy.types.Scene.list_filter_show_qb
    del bpy.types.Scene.list_filter_show_tb
    del bpy.types.Scene.list_filter_cm_qb
    del bpy.types.Scene.list_filter_cm_tb
    del bpy.types.Scene.list_navigation_filter
    del bpy.types.Scene.list_material_filter_vg
    del bpy.types.Scene.list_material_filter_cm
    del bpy.types.Scene.list_issue_filter
    del bpy.types.Scene.list_active_group
    del bpy.types.Scene.list_show_group_section
    del bpy.types.Scene.list_show_items
    del bpy.types.Scene.list_search_text
    del bpy.types.Scene.list_sort_name_direction
    del bpy.types.Scene.list_sort_type_direction
    del bpy.types.Scene.list_list_index
    del bpy.types.Scene.list_scroll_position
    del bpy.types.Scene.list_vertical_scroll