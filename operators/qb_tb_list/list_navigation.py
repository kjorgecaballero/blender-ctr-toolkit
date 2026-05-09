"""
Navigation Points Operators for Quadblock/Triblock List
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
        obj = context.edit_object
        if not self.material_name:
            self.report({'WARNING'}, "No material name provided")
            return {'CANCELLED'}

        if "constant_materials" not in obj or self.material_name not in obj["constant_materials"]:
            self.report({'WARNING'}, f"Constant material '{self.material_name}' not found")
            return {'CANCELLED'}

        info = obj["constant_materials"][self.material_name]
        current = info.get("is_navigation_point", False)
        info["is_navigation_point"] = not current

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
    """Toggle navigation point flag only for items currently visible in the filtered list"""
    bl_idname = "list.toggle_visible_navigation_points"
    bl_label = "Toggle Navigation State"
    bl_description = "Mark/unmark navigation points for all items shown in the current filtered list (respects search, material, group, QB/TB toggles, and navigation filter)"
    bl_options = {'REGISTER'}

    mark_as_nav: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                "constant_materials" in obj and
                context.scene.list_display_type == 'CONSTANT_MATERIALS')

    def execute(self, context):
        obj = context.edit_object
        scene = context.scene
        from ..qb_tb_list.list_multi_selection import _get_filtered_display_items
        visible_items = _get_filtered_display_items(context, obj, scene)

        if not visible_items:
            self.report({'WARNING'}, "No items visible in the current filtered list")
            return {'CANCELLED'}

        const_dict = dict(obj["constant_materials"])
        changed = 0
        for item in visible_items:
            mat_name = item['name']
            if mat_name in const_dict:
                current_state = const_dict[mat_name].get("is_navigation_point", False)
                if current_state != self.mark_as_nav:
                    const_dict[mat_name]["is_navigation_point"] = self.mark_as_nav
                    changed += 1

        if changed > 0:
            obj["constant_materials"] = const_dict

        action = "Marked" if self.mark_as_nav else "Unmarked"
        self.report({'INFO'}, f"{action} {changed} navigation points in the visible list")
        return {'FINISHED'}

    def invoke(self, context, event):
        obj = context.edit_object
        scene = context.scene
        from ..qb_tb_list.list_multi_selection import _get_filtered_display_items
        visible_items = _get_filtered_display_items(context, obj, scene)
        if not visible_items:
            self.report({'WARNING'}, "No visible items to toggle")
            return {'CANCELLED'}
        const_dict = dict(obj["constant_materials"])
        all_are_nav = all(const_dict.get(it['name'], {}).get("is_navigation_point", False) for it in visible_items)
        self.mark_as_nav = not all_are_nav
        return self.execute(context)


classes = [
    LIST_OT_ToggleNavigationPoint,
    LIST_OT_SetNavigationFilter,
    LIST_OT_ToggleVisibleNavigationPoints,
]