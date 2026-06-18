import bpy

class UVAnimationFrameItem(bpy.types.PropertyGroup):
    frame_index: bpy.props.IntProperty(default=0)
    uv_data: bpy.props.StringProperty()
    texture_path: bpy.props.StringProperty()

class UVTextureItem(bpy.types.PropertyGroup):
    texture_path: bpy.props.StringProperty(
        name="Texture Path",
        description="Path to the texture image"
    )
    blend_mode: bpy.props.EnumProperty(
        name="Blend Mode",
        description="Blend mode for this texture",
        items=[
            ("0", "Half Transparent", ""),
            ("1", "Additive", ""),
            ("2", "Subtractive", ""),
            ("3", "Additive Translucent", ""),
        ],
        default="0"
    )

def register():
    bpy.utils.register_class(UVAnimationFrameItem)
    bpy.utils.register_class(UVTextureItem)
    
    bpy.types.Object.uv_animation_frames = bpy.props.CollectionProperty(type=UVAnimationFrameItem)
    bpy.types.Object.uv_texture_items = bpy.props.CollectionProperty(type=UVTextureItem)
    bpy.types.Object.is_uv_animated = bpy.props.BoolProperty(default=False)
    bpy.types.Object.uv_animator_playback_enabled = bpy.props.BoolProperty(default=True)
    bpy.types.Object.uv_selected_for_group = bpy.props.BoolProperty(default=False)
    
    # Start frame index (always valid when frames exist)
    bpy.types.Object.uv_start_frame = bpy.props.IntProperty(
        name="Start Frame",
        description="Index of the frame to start playback from (0 if no frames)",
        default=0,
        min=0
    )
    
    # Frame duration multiplier
    bpy.types.Object.uv_frame_duration = bpy.props.IntProperty(
        name="Frame Duration",
        description="Duration multiplier for each frame (0 = 0.033s, 1 = 0.066s, 2 = 0.099s, ...)",
        default=0,
        min=0
    )
    
    bpy.types.Scene.active_uv_object_name = bpy.props.StringProperty(default="")
    bpy.types.Scene.uv_animator_expanded = bpy.props.StringProperty(default="{}")
    
    bpy.types.Scene.uv_animator_groups = bpy.props.StringProperty(
        name="UV Groups",
        default="{}",
        description="JSON string: { 'group_name': ['obj1', 'obj2'], ... }"
    )
    bpy.types.Scene.uv_animator_active_group = bpy.props.StringProperty(
        name="Active UV Group",
        default="",
        description="Current filter group for the UV Animator list"
    )
    
    bpy.types.Scene.uv_animator_group_toggles = bpy.props.StringProperty(
        name="Group Toggles",
        default="{}",
        description="JSON string: { 'group_name': true/false } for active group assignment"
    )
    
    bpy.types.Scene.uv_group_texture_expanded = bpy.props.StringProperty(
        name="Group Texture Expanded",
        default="{}",
        description="JSON string storing which texture subsections are expanded in the group popup"
    )

def unregister():
    del bpy.types.Scene.uv_group_texture_expanded
    del bpy.types.Scene.uv_animator_group_toggles
    del bpy.types.Scene.uv_animator_active_group
    del bpy.types.Scene.uv_animator_groups
    del bpy.types.Scene.uv_animator_expanded
    del bpy.types.Scene.active_uv_object_name
    del bpy.types.Object.uv_frame_duration
    del bpy.types.Object.uv_start_frame
    del bpy.types.Object.uv_selected_for_group
    del bpy.types.Object.uv_animator_playback_enabled
    del bpy.types.Object.is_uv_animated
    del bpy.types.Object.uv_texture_items
    del bpy.types.Object.uv_animation_frames
    bpy.utils.unregister_class(UVTextureItem)
    bpy.utils.unregister_class(UVAnimationFrameItem)