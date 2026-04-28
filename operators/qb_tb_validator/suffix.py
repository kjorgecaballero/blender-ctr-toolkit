import bpy
import time
from bpy.types import Operator
from ...utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type, get_object_issues
from ...utils.qb_tb_validator.qb_tb_naming import build_object_name, clean_object_name


class QB_TB_OT_ObjectQbTbSuffix(Operator):
    bl_idname = "qb_tb.object_qb_tb_suffix"
    bl_label = "Add Suffix"
    bl_description = "Add suffix to objects based on their type (uses current validator option)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        option = context.scene.validator_option

        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=0)
        start_time = time.time()

        all_objects = bpy.data.objects
        count = 0

        for obj in all_objects:
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)

            base_name = clean_object_name(obj.name)

            match = False
            if option == 'QUADBLOCK':
                match = (mesh_type == 'QUADBLOCK')
            elif option == 'TRIBLOCK':
                match = (mesh_type == 'TRIBLOCK')
            elif option == 'INVALID_GEOMETRY':
                match = any(issue in issues for issue in ["ngon", "invalid_geometry", "non_mesh"])
            elif option == 'INVALID_UVS':
                match = "invalid_uvs" in issues
            elif option == 'INVALID_TRIBLOCK_UVS':
                match = "invalid_triblock_uvs" in issues
            elif option == 'DEGENERATED_UVS':
                match = "degenerated_uvs" in issues
            elif option == 'NGONS':
                match = "ngon" in issues
            elif option == 'NON_MESH':
                match = "non_mesh" in issues
            elif option == 'OUT_OF_RANGE':
                match = "out_of_range" in issues
            elif option == 'ALL_INVALID':
                match = bool(issues)

            if match:
                new_name = build_object_name(base_name, mesh_type, issues)
                obj.name = new_name
                count += 1

        elapsed_time = time.time() - start_time
        self.report({'INFO'}, f"Found {count} objects matching '{option}' in {elapsed_time:.2f} seconds.")
        return {'FINISHED'}