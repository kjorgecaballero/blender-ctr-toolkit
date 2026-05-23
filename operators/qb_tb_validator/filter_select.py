import bpy
from bpy.types import Operator
from ...utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type, get_object_issues

class QB_TB_OT_FilterSelectObjects(Operator):
    bl_idname = "qb_tb.filter_select_objects"
    bl_label = "Select Object Types"
    bl_description = "Select objects based on their type (uses current validator option)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        option = scene.validator_object_option

        for obj in context.selected_objects:
            obj.select_set(False)

        count = 0
        selected_objects = []

        for obj in list(bpy.data.objects):
            select_this = False
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)

            if option == 'ALL_INVALID':
                select_this = bool(issues)
            elif option == 'INVALID_GEOMETRY':
                select_this = any(issue in issues for issue in ["ngon", "invalid_geometry", "non_mesh"])
            elif option == 'INVALID_UVS':
                select_this = "invalid_uvs" in issues
            elif option == 'INVALID_TRIBLOCK_UVS':
                select_this = "invalid_triblock_uvs" in issues
            elif option == 'DEGENERATED_UVS':
                select_this = "degenerated_uvs" in issues
            elif option == 'TRIBLOCK':
                select_this = mesh_type == 'TRIBLOCK'
            elif option == 'QUADBLOCK':
                select_this = mesh_type == 'QUADBLOCK'
            elif option == 'NON_MESH':
                select_this = "non_mesh" in issues
            elif option == 'NGONS':
                select_this = "ngon" in issues
            elif option == 'OUT_OF_RANGE':
                select_this = "out_of_range" in issues
            elif option == 'MULTIPLE_MATERIALS':
                select_this = "multiple_materials" in issues

            if select_this:
                try:
                    if obj and obj.name in bpy.data.objects:
                        obj.select_set(True)
                        selected_objects.append(obj)
                        count += 1
                except Exception as e:
                    print(f"Selection failed for {obj.name if hasattr(obj, 'name') else 'Unknown object'}: {e}")

        if selected_objects and context.view_layer.objects.active is None:
            try:
                context.view_layer.objects.active = selected_objects[0]
            except Exception as e:
                print(f"Failed to set active object: {e}")

        self.report({'INFO'}, f"Selected {count} objects.")
        return {'FINISHED'}