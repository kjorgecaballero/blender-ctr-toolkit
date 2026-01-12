"""
Range Box operator module for CTR Toolkit
Provides the Range Box creation operator for track boundaries
"""

from .range_box_operator import register, unregister


def register_range_box():
    """Register Range Box operator with Blender"""
    register()


def unregister_range_box():
    """Unregister Range Box operator from Blender"""
    unregister()