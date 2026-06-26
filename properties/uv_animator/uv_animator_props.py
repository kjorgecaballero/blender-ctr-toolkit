import bpy
from .uv_frame_item import UVAnimationFrameItem
from .uv_texture_item import UVTextureItem
from .uv_animated_block import UVAnimatedBlock

def register():
    bpy.utils.register_class(UVAnimationFrameItem)
    bpy.utils.register_class(UVTextureItem)
    bpy.utils.register_class(UVAnimatedBlock)

    # Singe object properties (
    bpy.types.Object.uv_animation_frames = bpy.props.CollectionProperty(type=UVAnimationFrameItem)
    bpy.types.Object.uv_texture_items = bpy.props.CollectionProperty(type=UVTextureItem)
    bpy.types.Object.is_uv_animated = bpy.props.BoolProperty(default=False)
    bpy.types.Object.uv_animator_playback_enabled = bpy.props.BoolProperty(default=True)
    bpy.types.Object.uv_selected_for_group = bpy.props.BoolProperty(default=False)
    bpy.types.Object.uv_start_frame = bpy.props.IntProperty(default=0, min=0)
    bpy.types.Object.uv_frame_duration = bpy.props.IntProperty(default=0, min=0)

    # Constant blocks
    bpy.types.Object.uv_animated_blocks = bpy.props.CollectionProperty(type=UVAnimatedBlock)
    bpy.types.Object.has_constant_materials = bpy.props.BoolProperty(default=False)

    # Scene properties
    bpy.types.Scene.active_uv_block_key = bpy.props.StringProperty(default="")
    bpy.types.Scene.uv_animator_expanded_blocks = bpy.props.StringProperty(default="{}")
    bpy.types.Scene.active_uv_object_name = bpy.props.StringProperty(default="")
    bpy.types.Scene.uv_animator_expanded = bpy.props.StringProperty(default="{}")
    bpy.types.Scene.uv_animator_groups = bpy.props.StringProperty(default="{}")
    bpy.types.Scene.uv_animator_active_group = bpy.props.StringProperty(default="")
    bpy.types.Scene.uv_animator_group_toggles = bpy.props.StringProperty(default="{}")
    bpy.types.Scene.uv_group_texture_expanded = bpy.props.StringProperty(default="{}")

    # Mode selector
    bpy.types.Scene.uv_animator_mode = bpy.props.EnumProperty(
        name="Animation Mode",
        items=[
            ('LEGACY', "Single", "Animate the whole object as one block"),
            ('CONSTANT', "Constant", "Animate each constant material block individually"),
        ],
        default='LEGACY'
    )

    # Tool selector for Anim Tools section
    bpy.types.Scene.uv_animator_active_tool = bpy.props.EnumProperty(
        name="Tool",
        description="Select the tool to use in the Anim Tools section",
        items=[
            ('INTERPOLATE', "Interpolate", "Create animations by interpolating textures between keyframes"),
            ('SCAN', "Scan", "Scan the timeline to capture UVs frame by frame"),
        ],
        default='INTERPOLATE'
    )

    # Interpolate properties
    bpy.types.Scene.uv_animator_base_animations = bpy.props.StringProperty(
        name="Base Animations",
        description="JSON storing the found base animations",
        default="{}"
    )
    bpy.types.Scene.uv_animator_secondary_texture = bpy.props.StringProperty(
        name="Secondary Texture",
        description="Path to the secondary texture for interpolation",
        subtype='FILE_PATH',
        default=""
    )
    bpy.types.Scene.uv_animator_revert_interpolation = bpy.props.BoolProperty(
        name="Revert",
        description="Add reverse sequence after the forward sequence",
        default=False
    )
    bpy.types.Scene.uv_animator_selected_animation = bpy.props.StringProperty(
        name="Selected Animation",
        description="Currently selected base animation for processing",
        default=""
    )

def unregister():
    # Tool selector
    del bpy.types.Scene.uv_animator_active_tool

    # Interpolate properties
    del bpy.types.Scene.uv_animator_selected_animation
    del bpy.types.Scene.uv_animator_revert_interpolation
    del bpy.types.Scene.uv_animator_secondary_texture
    del bpy.types.Scene.uv_animator_base_animations

    # Mode selector
    del bpy.types.Scene.uv_animator_mode

    # Scene properties
    del bpy.types.Scene.uv_group_texture_expanded
    del bpy.types.Scene.uv_animator_group_toggles
    del bpy.types.Scene.uv_animator_active_group
    del bpy.types.Scene.uv_animator_groups
    del bpy.types.Scene.uv_animator_expanded
    del bpy.types.Scene.active_uv_object_name
    del bpy.types.Scene.uv_animator_expanded_blocks
    del bpy.types.Scene.active_uv_block_key

    # Object properties
    del bpy.types.Object.uv_frame_duration
    del bpy.types.Object.uv_start_frame
    del bpy.types.Object.uv_selected_for_group
    del bpy.types.Object.uv_animator_playback_enabled
    del bpy.types.Object.is_uv_animated
    del bpy.types.Object.uv_texture_items
    del bpy.types.Object.uv_animation_frames
    del bpy.types.Object.uv_animated_blocks
    del bpy.types.Object.has_constant_materials

    bpy.utils.unregister_class(UVAnimatedBlock)
    bpy.utils.unregister_class(UVTextureItem)
    bpy.utils.unregister_class(UVAnimationFrameItem)