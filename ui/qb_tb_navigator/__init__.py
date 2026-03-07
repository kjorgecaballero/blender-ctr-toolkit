"""
Block Navigator UI Initialization
Registration of all UI components for the QB/TB Block Navigator
"""

import bpy

from .navigator_panel import (
    NAVIGATOR_PT_BlockToolsPanel,
)


def register():
    """Register all UI components for the block navigator"""
    # Register panel and its operators
    bpy.utils.register_class(NAVIGATOR_PT_BlockToolsPanel)


def unregister():
    """Unregister all UI components for the block navigator"""
    # Unregister panel and its operators
    bpy.utils.unregister_class(NAVIGATOR_PT_BlockToolsPanel)