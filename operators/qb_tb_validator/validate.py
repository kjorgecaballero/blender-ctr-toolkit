import bpy
import bmesh
from bpy.types import Operator
from bpy.props import BoolProperty
from mathutils import Vector
from ...utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type, get_object_issues
from ...utils.range_box.range_utils import get_range_dimensions

class QB_TB_OT_Validate(Operator):
    bl_idname = "qb_tb.validate"
    bl_label = "Remove"
    bl_description = "Remove objects or faces based on selected options"
    bl_options = {'REGISTER', 'UNDO'}

    remove_invalid_geometry: BoolProperty(
        name="Remove Invalid Geometry",
        description="For objects: remove objects with invalid geometry. For groups: remove faces of groups with invalid geometry",
        default=False
    )
    remove_invalid_uvs: BoolProperty(
        name="Remove Invalid UVs",
        description="For objects: remove objects with invalid UVs. For groups: remove faces of groups with invalid UVs",
        default=False
    )
    remove_degenerated_uvs: BoolProperty(
        name="Remove Degenerated UVs",
        description="For objects: remove objects with degenerated UVs. For groups: remove faces of groups with degenerated UVs",
        default=False
    )
    remove_out_of_range: BoolProperty(
        name="Remove Out of Range",
        description="For objects: remove objects outside range box. For groups: remove faces of groups whose vertices lie outside the range box",
        default=False
    )
    remove_multiple_materials: BoolProperty(
        name="Remove Multiple Materials",
        description="For objects: remove objects with more than one material. For groups: remove faces of groups with multiple materials",
        default=False
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Options", icon='OPTIONS')
        col = box.column(align=True)
        col.prop(self, "remove_invalid_geometry")
        col.prop(self, "remove_invalid_uvs")
        col.prop(self, "remove_degenerated_uvs")
        col.prop(self, "remove_out_of_range")
        col.prop(self, "remove_multiple_materials")

    def execute(self, context):
        scope = context.scene.validator_scope
        if scope == 'OBJECTS':
            return self.execute_objects(context)
        else:
            return self.execute_vertex_groups(context)

    def execute_objects(self, context):
        triblock_count = 0
        quadblock_count = 0
        non_mesh_count = 0
        ngon_count = 0
        geometry_invalid_count = 0
        uvs_invalid_count = 0
        degenerated_uvs_count = 0
        out_of_range_count = 0
        multiple_materials_count = 0

        invalid_geometry_objects = []
        invalid_uvs_objects = []
        degenerated_uvs_objects = []
        out_of_range_objects = []
        multiple_materials_objects = []
        all_invalid_objects = set()

        for obj in list(bpy.data.objects):
            if not obj or obj.name not in bpy.data.objects:
                continue

            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)

            if "non_mesh" in issues:
                non_mesh_count += 1
                invalid_geometry_objects.append(obj)
                all_invalid_objects.add(obj)
            elif "ngon" in issues:
                ngon_count += 1
                invalid_geometry_objects.append(obj)
                all_invalid_objects.add(obj)
            elif "invalid_geometry" in issues:
                geometry_invalid_count += 1
                invalid_geometry_objects.append(obj)
                all_invalid_objects.add(obj)
            else:
                if mesh_type == 'TRIBLOCK':
                    triblock_count += 1
                elif mesh_type == 'QUADBLOCK':
                    quadblock_count += 1

            if "invalid_uvs" in issues:
                uvs_invalid_count += 1
                invalid_uvs_objects.append(obj)
                all_invalid_objects.add(obj)

            if "degenerated_uvs" in issues:
                degenerated_uvs_count += 1
                degenerated_uvs_objects.append(obj)
                all_invalid_objects.add(obj)

            if "invalid_triblock_uvs" in issues:
                uvs_invalid_count += 1
                invalid_uvs_objects.append(obj)
                all_invalid_objects.add(obj)

            if "out_of_range" in issues:
                out_of_range_count += 1
                out_of_range_objects.append(obj)
                all_invalid_objects.add(obj)

            if "multiple_materials" in issues:
                multiple_materials_count += 1
                multiple_materials_objects.append(obj)
                all_invalid_objects.add(obj)

        objects_to_remove = set()

        if self.remove_invalid_geometry:
            objects_to_remove.update(obj for obj in invalid_geometry_objects if obj and obj.name in bpy.data.objects)
        if self.remove_invalid_uvs:
            objects_to_remove.update(obj for obj in invalid_uvs_objects if obj and obj.name in bpy.data.objects)
        if self.remove_degenerated_uvs:
            objects_to_remove.update(obj for obj in degenerated_uvs_objects if obj and obj.name in bpy.data.objects)
        if self.remove_out_of_range:
            objects_to_remove.update(obj for obj in out_of_range_objects if obj and obj.name in bpy.data.objects)
        if self.remove_multiple_materials:
            objects_to_remove.update(obj for obj in multiple_materials_objects if obj and obj.name in bpy.data.objects)

        removed_count = 0
        removed_geometry = 0
        removed_uvs = 0
        removed_degenerated = 0
        removed_out_of_range = 0
        removed_multiple_materials = 0

        for obj in objects_to_remove:
            if obj and obj.name in bpy.data.objects:
                try:
                    issues = get_object_issues(obj)
                    if any(issue in issues for issue in ["non_mesh", "ngon", "invalid_geometry"]):
                        removed_geometry += 1
                    if any(issue in issues for issue in ["invalid_uvs", "invalid_triblock_uvs"]):
                        removed_uvs += 1
                    if "degenerated_uvs" in issues:
                        removed_degenerated += 1
                    if "out_of_range" in issues:
                        removed_out_of_range += 1
                    if "multiple_materials" in issues:
                        removed_multiple_materials += 1

                    bpy.data.objects.remove(obj, do_unlink=True)
                    removed_count += 1
                except ReferenceError:
                    continue
                except Exception as e:
                    print(f"Error removing object {obj.name}: {e}")

        message_parts = []
        message_parts.append(f"Validated: {triblock_count} triblocks, {quadblock_count} quadblocks.")

        if removed_count > 0:
            message_parts.append(f"Removed {removed_count} objects:")
            if removed_geometry > 0:
                message_parts.append(f"- {removed_geometry} invalid geometry")
            if removed_uvs > 0:
                message_parts.append(f"- {removed_uvs} invalid UVs")
            if removed_degenerated > 0:
                message_parts.append(f"- {removed_degenerated} degenerated UVs")
            if removed_out_of_range > 0:
                message_parts.append(f"- {removed_out_of_range} out of range")
            if removed_multiple_materials > 0:
                message_parts.append(f"- {removed_multiple_materials} multiple materials")
        else:
            total_invalid = non_mesh_count + ngon_count + geometry_invalid_count
            message_parts.append(f"Found {total_invalid} invalid objects:")
            message_parts.append(f"- {non_mesh_count} non-mesh")
            message_parts.append(f"- {ngon_count} NGons")
            message_parts.append(f"- {geometry_invalid_count} invalid geometry")
            message_parts.append(f"- {uvs_invalid_count} invalid UVs")
            message_parts.append(f"- {degenerated_uvs_count} degenerated UVs")
            message_parts.append(f"- {out_of_range_count} out of range")
            message_parts.append(f"- {multiple_materials_count} multiple materials")

        self.report({'INFO'}, " ".join(message_parts))
        return {'FINISHED'}

    def execute_vertex_groups(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh object to validate vertex groups.")
            return {'CANCELLED'}

        issues_dict = obj.get("vertex_group_issues", {})
        if not issues_dict:
            self.report({'WARNING'}, "No vertex group issues found. Run 'Issues' first.")
            return {'CANCELLED'}

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        deform_layer = bm.verts.layers.deform.active

        vg_name_to_index = {vg.name: vg.index for vg in obj.vertex_groups}
        block_group_indices = {vg_name_to_index[name] for name in issues_dict.keys() if name in vg_name_to_index}

        group_faces = {idx: [] for idx in block_group_indices}
        if deform_layer:
            for face in bm.faces:
                common_groups = None
                for vert in face.verts:
                    deform = vert[deform_layer]
                    groups_here = {g for g, w in deform.items() if w > 0 and g in block_group_indices}
                    if common_groups is None:
                        common_groups = groups_here
                    else:
                        common_groups.intersection_update(groups_here)
                    if not common_groups:
                        break
                if common_groups:
                    for g_idx in common_groups:
                        group_faces[g_idx].append(face.index)
        bm.free()

        dims = get_range_dimensions()
        min_co = Vector(dims['min'])
        max_co = Vector(dims['max'])

        out_of_range_groups = set()
        for g_idx, face_indices in group_faces.items():
            out_of_range = False
            for fi in face_indices:
                face = mesh.polygons[fi]
                for v_idx in face.vertices:
                    co = obj.matrix_world @ mesh.vertices[v_idx].co
                    if (co.x < min_co.x or co.x > max_co.x or
                        co.y < min_co.y or co.y > max_co.y or
                        co.z < min_co.z or co.z > max_co.z):
                        out_of_range = True
                        break
                if out_of_range:
                    break
            if out_of_range:
                out_of_range_groups.add(g_idx)

        groups_to_remove_faces = set()
        if self.remove_invalid_geometry:
            groups_to_remove_faces.update(
                vg_name_to_index[name] for name, iss in issues_dict.items()
                if 'invalid_geometry' in iss and name in vg_name_to_index
            )
        if self.remove_invalid_uvs:
            groups_to_remove_faces.update(
                vg_name_to_index[name] for name, iss in issues_dict.items()
                if ('invalid_uvs' in iss or 'invalid_triblock_uvs' in iss) and name in vg_name_to_index
            )
        if self.remove_degenerated_uvs:
            groups_to_remove_faces.update(
                vg_name_to_index[name] for name, iss in issues_dict.items()
                if 'degenerated_uvs' in iss and name in vg_name_to_index
            )
        if self.remove_out_of_range:
            groups_to_remove_faces.update(out_of_range_groups)
        if self.remove_multiple_materials:
            groups_to_remove_faces.update(
                vg_name_to_index[name] for name, iss in issues_dict.items()
                if 'multiple_materials' in iss and name in vg_name_to_index
            )

        removed_face_count = 0
        if groups_to_remove_faces:
            original_mode = context.mode
            if original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            deform_layer = bm.verts.layers.deform.active
            if deform_layer:
                vert_to_groups = {}
                for vert in bm.verts:
                    deform = vert[deform_layer]
                    found = set()
                    for g_idx in groups_to_remove_faces:
                        if g_idx in deform and deform[g_idx] > 0:
                            found.add(g_idx)
                    if found:
                        vert_to_groups[vert.index] = found

                faces_to_delete = []
                for face in bm.faces:
                    common_groups = None
                    for vert in face.verts:
                        v_idx = vert.index
                        if v_idx not in vert_to_groups:
                            common_groups = None
                            break
                        groups_here = vert_to_groups[v_idx]
                        if common_groups is None:
                            common_groups = set(groups_here)
                        else:
                            common_groups.intersection_update(groups_here)
                        if not common_groups:
                            break
                    if common_groups:
                        faces_to_delete.append(face)

                if faces_to_delete:
                    bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
                    removed_face_count = len(faces_to_delete)

            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        report = "Vertex groups validation completed."
        if removed_face_count > 0:
            report += f" Removed {removed_face_count} faces from problematic groups."
        self.report({'INFO'}, report)

        return {'FINISHED'}