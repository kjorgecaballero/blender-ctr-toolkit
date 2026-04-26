"""
QB/TB Navigator Properties
Property definitions for the block navigation system
"""

import bpy
from bpy.props import BoolProperty, EnumProperty


def get_quad_group_items(self, context):
    """Return a list of (key, name, description) for existing quadblock groups."""
    items = [("0", "None", "No groups available")]
    obj = context.edit_object
    if obj and "quad_group_members" in obj:
        groups = obj.get("quad_group_members", {})
        if groups:
            items = []
            for group_key in sorted(groups.keys(), key=int):
                group_num = int(group_key)
                count = len(groups[group_key])
                items.append((group_key, f"Group {group_num}", f"{count} quadblocks"))
    return items


def get_tri_group_items(self, context):
    """Return a list of (key, name, description) for existing triblock groups."""
    items = [("0", "None", "No groups available")]
    obj = context.edit_object
    if obj and "tri_group_members" in obj:
        groups = obj.get("tri_group_members", {})
        if groups:
            items = []
            for group_key in sorted(groups.keys(), key=int):
                group_num = int(group_key)
                count = len(groups[group_key])
                items.append((group_key, f"Group {group_num}", f"{count} triblocks"))
    return items


def register():
    # Property for collapsed group selection panel
    bpy.types.Scene.navigator_show_group_selection = BoolProperty(
        name="Show Group Selection",
        description="Show group selection dropdowns for quadblocks and triblocks",
        default=False
    )

    # Dynamic dropdown for quadblock groups
    bpy.types.Scene.navigator_selected_quad_group = EnumProperty(
        name="Quad Group",
        description="Select a quadblock group to select",
        items=get_quad_group_items
    )

    # Dynamic dropdown for triblock groups
    bpy.types.Scene.navigator_selected_tri_group = EnumProperty(
        name="Tri Group",
        description="Select a triblock group to select",
        items=get_tri_group_items
    )


def unregister():
    del bpy.types.Scene.navigator_selected_tri_group
    del bpy.types.Scene.navigator_selected_quad_group
    del bpy.types.Scene.navigator_show_group_selection