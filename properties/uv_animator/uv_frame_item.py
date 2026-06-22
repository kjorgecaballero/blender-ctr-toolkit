import bpy

class UVAnimationFrameItem(bpy.types.PropertyGroup):
    frame_index: bpy.props.IntProperty(default=0)
    uv_data: bpy.props.StringProperty(default="")
    texture_path: bpy.props.StringProperty(default="")
    face_centers: bpy.props.StringProperty(
        name="Face Centers",
        description="JSON string with face center coordinates for matching",
        default=""
    )

def register():
    bpy.utils.register_class(UVAnimationFrameItem)

def unregister():
    bpy.utils.unregister_class(UVAnimationFrameItem)