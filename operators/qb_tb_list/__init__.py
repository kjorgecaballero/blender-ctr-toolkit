"""
QB/TB List Operators Initialization
Registration of ALL operators for the item list system.
"""

import bpy

from .qb_tb_constant_material import classes as constant_material_classes
from .qb_tb_vertex_groups import classes as vertex_classes
from .list_multi_selection import classes as multi_selection_classes
from .list_navigation import classes as navigation_classes
from .list_group import group_operator_classes
from .list_scroll import classes as scroll_classes
from .list_sort_filter import classes as sort_filter_classes
from .list_select import classes as select_classes
from .list_duplicate import classes as duplicate_classes
from .list_toggle_seams import classes as seams_classes
from .update_derived_materials import classes as update_classes

operator_classes = (
    constant_material_classes +
    vertex_classes +
    multi_selection_classes +
    navigation_classes +
    group_operator_classes +
    scroll_classes +
    sort_filter_classes +
    select_classes +
    duplicate_classes +
    seams_classes +
    update_classes
)

def register():
    for cls in operator_classes:
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(operator_classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass