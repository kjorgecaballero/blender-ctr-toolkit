"""
Navigation Filter Menu for Constant Materials
"""

import bpy
from bpy.types import Menu
from ...operators.qb_tb_list.list_multi_selection import _get_filtered_display_items
from ...icons import get_icon


class LIST_MT_NavigationFilterMenu(Menu):
    bl_label = "Filter by Navigation"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        current = scene.list_navigation_filter
        obj = context.edit_object

        icon = 'CHECKBOX_HLT' if current == 'ALL' else 'CHECKBOX_DEHLT'
        op = layout.operator("list.set_navigation_filter", text="All", icon=icon)
        op.filter_type = 'ALL'

        icon = 'CHECKBOX_HLT' if current == 'NAVIGATION_POINTS' else 'CHECKBOX_DEHLT'
        op = layout.operator("list.set_navigation_filter", text="Navigation Points", icon=icon)
        op.filter_type = 'NAVIGATION_POINTS'

        icon = 'CHECKBOX_HLT' if current == 'NON_NAVIGATION' else 'CHECKBOX_DEHLT'
        op = layout.operator("list.set_navigation_filter", text="Constant Materials", icon=icon)
        op.filter_type = 'NON_NAVIGATION'

        layout.separator()

        all_are_nav = False
        if obj and scene.list_display_type == 'CONSTANT_MATERIALS':
            visible_items = _get_filtered_display_items(context, obj, scene)
            if visible_items:
                all_are_nav = all(
                    bpy.data.materials.get(it['name'], {}).get("ctr_is_navigation_point", False)
                    for it in visible_items
                )

        if all_are_nav:
            icon_id = get_icon("constant_mat_icon")
            fallback_icon = 'MATERIAL'
        else:
            icon_id = get_icon("nav_point_icon")
            fallback_icon = 'PIVOT_CURSOR'

        if icon_id:
            layout.operator(
                "list.toggle_visible_navigation_points",
                text="Toggle Navigation State",
                icon_value=icon_id
            )
        else:
            layout.operator(
                "list.toggle_visible_navigation_points",
                text="Toggle Navigation State",
                icon=fallback_icon
            )


classes = [LIST_MT_NavigationFilterMenu]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)