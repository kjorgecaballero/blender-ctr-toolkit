"""
Group Management Menu for Constant Materials
Menu only; operators are in operators/qb_tb_list/list_group.py
"""

import bpy
import json
from bpy.types import Menu


class LIST_MT_ConstantMaterialGroupMenu(Menu):
    bl_label = "Select Group"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        op = layout.operator("list.set_constant_material_group", text="All Groups", icon='X')
        op.group_name = ""

        layout.separator()

        if "constant_material_groups" in scene:
            try:
                groups = json.loads(scene["constant_material_groups"])
                for group_name in sorted(groups.keys()):
                    op = layout.operator("list.set_constant_material_group", text=group_name, icon='GROUP')
                    op.group_name = group_name
            except:
                pass


classes = [LIST_MT_ConstantMaterialGroupMenu]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)