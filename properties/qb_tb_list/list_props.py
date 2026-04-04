"""
QB/TB List Properties
Property definitions for the block list system.

Provides filtering and sorting properties for vertex groups (QB/TB blocks)
and constant materials, including navigation point filtering, material name
filters per display mode, issue filtering for vertex groups, and UI state
properties.
"""

import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty, StringProperty

def update_filter_vertex_groups(self, context):
    """Ensure at least one of the QB/TB filters is active"""
    if not self.list_filter_show_qb and not self.list_filter_show_tb:
        # If both are disabled, activate QB by default
        self.list_filter_show_qb = True

def update_filter_constant_materials(self, context):
    """Ensure at least one of the QB/TB filters is active"""
    if not self.list_filter_cm_qb and not self.list_filter_cm_tb:
        # If both are disabled, activate QB by default
        self.list_filter_cm_qb = True

def register():
    # Display type selector
    bpy.types.Scene.list_display_type = EnumProperty(
        name="Display Type",
        description="Type of elements to display in the block list",
        items=[
            ('VERTEX_GROUPS', 'Vertex Groups', 'Show block vertex groups (QB/TB)'),
            ('CONSTANT_MATERIALS', 'Constant Materials', 'Show constant materials'),
        ],
        default='VERTEX_GROUPS'
    )
    
    # Filters for vertex groups display
    bpy.types.Scene.list_filter_show_qb = BoolProperty(
        name="Show Quadblocks",
        description="Show quadblocks in the vertex groups list",
        default=True,
        update=update_filter_vertex_groups
    )
    
    bpy.types.Scene.list_filter_show_tb = BoolProperty(
        name="Show Triblocks",
        description="Show triblocks in the vertex groups list",
        default=True,
        update=update_filter_vertex_groups
    )
    
    # Filters for constant materials display
    bpy.types.Scene.list_filter_cm_qb = BoolProperty(
        name="Show Quadblocks",
        description="Show quadblock constant materials",
        default=True,
        update=update_filter_constant_materials
    )
    
    bpy.types.Scene.list_filter_cm_tb = BoolProperty(
        name="Show Triblocks",
        description="Show triblock constant materials",
        default=True,
        update=update_filter_constant_materials
    )
    
    # Navigation point filter for constant materials
    bpy.types.Scene.list_navigation_filter = EnumProperty(
        name="Navigation Filter",
        description="Filter constant materials by navigation point status",
        items=[
            ('ALL', 'All', 'Show all constant materials'),
            ('NAVIGATION_POINTS', 'Navigation Points', 'Show only materials marked as navigation points'),
            ('NON_NAVIGATION', 'Constant Materials', 'Show only materials NOT marked as navigation points'),
        ],
        default='ALL'
    )
    
    # SEPARATE MATERIAL FILTERS FOR EACH DISPLAY TYPE
    # Material filter for Vertex Groups mode
    bpy.types.Scene.list_material_filter_vg = StringProperty(
        name="Material Filter (Vertex Groups)",
        description="Filter vertex groups by material name",
        default=""
    )
    
    # Material filter for Constant Materials mode
    bpy.types.Scene.list_material_filter_cm = StringProperty(
        name="Material Filter (Constant Materials)",
        description="Filter constant materials by material name",
        default=""
    )
    
    # Issue filter for Vertex Groups mode
    bpy.types.Scene.list_issue_filter = EnumProperty(
        name="Issue Filter",
        description="Filter vertex groups by validation issues",
        items=[
            ('ALL', 'All', 'Show all vertex groups'),
            ('VALID', 'Valid Blocks', 'Show only blocks with no issues'),
            ('INVALID_GEOMETRY', 'Invalid Geometry', 'Show blocks with invalid geometry'),
            ('INVALID_UVS', 'Invalid UVs', 'Show blocks with UVs outside 0-1 range'),
            ('INVALID_TRIBLOCK_UVS', 'Invalid Triblock UVs', 'Show triblocks with incorrect UV arrangement'),
            ('DEGENERATED_UVS', 'Degenerated UVs', 'Show blocks with all UVs identical'),
            ('NO_ISSUES', 'No Issues', 'Show blocks that are valid (alias for Valid Blocks)'),
        ],
        default='ALL'
    )
    
    # Group filter property
    bpy.types.Scene.list_active_group = StringProperty(
        name="Active Group",
        description="Active constant material group for filtering",
        default=""
    )
    
    # Group management section visibility
    bpy.types.Scene.list_show_group_section = BoolProperty(
        name="Show Group Section",
        description="Show/hide the group management section",
        default=False
    )
    
    # Search and sort properties
    bpy.types.Scene.list_search_text = StringProperty(
        name="Search",
        description="Search items by name, type, or ID",
        default="",
        update=lambda self, context: setattr(self, 'list_scroll_position', 0)
    )
    
    # Independent sort properties for name and type
    bpy.types.Scene.list_sort_name_direction = EnumProperty(
        name="Name Sort Direction",
        description="Direction for sorting by name",
        items=[
            ('ASC', 'A-Z', 'Sort by name ascending'),
            ('DESC', 'Z-A', 'Sort by name descending'),
        ],
        default='ASC'
    )
    
    bpy.types.Scene.list_sort_type_direction = EnumProperty(
        name="Type Sort Direction",
        description="Direction for sorting by block type",
        items=[
            ('ASC', 'QB/TB', 'Sort by block type (QB then TB)'),
            ('DESC', 'TB/QB', 'Sort by block type (TB then QB)'),
        ],
        default='ASC'
    )
    
    # List index for selection
    bpy.types.Scene.list_list_index = IntProperty(
        name="List Index",
        default=0
    )
    
    # Horizontal scroll position for the list
    bpy.types.Scene.list_scroll_position = IntProperty(
        name="Scroll Position",
        description="Horizontal scroll position in the list",
        default=0,
        min=0
    )
    
    # Vertical scroll properties
    bpy.types.Scene.list_vertical_scroll = IntProperty(
        name="Vertical Stack",
        description="Vertical scroll position in the list",
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
    del bpy.types.Scene.list_search_text
    del bpy.types.Scene.list_sort_name_direction
    del bpy.types.Scene.list_sort_type_direction
    del bpy.types.Scene.list_list_index
    del bpy.types.Scene.list_scroll_position
    del bpy.types.Scene.list_vertical_scroll