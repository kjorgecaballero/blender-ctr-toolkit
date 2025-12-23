import bpy
from bpy.types import Panel

class QB_TB_PT_ToolsPanel(Panel):
    """Panel for QB/TB Validation Tools."""
    bl_label = "QB/TB Validation"
    bl_idname = "QB_TB_PT_ValidationPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CTR"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        # Find section
        row = layout.row()
        col = row.column()
        col.label(text="Find:", icon='VIEWZOOM')
        col = row.column()
        col.prop(scene, "find_option", text="")
        col = row.column()
        
        # Dynamic icon for FIND button - these are placeholders for custom icons
        find_icon = 'MESH_CONE' if scene.find_option == 'TRIBLOCK' else 'MESH_CUBE'
        col.operator("qb_tb.object_qb_tb_suffix", text="", icon=find_icon)
        
        col = row.column()
        col.operator("qb_tb.validate_all_objects", text="", icon='ERROR')
        
        # Select section
        row = layout.row()
        col = row.column()
        col.label(text="Select:", icon='RESTRICT_SELECT_OFF')
        col = row.column()
        col.prop(scene, "select_option", text="")
        col = row.column()
        
        # Dynamic icon for SELECT button - these are placeholders for custom icons
        select_icon = self.get_select_icon(scene.select_option)
        col.operator("qb_tb.filter_select_objects", text="", icon=select_icon)
        
        col = row.column()
        col.operator("qb_tb.clean_object_suffixes", text="", icon='FILE_REFRESH')
    
    def get_select_icon(self, select_option):
        """Returns appropriate icon for each select option - placeholder icons"""
        icon_mapping = {
            'ALL_INVALID': 'ERROR',
            'INVALID_GEOMETRY': 'MESH_DATA',
            'INVALID_UVS': 'UV',
            'DEGENERATED_UVS': 'GROUP_UVS',
            'TRIBLOCKS': 'MESH_CONE',
            'QUADBLOCKS': 'MESH_CUBE',
            'NON_MESH': 'OUTLINER_OB_EMPTY',
            'NGONS': 'MESH_CYLINDER'
        }
        
        return icon_mapping.get(select_option, 'SELECT_SET')

def register():
    bpy.utils.register_class(QB_TB_PT_ToolsPanel)

def unregister():
    bpy.utils.unregister_class(QB_TB_PT_ToolsPanel)