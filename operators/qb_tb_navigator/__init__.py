"""
QB/TB Navigator Operators Initialization
Registration of all operators for the block navigation system
"""

import bpy

from .qb_tb_detection import classes as detection_classes
from .qb_tb_selection import classes as selection_classes
from .qb_tb_duplication import classes as duplication_classes
from .clear_cache import classes as cache_classes


operator_classes = detection_classes + selection_classes + duplication_classes + cache_classes


def register():
    for cls in operator_classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(operator_classes):
        bpy.utils.unregister_class(cls)