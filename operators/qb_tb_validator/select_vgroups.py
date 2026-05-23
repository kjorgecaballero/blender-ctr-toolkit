import bpy
from bpy.types import Operator


class QB_TB_OT_SelectVertexGroupsByType(Operator):
    bl_idname = "qb_tb.select_vertex_groups_by_type"
    bl_label = "Select Vertex Groups by Type"
    bl_description = "Mark vertex groups in the navigation list and select them in 3D view according to the selected validator option"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        scene = context.scene
        option = scene.validator_vertex_group_option

        if option in {'NGONS', 'NON_MESH'}:
            self.report({'INFO'}, f"Option '{option}' is not available for vertex groups.")
            return {'CANCELLED'}

        if "vertex_group_issues" not in obj:
            try:
                bpy.ops.list.validate_vertex_groups()
            except Exception as e:
                self.report({'ERROR'}, f"Could not validate vertex groups: {e}")
                return {'CANCELLED'}

        issues_dict = dict(obj.get("vertex_group_issues", {}))

        matched_groups = []
        for vg in obj.vertex_groups:
            name = vg.name
            if not (name.startswith("QB_") or name.startswith("TB_")):
                continue

            issues = issues_dict.get(name, [])
            is_valid_qb = 'quadblock' in issues and 'invalid_geometry' not in issues
            is_valid_tb = 'triblock' in issues and 'invalid_geometry' not in issues

            if option == 'QUADBLOCK':
                match = is_valid_qb
            elif option == 'TRIBLOCK':
                match = is_valid_tb
            elif option == 'INVALID_GEOMETRY':
                match = 'invalid_geometry' in issues
            elif option == 'INVALID_UVS':
                match = 'invalid_uvs' in issues
            elif option == 'INVALID_TRIBLOCK_UVS':
                match = 'invalid_triblock_uvs' in issues
            elif option == 'DEGENERATED_UVS':
                match = 'degenerated_uvs' in issues
            elif option == 'OUT_OF_RANGE':
                match = 'out_of_range' in issues
            elif option == 'MULTIPLE_MATERIALS':
                match = 'multiple_materials' in issues
            elif option == 'ALL_INVALID':
                other_issues = [iss for iss in issues if iss not in ('quadblock', 'triblock')]
                match = bool(other_issues)
            else:
                match = False

            if match:
                matched_groups.append(name)

        if not matched_groups:
            self.report({'INFO'}, f"No vertex groups match the filter '{option}'.")
            return {'FINISHED'}

        if "multi_selected_items" in obj:
            obj["multi_selected_items"].clear()
        else:
            obj["multi_selected_items"] = {}

        multi = obj["multi_selected_items"]
        for name in matched_groups:
            multi[name] = True
        obj["multi_selected_items"] = multi

        scene.list_display_type = 'VERTEX_GROUPS'

        original_mode = context.mode
        if original_mode != 'EDIT_MESH':
            try:
                bpy.ops.object.mode_set(mode='EDIT')
            except Exception as e:
                self.report({'WARNING'}, f"Could not enter edit mode: {e}")
                self.report({'INFO'}, f"Marked {len(matched_groups)} vertex groups matching filter '{option}' in the checklist.")
                return {'FINISHED'}

        try:
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.list.select_multi_checked(select_all=False, clear_existing=True)
            self.report({'INFO'}, f"Marked and selected {len(matched_groups)} vertex groups matching filter '{option}'. List switched to Vertex Groups mode.")
        except Exception as e:
            self.report({'WARNING'}, f"Could not select geometry: {e}")
            self.report({'INFO'}, f"Marked {len(matched_groups)} vertex groups matching filter '{option}' in the checklist.")
        finally:
            if original_mode != 'EDIT_MESH':
                bpy.ops.object.mode_set(mode=original_mode)

        return {'FINISHED'}