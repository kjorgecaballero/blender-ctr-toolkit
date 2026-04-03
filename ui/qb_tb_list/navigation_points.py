"""
Navigation Filter Menu for Constant Materials
Menu only; operators are in operators/qb_tb_list/list_navigation.py
"""

import bpy
from bpy.types import Menu


class LIST_MT_NavigationFilterMenu(Menu):
    bl_label = "Filter by Navigation"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        current = scene.list_navigation_filter

        icon = 'CHECKBOX_HLT' if current == 'ALL' else 'CHECKBOX_DEHLT'
        op = layout.operator("list.set_navigation_filter", text="All", icon=icon)
        op.filter_type = 'ALL'

        icon = 'CHECKBOX_HLT' if current == 'NAVIGATION_POINTS' else 'CHECKBOX_DEHLT'
        op = layout.operator("list.set_navigation_filter", text="Navigation Points", icon=icon)
        op.filter_type = 'NAVIGATION_POINTS'

        icon = 'CHECKBOX_HLT' if current == 'NON_NAVIGATION' else 'CHECKBOX_DEHLT'
        op = layout.operator("list.set_navigation_filter", text="Constant Materials", icon=icon)
        op.filter_type = 'NON_NAVIGATION'


classes = [LIST_MT_NavigationFilterMenu]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)