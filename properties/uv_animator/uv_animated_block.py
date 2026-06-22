import bpy
from .uv_frame_item import UVAnimationFrameItem
from .uv_texture_item import UVTextureItem

class UVAnimatedBlock(bpy.types.PropertyGroup):
    block_id: bpy.props.StringProperty(default="")
    block_type: bpy.props.EnumProperty(
        items=[('QUADBLOCK', "Quadblock", ""), ('TRIBLOCK', "Triblock", "")],
        default='QUADBLOCK'
    )
    material_name: bpy.props.StringProperty(default="")
    frames: bpy.props.CollectionProperty(type=UVAnimationFrameItem)
    texture_items: bpy.props.CollectionProperty(type=UVTextureItem)
    is_animated: bpy.props.BoolProperty(default=False)
    playback_enabled: bpy.props.BoolProperty(default=True)
    selected_for_group: bpy.props.BoolProperty(default=False)
    start_frame: bpy.props.IntProperty(default=0, min=0)
    frame_duration: bpy.props.IntProperty(default=0, min=0)

def register():
    bpy.utils.register_class(UVAnimatedBlock)

def unregister():
    bpy.utils.unregister_class(UVAnimatedBlock)