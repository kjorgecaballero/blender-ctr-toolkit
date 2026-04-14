"""
Sort and Filter Operators for Quadblock/Triblock List
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


class LIST_OT_SetIssueFilter(Operator):
    bl_idname = "list.set_issue_filter"
    bl_label = "Set Issue Filter"
    bl_description = "Filter vertex groups by validation issues"
    bl_options = {'REGISTER'}

    filter_type: EnumProperty(
        name="Filter Type",
        items=[
            ('ALL', 'All', 'Show all blocks (valid and invalid)'),
            ('VALID', 'Valid', 'Show only valid blocks'),
            ('INVALID', 'Invalid', 'Show only blocks with any issue'),
            ('INVALID_GEOMETRY', 'Invalid Geometry', 'Show blocks with invalid geometry'),
            ('INVALID_UVS', 'Invalid UVs', 'Show blocks with UVs outside 0-1 range'),
            ('INVALID_TRIBLOCK_UVS', 'Invalid Triblock UVs', 'Show triblocks with incorrect UV arrangement'),
            ('DEGENERATED_UVS', 'Degenerated UVs', 'Show blocks with all UVs identical'),
            ('OUT_OF_RANGE', 'Out of Range', 'Show blocks with vertices outside the range box'),
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