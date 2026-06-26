"""
QB/TB Duplication Operators
Operators for duplicating blocks by group
"""

import bpy
import bmesh
import os
import re

from ...utils import qb_tb_navigator
from ...utils.compat import (
    execute_obj_export,
    execute_obj_import,
    ensure_objects_in_view_layer,
    cleanup_temporarily_linked_objects
)
from ..qb_tb_export.export_manager import ExportManager
from ..qb_tb_export.export_settings import ExportSettings
from ..qb_tb_export.texture_handler import TextureHandler
from ...utils.export_helpers import (
    temporary_disable_ps1_render,
    restore_ps1_render,
    get_vertex_snap_modifiers,
    disable_vertex_snap_modifiers,
    restore_vertex_snap_modifiers
)
from .multiple_objects_helper import (
    gather_objects_navigation_data,
    join_selected_objects,
    restore_original_objects
)


_temp_duplicated_objects = []


def strip_blender_suffix(name):
    return re.sub(r'\.\d+$', '', name)


def move_object_to_collection_manual(obj, target_collection):
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    target_collection.objects.link(obj)


def clean_material_slots(obj):
    """Remove unused material slots from the object."""
    if obj.type != 'MESH':
        return
    used_indices = set()
    for poly in obj.data.polygons:
        used_indices.add(poly.material_index)
    # Remove slots in reverse order to avoid index shifting
    for i in range(len(obj.material_slots) - 1, -1, -1):
        if i not in used_indices:
            obj.data.materials.pop(index=i)
    obj.data.update()


def export_duplicated_objects_to_path(context, objects, obj_filepath, texture_dir, settings):
    if not objects:
        return False

    previous_mode = context.mode
    if previous_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    original_active = context.view_layer.objects.active
    original_selection = context.selected_objects[:]

    # Ensure all objects are in the view layer (Blender 5.0)
    temporarily_linked = ensure_objects_in_view_layer(objects, context)

    try:
        for ob in bpy.data.objects:
            ob.select_set(False)
        for obj in objects:
            obj.select_set(True)
        if objects:
            context.view_layer.objects.active = objects[0]

        class TempExportProps:
            def __init__(self):
                self.filepath = obj_filepath
                self.use_selection = True
                self.export_colors = settings.export_colors
                self.export_textures = settings.include_textures
                self.path_mode = settings.path_mode
                self.global_scale = settings.global_scale
                self.export_quadblocks = True
                self.export_triblocks = True
                self.export_invalid_uvs = True
                self.export_degenerated_uvs = True
                self.apply_modifiers = False
                self.separate_loose_parts = False

        temp_props = TempExportProps()

        if settings.include_textures and texture_dir:
            try:
                os.makedirs(texture_dir, exist_ok=True)
                texture_handler = TextureHandler()
                texture_handler.copy_textures_to_folder(texture_dir, objects)
            except Exception as e:
                print(f"Error copying textures: {e}")

        result = execute_obj_export(temp_props, objects)

    finally:
        # Clean up temporary view‑layer links
        cleanup_temporarily_linked_objects(temporarily_linked, context)

        # Restore selection and active object
        for ob in bpy.data.objects:
            ob.select_set(False)
        for obj in original_selection:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if original_active and original_active.name in bpy.data.objects:
            context.view_layer.objects.active = original_active

        if previous_mode != 'OBJECT' and previous_mode is not None:
            try:
                bpy.ops.object.mode_set(mode=previous_mode)
            except:
                pass

    return 'FINISHED' in result


class NAVIGATOR_OT_DuplicateQuadblocksByGroup(bpy.types.Operator):
    bl_idname = "navigator.duplicate_quadblocks_by_group"
    bl_label = "Duplicate Quadblocks by Group"
    bl_description = "Duplicate quadblocks by group for massive duplication"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        global _temp_duplicated_objects
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

                move_object_to_collection_manual(new_obj, target_collection)

                duplicated_objects.append(new_obj)
                _temp_duplicated_objects.append(new_obj.name)

                for ob in bpy.data.objects:
                    ob.select_set(False)
                obj.select_set(True)
                context.view_layer.objects.active = obj

            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

        for ob in bpy.data.objects:
            ob.select_set(False)
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
        global _temp_duplicated_objects
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

                move_object_to_collection_manual(new_obj, target_collection)

                duplicated_objects.append(new_obj)
                _temp_duplicated_objects.append(new_obj.name)

                for ob in bpy.data.objects:
                    ob.select_set(False)
                obj.select_set(True)
                context.view_layer.objects.active = obj

            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

        for ob in bpy.data.objects:
            ob.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        total_triblocks = sum(len(members) for members in tri_group_members.values())
        self.report({'INFO'}, f"Duplicated {total_triblocks} triblocks in {len(tri_group_members)} groups")

        return {'FINISHED'}


class NAVIGATOR_OT_DuplicateAllBlocksByGroup(bpy.types.Operator):
    bl_idname = "navigator.duplicate_all_blocks_by_group"
    bl_label = "Duplicate ALL Blocks by Group"
    bl_description = "Duplicate all quadblocks and triblocks by group, export to OBJ, and import back (optimized)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH' and context.edit_object:
            return True
        if context.mode == 'OBJECT' and context.selected_objects:
            return any(obj.type == 'MESH' for obj in context.selected_objects)
        return False

    directory: bpy.props.StringProperty(
        name="Export Directory",
        description="Choose a directory to export duplicated blocks",
        subtype='DIR_PATH',
        default=""
    )

    multiple_objects: bpy.props.BoolProperty(
        name="Multiple Objects",
        description="Join selected objects before duplication (requires OBJECT mode)",
        default=False,
    )

    def _sanitize_material_suffixes(self, obj):
        from ...utils.material_utils import rename_base_material_family
        renamed_count = 0
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            old_name = mat.name
            match = re.search(r'\.(\d{1,3})$', old_name)
            if match:
                new_name = re.sub(r'\.(\d{1,3})$', r'_\1', old_name)
                original_new = new_name
                counter = 1
                while new_name in bpy.data.materials and new_name != old_name:
                    new_name = f"{original_new}_{counter:03d}"
                    counter += 1
                if new_name != old_name:
                    success, msg, updated = rename_base_material_family(obj, old_name, new_name)
                    if success:
                        self.report({'INFO'}, msg)
                        renamed_count += 1
                    else:
                        self.report({'WARNING'}, f"Could not rename material '{old_name}': {msg}")
        if renamed_count:
            self.report({'INFO'}, f"Renamed {renamed_count} material family(s) in {obj.name}")

    def _clear_processed_collection(self, context, collection_name="Processed_Blocks"):
        col = bpy.data.collections.get(collection_name)
        if not col:
            return
        objects = list(col.objects)
        if not objects:
            return
        for obj in objects:
            for coll in list(obj.users_collection):
                coll.objects.unlink(obj)
        bpy.ops.outliner.orphans_purge()
        bpy.data.collections.remove(col)
        print(f"[Processed_Blocks] Cleared {len(objects)} old objects")

    def _move_to_processed_collection(self, context, objects, collection_name="Processed_Blocks"):
        col = bpy.data.collections.get(collection_name)
        if not col:
            col = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(col)
        for obj in objects:
            for coll in list(obj.users_collection):
                coll.objects.unlink(obj)
            col.objects.link(obj)
        print(f"[Processed_Blocks] Moved {len(objects)} objects to collection '{collection_name}'")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        global _temp_duplicated_objects

        self._clear_processed_collection(context, "Processed_Blocks")
        _temp_duplicated_objects = []

        # Handle case: user is in EDIT mode but has "Multiple Objects" checked.
        # Automatically switch to OBJECT mode and select all visible mesh objects.

        if context.mode == 'EDIT_MESH' and self.multiple_objects:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.visible_get() and not obj.hide_viewport:
                    obj.select_set(True)
            if not context.selected_objects:
                active = context.active_object
                if active and active.type == 'MESH':
                    active.select_set(True)
                else:
                    self.report({'ERROR'}, "No mesh objects found to join.")
                    return {'CANCELLED'}

        # Determine source object
        source_obj = None
        nav_data = None
        collections_data = None
        if context.mode == 'EDIT_MESH':
            source_obj = context.edit_object
            if source_obj is None:
                self.report({'ERROR'}, "No active mesh object in edit mode.")
                return {'CANCELLED'}
        else:  # OBJECT mode
            if self.multiple_objects:
                # Sanitize materials on each selected object BEFORE gathering nav data
                selected_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
                for obj in selected_objs:
                    self._sanitize_material_suffixes(obj)

                nav_data, summary_lines, collections_data = gather_objects_navigation_data(context)
                for line in summary_lines:
                    self.report({'INFO'}, line)
                source_obj = join_selected_objects(context)
                if source_obj is None:
                    self.report({'ERROR'}, "Failed to join selected objects. Make sure at least two mesh objects are selected.")
                    return {'CANCELLED'}

                # Store data on the joined object
                original_names = list(nav_data.keys())
                source_obj["joined_original_objects"] = original_names
                source_obj["joined_nav_data"] = nav_data
                source_obj["joined_original_collections"] = collections_data
                source_obj["joined_result_name"] = source_obj.name  # "_joined" suffix

                print(f"\nJoined object: '{source_obj.name}'")
                print(f"Original objects: {original_names}")
                print(f"Navigation data per object: {nav_data}")
                print(f"Collections data per object: {collections_data}")
            else:
                source_obj = context.active_object
                if source_obj is None or source_obj.type != 'MESH':
                    self.report({'ERROR'}, "Active object is not a mesh.")
                    return {'CANCELLED'}

        # Switch to Edit Mode on the source object
        if context.mode != 'EDIT_MESH':
            for ob in bpy.data.objects:
                ob.select_set(False)
            source_obj.select_set(True)
            context.view_layer.objects.active = source_obj
            bpy.ops.object.mode_set(mode='EDIT')
            if context.edit_object != source_obj:
                self.report({'ERROR'}, "Failed to enter edit mode on the target object.")
                return {'CANCELLED'}

        # WORKFLOW FOR MULTIPLE OBJECTS

        if self.multiple_objects:
            # 1. Clear any old block data from the joined object
            props_to_remove = [
                "quadblock_centers", "triblock_faces", "used_face_indices",
                "block_type", "quadblock_groups", "quad_group_members",
                "triblock_groups", "tri_group_members", "face_to_quadblock",
                "face_to_triblock", "quadblock_faces_map", "triblock_faces_map",
                "multi_selected_items"
            ]
            for prop in props_to_remove:
                if prop in source_obj:
                    del source_obj[prop]

            # 2. Deselect everything (so find_blocks uses navigation points)
            bpy.ops.mesh.select_all(action='DESELECT')
            bmesh.update_edit_mesh(source_obj.data)

            # 3. Navigate
            self.report({'INFO'}, "Running block detection (Navigate)...")
            try:
                bpy.ops.navigator.find_blocks()
            except Exception as e:
                self.report({'ERROR'}, f"Block detection failed: {str(e)}")
                return {'CANCELLED'}


        # Normal duplication pipeline

        original_obj_name = source_obj.name

        try:
            original_mode = context.mode
            original_obj = context.object

            source_obj = context.edit_object
            if source_obj is None:
                self.report({'ERROR'}, "No active mesh object in edit mode")
                return {'CANCELLED'}

            context.view_layer.objects.active = source_obj
            source_obj.select_set(True)

            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            root_collection = context.scene.collection
            original_collections = list(source_obj.users_collection)
            moved_to_root = False
            if root_collection not in original_collections:
                moved_to_root = True
                self.report({'INFO'}, f"Temporarily moving '{source_obj.name}' to root collection to prevent duplication bug")
                for ob in bpy.data.objects:
                    ob.select_set(False)
                source_obj.select_set(True)
                context.view_layer.objects.active = source_obj
                move_object_to_collection_manual(source_obj, root_collection)
                context.view_layer.update()

            ps1_was_active = temporary_disable_ps1_render(context)
            snap_mods = get_vertex_snap_modifiers([source_obj])
            snap_states = disable_vertex_snap_modifiers(snap_mods)

            try:
                # Sanitization already done before join for multiple_objects,
                # but for single object mode we still need to sanitize.
                if not self.multiple_objects:
                    self._sanitize_material_suffixes(source_obj)

                context.view_layer.objects.active = source_obj
                source_obj.select_set(True)
                if context.mode != 'EDIT_MESH':
                    bpy.ops.object.mode_set(mode='EDIT')
                if context.edit_object != source_obj:
                    self.report({'ERROR'}, "Failed to enter edit mode on the correct object")
                    return {'CANCELLED'}

                if "quad_group_members" in source_obj and source_obj["quad_group_members"]:
                    bpy.ops.navigator.duplicate_quadblocks_by_group()
                    quad_group_members = source_obj["quad_group_members"]
                    quadblock_count = sum(len(members) for members in quad_group_members.values())

                if "tri_group_members" in source_obj and source_obj["tri_group_members"]:
                    bpy.ops.navigator.duplicate_triblocks_by_group()
                    tri_group_members = source_obj["tri_group_members"]
                    triblock_count = sum(len(members) for members in tri_group_members.values())

                if context.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

                obj_names = _temp_duplicated_objects
                duplicated_objs = []
                for name in obj_names:
                    obj = bpy.data.objects.get(name)
                    if obj:
                        duplicated_objs.append(obj)

                if not duplicated_objs:
                    self.report({'WARNING'}, "No objects were duplicated")
                    return {'CANCELLED'}

                settings = ExportSettings.from_scene_props(context)
                settings.export_quadblocks = True
                settings.export_triblocks = True
                settings.export_invalid_uvs = True
                settings.export_degenerated_uvs = True
                settings.allow_out_of_range = True
                settings.include_textures = True

                duplicates_dir = os.path.join(self.directory, "duplicates")
                os.makedirs(duplicates_dir, exist_ok=True)

                obj_filepath = os.path.join(duplicates_dir, "duplicates.obj")
                tex_dir = os.path.join(duplicates_dir, "textures")
                os.makedirs(tex_dir, exist_ok=True)

                success = export_duplicated_objects_to_path(
                    context,
                    duplicated_objs,
                    obj_filepath,
                    tex_dir,
                    settings
                )

                if not success:
                    self.report({'ERROR'}, "Export failed")
                    return {'CANCELLED'}

                for ob in bpy.data.objects:
                    ob.select_set(False)
                for obj in duplicated_objs:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                bpy.ops.object.delete(use_global=False)
                bpy.context.view_layer.update()
                duplicated_objs.clear()
                _temp_duplicated_objects.clear()

                import_result = execute_obj_import(obj_filepath)
                if 'FINISHED' not in import_result:
                    self.report({'WARNING'}, "OBJ imported but with issues")

                imported_objects = [obj for obj in context.selected_objects if obj.type == 'MESH' and len(obj.data.polygons) > 0]

                if not imported_objects:
                    separated_objects = []
                else:
                    context.view_layer.objects.active = imported_objects[0]
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.separate(type='LOOSE')
                    bpy.ops.object.mode_set(mode='OBJECT')
                    separated_objects = [obj for obj in context.selected_objects if obj.type == 'MESH' and len(obj.data.polygons) > 0]
                    for obj in imported_objects:
                        if obj.type == 'MESH' and len(obj.data.polygons) == 0:
                            bpy.data.objects.remove(obj, do_unlink=True)

                self.report({'INFO'}, f"Separation completed, generated {len(separated_objects)} parts.")

                # Ensure all separated objects are in the view layer
                temp_linked = ensure_objects_in_view_layer(separated_objects, context)
                try:
                    base_materials_cache = {}
                    for ob in bpy.data.objects:
                        ob.select_set(False)
                    for obj in separated_objects:
                        obj.select_set(True)

                    for obj in separated_objects:
                        if obj.type != 'MESH' or not obj.data.polygons:
                            continue
                        mesh = obj.data
                        if len(mesh.polygons) == 0:
                            continue
                        first_poly = mesh.polygons[0]
                        if first_poly.material_index >= len(mesh.materials):
                            continue
                        current_mat = mesh.materials[first_poly.material_index]
                        if not current_mat:
                            continue
                        mat_name = current_mat.name
                        if "_ID" in mat_name:
                            parts = mat_name.rsplit("_ID", 1)
                            if len(parts) == 2:
                                base_name_raw = parts[0]
                                id_suffix_raw = parts[1]
                                base_name = strip_blender_suffix(base_name_raw)
                                id_suffix = strip_blender_suffix(id_suffix_raw)
                                new_obj_name = id_suffix
                                count = 1
                                orig_new_name = new_obj_name
                                while new_obj_name in bpy.data.objects:
                                    new_obj_name = f"{orig_new_name}_{count:03d}"
                                    count += 1
                                obj.name = new_obj_name
                                base_mat = base_materials_cache.get(base_name)
                                if base_mat is None:
                                    base_mat = bpy.data.materials.get(base_name)
                                    if base_mat is None:
                                        base_mat = current_mat.copy()
                                        base_mat.name = base_name
                                    base_materials_cache[base_name] = base_mat
                                target_mat = base_mat
                            else:
                                target_mat = current_mat
                        else:
                            base_candidate = strip_blender_suffix(mat_name)
                            if base_candidate != mat_name:
                                base_mat = bpy.data.materials.get(base_candidate)
                                if base_mat is not None:
                                    target_mat = base_mat
                                else:
                                    if base_candidate not in bpy.data.materials:
                                        current_mat.name = base_candidate
                                        target_mat = current_mat
                                    else:
                                        target_mat = current_mat
                            else:
                                target_mat = current_mat

                        target_index = None
                        for i, mat in enumerate(mesh.materials):
                            if mat == target_mat:
                                target_index = i
                                break
                        if target_index is None:
                            mesh.materials.append(target_mat)
                            target_index = len(mesh.materials) - 1

                        poly_count = len(mesh.polygons)
                        indices = [target_index] * poly_count
                        mesh.polygons.foreach_set("material_index", indices)
                        mesh.update()

                    bpy.ops.object.material_slot_remove_unused()
                    mats_to_remove = [mat for mat in bpy.data.materials if "_ID" in mat.name and mat.users == 0]
                    for mat in mats_to_remove:
                        bpy.data.materials.remove(mat)
                    suffixed_mats = [mat for mat in bpy.data.materials if re.search(r'\.\d+$', mat.name) and mat.users == 0]
                    for mat in suffixed_mats:
                        bpy.data.materials.remove(mat)

                    self.report({'INFO'}, "Material consolidation and renaming completed.")

                    # Move all processed objects to "Processed_Blocks" collection
                    self._move_to_processed_collection(context, separated_objects, "Processed_Blocks")

                    self.report({'INFO'}, f"Duplicated blocks exported to {obj_filepath} and imported")
                    self.report({'INFO'}, f"Generated {len(separated_objects)} objects in collection 'Processed_Blocks'")
                finally:
                    cleanup_temporarily_linked_objects(temp_linked, context)

                # RESTORE ORIGINAL OBJECTS FROM JOINED MESH (only for multiple objects)
                if self.multiple_objects and nav_data:
                    self.report({'INFO'}, "Restoring original objects from joined mesh...")
                    try:
                        collections_data = source_obj.get("joined_original_collections", {})
                        restored = restore_original_objects(
                            context, source_obj, nav_data, list(nav_data.keys()), collections_data
                        )
                        self.report({'INFO'}, f"Restored {len(restored)} original objects.")
                        # Clean unused material slots from restored objects
                        if restored:
                            for obj in restored:
                                clean_material_slots(obj)
                            self.report({'INFO'}, "Cleaned unused material slots from restored objects.")
                    except Exception as e:
                        self.report({'ERROR'}, f"Failed to restore original objects: {str(e)}")
                        import traceback
                        traceback.print_exc()

            finally:
                restore_vertex_snap_modifiers(snap_states)
                restore_ps1_render(context, ps1_was_active)

                # RESTORE ORIGINAL COLLECTIONS FOR SINGLE OBJECT MODE
                # For multiple objects, the joined object is temporary and will be
                # either deleted or left in the root/processed collection.
                # For single object, the original object must be restored to its original collections.
                if not self.multiple_objects and moved_to_root:
                    obj_to_restore = bpy.data.objects.get(original_obj_name)
                    if obj_to_restore is not None:
                        # Remove from root collection if present
                        if obj_to_restore.name in root_collection.objects:
                            root_collection.objects.unlink(obj_to_restore)
                        # Link back to original collections
                        for coll in original_collections:
                            if coll != root_collection and coll.name in bpy.data.collections:
                                if obj_to_restore.name not in coll.objects:
                                    coll.objects.link(obj_to_restore)
                        context.view_layer.update()
                        self.report({'INFO'}, f"Restored '{obj_to_restore.name}' to its original collections")
                    else:
                        # Object no longer exists (should not happen in single mode)
                        self.report({'WARNING'}, f"Object '{original_obj_name}' not found for restoration.")

                # For multiple objects, we do NOT restore the joined object to original collections,
                # because it is either deleted or kept as a container for unassigned faces.
                # The individual original objects are restored by restore_original_objects above.

        finally:
            _temp_duplicated_objects = []

        return {'FINISHED'}


classes = [
    NAVIGATOR_OT_DuplicateQuadblocksByGroup,
    NAVIGATOR_OT_DuplicateTriblocksByGroup,
    NAVIGATOR_OT_DuplicateAllBlocksByGroup,
]