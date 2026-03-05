"""
QB/TB Navigator Properties
Property definitions for the block navigation system
"""

import bpy
from bpy.props import BoolProperty


def register():
    # Property for collapsed group selection panel
    bpy.types.Scene.navigator_show_group_selection = BoolProperty(
        name="Show Group Selection",
        description="Show group selection buttons for quadblocks and triblocks",
        default=False
    )


def unregister():
    del bpy.types.Scene.navigator_show_group_selection