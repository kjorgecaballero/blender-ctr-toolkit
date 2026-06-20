"""
Navigation Points Operators
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty, BoolProperty


class LIST_OT_ToggleNavigationPoint(Operator):
    bl_idname = "list.toggle_navigation_point"
    bl_label = "Toggle Navigation Point"
    bl_description = "Mark/unmark this constant material as a navigation starting point"
    bl_options = {'REGISTER'}

    material_name: StringProperty(name="Material Name")

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS')

    def execute(self, context):
        if not self.material_name:
            self.report({'WARNING'}, "No material name provided")
            return {'CANCELLED'}

        mat = bpy.data.materials.get(self.material_name)
        if not mat:
            self.report({'WARNING'}, f"Material '{self.material_name}' not found")
            return {'CANCELLED'}

        if mat.get("ctr_block_type") is None:
            self.report({'WARNING'}, f"'{self.material_name}' is not a constant material.")
            return {'CANCELLED'}

        current = mat.get("ctr_is_navigation_point", False)
        mat["ctr_is_navigation_point"] = not current

        self.report({'INFO'}, f"Navigation point {'enabled' if not current else 'disabled'} for '{self.material_name}'")
        return {'FINISHED'}


class LIST_OT_SetNavigationFilter(Operator):
    bl_idname = "list.set_navigation_filter"
    bl_label = "Set Navigation Filter"
    bl_description = "Filter constant materials by navigation point status"
    bl_options = {'REGISTER'}

    filter_type: EnumProperty(
        name="Filter Type",
        items=[
            ('ALL', 'All Constant Materials', ''),
            ('NAVIGATION_POINTS', 'Only Navigation Points', ''),
            ('NON_NAVIGATION', 'Non-Navigation Materials', ''),
        ],
        default='ALL'
    )

    def execute(self, context):
        context.scene.list_navigation_filter = self.filter_type
        return {'FINISHED'}


class LIST_OT_ToggleVisibleNavigationPoints(Operator):
    bl_idname = "list.toggle_visible_navigation_points"
    bl_label = "Toggle Navigation State"
    bl_description = "Mark/unmark navigation points for all items shown in the current filtered list"
    bl_options = {'REGISTER'}

    mark_as_nav: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS')

    def execute(self, context):
        obj = context.edit_object
        scene = context.scene
        from .list_multi_selection import _get_filtered_display_items
        visible_items = _get_filtered_display_items(context, obj, scene)

        if not visible_items:
            self.report({'WARNING'}, "No items visible in the current filtered list")
            return {'CANCELLED'}

        changed = 0
        for item in visible_items:
            mat = bpy.data.materials.get(item['name'])
            if mat and mat.get("ctr_block_type") is not None:
                current = mat.get("ctr_is_navigation_point", False)
                if current != self.mark_as_nav:
                    mat["ctr_is_navigation_point"] = self.mark_as_nav
                    changed += 1

        action = "Marked" if self.mark_as_nav else "Unmarked"
        self.report({'INFO'}, f"{action} {changed} navigation points in the visible list")
        return {'FINISHED'}

    def invoke(self, context, event):
        obj = context.edit_object
        scene = context.scene
        from .list_multi_selection import _get_filtered_display_items
        visible_items = _get_filtered_display_items(context, obj, scene)
        if not visible_items:
            self.report({'WARNING'}, "No visible items to toggle")
            return {'CANCELLED'}

        all_are_nav = True
        for item in visible_items:
            mat = bpy.data.materials.get(item['name'])
            if not mat or not mat.get("ctr_is_navigation_point", False):
                all_are_nav = False
                break
        self.mark_as_nav = not all_are_nav
        return self.execute(context)


classes = [
    LIST_OT_ToggleNavigationPoint,
    LIST_OT_SetNavigationFilter,
    LIST_OT_ToggleVisibleNavigationPoints,
]