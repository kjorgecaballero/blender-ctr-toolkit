"""
QB/TB List Operators Initialization
Registration of ALL operators for the block list system.
Now includes vertex group validation operator.
"""

import bpy

from .qb_tb_constant_material import classes as constant_material_classes
from .qb_tb_vertex_groups import classes as vertex_classes
from .list_multi_selection import classes as multi_selection_classes
from .list_navigation import classes as navigation_classes
from .list_group import classes as group_classes
from .list_scroll import classes as scroll_classes
from .list_sort_filter import classes as sort_filter_classes
from .list_select import classes as select_classes

operator_classes = (
    constant_material_classes +
    vertex_classes +          
    multi_selection_classes +
    navigation_classes +
    group_classes +
    scroll_classes +
    sort_filter_classes +
    select_classes
)

def register():
    for cls in operator_classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(operator_classes):
        bpy.utils.unregister_class(cls)