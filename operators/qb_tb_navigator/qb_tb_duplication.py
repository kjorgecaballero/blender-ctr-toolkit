"""
QB/TB Duplication Operators
Operators for duplicating blocks by group
Restored: duplicate_quadblocks_by_group and duplicate_triblocks_by_group
These are called by duplicate_all_blocks_by_group.
"""

import bpy
import bmesh

from ...utils import qb_tb_navigator


class NAVIGATOR_OT_DuplicateQuadblocksByGroup(bpy.types.Operator):
    bl_idname = "navigator.duplicate_quadblocks_by_group"
    bl_label = "Duplicate Quadblocks by Group"
    bl_description = "Duplicate quadblocks by group for massive duplication"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object
        original_obj_name = obj.name

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        if "quad_group_members" not in obj:
            self.report({'WARNING'}, "No quadblock groups found. Run Find Blocks first.")
            return {'CANCELLED'}

        quad_group_members = obj["quad_group_members"]

        if not quad_group_members:
            self.report({'WARNING'}, "No quadblock groups to duplicate")
            return {'CANCELLED'}

        collection_name = "Duplicated_Blocks"
        if collection_name not in bpy.data.collections:
            new_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(new_collection)

        target_collection = bpy.data.collections[collection_name]

        duplicated_objects = []

        for group_num_str, member_indices in quad_group_members.items():
            group_num = int(group_num_str)

            bpy.ops.mesh.select_all(action='DESELECT')
            bmesh.update_edit_mesh(obj.data)

            if "quadblock_faces_map" in obj:
                quadblock_faces_map = obj["quadblock_faces_map"]
                faces_to_select = []

                for vert_index in member_indices:
                    if str(vert_index) in quadblock_faces_map:
                        faces_to_select.extend(quadblock_faces_map[str(vert_index)])

                for face_index in set(faces_to_select):
                    if face_index < len(bm.faces):
                        bm.faces[face_index].select = True
            else:
                faces_to_duplicate = set()
                for vert_index in member_indices:
                    if vert_index >= len(bm.verts):
                        continue

                    center_vert = bm.verts[vert_index]
                    if not qb_tb_navigator.is_quadblock_center(center_vert):
                        continue

                    for face in center_vert.link_faces:
                        faces_to_duplicate.add(face)

                for face in faces_to_duplicate:
                    face.select = True

            bmesh.update_edit_mesh(obj.data)

            selected_faces = [f for f in bm.faces if f.select]
            if not selected_faces:
                continue

            bpy.ops.mesh.duplicate()

            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()

            bpy.ops.mesh.separate(type='SELECTED')

            bpy.ops.object.mode_set(mode='OBJECT')

            new_objects = [o for o in context.selected_objects if o.name != original_obj_name]

            if new_objects:
                new_obj = new_objects[0]

                new_obj.name = f"{original_obj_name}_Quad_Group_{group_num}"

                for col in new_obj.users_collection:
                    col.objects.unlink(new_obj)
                target_collection.objects.link(new_obj)

                duplicated_objects.append(new_obj)

                obj.select_set(True)
                context.view_layer.objects.active = obj

            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

        obj.select_set(True)
        context.view_layer.objects.active = obj

        total_quadblocks = sum(len(members) for members in quad_group_members.values())
        self.report({'INFO'}, f"Duplicated {total_quadblocks} quadblocks in {len(quad_group_members)} groups")

        return {'FINISHED'}


class NAVIGATOR_OT_DuplicateTriblocksByGroup(bpy.types.Operator):
    bl_idname = "navigator.duplicate_triblocks_by_group"
    bl_label = "Duplicate Triblocks by Group"
    bl_description = "Duplicate triblocks by group for massive duplication"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object
        original_obj_name = obj.name

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        if "tri_group_members" not in obj:
            self.report({'WARNING'}, "No triblock groups found. Run Find Blocks first.")
            return {'CANCELLED'}

        tri_group_members = obj["tri_group_members"]

        if not tri_group_members:
            self.report({'WARNING'}, "No triblock groups to duplicate")
            return {'CANCELLED'}

        collection_name = "Duplicated_Blocks"
        if collection_name not in bpy.data.collections:
            new_collection = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(new_collection)

        target_collection = bpy.data.collections[collection_name]

        duplicated_objects = []

        for group_num_str, member_indices in tri_group_members.items():
            group_num = int(group_num_str)

            bpy.ops.mesh.select_all(action='DESELECT')
            bmesh.update_edit_mesh(obj.data)

            if "triblock_faces_map" in obj:
                triblock_faces_map = obj["triblock_faces_map"]
                faces_to_select = []

                for face_index in member_indices:
                    if str(face_index) in triblock_faces_map:
                        faces_to_select.extend(triblock_faces_map[str(face_index)])

                for face_index in set(faces_to_select):
                    if face_index < len(bm.faces):
                        bm.faces[face_index].select = True
            else:
                faces_to_duplicate = set()
                for face_index in member_indices:
                    if face_index >= len(bm.faces):
                        continue

                    center_face = bm.faces[face_index]

                    adjacent_faces = qb_tb_navigator.find_adjacent_triangular_faces(center_face)
                    if not qb_tb_navigator.is_valid_triblock(center_face, adjacent_faces):
                        continue

                    faces_to_duplicate.add(center_face)
                    for face in adjacent_faces:
                        faces_to_duplicate.add(face)

                for face in faces_to_duplicate:
                    face.select = True

            bmesh.update_edit_mesh(obj.data)

            selected_faces = [f for f in bm.faces if f.select]
            if not selected_faces:
                continue

            bpy.ops.mesh.duplicate()

            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()

            bpy.ops.mesh.separate(type='SELECTED')

            bpy.ops.object.mode_set(mode='OBJECT')

            new_objects = [o for o in context.selected_objects if o.name != original_obj_name]

            if new_objects:
                new_obj = new_objects[0]

                new_obj.name = f"{original_obj_name}_Tri_Group_{group_num}"

                for col in new_obj.users_collection:
                    col.objects.unlink(new_obj)
                target_collection.objects.link(new_obj)

                duplicated_objects.append(new_obj)

                obj.select_set(True)
                context.view_layer.objects.active = obj

            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

        obj.select_set(True)
        context.view_layer.objects.active = obj

        total_triblocks = sum(len(members) for members in tri_group_members.values())
        self.report({'INFO'}, f"Duplicated {total_triblocks} triblocks in {len(tri_group_members)} groups")

        return {'FINISHED'}


class NAVIGATOR_OT_DuplicateAllBlocksByGroup(bpy.types.Operator):
    bl_idname = "navigator.duplicate_all_blocks_by_group"
    bl_label = "Duplicate ALL Blocks by Group"
    bl_description = "Duplicate all quadblocks and triblocks by group"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object

        if "quadblock_centers" not in obj and "triblock_faces" not in obj:
            self.report({'WARNING'}, "No blocks found. Run Find Blocks first.")
            return {'CANCELLED'}

        quadblock_count = 0
        triblock_count = 0

        if "quad_group_members" in obj and obj["quad_group_members"]:
            bpy.ops.navigator.duplicate_quadblocks_by_group()
            quad_group_members = obj["quad_group_members"]
            quadblock_count = sum(len(members) for members in quad_group_members.values())

        if "tri_group_members" in obj and obj["tri_group_members"]:
            bpy.ops.navigator.duplicate_triblocks_by_group()
            tri_group_members = obj["tri_group_members"]
            triblock_count = sum(len(members) for members in tri_group_members.values())

        self.report({'INFO'}, f"Duplicated {quadblock_count} quadblocks and {triblock_count} triblocks by group")
        return {'FINISHED'}


classes = [
    NAVIGATOR_OT_DuplicateQuadblocksByGroup,
    NAVIGATOR_OT_DuplicateTriblocksByGroup,
    NAVIGATOR_OT_DuplicateAllBlocksByGroup,
]