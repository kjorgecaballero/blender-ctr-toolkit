import bpy
from bpy.types import Operator


class QB_TB_OT_ClearVertexGroupIssues(Operator):
    """Clear vertex group issues (warnings) from the active mesh object"""
    bl_idname = "qb_tb.clear_vertex_group_issues"
    bl_label = "Clear Vertex Group Issues"
    bl_description = "Remove all stored vertex group issues from the active mesh object"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and "vertex_group_issues" in obj

    def execute(self, context):
        obj = context.active_object
        if "vertex_group_issues" in obj:
            del obj["vertex_group_issues"]
            self.report({'INFO'}, "Vertex group issues cleared.")
        else:
            self.report({'INFO'}, "No vertex group issues to clear.")
        return {'FINISHED'}