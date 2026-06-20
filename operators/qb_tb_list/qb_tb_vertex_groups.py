"""
QB/TB Vertex Groups Operators
Operators for creating vertex groups for each detected block
Validate vertex groups quadblock/triblock
"""

import bpy
import bmesh
from collections import defaultdict
from mathutils import Vector

from ...utils.qb_tb_validator.qb_tb_validation import (
    get_faces_of_vertex_group,
    analyze_faces_for_block
)
from ...utils.range_box.range_utils import get_range_dimensions


class LIST_OT_CreateBlockVertexGroups(bpy.types.Operator):
    """Create individual vertex groups for each quadblock and triblock"""
    bl_idname = "list.create_block_vertex_groups"
    bl_label = "Create Block Vertex Groups"
    bl_description = "Create individual vertex groups for each quadblock and triblock (cleans existing groups to avoid contamination)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object

        if "quadblock_centers" not in obj and "triblock_faces" not in obj:
            self.report({'WARNING'}, "No block data found. Run 'Find All Blocks' first.")
            return {'CANCELLED'}

        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Collect existing groups to preserve names
        existing_qb_groups = {}
        existing_tb_groups = {}

        for vg in obj.vertex_groups:
            if vg.name.startswith("QB_"):
                try:
                    index = int(vg.name[3:])
                    if "quadblock_centers" in obj and index in obj["quadblock_centers"]:
                        existing_qb_groups[index] = vg.name
                except ValueError:
                    continue
            elif vg.name.startswith("TB_"):
                try:
                    index = int(vg.name[3:])
                    if "triblock_faces" in obj and index in obj["triblock_faces"]:
                        existing_tb_groups[index] = vg.name
                except ValueError:
                    continue

        # Remove existing block vertex groups
        groups_to_remove = [vg for vg in obj.vertex_groups if vg.name.startswith(("QB_", "TB_"))]
        removed_count = len(groups_to_remove)
        for vg in groups_to_remove:
            obj.vertex_groups.remove(vg)

        if removed_count > 0:
            self.report({'INFO'}, f"Removed {removed_count} existing block vertex groups")

        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        created_groups = []

        # Quadblocks
        if "quadblock_centers" in obj:
            for center_index in obj["quadblock_centers"]:
                if center_index < len(bm.verts):
                    center_vert = bm.verts[center_index]
                    if not self.is_quadblock_center(center_vert):
                        continue

                    if center_index in existing_qb_groups:
                        group_name = existing_qb_groups[center_index]
                    else:
                        group_name = f"QB_{center_index}"

                    vg = obj.vertex_groups.new(name=group_name)

                    block_vertices = set()
                    block_vertices.add(center_vert)
                    for face in center_vert.link_faces:
                        for vert in face.verts:
                            if vert != center_vert:
                                block_vertices.add(vert)

                    vertex_indices = [v.index for v in block_vertices]
                    if vertex_indices:
                        vg.add(vertex_indices, 1.0, 'ADD')
                    created_groups.append(vg)

        # Triblocks
        if "triblock_faces" in obj:
            for center_face_index in obj["triblock_faces"]:
                if center_face_index < len(bm.faces):
                    center_face = bm.faces[center_face_index]
                    adjacent_faces = self.find_adjacent_triangular_faces(center_face)
                    if not self.is_valid_triblock(center_face, adjacent_faces):
                        continue

                    if center_face_index in existing_tb_groups:
                        group_name = existing_tb_groups[center_face_index]
                    else:
                        group_name = f"TB_{center_face_index}"

                    vg = obj.vertex_groups.new(name=group_name)

                    block_vertices = set()
                    for vert in center_face.verts:
                        block_vertices.add(vert)
                    for face in adjacent_faces:
                        for vert in face.verts:
                            block_vertices.add(vert)

                    vertex_indices = [v.index for v in block_vertices]
                    if vertex_indices:
                        vg.add(vertex_indices, 1.0, 'ADD')
                    created_groups.append(vg)

        bm.free()

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        quad_count = sum(1 for vg in created_groups if vg.name.startswith("QB_"))
        tri_count = sum(1 for vg in created_groups if vg.name.startswith("TB_"))

        self.report({'INFO'}, f"Created {quad_count} quadblocks and {tri_count} triblocks vertex groups")
        return {'FINISHED'}

    def is_quadblock_center(self, center_vert):
        if len(center_vert.link_faces) != 4:
            return False
        for face in center_vert.link_faces:
            if len(face.verts) != 4:
                return False
        all_vertices = set()
        for face in center_vert.link_faces:
            for vert in face.verts:
                all_vertices.add(vert)
        all_vertices.discard(center_vert)
        if len(all_vertices) != 8:
            return False
        direct_connected = set()
        for edge in center_vert.link_edges:
            other_vert = edge.other_vert(center_vert)
            direct_connected.add(other_vert)
        if len(direct_connected) != 4:
            return False
        for vert in direct_connected:
            face_count = 0
            for face in center_vert.link_faces:
                if vert in face.verts:
                    face_count += 1
            if face_count != 2:
                return False
        return True

    def find_adjacent_triangular_faces(self, central_face):
        if len(central_face.verts) != 3:
            return []
        adjacent_faces = []
        for edge in central_face.edges:
            for face in edge.link_faces:
                if face != central_face and len(face.verts) == 3 and face not in adjacent_faces:
                    adjacent_faces.append(face)
        return adjacent_faces

    def is_triangle_face(self, face):
        return len(face.verts) == 3

    def is_valid_triblock(self, central_face, adjacent_faces):
        if len(adjacent_faces) != 3:
            return False
        for face in adjacent_faces:
            if len(face.verts) != 3:
                return False
        for adj_face in adjacent_faces:
            shared_edges = 0
            for edge in adj_face.edges:
                if edge in central_face.edges:
                    shared_edges += 1
            if shared_edges != 1:
                return False
        if self.central_face_has_quad_edge(central_face):
            return False
        return True

    def central_face_has_quad_edge(self, central_face):
        for edge in central_face.edges:
            quad_count = 0
            for face in edge.link_faces:
                if face != central_face and len(face.verts) == 4:
                    quad_count += 1
            if quad_count > 0:
                return True
        return False

    def is_quad_face(self, face):
        return len(face.verts) == 4


class LIST_OT_ClearBlockVertexGroups(bpy.types.Operator):
    """Clear vertex groups of quadblocks and triblocks - selected blocks or all blocks"""
    bl_idname = "list.clear_block_vertex_groups"
    bl_label = "Clear Block Vertex Groups"
    bl_description = "Clear vertex groups for selected blocks or all blocks"
    bl_options = {'REGISTER', 'UNDO'}

    clear_mode: bpy.props.EnumProperty(
        name="Clear Mode",
        items=[
            ('SELECTED', "Clear Selected", "Clear checked items AND selected blocks"),
            ('ALL', "Clear All", "Clear all block vertex groups"),
        ],
        default='SELECTED'
    )

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None)

    def invoke(self, context, event):
        obj = context.edit_object
        has_block_vg = any(vg.name.startswith(("QB_", "TB_")) for vg in obj.vertex_groups)
        if not has_block_vg:
            self.report({'WARNING'}, "No block vertex groups found.")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        obj = context.edit_object
        block_groups = [vg for vg in obj.vertex_groups if vg.name.startswith(("QB_", "TB_"))]
        layout.label(text=f"Found {len(block_groups)} block vertex groups", icon='GROUP_VERTEX')
        layout.separator()
        col = layout.column(align=True)
        col.prop(self, "clear_mode", expand=True)
        box = layout.box()
        if self.clear_mode == 'SELECTED':
            box.label(text="Clears checked items AND selected blocks.", icon='INFO')
        else:
            box.label(text="Removes ALL block vertex groups.", icon='ERROR')
            box.label(text="This action cannot be undone.")
        layout.separator()
        layout.label(text="This action cannot be undone.", icon='QUESTION')

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            if self.clear_mode == 'ALL':
                groups_to_remove = [vg for vg in obj.vertex_groups if vg.name.startswith(("QB_", "TB_"))]
                removed_count = len(groups_to_remove)
                for vg in groups_to_remove:
                    obj.vertex_groups.remove(vg)
                self.report({'INFO'}, f"Removed {removed_count} block vertex groups")
                if "multi_selected_items" in obj:
                    obj["multi_selected_items"].clear()
                return {'FINISHED'}

            # SELECTED mode
            vertex_groups_to_remove = set()

            if "multi_selected_items" in obj and obj["multi_selected_items"]:
                multi = dict(obj["multi_selected_items"])
                for vg_name in multi.keys():
                    if vg_name.startswith(("QB_", "TB_")):
                        vertex_groups_to_remove.add(vg_name)
                if vertex_groups_to_remove:
                    self.report({'INFO'}, f"Adding {len(vertex_groups_to_remove)} checked vertex group(s) from list.")

            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            selected_faces = [f for f in bm.faces if f.select]
            selected_verts = [v for v in bm.verts if v.select]

            if not ("face_to_quadblock" in obj and "face_to_triblock" in obj and "quadblock_centers" in obj):
                self.report({'WARNING'}, "No block data found. Run 'Find All Blocks' first.")
                return {'CANCELLED'}

            face_to_quadblock = obj["face_to_quadblock"]
            face_to_triblock = obj["face_to_triblock"]
            quadblock_centers = obj["quadblock_centers"]

            blocks_to_remove = set()

            for face in selected_faces:
                face_index = str(face.index)
                if face_index in face_to_quadblock:
                    block_id = int(face_to_quadblock[face_index])
                    blocks_to_remove.add(('quadblock', block_id))
                elif face_index in face_to_triblock:
                    block_id = int(face_to_triblock[face_index])
                    blocks_to_remove.add(('triblock', block_id))

            for vert in selected_verts:
                if vert.index in quadblock_centers:
                    blocks_to_remove.add(('quadblock', vert.index))

            if blocks_to_remove:
                for block_type, block_id in blocks_to_remove:
                    if block_type == 'quadblock':
                        vg_name = f"QB_{block_id}"
                    else:
                        vg_name = f"TB_{block_id}"
                    vertex_groups_to_remove.add(vg_name)
                self.report({'INFO'}, f"Adding {len(blocks_to_remove)} block(s) from 3D selection.")

            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='OBJECT')

            if not vertex_groups_to_remove:
                self.report({'WARNING'}, "No vertex groups to clear.")
                return {'CANCELLED'}

            removed_count = 0
            for vg_name in vertex_groups_to_remove:
                if vg_name in obj.vertex_groups:
                    vg = obj.vertex_groups[vg_name]
                    obj.vertex_groups.remove(vg)
                    removed_count += 1

            if "multi_selected_items" in obj:
                multi = dict(obj["multi_selected_items"])
                for vg_name in vertex_groups_to_remove:
                    if vg_name in multi:
                        del multi[vg_name]
                obj["multi_selected_items"] = multi

            self.report({'INFO'}, f"Removed {removed_count} block vertex groups")

        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


class LIST_OT_SelectBlockByVertexGroup(bpy.types.Operator):
    bl_idname = "list.select_block_by_vertex_group"
    bl_label = "Select Block by Vertex Group"
    bl_description = "Select a quadblock or triblock by its vertex group"
    bl_options = {'REGISTER', 'UNDO'}

    vertex_group_name: bpy.props.StringProperty(name="Vertex Group", default="")

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        if self.vertex_group_name:
            return self.execute(context)
        obj = context.edit_object
        block_groups = [vg for vg in obj.vertex_groups if vg.name.startswith(("QB_", "TB_"))]
        if not block_groups:
            self.report({'WARNING'}, "No block vertex groups found.")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        obj = context.edit_object
        block_groups = [vg for vg in obj.vertex_groups if vg.name.startswith(("QB_", "TB_"))]
        block_groups.sort(key=lambda x: x.name)
        layout.prop_search(self, "vertex_group_name", obj, "vertex_groups", text="")

    def execute(self, context):
        obj = context.edit_object
        if not self.vertex_group_name:
            self.report({'WARNING'}, "No vertex group selected.")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')

        if self.vertex_group_name not in obj.vertex_groups:
            self.report({'WARNING'}, f"Vertex group '{self.vertex_group_name}' not found")
            bpy.ops.object.mode_set(mode='EDIT')
            return {'CANCELLED'}

        vg = obj.vertex_groups[self.vertex_group_name]
        vertex_indices = []
        for vert in obj.data.vertices:
            try:
                if vg.weight(vert.index) > 0:
                    vertex_indices.append(vert.index)
            except RuntimeError:
                pass

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        for v in bm.verts:
            v.select = False
        for f in bm.faces:
            f.select = False

        selected_count = 0
        for vert_index in vertex_indices:
            if vert_index < len(bm.verts):
                bm.verts[vert_index].select = True
                selected_count += 1

        if selected_count > 0:
            for face in bm.faces:
                all_selected = all(v.select for v in face.verts)
                if all_selected:
                    face.select = True

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected block from vertex group '{self.vertex_group_name}' ({selected_count} vertices)")
        return {'FINISHED'}


class LIST_OT_ValidateVertexGroups(bpy.types.Operator):
    bl_idname = "list.validate_vertex_groups"
    bl_label = "Validate Groups"
    bl_description = "Analyze each vertex group (QB/TB) and report issues (stored for filtering)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None)

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            mesh = obj.data
            all_vgroups = obj.vertex_groups
            block_group_indices = []
            group_index_to_name = {}
            for idx, vg in enumerate(all_vgroups):
                if vg.name.startswith(("QB_", "TB_")):
                    block_group_indices.append(idx)
                    group_index_to_name[idx] = vg.name

            if not block_group_indices:
                self.report({'WARNING'}, "No block vertex groups found.")
                return {'CANCELLED'}

            vert_groups = [set() for _ in range(len(mesh.vertices))]
            for v in mesh.vertices:
                v_idx = v.index
                for g in v.groups:
                    if g.group in block_group_indices:
                        vert_groups[v_idx].add(g.group)

            group_faces = defaultdict(list)
            for face in mesh.polygons:
                if not face.vertices:
                    continue
                common_groups = set(vert_groups[face.vertices[0]])
                for v_idx in face.vertices[1:]:
                    common_groups.intersection_update(vert_groups[v_idx])
                    if not common_groups:
                        break
                for g_idx in common_groups:
                    group_faces[g_idx].append(face.index)

            def is_group_out_of_range(face_indices):
                dims = get_range_dimensions()
                min_co = Vector(dims['min'])
                max_co = Vector(dims['max'])
                for fi in face_indices:
                    face = mesh.polygons[fi]
                    for v_idx in face.vertices:
                        co = obj.matrix_world @ mesh.vertices[v_idx].co
                        if (co.x < min_co.x or co.x > max_co.x or
                            co.y < min_co.y or co.y > max_co.y or
                            co.z < min_co.z or co.z > max_co.z):
                            return True
                return False

            issues_dict = {}
            total = len(block_group_indices)
            validated = 0

            for g_idx in block_group_indices:
                vg_name = group_index_to_name[g_idx]
                face_indices = group_faces.get(g_idx, [])
                if not face_indices:
                    issues_dict[vg_name] = ["invalid_geometry"]
                else:
                    issues = analyze_faces_for_block(obj, face_indices)
                    if is_group_out_of_range(face_indices):
                        issues.append("out_of_range")
                    issues_dict[vg_name] = issues
                validated += 1
                if validated % 20 == 0:
                    self.report({'INFO'}, f"Validated {validated}/{total} groups")

            obj["vertex_group_issues"] = issues_dict
            self.report({'INFO'}, f"Validation complete. Checked {validated} groups.")

        except Exception as e:
            self.report({'ERROR'}, f"Error during validation: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


classes = [
    LIST_OT_CreateBlockVertexGroups,
    LIST_OT_ClearBlockVertexGroups,
    LIST_OT_SelectBlockByVertexGroup,
    LIST_OT_ValidateVertexGroups,
]