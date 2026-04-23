import bpy
from bpy.types import Operator

class ToggleSplitScreen(Operator):
    bl_idname = "psx.toggle_split_screen"
    bl_label = "Toggle Split Screen"
    bl_description = "Toggle between Properties area and 3D Viewport with rendering"
    def execute(self, context):
        scene = context.scene
        if scene.split_screen_enabled:
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.ui_type = 'PROPERTIES'
                    break
            scene.split_screen_enabled = False
            self.report({'INFO'}, "Split Screen deactivated - Returning to Properties")
        else:
            for area in context.screen.areas:
                if area.type == 'PROPERTIES':
                    area.ui_type = 'VIEW_3D'
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            space.shading.type = 'RENDERED'
                            break
                    break
            scene.split_screen_enabled = True
            self.report({'INFO'}, "Split Screen activated - Properties changed to Rendered Viewport")
        return {'FINISHED'}