"""
Export helpers for temporarily disabling PS1 render and vertex snap modifiers.
Used during export operations to avoid conflicts and improve performance.
"""

import bpy
from .compat import is_blender_ge_4_0


def temporary_disable_ps1_render(context):
    """
    Temporarily disable CTR Render mode if it was active.
    Returns True if it was active, so it can be restored later.
    """
    scene = context.scene
    was_active = scene.ps1_render_active
    if was_active:
        bpy.ops.psx.toggle_ctr_render()
    return was_active


def restore_ps1_render(context, was_active):
    """Restore CTR Render mode to its previous state."""
    if was_active and not context.scene.ps1_render_active:
        bpy.ops.psx.toggle_ctr_render()


def get_vertex_snap_modifiers(objects):
    """
    Collect all vertex snap modifiers (VX_WorldSnap) from given objects.
    Returns a list of (object, modifier) tuples.
    """
    snap_modifiers = []
    if not is_blender_ge_4_0():
        return snap_modifiers
    for obj in objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'NODES' and mod.node_group and mod.node_group.name == "VX_WorldSnap":
                    snap_modifiers.append((obj, mod))
    return snap_modifiers


def disable_vertex_snap_modifiers(snap_modifiers):
    """
    Disable viewport display of the given vertex snap modifiers.
    Returns a list of original states (object, modifier, show_viewport) for restoration.
    """
    original_states = []
    for obj, mod in snap_modifiers:
        original_states.append((obj, mod, mod.show_viewport))
        mod.show_viewport = False
    return original_states


def restore_vertex_snap_modifiers(original_states):
    """Restore the original viewport visibility of vertex snap modifiers."""
    for obj, mod, was_visible in original_states:
        if obj.name in bpy.data.objects and mod.name in obj.modifiers:
            obj.modifiers[mod.name].show_viewport = was_visible