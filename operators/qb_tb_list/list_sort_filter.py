"""
Sort and Filter Operators for Quadblock/Triblock List
Each issue filter has its own operator for custom tooltips.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from ..qb_tb_list.list_multi_selection import _get_filtered_display_items

ITEMS_PER_PAGE = 10


def _adjust_scroll_to_checked(context, obj, scene):
    """Adjust scroll position and list index to show the first checked item."""
    if "multi_selected_items" not in obj or not obj["multi_selected_items"]:
        return

    checked_names = set(dict(obj["multi_selected_items"]).keys())
    if not checked_names:
        return

    # Get the current list of visible items (respects filters, search, etc.)
    items = _get_filtered_display_items(context, obj, scene)
    if not items:
        return

    # Sort items according to current sort settings (same logic as in list_panel)
    reverse_type = (scene.list_sort_type_direction == 'DESC')
    reverse_name = (scene.list_sort_name_direction == 'DESC')

    def sort_key(item):
        # Primary sort: block type (QB first or TB first)
        type_order = 0 if item['block_type'] == 'quadblock' else 1
        if reverse_type:
            type_order = 1 - type_order
        # Secondary: name
        name_key = item['name'].lower()
        return (type_order, name_key)

    items.sort(key=sort_key)
    if reverse_name:
        items.reverse()

    # Find first checked item in the sorted list
    target_index = -1
    for idx, it in enumerate(items):
        if it['name'] in checked_names:
            target_index = idx
            break

    if target_index == -1:
        return

    # Calculate page start index
    page_start = (target_index // ITEMS_PER_PAGE) * ITEMS_PER_PAGE
    max_scroll = max(0, len(items) - ITEMS_PER_PAGE)
    new_scroll = min(page_start, max_scroll)

    # Apply new scroll and list index
    scene.list_vertical_scroll = new_scroll
    scene.list_list_index = target_index

    # Force UI redraw
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


class LIST_OT_ToggleSortName(Operator):
    bl_idname = "list.toggle_sort_name"
    bl_label = "Toggle Name Sort"
    bl_description = "Change sorting order of the list by name (ascending/descending)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        obj = context.edit_object
        # Flip direction
        scene.list_sort_name_direction = 'DESC' if scene.list_sort_name_direction == 'ASC' else 'ASC'
        # Adjust scroll to keep checked items visible
        if obj:
            _adjust_scroll_to_checked(context, obj, scene)
        return {'FINISHED'}


class LIST_OT_ToggleSortType(Operator):
    bl_idname = "list.toggle_sort_type"
    bl_label = "Toggle Type Sort"
    bl_description = "Change sorting order of the list by block type (QB/TB ascending or TB/QB descending)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        scene = context.scene
        obj = context.edit_object
        # Flip direction
        scene.list_sort_type_direction = 'DESC' if scene.list_sort_type_direction == 'ASC' else 'ASC'
        # Adjust scroll to keep checked items visible
        if obj:
            _adjust_scroll_to_checked(context, obj, scene)
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


class LIST_OT_SetIssueFilterMissingUVs(Operator):
    bl_idname = "list.set_issue_filter_missing_uvs"
    bl_label = "Missing UVs"
    bl_description = "Show blocks that have no UV map"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.list_issue_filter = 'MISSING_UVS'
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
    LIST_OT_SetIssueFilterMissingUVs,
    LIST_OT_SetIssueFilterOutOfRange,
    LIST_OT_SetIssueFilterMultipleMaterials,
]