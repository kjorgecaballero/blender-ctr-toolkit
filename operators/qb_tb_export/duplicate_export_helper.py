"""
Duplicate export helper for QB/TB export operations.
Provides reusable functions for exporting duplicates and processed blocks.
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
    def export_duplicates_only(context, export_paths, report_func=None):
        """
        Export only duplicates (no final processed OBJ).

        Args:
            context: Blender context
            export_paths: Dictionary with paths from ExportManager.prepare_export_paths()
            report_func: Optional function to report messages (e.g., self.report)

        Returns:
            tuple: (duplicates_dir, main_texture_dir) or (None, None) on failure
        """
        base_dir = export_paths.get('export_subfolder') or os.path.dirname(export_paths['obj_filepath'])
        duplicates_dir = os.path.join(base_dir, "duplicates")
        os.makedirs(duplicates_dir, exist_ok=True)

        block_obj = DuplicateExportHelper._find_block_object(context)
        if not block_obj:
            if report_func:
                report_func({'WARNING'}, "No object with block data found. Run 'Find Blocks' first.")
            return None, None

        original_mode = context.mode
        original_active_name = context.view_layer.objects.active.name if context.view_layer.objects.active else None

        if context.mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass

        context.view_layer.objects.active = block_obj
        block_obj.select_set(True)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except Exception as e:
            if report_func:
                report_func({'ERROR'}, f"Failed to switch to EDIT mode: {e}")
            if original_active_name and original_active_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[original_active_name]
            if original_mode != 'OBJECT' and original_mode != context.mode:
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
            return None, None

        try:
            bpy.ops.navigator.duplicate_all_blocks_by_group('EXEC_DEFAULT', directory=base_dir)
        except Exception as e:
            if report_func:
                report_func({'ERROR'}, f"Duplication operator failed: {e}")
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except:
                pass
            if original_active_name and original_active_name in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[original_active_name]
            if original_mode != 'OBJECT' and original_mode != context.mode:
                try:
                    bpy.ops.object.mode_set(mode=original_mode)
                except:
                    pass
            return None, None

        if report_func:
            report_func({'INFO'}, f"Duplicates exported to: {duplicates_dir}")

        try:
            bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        if original_active_name and original_active_name in bpy.data.objects:
            context.view_layer.objects.active = bpy.data.objects[original_active_name]
        if original_mode != 'OBJECT' and original_mode != context.mode:
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except:
                pass

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
            # Step 1: export duplicates
            duplicates_dir, main_texture_dir = DuplicateExportHelper.export_duplicates_only(
                context, export_paths, report_func
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

            # Get processed objects from the dedicated collection
            processed_collection = bpy.data.collections.get("Processed_Blocks")
            if not processed_collection:
                if report_func:
                    report_func({'WARNING'}, "No Processed_Blocks collection found.")
                return False
            processed_objs = [obj for obj in processed_collection.objects if obj.type == 'MESH']
            if not processed_objs:
                if report_func:
                    report_func({'WARNING'}, "No mesh objects in Processed_Blocks.")
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

                # Select valid objects for export
                for ob in bpy.data.objects:
                    ob.select_set(False)
                for obj in valid_objs:
                    obj.select_set(True)
                if valid_objs:
                    context.view_layer.objects.active = valid_objs[0]

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