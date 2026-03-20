"""
QB/TB Duplication Operators
Operators for duplicating blocks by group
Now with export to OBJ and re-import functionality for optimized performance.
"""

import bpy
import bmesh
import os
import re

from ...utils import qb_tb_navigator
from ...utils.compat import execute_obj_export, execute_obj_import
from ..qb_tb_export.export_manager import ExportManager
from ..qb_tb_export.export_settings import ExportSettings
from ..qb_tb_export.texture_handler import TextureHandler


# Temporary global list to collect names of duplicated objects during a single
# "Duplicate All" operation. It is cleared before use and not saved elsewhere.
_temp_duplicated_objects = []


def strip_blender_suffix(name):
    """Remove Blender's automatic .001, .002 suffixes from a string."""
    return re.sub(r'\.\d+$', '', name)


def export_duplicated_objects_to_path(context, objects, obj_filepath, texture_dir, settings):
    """
    Export the list of objects to obj_filepath, copying textures to texture_dir if enabled.
    Returns True if export was successful.
    """
    if not objects:
        return False

    # Ensure we are in OBJECT mode before manipulating selection
    previous_mode = context.mode
    if previous_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Save current selection and active object
    original_active = context.view_layer.objects.active
    original_selection = context.selected_objects[:]

    # Select only the objects to export
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    if objects:
        context.view_layer.objects.active = objects[0]

    # Temporary properties container for export
    class TempExportProps:
        def __init__(self):
            self.filepath = obj_filepath
            self.use_selection = True
            self.export_colors = settings.export_colors
            self.export_textures = settings.include_textures
            self.path_mode = settings.path_mode
            self.global_scale = settings.global_scale
            # Force export of everything (ignore filters)
            self.export_quadblocks = True
            self.export_triblocks = True
            self.export_invalid_uvs = True
            self.export_degenerated_uvs = True
            self.apply_modifiers = False
            self.separate_loose_parts = False

    temp_props = TempExportProps()

    # Copy textures if enabled
    if settings.include_textures and texture_dir:
        try:
            os.makedirs(texture_dir, exist_ok=True)
            texture_handler = TextureHandler()
            texture_handler.copy_textures_to_folder(texture_dir, objects)
        except Exception as e:
            print(f"Error copying textures: {e}")

    # Execute export
    result = execute_obj_export(temp_props, objects)

    # Restore original selection
    bpy.ops.object.select_all(action='DESELECT')
    for obj in original_selection:
        if obj.name in bpy.data.objects:
            obj.select_set(True)
    if original_active and original_active.name in bpy.data.objects:
        context.view_layer.objects.active = original_active

    # Restore previous mode if it was not OBJECT
    if previous_mode != 'OBJECT' and previous_mode is not None:
        try:
            bpy.ops.object.mode_set(mode=previous_mode)
        except:
            pass  # In case the mode cannot be restored

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

                for col in new_obj.users_collection:
                    col.objects.unlink(new_obj)
                target_collection.objects.link(new_obj)

                duplicated_objects.append(new_obj)

                # Store the new object name in the global temporary list
                _temp_duplicated_objects.append(new_obj.name)

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

                for col in new_obj.users_collection:
                    col.objects.unlink(new_obj)
                target_collection.objects.link(new_obj)

                duplicated_objects.append(new_obj)

                # Store the new object name in the global temporary list
                _temp_duplicated_objects.append(new_obj.name)

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
    bl_description = "Duplicate all quadblocks and triblocks by group, export to OBJ, and import back (optimized)"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(
        name="Export Directory",
        description="Choose a directory to export duplicated blocks",
        subtype='DIR_PATH',
        default=""
    )


    # Helper methods for managing the Processed_Blocks collection

    def _clear_processed_collection(self, context, collection_name="Processed_Blocks"):
        """
        Delete all objects in the specified collection using the fast
        unlink + purge method (Option B). This removes them entirely.
        """
        col = bpy.data.collections.get(collection_name)
        if not col:
            return

        objects = list(col.objects)
        if not objects:
            return

        # Unlink objects from all collections (they become orphans)
        for obj in objects:
            for coll in list(obj.users_collection):
                coll.objects.unlink(obj)

        # Purge all orphaned data blocks (including objects)
        bpy.ops.outliner.orphans_purge()

        # Optionally remove the now empty collection (it will be recreated later if needed)
        bpy.data.collections.remove(col)

        print(f"[Processed_Blocks] Cleared {len(objects)} old objects")

    def _move_to_processed_collection(self, context, objects, collection_name="Processed_Blocks"):
        """
        Move the given objects exclusively to the specified collection.
        If the collection does not exist, it is created.
        """
        # Ensure destination collection exists
        col = bpy.data.collections.get(collection_name)
        if not col:
            col = bpy.data.collections.new(collection_name)
            context.scene.collection.children.link(col)

        for obj in objects:
            # Unlink from all current collections
            for coll in list(obj.users_collection):
                coll.objects.unlink(obj)
            # Link to the target collection
            col.objects.link(obj)

        print(f"[Processed_Blocks] Moved {len(objects)} objects to collection '{collection_name}'")


    # Main execution

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        global _temp_duplicated_objects

        # Clean previous processed objects
        self._clear_processed_collection(context, "Processed_Blocks")

        # Reset global list 
        _temp_duplicated_objects = []

        quadblock_count = 0
        triblock_count = 0

        try:
            # Store original mode and object for later restoration
            original_mode = context.mode
            original_obj = context.object

            # Duplicate quadblocks if any
            if "quad_group_members" in context.object and context.object["quad_group_members"]:
                bpy.ops.navigator.duplicate_quadblocks_by_group()
                quad_group_members = context.object["quad_group_members"]
                quadblock_count = sum(len(members) for members in quad_group_members.values())

            # Duplicate triblocks if any
            if "tri_group_members" in context.object and context.object["tri_group_members"]:
                bpy.ops.navigator.duplicate_triblocks_by_group()
                tri_group_members = context.object["tri_group_members"]
                triblock_count = sum(len(members) for members in tri_group_members.values())

            # Ensure we are in OBJECT mode for export
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            # Collect the duplicated objects
            obj_names = _temp_duplicated_objects
            duplicated_objs = []
            for name in obj_names:
                obj = bpy.data.objects.get(name)
                if obj:
                    duplicated_objs.append(obj)

            if not duplicated_objs:
                self.report({'WARNING'}, "No objects were duplicated")
                return {'CANCELLED'}

            # Configure export settings
            settings = ExportSettings.from_scene_props(context)
            # Force export all duplicated objects (ignore UV filters, etc.)
            settings.export_quadblocks = True
            settings.export_triblocks = True
            settings.export_invalid_uvs = True
            settings.export_degenerated_uvs = True
            settings.allow_out_of_range = True

            # Base filepath inside the chosen folder
            base_filepath = os.path.join(self.directory, "duplicated_blocks.obj")
            settings.filepath = base_filepath

            # Use ExportManager to generate the actual path according to folder_behavior
            manager = ExportManager(context)
            original_last_export = context.scene.last_export_path
            try:
                context.scene.last_export_path = self.directory
                export_paths = manager.prepare_export_paths(base_filepath, settings, is_quick_export=False)
            finally:
                context.scene.last_export_path = original_last_export

            # Export the objects
            success = export_duplicated_objects_to_path(
                context,
                duplicated_objs,
                export_paths['obj_filepath'],
                export_paths['texture_dir'],
                settings
            )

            if not success:
                self.report({'ERROR'}, "Export failed")
                return {'CANCELLED'}

            # Delete the temporary duplicated objects
            bpy.ops.object.select_all(action='DESELECT')
            for obj in duplicated_objs:
                if obj.name in bpy.data.objects:
                    obj.select_set(True)
            bpy.ops.object.delete()

            # Import the newly created OBJ file
            import_result = execute_obj_import(export_paths['obj_filepath'])
            if 'FINISHED' not in import_result:
                self.report({'WARNING'}, "OBJ imported but with issues")

            # Batch separation of imported objects (optimized)
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

            # Material processing
            base_materials_cache = {}

            # Ensure all objects are selected for later operations
            bpy.ops.object.select_all(action='DESELECT')
            for obj in separated_objects:
                obj.select_set(True)

            # Process each object using pure API for best performance
            for obj in separated_objects:
                if obj.type != 'MESH' or not obj.data.polygons:
                    continue

                mesh = obj.data

                # Determine current material (use first polygon's material)
                first_poly = mesh.polygons[0]
                if first_poly.material_index >= len(mesh.materials):
                    continue
                current_mat = mesh.materials[first_poly.material_index]
                if not current_mat:
                    continue

                mat_name = current_mat.name

                # Check for constant material pattern
                if "_ID" in mat_name:
                    parts = mat_name.rsplit("_ID", 1)
                    if len(parts) == 2:
                        base_name_raw = parts[0]
                        id_suffix_raw = parts[1]

                        # Remove Blender suffixes from both parts
                        base_name = strip_blender_suffix(base_name_raw)
                        id_suffix = strip_blender_suffix(id_suffix_raw)

                        # Rename object
                        new_obj_name = id_suffix
                        count = 1
                        orig_new_name = new_obj_name
                        while new_obj_name in bpy.data.objects:
                            new_obj_name = f"{orig_new_name}_{count:03d}"
                            count += 1
                        obj.name = new_obj_name

                        # Get or create base material
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
                    # Handle materials without "_ID" that may have numeric suffixes
                    base_candidate = strip_blender_suffix(mat_name)
                    if base_candidate != mat_name:
                        # Material has a .001 suffix
                        base_mat = bpy.data.materials.get(base_candidate)
                        if base_mat is not None:
                            # Use the base material
                            target_mat = base_mat
                        else:
                            # Base material doesn't exist; rename current to base if available
                            if base_candidate not in bpy.data.materials:
                                current_mat.name = base_candidate
                                target_mat = current_mat
                            else:
                                target_mat = current_mat
                    else:
                        target_mat = current_mat

                # Ensure target material is in mesh.materials list
                target_index = None
                for i, mat in enumerate(mesh.materials):
                    if mat == target_mat:
                        target_index = i
                        break
                if target_index is None:
                    # Append material to mesh.materials (this creates a slot automatically)
                    mesh.materials.append(target_mat)
                    target_index = len(mesh.materials) - 1

                # Assign target_index to all faces using foreach_set (much faster)
                poly_count = len(mesh.polygons)
                indices = [target_index] * poly_count
                mesh.polygons.foreach_set("material_index", indices)
                mesh.update()  # Required after foreach_set

            # Remove unused material slots from all objects at once
            bpy.ops.object.material_slot_remove_unused()

            # Delete any constant materials that are now unused
            mats_to_remove = [mat for mat in bpy.data.materials if "_ID" in mat.name and mat.users == 0]
            for mat in mats_to_remove:
                bpy.data.materials.remove(mat)

            # Also remove any materials with numeric suffixes that have no users (leftovers)
            suffixed_mats = [mat for mat in bpy.data.materials if re.search(r'\.\d+$', mat.name) and mat.users == 0]
            for mat in suffixed_mats:
                bpy.data.materials.remove(mat)

            self.report({'INFO'}, "Material consolidation and renaming completed.")

            # Move final objects to Processed_Blocks collection 
            self._move_to_processed_collection(context, separated_objects, "Processed_Blocks")

            self.report({'INFO'}, f"Duplicated blocks exported to {export_paths['obj_filepath']} and imported")
            self.report({'INFO'}, f"Generated {len(separated_objects)} objects in collection 'Processed_Blocks'")

        finally:
            # Clean up the global list
            _temp_duplicated_objects = []

        return {'FINISHED'}


classes = [
    NAVIGATOR_OT_DuplicateQuadblocksByGroup,
    NAVIGATOR_OT_DuplicateTriblocksByGroup,
    NAVIGATOR_OT_DuplicateAllBlocksByGroup,
]