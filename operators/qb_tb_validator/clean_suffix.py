import bpy
from bpy.types import Operator
from ...utils.qb_tb_validator.qb_tb_naming import clean_object_name


class QB_TB_OT_CleanObjectSuffixes(Operator):
    bl_idname = "qb_tb.clean_object_suffixes"
    bl_label = "Clear Suffix"
    bl_description = "Clear all suffixes from object names"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = 0
        for obj in list(bpy.data.objects):
            if not obj or obj.name not in bpy.data.objects:
                continue

            original_name = obj.name
            obj.name = clean_object_name(obj.name)
            if original_name != obj.name:
                count += 1

        self.report({'INFO'}, f"Reset {count} object names.")
        return {'FINISHED'}