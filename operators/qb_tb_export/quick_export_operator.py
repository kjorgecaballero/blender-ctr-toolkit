import bpy
import os
from bpy.types import Operator
from .export_manager import ExportManager
from .export_settings import ExportSettings, ExportStats
from .texture_handler import TextureHandler
from .texture_remapper import TextureRemapper
from .duplicate_export_helper import DuplicateExportHelper


class QB_TB_OT_QuickExport(Operator):
    bl_idname = "qb_tb.quick_export"
    bl_label = "Quick Export Qb/Tb"
    bl_description = "Quick export using last export location (Ctrl+Shift+E)"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        # Check if a valid export path exists
        last_path = context.scene.last_export_path
        if not last_path:
            self.report({'ERROR'}, "No previous export found. Please do a normal export first (File > Export > Qb/Tb .obj).")
            return {'CANCELLED'}

        if not context.scene.export_quadblocks and not context.scene.export_triblocks:
            self.report({'ERROR'}, "Must select at least one block type (Quadblocks or Triblocks)")
            return {'CANCELLED'}

        try:
            settings = ExportSettings.from_scene_props(context)

            # Determine filename and base path based on last_export_path
            if last_path.lower().endswith('.obj'):
                # Last export was a direct .obj file
                export_dir = os.path.dirname(last_path)
                obj_filename = os.path.basename(last_path)
                # Use the same filename to keep consistency.
                filename = obj_filename
                # Force direct export (no folder structure) - the manager will detect this
                # because last_path is a .obj and we'll pass it as filepath.
                filepath = last_path
            else:
                # Last export was a folder (project folder)
                export_dir = last_path
                # Get scene name for default .obj filename
                if bpy.data.filepath:
                    scene_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                else:
                    scene_name = "untitled"
                filename = f"{scene_name}.obj"
                filepath = os.path.join(export_dir, filename)

            manager = ExportManager(context)
            export_paths = manager.prepare_export_paths(filepath, settings, is_quick_export=True)
            settings.filepath = export_paths['obj_filepath']

            # DUPLICATE EXPORT LOGIC (if enabled)
            if context.scene.export_duplicates and context.scene.export_processed_duplicates:
                success = DuplicateExportHelper.export_duplicates_and_processed(
                    context, export_paths, settings, report_func=self.report
                )
                if success:
                    return {'FINISHED'}
                else:
                    return {'CANCELLED'}

            elif context.scene.export_duplicates and not context.scene.export_processed_duplicates:
                DuplicateExportHelper.export_duplicates_only(context, export_paths, report_func=self.report)
                self.report({'INFO'}, "Duplicates exported (no final OBJ saved).")
                return {'FINISHED'}

            # NORMAL EXPORT (no duplicates)
            else:
                initial_objects = manager.prepare_objects(settings)
                if not initial_objects:
                    self.report({'ERROR'}, "No objects to export")
                    return {'CANCELLED'}

                processed_objects = manager.preprocess_objects(initial_objects, settings)
                valid_objects, stats = manager.validate_objects(processed_objects, settings)

                if not valid_objects:
                    error_msg = manager.get_no_objects_error(settings, stats)
                    self.report({'ERROR'}, error_msg)
                    return {'CANCELLED'}

                from ...utils.export_helpers import (
                    temporary_disable_ps1_render,
                    restore_ps1_render,
                    get_vertex_snap_modifiers,
                    disable_vertex_snap_modifiers,
                    restore_vertex_snap_modifiers
                )
                ps1_was_active = temporary_disable_ps1_render(context)
                snap_mods = get_vertex_snap_modifiers(valid_objects)
                snap_states = disable_vertex_snap_modifiers(snap_mods)

                texture_remapper = None
                try:
                    if settings.include_textures and export_paths['texture_dir']:
                        if context.scene.remap_textures:
                            texture_remapper = TextureRemapper()
                            success = texture_remapper.execute_remapping(
                                settings.filepath,
                                export_paths['texture_dir'],
                                valid_objects,
                                remap_in_blender=True
                            )
                            if not success:
                                self.report({'WARNING'}, "Texture remapping encountered issues")
                        else:
                            texture_handler = TextureHandler()
                            texture_handler.copy_textures_to_folder(export_paths['texture_dir'], valid_objects)

                    manager.prepare_export_operation(valid_objects)
                    export_result = manager.execute_export(settings, valid_objects)

                    if texture_remapper:
                        texture_remapper.restore_blender_texture_paths()

                    if 'FINISHED' not in export_result:
                        self.report({'ERROR'}, "Export failed")
                        manager.restore_state()
                        return {'CANCELLED'}

                    if hasattr(context.scene, 'export_details') and context.scene.export_details:
                        export_index = context.scene.export_index
                        context.scene.export_index += 1
                        manager.export_details_if_needed(
                            valid_objects, stats, settings, export_paths['obj_filepath'],
                            True, export_index
                        )

                    obj_dir = os.path.dirname(settings.filepath)
                    obj_name = os.path.splitext(os.path.basename(settings.filepath))[0]
                    mtl_path = os.path.join(obj_dir, f"{obj_name}.mtl")

                    if settings.include_textures and export_paths['texture_dir']:
                        if not context.scene.remap_textures:
                            texture_handler = TextureHandler()
                            texture_handler.copy_textures_to_folder(export_paths['texture_dir'], valid_objects)

                    manager.restore_state()

                    stats_obj = ExportStats()
                    stats_obj.quadblocks = stats['quadblocks']
                    stats_obj.triblocks = stats['triblocks']
                    stats_obj.total_exported = stats['total_exported']
                    stats_obj.exported_with_uv_issues = stats['exported_with_uv_issues']

                    if settings.export_to_folder and export_paths['export_subfolder']:
                        stats_obj.exported_folder = os.path.basename(export_paths['export_subfolder'])

                    self.report({'INFO'}, f"Quick export completed: {stats_obj.get_report_message()}")
                    return {'FINISHED'}

                finally:
                    restore_vertex_snap_modifiers(snap_states)
                    restore_ps1_render(context, ps1_was_active)
                    if texture_remapper:
                        try:
                            texture_remapper.restore_blender_texture_paths()
                        except Exception as e:
                            print(f"Error restoring textures: {e}")

        except Exception as e:
            self.report({'ERROR'}, f"Error during quick export: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}