"""
Block List UI Initialization
Registration of panels and menus
IssueFilterMenu.
"""

import bpy

from .list_panel import LIST_PT_BlockListPanel
from .list_material_menus import (
    LIST_MT_MaterialFilterMenu,
    LIST_MT_VertexGroupMenu,
    LIST_MT_IssueFilterMenu,  
)
from .navigation_points import LIST_MT_NavigationFilterMenu


classes = [
    LIST_PT_BlockListPanel,
    LIST_MT_MaterialFilterMenu,
    LIST_MT_VertexGroupMenu,
    LIST_MT_NavigationFilterMenu,
    LIST_MT_IssueFilterMenu,   
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)