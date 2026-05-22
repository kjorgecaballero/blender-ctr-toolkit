"""
Sort and Filter Operators for Quadblock/Triblock List
Each issue filter has its own operator for custom tooltips.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty


class LIST_OT_ToggleSortName(Operator):
    bl_idname = "list.toggle_sort_name"
    bl_label = "Toggle Name Sort"
    bl_description = "Change sorting order of the list by name (ascending/descending)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.list_sort_name_direction = 'DESC' if scene.list_sort_name_direction == 'ASC' else 'ASC'
        return {'FINISHED'}


class LIST_OT_ToggleSortType(Operator):
    bl_idname = "list.toggle_sort_type"
    bl_label = "Toggle Type Sort"
    bl_description = "Change sorting order of the list by block type (QB/TB ascending or TB/QB descending)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        scene.list_sort_type_direction = 'DESC' if scene.list_sort_type_direction == 'ASC' else 'ASC'
        return {'FINISHED'}


class LIST_OT_SetMaterialFilter(Operator):
    bl_idname = "list.set_material_filter"
    bl_label = "Set Material Filter"
    bl_description = "Filter the block list to show only blocks that use a specific material"
    bl_options = {'REGISTER'}

    material_name: StringProperty(name="Material Name")

    def execute(self, context):
        scene = context.scene
        if scene.list_display_type == 'VERTEX_GROUPS':
            scene.list_material_filter_vg = self.material_name
        else:
            scene.list_material_filter_cm = self.material_name
        return {'FINISHED'}


# Individual Issue Filter Operators

class LIST_OT_SetIssueFilterAll(Operator):
    bl_idname = "list.set_issue_filter_all"
    bl_label = "All"
    bl_description = "Show all blocks (valid and invalid) – no filtering"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'ALL'
        return {'FINISHED'}


class LIST_OT_SetIssueFilterValid(Operator):
    bl_idname = "list.set_issue_filter_valid"
    bl_label = "Valid"
    bl_description = "Show only valid blocks (no geometry or UV issues)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'VALID'
        return {'FINISHED'}


class LIST_OT_SetIssueFilterInvalid(Operator):
    bl_idname = "list.set_issue_filter_invalid"
    bl_label = "Invalid"
    bl_description = "Show any block that has at least one issue (geometry, UVs, out of range, etc.)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'INVALID'
        return {'FINISHED'}


class LIST_OT_SetIssueFilterInvalidGeometry(Operator):
    bl_idname = "list.set_issue_filter_invalid_geometry"
    bl_label = "Invalid Geometry"
    bl_description = "Show blocks whose vertex/face configuration does not form a valid quadblock or triblock"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'INVALID_GEOMETRY'
        return {'FINISHED'}


class LIST_OT_SetIssueFilterInvalidUVs(Operator):
    bl_idname = "list.set_issue_filter_invalid_uvs"
    bl_label = "Invalid UVs"
    bl_description = "Show blocks with UV coordinates outside the 0-1 range"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'INVALID_UVS'
        return {'FINISHED'}


class LIST_OT_SetIssueFilterInvalidTriblockUVs(Operator):
    bl_idname = "list.set_issue_filter_invalid_triblock_uvs"
    bl_label = "Invalid Triblock UVs"
    bl_description = "Show triblocks where the UV layout does not follow the expected pattern (adjacent triangles share UVs)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'INVALID_TRIBLOCK_UVS'
        return {'FINISHED'}


class LIST_OT_SetIssueFilterDegeneratedUVs(Operator):
    bl_idname = "list.set_issue_filter_degenerated_uvs"
    bl_label = "Degenerated UVs"
    bl_description = "Show blocks where all UV coordinates are identical (collapsed UVs)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'DEGENERATED_UVS'
        return {'FINISHED'}


class LIST_OT_SetIssueFilterOutOfRange(Operator):
    bl_idname = "list.set_issue_filter_out_of_range"
    bl_label = "Out of Range"
    bl_description = "Show blocks that have vertices outside the defined Range Box (global bounds)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'OUT_OF_RANGE'
        return {'FINISHED'}


class LIST_OT_SetIssueFilterMultipleMaterials(Operator):
    bl_idname = "list.set_issue_filter_multiple_materials"
    bl_label = "Multiple Materials"
    bl_description = "Show blocks whose faces use more than one material"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'MULTIPLE_MATERIALS'
        return {'FINISHED'}


# All operator classes to register
classes = [
    LIST_OT_ToggleSortName,
    LIST_OT_ToggleSortType,
    LIST_OT_SetMaterialFilter,
    LIST_OT_SetIssueFilterAll,
    LIST_OT_SetIssueFilterValid,
    LIST_OT_SetIssueFilterInvalid,
    LIST_OT_SetIssueFilterInvalidGeometry,
    LIST_OT_SetIssueFilterInvalidUVs,
    LIST_OT_SetIssueFilterInvalidTriblockUVs,
    LIST_OT_SetIssueFilterDegeneratedUVs,
    LIST_OT_SetIssueFilterOutOfRange,
    LIST_OT_SetIssueFilterMultipleMaterials,
]