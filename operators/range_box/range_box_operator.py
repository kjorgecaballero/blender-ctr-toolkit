"""
Range Box operator for CTR Toolkit
Creates a 1000x1000x1000 wireframe cube for track boundary visualization
"""

import bpy

CUBE_NAME = "Range"
CUBE_SIZE = 1000

def create_wireframe_cube():
    """Create or retrieve a wireframe cube for range visualization"""
    if CUBE_NAME in bpy.data.objects:
        cube = bpy.data.objects[CUBE_NAME]
        bpy.context.view_layer.objects.active = cube
        cube.select_set(True)
        cube.hide_set(False)
        return cube

    # Create new cube
    bpy.ops.mesh.primitive_cube_add(size=CUBE_SIZE)
    cube = bpy.context.active_object
    cube.name = CUBE_NAME
    
    # Convert to wireframe
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.delete(type='ONLY_FACE')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    cube.display_type = 'WIRE'
    
    # Lock transformations to prevent accidental modification
    cube.lock_location = [True, True, True]
    cube.lock_rotation = [True, True, True]
    cube.lock_scale = [True, True, True]
    
    return cube

def adjust_camera():
    """Adjust camera settings to properly view the range box"""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.clip_end = 9000
                    return

class CTR_OT_AddRangeBox(bpy.types.Operator):
    """Operator to add Range Box to scene"""
    
    bl_idname = "ctr.add_range_box"
    bl_label = "Range Box"
    bl_description = "Adds a 1000x1000x1000 wireframe cube for track boundaries"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        """Check if operator can be executed"""
        return context.mode == 'OBJECT'

    def execute(self, context):
        """Execute the operator"""
        create_wireframe_cube()
        adjust_camera()
        self.report({'INFO'}, "Range Box created - 1000x1000x1000 wireframe cube")
        return {'FINISHED'}

def menu_func(self, context):
    """Add operator to Blender's Add menu"""
    self.layout.operator(CTR_OT_AddRangeBox.bl_idname, text="Range Box", icon='CUBE')

def register():
    """Register the operator with Blender"""
    bpy.utils.register_class(CTR_OT_AddRangeBox)
    bpy.types.VIEW3D_MT_add.append(menu_func)

def unregister():
    """Unregister the operator from Blender"""
    bpy.utils.unregister_class(CTR_OT_AddRangeBox)
    bpy.types.VIEW3D_MT_add.remove(menu_func)