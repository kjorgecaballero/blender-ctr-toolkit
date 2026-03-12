"""
Navigation Points Operators for Quadblock/Triblock List
Moved from ui/qb_tb_list/navigation_points.py
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
    bl_description = "Filter constant materials by navigation point status (All, Navigation Points only, Non-Navigation only)"
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


class LIST_OT_ToggleAllNavigationPoints(Operator):
    bl_idname = "list.toggle_all_navigation_points"
    bl_label = "Toggle All Navigation Points"
    bl_description = "Mark/unmark all visible constant materials as navigation points"
    bl_options = {'REGISTER'}

    mark_as_nav: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                "constant_materials" in obj and
                context.scene.list_display_type == 'CONSTANT_MATERIALS')

    def execute(self, context):
        scene = context.scene
        obj = context.edit_object
        const_dict = dict(obj["constant_materials"])

        # Filter visible items
        filtered = []
        for mat_name, info in const_dict.items():
            bt = info.get("block_type", "")
            if (bt == "quadblock" and not scene.list_filter_cm_qb) or \
               (bt == "triblock" and not scene.list_filter_cm_tb):
                continue
            if scene.list_navigation_filter != 'ALL':
                is_nav = info.get("is_navigation_point", False)
                if scene.list_navigation_filter == 'NAVIGATION_POINTS' and not is_nav:
                    continue
                if scene.list_navigation_filter == 'NON_NAVIGATION' and is_nav:
                    continue
            filtered.append((mat_name, info))

        if not filtered:
            self.report({'WARNING'}, "No items match current filters")
            return {'CANCELLED'}

        changed = 0
        for mat_name, info in filtered:
            if info.get("is_navigation_point", False) != self.mark_as_nav:
                info["is_navigation_point"] = self.mark_as_nav
                changed += 1

        obj["constant_materials"] = const_dict
        action = "Marked" if self.mark_as_nav else "Unmarked"
        self.report({'INFO'}, f"{action} {changed} navigation points")
        return {'FINISHED'}

    def invoke(self, context, event):
        obj = context.edit_object
        if "constant_materials" in obj:
            scene = context.scene
            all_nav = True
            any_nav = False
            visible = 0
            for mat_name, info in dict(obj["constant_materials"]).items():
                bt = info.get("block_type", "")
                if (bt == "quadblock" and not scene.list_filter_cm_qb) or \
                   (bt == "triblock" and not scene.list_filter_cm_tb):
                    continue
                if scene.list_navigation_filter != 'ALL':
                    is_nav = info.get("is_navigation_point", False)
                    if scene.list_navigation_filter == 'NAVIGATION_POINTS' and not is_nav:
                        continue
                    if scene.list_navigation_filter == 'NON_NAVIGATION' and is_nav:
                        continue
                visible += 1
                is_nav = info.get("is_navigation_point", False)
                if is_nav:
                    any_nav = True
                else:
                    all_nav = False
            if visible == 0:
                self.report({'WARNING'}, "No visible items")
                return {'CANCELLED'}
            self.mark_as_nav = not all_nav
        return self.execute(context)


classes = [
    LIST_OT_ToggleNavigationPoint,
    LIST_OT_SetNavigationFilter,
    LIST_OT_ToggleAllNavigationPoints,
]