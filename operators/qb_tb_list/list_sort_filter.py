"""
Sort and Filter Operators for Quadblock/Triblock List
Moved from ui/qb_tb_list/list_sort_filters.py
Now includes operator for issue filter
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty


class LIST_OT_ToggleSortName(Operator):
    bl_idname = "list.toggle_sort_name"
    bl_label = "Toggle Name Sort"
    bl_description = "Toggle alphabetical sorting of names (A-Z / Z-A)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.list_sort_name_direction = 'DESC' if scene.list_sort_name_direction == 'ASC' else 'ASC'
        return {'FINISHED'}


class LIST_OT_ToggleSortType(Operator):
    bl_idname = "list.toggle_sort_type"
    bl_label = "Toggle Type Sort"
    bl_description = "Toggle sorting by block type (Quadblocks first / Triblocks first)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.list_sort_type_direction = 'DESC' if scene.list_sort_type_direction == 'ASC' else 'ASC'
        return {'FINISHED'}


class LIST_OT_SetMaterialFilter(Operator):
    bl_idname = "list.set_material_filter"
    bl_label = "Set Material Filter"
    bl_description = "Filter the list by a specific material name"
    bl_options = {'REGISTER'}

    material_name: StringProperty(name="Material Name")

    def execute(self, context):
        scene = context.scene
        if scene.list_display_type == 'VERTEX_GROUPS':
            scene.list_material_filter_vg = self.material_name
        else:
            scene.list_material_filter_cm = self.material_name
        return {'FINISHED'}


# Operator to set issue filter
class LIST_OT_SetIssueFilter(Operator):
    bl_idname = "list.set_issue_filter"
    bl_label = "Set Issue Filter"
    bl_description = "Filter vertex groups by validation issues"
    bl_options = {'REGISTER'}

    filter_type: EnumProperty(
        name="Filter Type",
        items=[
            ('ALL', 'All', ''),
            ('VALID', 'Valid Blocks', ''),
            ('INVALID_GEOMETRY', 'Invalid Geometry', ''),
            ('INVALID_UVS', 'Invalid UVs', ''),
            ('INVALID_TRIBLOCK_UVS', 'Invalid Triblock UVs', ''),
            ('DEGENERATED_UVS', 'Degenerated UVs', ''),
            ('NO_ISSUES', 'No Issues', ''),
        ],
        default='ALL'
    )

    def execute(self, context):
        context.scene.list_issue_filter = self.filter_type
        return {'FINISHED'}


classes = [
    LIST_OT_ToggleSortName,
    LIST_OT_ToggleSortType,
    LIST_OT_SetMaterialFilter,
    LIST_OT_SetIssueFilter,  
]