import bpy
from .uv_controls import *
from .uv_groups import *
from .uv_collapse import *
from .uv_textures import *
from .uv_animation import *
from .uv_export import *
from .uv_interpolate import *

classes = [
    UV_OT_ToggleExpand,
    UV_OT_TogglePlayback,
    UV_OT_ToggleGroupSelection,
    UV_OT_SetActiveUVObject,
    UV_OT_SetStartFrame,
    UV_OT_SetFrameDuration,
    UV_OT_ToggleGroupActive,
    UV_OT_GroupManagementDialog,
    UV_OT_NewGroupSimple,
    UV_OT_DeleteGroupSimple,
    UV_OT_AddToGroup,
    UV_OT_RemoveFromGroup,
    UV_OT_ClearActiveGroupFilter,
    UV_OT_GroupSetFrameDuration,
    UV_OT_ToggleGroupSection,
    UV_OT_ToggleTextureSection,
    UV_OT_ToggleTextureSubsection,
    UV_OT_ShowFrameTexturePopup,
    UV_OT_ChangeTexturePath,
    UV_OT_GroupTextureSettings,
    UV_OT_GroupToggleTextureSubsection,
    UV_OT_GroupChangeTextureImage,
    UV_OT_NewAnimation,
    UV_OT_NewAnimationFromConstants,
    UV_OT_AssignFrame,
    UV_OT_DeleteFrame,
    UV_OT_PlayPreview,
    UV_OT_StopPreview,
    UV_OT_DeleteAnimation,
    UV_OT_ToggleGroupPlayback,
    UV_OT_ExportAnimation,
    UV_OT_AutoGroupCollections,
    UV_OT_AutoFindCollections,
    UV_OT_AutoSelectSecondaryTexture,
    UV_OT_AutoAssignInterpolation,
    UV_OT_AutoSelectAnimation,
    UV_MT_AutoAnimationMenu,
    UV_OT_ScanTimeline,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)