import bpy
import time
import bmesh
from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty
from mathutils import Vector

from ...utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type, get_object_issues
from ...utils.qb_tb_validator.qb_tb_naming import build_object_name, clean_object_name
from ...utils.range_box.range_utils import get_range_dimensions


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
                match = any(issue in issues for issue in ["invalid_uvs", "invalid_triblock_uvs"])
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


# -------------------------------------------------------------------
# Unified Validate Operator (Objects or Vertex Groups)
# -------------------------------------------------------------------
class QB_TB_OT_Validate(Operator):
    bl_idname = "qb_tb.validate"
    bl_label = "Validate"
    bl_description = "Validate objects or vertex groups with common options"
    bl_options = {'REGISTER', 'UNDO'}

    scope: EnumProperty(
        name="Scope",
        description="What to validate",
        items=[
            ('OBJECTS', "Objects", "Validate all objects in the scene"),
            ('VERTEX_GROUPS', "Vertex Groups", "Validate vertex groups of active mesh object"),
        ],
        default='OBJECTS'
    )

    # Common options (labels will be adapted in draw)
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
    add_suffixes_or_checklist: BoolProperty(
        name="Add Suffixes / Add to Checklist",
        description="For objects: add suffixes to names. For groups: mark groups in the multi-selection checklist",
        default=True
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout

        # Scope selection (mutually exclusive)
        row = layout.row(align=True)
        row.prop(self, "scope", expand=True)

        layout.separator()

        # Options box
        box = layout.box()
        box.label(text="Options", icon='OPTIONS')
        col = box.column(align=True)

        # Adapt labels based on scope
        if self.scope == 'OBJECTS':
            col.prop(self, "remove_invalid_geometry", text="Remove Invalid Geometry Objects")
            col.prop(self, "remove_invalid_uvs", text="Remove Invalid UVs Objects")
            col.prop(self, "remove_degenerated_uvs", text="Remove Degenerated UVs Objects")
            col.prop(self, "remove_out_of_range", text="Remove Out of Range Objects")
            col.separator()
            col.prop(self, "add_suffixes_or_checklist", text="Add Suffixes to Objects")
        else:  # VERTEX_GROUPS
            col.prop(self, "remove_invalid_geometry", text="Remove Faces with Invalid Geometry")
            col.prop(self, "remove_invalid_uvs", text="Remove Faces with Invalid UVs")
            col.prop(self, "remove_degenerated_uvs", text="Remove Faces with Degenerated UVs")
            col.prop(self, "remove_out_of_range", text="Remove Faces Out of Range")
            col.separator()
            col.prop(self, "add_suffixes_or_checklist", text="Add to Checklist (mark in list)")

        # Contextual notes
        if self.scope == 'VERTEX_GROUPS':
            box = layout.box()
            box.label(text="Note for Vertex Groups:", icon='INFO')
            box.label(text="• 'Remove' options will delete the faces belonging to those groups.")
            box.label(text="• 'Add to Checklist' will check the groups in the Navigation List.")
            box.label(text="• Validation results always appear in Navigation List (Edit Mode).")

    def execute(self, context):
        if self.scope == 'OBJECTS':
            return self.execute_objects(context)
        else:
            return self.execute_vertex_groups(context)

    # -----------------------------------------------------------------
    # Object validation (existing logic, adapted)
    # -----------------------------------------------------------------
    def execute_objects(self, context):
        triblock_count = 0
        quadblock_count = 0
        non_mesh_count = 0
        ngon_count = 0
        geometry_invalid_count = 0
        uvs_invalid_count = 0
        degenerated_uvs_count = 0
        out_of_range_count = 0

        invalid_geometry_objects = []
        invalid_uvs_objects = []
        degenerated_uvs_objects = []
        out_of_range_objects = []
        all_invalid_objects = set()
        
        for obj in list(bpy.data.objects):
            if not obj or obj.name not in bpy.data.objects:
                continue
                
            mesh_type = get_mesh_type(obj) if obj.type == 'MESH' else None
            issues = get_object_issues(obj)
            
            if self.add_suffixes_or_checklist:
                base_name = clean_object_name(obj.name)
                new_name = build_object_name(base_name, mesh_type, issues)
                obj.name = new_name
            
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

        objects_to_remove = set()
        
        if self.remove_invalid_geometry:
            objects_to_remove.update(obj for obj in invalid_geometry_objects 
                                   if obj and obj.name in bpy.data.objects)
                    
        if self.remove_invalid_uvs:
            objects_to_remove.update(obj for obj in invalid_uvs_objects 
                                   if obj and obj.name in bpy.data.objects)
                    
        if self.remove_degenerated_uvs:
            objects_to_remove.update(obj for obj in degenerated_uvs_objects 
                                   if obj and obj.name in bpy.data.objects)

        if self.remove_out_of_range:
            objects_to_remove.update(obj for obj in out_of_range_objects 
                                   if obj and obj.name in bpy.data.objects)

        removed_count = 0
        removed_geometry = 0
        removed_uvs = 0
        removed_degenerated = 0
        removed_out_of_range = 0
        
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
                        
                    bpy.data.objects.remove(obj, do_unlink=True)
                    removed_count += 1
                except ReferenceError:
                    continue
                except Exception as e:
                    print(f"Error removing object {obj.name}: {e}")

        message_parts = []
        suffix_status = "renamed" if self.add_suffixes_or_checklist else "validated"
        message_parts.append(f"{suffix_status.capitalize()}: {triblock_count} triblocks, {quadblock_count} quadblocks.")
        
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
        else:
            total_invalid = non_mesh_count + ngon_count + geometry_invalid_count
            message_parts.append(f"Found {total_invalid} invalid objects:")
            message_parts.append(f"- {non_mesh_count} non-mesh")
            message_parts.append(f"- {ngon_count} NGons")
            message_parts.append(f"- {geometry_invalid_count} invalid geometry")
            message_parts.append(f"- {uvs_invalid_count} invalid UVs")
            message_parts.append(f"- {degenerated_uvs_count} degenerated UVs")
            message_parts.append(f"- {out_of_range_count} out of range")

        self.report({'INFO'}, " ".join(message_parts))
        return {'FINISHED'}

    # -----------------------------------------------------------------
    # Vertex group validation with face removal and checklist marking
    # Now includes out-of-range detection and removal.
    # -----------------------------------------------------------------
    def execute_vertex_groups(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No active mesh object to validate vertex groups.")
            return {'CANCELLED'}

        # First, run the validation to populate vertex_group_issues
        try:
            bpy.ops.list.validate_vertex_groups()
        except Exception as e:
            self.report({'ERROR'}, f"Vertex group validation failed: {e}")
            return {'CANCELLED'}

        issues_dict = obj.get("vertex_group_issues", {})
        if not issues_dict:
            self.report({'INFO'}, "No vertex group issues found.")
            return {'FINISHED'}

        # --- Build a mapping from group indices to face indices (only for groups in issues_dict) ---
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        deform_layer = bm.verts.layers.deform.active

        # Map group names to indices for groups that have issues
        vg_name_to_index = {vg.name: vg.index for vg in obj.vertex_groups}
        block_group_indices = {vg_name_to_index[name] for name in issues_dict.keys() if name in vg_name_to_index}

        # Dictionary: group index -> list of face indices fully belonging to that group
        group_faces = {idx: [] for idx in block_group_indices}
        if deform_layer:
            for face in bm.faces:
                # Gather groups that all vertices of this face belong to (with weight > 0)
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

        # --- Determine which groups are out of range ---
        dims = get_range_dimensions()
        min_co = Vector(dims['min'])
        max_co = Vector(dims['max'])

        out_of_range_groups = set()
        for g_idx, face_indices in group_faces.items():
            # For each group, check if any face has a vertex outside the range box
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

        # --- Collect groups to remove faces from based on options ---
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

        # --- Remove faces (if any groups to process) ---
        removed_face_count = 0
        if groups_to_remove_faces:
            # Store original mode and switch to OBJECT for mesh manipulation
            original_mode = context.mode
            if original_mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            # Map group indices back to names (needed for later checklist update)
            index_to_name = {idx: name for name, idx in vg_name_to_index.items()}

            # Use BMesh to access deform layer efficiently
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            deform_layer = bm.verts.layers.deform.active
            if deform_layer:
                # Build a map: vertex index -> set of groups (only those we care about)
                vert_to_groups = {}
                for vert in bm.verts:
                    deform = vert[deform_layer]
                    found = set()
                    for g_idx in groups_to_remove_faces:
                        if g_idx in deform and deform[g_idx] > 0:
                            found.add(g_idx)
                    if found:
                        vert_to_groups[vert.index] = found

                # Find faces where all vertices belong to at least one of the target groups
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

            # Write back to mesh
            bm.to_mesh(mesh)
            bm.free()
            mesh.update()

            # Restore original mode
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        # --- Add to checklist ---
        checked_count = 0
        if self.add_suffixes_or_checklist:
            all_issue_groups = set(issues_dict.keys())
            if all_issue_groups:
                if "multi_selected_items" not in obj:
                    obj["multi_selected_items"] = {}
                multi = obj["multi_selected_items"]
                for vg_name in all_issue_groups:
                    if vg_name not in multi:
                        multi[vg_name] = True
                        checked_count += 1
                obj["multi_selected_items"] = multi

        # Final report
        report = "Vertex groups validation completed."
        if removed_face_count > 0:
            report += f" Removed {removed_face_count} faces from problematic groups."
        if checked_count > 0:
            report += f" Added {checked_count} groups to checklist."
        self.report({'INFO'}, report)

        return {'FINISHED'}


class QB_TB_OT_FilterSelectObjects(Operator):
    bl_idname = "qb_tb.filter_select_objects"
    bl_label = "Select Object Types"
    bl_description = "Select objects based on their type (uses current validator option)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        option = context.scene.validator_option

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
                select_this = any(issue in issues for issue in ["invalid_uvs", "invalid_triblock_uvs"])
            elif option == 'DEGENERATED_UVS':
                select_this = "degenerated_uvs" in issues
            elif option == 'INVALID_TRIBLOCK_UVS':
                select_this = "invalid_triblock_uvs" in issues
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


class QB_TB_OT_CleanObjectSuffixes(Operator):
    bl_idname = "qb_tb.clean_object_suffixes"
    bl_label = "Clean Suffix"
    bl_description = "Clean all suffixes from object names"
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


def register():
    bpy.utils.register_class(QB_TB_OT_ObjectQbTbSuffix)
    bpy.utils.register_class(QB_TB_OT_Validate)
    bpy.utils.register_class(QB_TB_OT_FilterSelectObjects)
    bpy.utils.register_class(QB_TB_OT_CleanObjectSuffixes)


def unregister():
    bpy.utils.unregister_class(QB_TB_OT_CleanObjectSuffixes)
    bpy.utils.unregister_class(QB_TB_OT_FilterSelectObjects)
    bpy.utils.unregister_class(QB_TB_OT_Validate)
    bpy.utils.unregister_class(QB_TB_OT_ObjectQbTbSuffix)