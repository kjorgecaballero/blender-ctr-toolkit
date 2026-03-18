import bpy
from bpy.types import Panel
from .qb_tb_navigator import draw_navigator
from .qb_tb_validator import draw_validator
from .help_utils import draw_help_buttons   # Import help buttons

class CTR_PT_MainPanel(Panel):
    bl_label = "CTR Toolkit"
    bl_idname = "CTR_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CTR"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Top row: mode switcher on the left, help buttons on the right
        row = layout.row(align=True)
        row.prop(scene, "ctr_tool_mode", text="")     
        row.separator(factor=2.0)                      # Spacing
        draw_help_buttons(row)                          # Help icons aligned to the right

        # Delegate drawing to the appropriate submodule
        if scene.ctr_tool_mode == 'NAVIGATOR':
            draw_navigator(context, layout)
        else:
            draw_validator(context, layout)

def register():
    bpy.utils.register_class(CTR_PT_MainPanel)

def unregister():
    bpy.utils.unregister_class(CTR_PT_MainPanel)