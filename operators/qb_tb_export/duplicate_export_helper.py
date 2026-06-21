"""
Duplicate export helper for QB/TB export operations.
Functions for exporting duplicates and processed blocks.
"""

import bpy
import os

from .export_manager import ExportManager
from .export_settings import ExportSettings
from .texture_handler import TextureHandler
from .texture_remapper import TextureRemapper
from ...utils.export_helpers import (
    temporary_disable_ps1_render,
    restore_ps1_render,
    get_vertex_snap_modifiers,
    disable_vertex_snap_modifiers,
    restore_vertex_snap_modifiers,
)
from ...utils.compat import (
    ensure_objects_in_view_layer,
    cleanup_temporarily_linked_objects,
)


class DuplicateExportHelper:
    """Helper class for duplicate export logic shared between export operators."""

    @staticmethod
    def _find_block_object(context):
        """Find an object that contains block group data (quadgroup or trigroup)."""
        if context.mode == 'EDIT_MESH' and context.edit_object:
            return context.edit_object
        obj = context.object
        if obj and obj.type == 'MESH':
            if "quad_group_members" in obj or "tri_group_members" in obj:
                return obj
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if "quad_group_members" in obj or "tri_group_members" in obj:
                    return obj
        return None

    @staticmethod
    def _get_objects_to_process(context, use_selection):
        """
        Return the list of mesh objects that should be processed based on use_selection,
        but only if they are visible and in the view layer.
        """
        if use_selection:
            candidates = [obj for obj in context.selected_objects if obj.type == 'MESH']
        else:
            candidates = [obj for obj in bpy.data.objects if obj.type == 'MESH']

        # Filter out objects not in view layer or not visible
        valid = []
        for obj in candidates:
            if obj.name not in context.view_layer.objects:
                continue
            if not obj.visible_get():
                continue
            if obj.hide_select or obj.hide_viewport:
                continue
            valid.append(obj)
        return valid

    @staticmethod
    def export_duplicates_only(context, export_paths, report_func=None, multi_object=False, use_selection=False):
        """
        Export only duplicates (no final processed OBJ).

        Args:
            context: Blender context
            export_paths: Dictionary with paths from ExportManager.prepare_export_paths()
            report_func: Optional function to report messages (e.g., self.report)
            multi_object: If True, process all selected objects together (joins them temporarily)
            use_selection: If True, only process selected objects (only meaningful when multi_object=True)

        Returns:
            tuple: (duplicates_dir, main_texture_dir) or (None, None) on failure
        """
        base_dir = export_paths.get('export_subfolder') or os.path.dirname(export_paths['obj_filepath'])
        duplicates_dir = os.path.join(base_dir, "duplicates")
        os.makedirs(duplicates_dir, exist_ok=True)

        # If multi_object is True, we need to restrict processing to visible/selectable objects
        # by temporarily hiding others. We do this by setting hide_viewport on non-target objects.
        visibility_states = {}
        if multi_object:
            objects_to_process = DuplicateExportHelper._get_objects_to_process(context, use_selection)
            # Hide all mesh objects that are NOT in the processing list
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    visibility_states[obj.name] = obj.hide_viewport
                    if obj not in objects_to_process:
                        obj.hide_viewport = True
                    else:
                        obj.hide_viewport = False
            context.view_layer.update()

        block_obj = DuplicateExportHelper._find_block_object(context)
        if not block_obj:
            if report_func:
                report_func({'WARNING'}, "No object with block data found. Run 'Find Blocks' first.")
            # Restore visibility if changed
            if multi_object:
                for name, state in visibility_states.items():
                    if name in bpy.data.objects:
                        bpy.data.objects[name].hide_viewport = state
                context.view_layer.update()
            return None, None

        # Store the name of the block object (in case it gets deleted)
        block_obj_name = block_obj.name

        # Store original visibility states
        original_hide_viewport = block_obj.hide_viewport
        original_hide = block_obj.hide_get()

        # Ensure the object is in the view layer
        temporarily_linked = ensure_objects_in_view_layer([block_obj], context)

        # Make it visible if it was hidden
        if block_obj.hide_viewport or block_obj.hide_get():
            block_obj.hide_viewport = False
            block_obj.hide_set(False)
            context.view_layer.update()

        # Verify that the object is now visible and selectable
        if not block_obj.visible_get() or block_obj.name not in context.view_layer.objects:
            if report_func:
                report_func({'ERROR'}, f"Object '{block_obj.name}' cannot be made visible or is not in the view layer.")
            # Restore visibility and cleanup
            if block_obj.name in bpy.data.objects:
                block_obj.hide_viewport = original_hide_viewport
                block_obj.hide_set(original_hide)
            cleanup_temporarily_linked_objects(temporarily_linked, context)
            if multi_object:
                for name, state in visibility_states.items():
                    if name in bpy.data.objects:
                        bpy.data.objects[name].hide_viewport = state
                context.view_layer.update()
            return None, None

        original_mode = context.mode
        original_active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

        if context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass

        # Select and activate the block object
        context.view_layer.objects.active = block_obj
        block_obj.select_set(True)

        # Now try to enter edit mode
        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except Exception as e:
            if report_func:
                report_func({'ERROR'}, f"Failed to switch to EDIT mode: {e}")
            # Restore original visibility and cleanup
            if block_obj.name in bpy.data.objects:
                block_obj.hide_viewport = original_hide_viewport
                block_obj.hide_set(original_hide)
            cleanup_temporarily_linked_objects(temporarily_linked, context)
            if original_active_name and original_active_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[original_active_name]
            if original_mode != 'OBJECT' and original_mode != context.mode:
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
            if multi_object:
                for name, state in visibility_states.items():
                    if name in bpy.data.objects:
                        bpy.data.objects[name].hide_viewport = state
                context.view_layer.update()
            return None, None

        try:
            # Pass multi_object flag to navigator; the navigator will respect visibility
            bpy.ops.navigator.duplicate_all_blocks_by_group(
                'EXEC_DEFAULT',
                directory=base_dir,
                multiple_objects=multi_object
            )
        except Exception as e:
            if report_func:
                report_func({'ERROR'}, f"Duplication operator failed: {e}")
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            # Restore original visibility and cleanup
            if block_obj.name in bpy.data.objects:
                block_obj.hide_viewport = original_hide_viewport
                block_obj.hide_set(original_hide)
            cleanup_temporarily_linked_objects(temporarily_linked, context)
            if original_active_name and original_active_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[original_active_name]
            if original_mode != 'OBJECT' and original_mode != context.mode:
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
            if multi_object:
                for name, state in visibility_states.items():
                    if name in bpy.data.objects:
                        bpy.data.objects[name].hide_viewport = state
                context.view_layer.update()
            return None, None

        if report_func:
            report_func({'INFO'}, f"Duplicates exported to: {duplicates_dir}")

        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass

        # Restore original visibility and cleanup
        # Use the stored name to check if the object still exists
        if block_obj_name in bpy.data.objects:
            block_obj_restore = bpy.data.objects[block_obj_name]
            block_obj_restore.hide_viewport = original_hide_viewport
            block_obj_restore.hide_set(original_hide)
        else:
            # The object was deleted; just clean up temporary links and continue
            pass

        cleanup_temporarily_linked_objects(temporarily_linked, context)

        if original_active_name and original_active_name in bpy.data.objects:
            context.view_layer.objects.active = bpy.data.objects[original_active_name]
        if original_mode != 'OBJECT' and original_mode != context.mode:
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except:
                pass

        # Restore visibility for multi_object mode
        if multi_object:
            for name, state in visibility_states.items():
                if name in bpy.data.objects:
                    bpy.data.objects[name].hide_viewport = state
            context.view_layer.update()

        return duplicates_dir, export_paths.get('texture_dir')

    @staticmethod
    def export_duplicates_and_processed(context, export_paths, settings, report_func=None):
        """
        Export duplicates and then export the processed objects (final OBJ).

        Args:
            context: Blender context
            export_paths: Dictionary with paths from ExportManager.prepare_export_paths()
            settings: ExportSettings object
            report_func: Optional function to report messages (e.g., self.report)

        Returns:
            bool: True on success, False on failure
        """
        texture_remapper = None
        try:
            # Step 1: export duplicates (pass multi_object and use_selection)
            duplicates_dir, main_texture_dir = DuplicateExportHelper.export_duplicates_only(
                context, export_paths, report_func,
                multi_object=settings.multi_object,
                use_selection=settings.use_selection
            )
            if duplicates_dir is None:
                return False

            # Step 2: prepare paths for processed export
            base_dir = export_paths.get('export_subfolder') or os.path.dirname(export_paths['obj_filepath'])
            export_root = base_dir
            final_obj_dir = os.path.join(export_root, "export")
            os.makedirs(final_obj_dir, exist_ok=True)
            final_obj_path = os.path.join(final_obj_dir, os.path.basename(export_paths['obj_filepath']))

            # Create a fresh settings object for the processed export
            proc_settings = ExportSettings()
            proc_settings.export_to_folder = False
            proc_settings.include_textures = settings.include_textures
            proc_settings.remap_textures = settings.remap_textures
            proc_settings.export_multiple_materials = settings.export_multiple_materials
            proc_settings.filepath = final_obj_path
            proc_settings.export_quadblocks = settings.export_quadblocks
            proc_settings.export_triblocks = settings.export_triblocks
            proc_settings.export_colors = settings.export_colors
            proc_settings.apply_modifiers = settings.apply_modifiers
            proc_settings.separate_loose_parts = settings.separate_loose_parts
            proc_settings.export_invalid_uvs = settings.export_invalid_uvs
            proc_settings.export_invalid_triblock_uvs = settings.export_invalid_triblock_uvs
            proc_settings.export_degenerated_uvs = settings.export_degenerated_uvs
            proc_settings.path_mode = settings.path_mode
            proc_settings.allow_out_of_range = settings.allow_out_of_range
            proc_settings.export_details = settings.export_details
            proc_settings.multi_object = False 

            # Get processed objects from the dedicated collection, but only those visible/selectable
            processed_collection = bpy.data.collections.get("Processed_Blocks")
            if not processed_collection:
                if report_func:
                    report_func({'WARNING'}, "No Processed_Blocks collection found.")
                return False
            processed_objs = []
            for obj in processed_collection.objects:
                if obj.type == 'MESH':
                    if obj.name in context.view_layer.objects and obj.visible_get() and not obj.hide_select:
                        processed_objs.append(obj)
            if not processed_objs:
                if report_func:
                    report_func({'WARNING'}, "No visible/selectable mesh objects in Processed_Blocks.")
                return False

            # Disable PS1 render and vertex snap modifiers temporarily
            ps1_was_active = temporary_disable_ps1_render(context)
            snap_mods = get_vertex_snap_modifiers(processed_objs)
            snap_states = disable_vertex_snap_modifiers(snap_mods)

            try:
                # Handle textures
                if proc_settings.include_textures:
                    texture_dir = os.path.join(final_obj_dir, "textures")
                    os.makedirs(texture_dir, exist_ok=True)
                    if proc_settings.remap_textures:
                        texture_remapper = TextureRemapper()
                        try:
                            texture_remapper.execute_remapping(
                                proc_settings.filepath, texture_dir, processed_objs, remap_in_blender=True
                            )
                        except Exception as e:
                            if report_func:
                                report_func({'WARNING'}, f"Texture remapping failed: {e}")
                            texture_remapper = None
                    else:
                        texture_handler = TextureHandler()
                        texture_handler.copy_textures_to_folder(texture_dir, processed_objs)

                # Validate and export
                manager = ExportManager(context)
                valid_objs, stats = manager.validate_objects(processed_objs, proc_settings)
                if not valid_objs:
                    error_msg = manager.get_no_objects_error(proc_settings, stats)
                    if report_func:
                        report_func({'ERROR'}, error_msg)
                    return False

                # Store original selection and active object
                old_sel_names = [obj.name for obj in context.selected_objects if obj.name in bpy.data.objects]
                old_active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

                # prepare_export_operation will handle selection and view‑layer assurance
                manager.prepare_export_operation(valid_objs)
                export_result = manager.execute_export(proc_settings, valid_objs)

                # Restore selection
                for ob in bpy.data.objects:
                    ob.select_set(False)
                for name in old_sel_names:
                    if name in bpy.data.objects:
                        bpy.data.objects[name].select_set(True)
                if old_active_name and old_active_name in bpy.data.objects:
                    context.view_layer.objects.active = bpy.data.objects[old_active_name]

                if 'FINISHED' not in export_result:
                    if report_func:
                        report_func({'ERROR'}, "Processed export failed")
                    return False

                # Export JSON details if enabled
                if settings.export_details:
                    export_index = context.scene.export_index
                    context.scene.export_index += 1
                    manager.export_details_if_needed(
                        valid_objs, stats, proc_settings, proc_settings.filepath, True, export_index
                    )

                if report_func:
                    report_func({'INFO'}, f"Export completed: final model saved to {proc_settings.filepath}")
                return True

            finally:
                restore_vertex_snap_modifiers(snap_states)
                restore_ps1_render(context, ps1_was_active)

        except Exception as e:
            if report_func:
                report_func({'ERROR'}, f"Error during duplicate+processed export: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if texture_remapper:
                try:
                    texture_remapper.restore_blender_texture_paths()
                except Exception as e:
                    print(f"Error restoring textures: {e}")