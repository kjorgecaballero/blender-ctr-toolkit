"""
Range Box operator for CTR Toolkit
Creates a visual 1000x1000x1000 boundary box using an Empty cube
"""

import bpy

EMPTY_NAME = "Range"
EMPTY_SCALE = 500.0      # Base empty cube size is 2x2x2, scale 500 gives 1000x1000x1000


def create_range_empty():
    """Create or retrieve an empty cube for range visualization."""
    # If the empty already exists, ensure it's visible and in the view layer
    if EMPTY_NAME in bpy.data.objects:
        empty = bpy.data.objects[EMPTY_NAME]
        # Ensure the object is linked to the current view layer
        if empty.name not in bpy.context.view_layer.objects:
            bpy.context.scene.collection.objects.link(empty)
        empty.hide_set(False)
        empty.hide_viewport = False
        return empty

    # Create a new empty cube at world origin
    original_cursor = bpy.context.scene.cursor.location.copy()
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)

    bpy.ops.object.empty_add(type='CUBE', location=(0, 0, 0))
    empty = bpy.context.active_object
    empty.name = EMPTY_NAME
    empty.scale = (EMPTY_SCALE, EMPTY_SCALE, EMPTY_SCALE)

    # Restore original cursor position
    bpy.context.scene.cursor.location = original_cursor

    # Lock transformations to prevent accidental modification
    empty.lock_location = [True, True, True]
    empty.lock_rotation = [True, True, True]
    empty.lock_scale = [True, True, True]

    # Ensure the empty is linked to the current view layer
    if empty.name not in bpy.context.view_layer.objects:
        bpy.context.scene.collection.objects.link(empty)

    return empty


def adjust_camera():
    """Adjust camera clip end to properly view the range box."""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.clip_end = 9000
                    return


class CTR_OT_AddRangeBox(bpy.types.Operator):
    """Operator to add Range Box to scene."""
    bl_idname = "ctr.add_range_box"
    bl_label = "Range Box"
    bl_description = "Adds a 1000x1000x1000 visual boundary box (empty cube)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        create_range_empty()
        adjust_camera()
        self.report({'INFO'}, "Range Box added")
        return {'FINISHED'}


def menu_func(self, context):
    """Add operator to Blender's Add menu."""
    self.layout.operator(CTR_OT_AddRangeBox.bl_idname, text="Range Box", icon='CUBE')


def register():
    """Register the operator with Blender."""
    bpy.utils.register_class(CTR_OT_AddRangeBox)
    bpy.types.VIEW3D_MT_add.append(menu_func)


def unregister():
    """Unregister the operator from Blender."""
    bpy.utils.unregister_class(CTR_OT_AddRangeBox)
    bpy.types.VIEW3D_MT_add.remove(menu_func)