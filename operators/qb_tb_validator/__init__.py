import bpy
from .suffix import QB_TB_OT_ObjectQbTbSuffix
from .validate import QB_TB_OT_Validate
from .filter_select import QB_TB_OT_FilterSelectObjects
from .clean_suffix import QB_TB_OT_CleanObjectSuffixes
from .clear_issues import QB_TB_OT_ClearVertexGroupIssues
from .select_vgroups import QB_TB_OT_SelectVertexGroupsByType

classes = (
    QB_TB_OT_ObjectQbTbSuffix,
    QB_TB_OT_Validate,
    QB_TB_OT_FilterSelectObjects,
    QB_TB_OT_CleanObjectSuffixes,
    QB_TB_OT_ClearVertexGroupIssues,
    QB_TB_OT_SelectVertexGroupsByType,
)

def register_qb_tb():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister_qb_tb():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)