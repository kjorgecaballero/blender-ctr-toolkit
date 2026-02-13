import bpy
from bpy.types import Panel
from ..help_utils import draw_help_buttons


class QB_TB_PT_ToolsPanel(Panel):
    bl_label = "QB/TB Validation"
    bl_idname = "QB_TB_PT_ValidationPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CTR"

    def get_find_icon(self, find_option):
        icon_mapping = {
            'QUADBLOCK': 'MESH_CUBE',
            'TRIBLOCK': 'MESH_CONE',
            'INVALID_GEOMETRY': 'MESH_DATA',
            'INVALID_UVS': 'UV',
            'INVALID_TRIBLOCK_UVS': 'MESH_CONE',
            'DEGENERATED_UVS': 'GROUP_UVS',
            'NGONS': 'MESH_CYLINDER',
            'NON_MESH': 'OUTLINER_OB_EMPTY',
            'OUT_OF_RANGE': 'CUBE',  # ¡CORREGIDO: Coma añadida!
            'ALL_INVALID': 'ERROR'
        }
        return icon_mapping.get(find_option, 'VIEWZOOM')
    
    def get_select_icon(self, select_option):
        icon_mapping = {
            'QUADBLOCKS': 'MESH_CUBE',
            'TRIBLOCKS': 'MESH_CONE',
            'INVALID_GEOMETRY': 'MESH_DATA',
            'INVALID_UVS': 'UV',
            'INVALID_TRIBLOCK_UVS': 'MESH_CONE',
            'DEGENERATED_UVS': 'GROUP_UVS',
            'NGONS': 'MESH_CYLINDER',
            'NON_MESH': 'OUTLINER_OB_EMPTY',
            'OUT_OF_RANGE': 'CUBE',
            'ALL_INVALID': 'ERROR'
        }
        
        return icon_mapping.get(select_option, 'SELECT_SET')

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        draw_help_buttons(layout)
        
        row = layout.row()
        col = row.column()
        col.label(text="Find:", icon='VIEWZOOM')
        col = row.column()
        col.prop(scene, "find_option", text="")
        col = row.column()
        
        find_icon = self.get_find_icon(scene.find_option)
        col.operator("qb_tb.object_qb_tb_suffix", text="", icon=find_icon)
        
        col = row.column()
        col.operator("qb_tb.validate_all_objects", text="", icon='ERROR')
        
        row = layout.row()
        col = row.column()
        col.label(text="Select:", icon='RESTRICT_SELECT_OFF')
        col = row.column()
        col.prop(scene, "select_option", text="")
        col = row.column()
        
        select_icon = self.get_select_icon(scene.select_option)
        col.operator("qb_tb.filter_select_objects", text="", icon=select_icon)
        
        col = row.column()
        col.operator("qb_tb.clean_object_suffixes", text="", icon='FILE_REFRESH')


def register():
    bpy.utils.register_class(QB_TB_PT_ToolsPanel)


def unregister():
    bpy.utils.unregister_class(QB_TB_PT_ToolsPanel)