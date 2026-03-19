import bpy
import os
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, FloatProperty, StringProperty, EnumProperty
from bpy.types import Operator
from .export_manager import ExportManager
from .export_settings import ExportSettings, ExportStats
from .texture_handler import TextureHandler
from .texture_remapper import TextureRemapper
from ...ui.help_utils import draw_help_buttons


class QB_TB_OT_ExportQuadTriBlocks(Operator, ExportHelper):
    """Export Quadblocks and Triblocks to OBJ format."""

    bl_idname = "export_scene.qb_tb_obj"
    bl_label = "Qb/Tb (.obj)"
    bl_description = "Export Quadblocks and Triblocks to OBJ format (Quick Export: Ctrl+Shift+E)"

    filename_ext = ".obj"

    filter_glob: StringProperty(
        default="*.obj",
        options={'HIDDEN'},
    )

    use_selection: BoolProperty(
        name="Selection Only",
        description="Export only selected objects",
        default=False,
    )

    export_quadblocks: BoolProperty(
        name="Quadblocks",
        description="Export Quadblocks",
        default=True,
    )

    export_triblocks: BoolProperty(
        name="Triblocks",
        description="Export Triblocks",
        default=True,
    )

    export_colors: BoolProperty(
        name="Vertex Colors",
        description="Export Vertex Colors",
        default=True,
    )

    export_to_folder: BoolProperty(
        name="Export to Folder",
        description="Export OBJ to organized folder structure",
        default=False,
    )

    include_textures: BoolProperty(
        name="Include Textures",
        description="Copy textures to texture folder",
        default=False,
    )

    remap_textures: BoolProperty(
        name="Remap Textures",
        description="Remap model to use exported textures in texture folder",
        default=False,
    )

    folder_behavior: EnumProperty(
        name="Behavior",
        description="How to handle existing folders when exporting to folder",
        items=[
            ('REPLACE', 'Replace', 'Replace existing folder'),
            ('INCREMENTAL', 'Numerical Increment', 'Create folder with numerical increment'),
        ],
        default='INCREMENTAL',
    )

    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before validating and exporting",
        default=False,
    )

    separate_loose_parts: BoolProperty(
        name="Separate by Loose Parts",
        description="Separate mesh by loose parts before validating",
        default=False,
    )

    global_scale: FloatProperty(
        name="Scale",
        description="Global export scale",
        min=0.001, max=1000.0,
        default=1.0,
    )

    export_invalid_uvs: BoolProperty(
        name="Invalid UVs",
        description="Export objects with invalid UVs",
        default=False,
    )

    export_degenerated_uvs: BoolProperty(
        name="Degenerated UVs",
        description="Export objects with degenerated UVs",
        default=False,
    )

    path_mode: EnumProperty(
        name="Path Mode",
        description="Texture path handling",
        items=[
            ('AUTO', 'Auto', 'Automatic path handling'),
            ('ABSOLUTE', 'Absolute', 'Use absolute paths'),
            ('RELATIVE', 'Relative', 'Use relative paths'),
            ('COPY', 'Copy', 'Copy textures to export folder'),
            ('STRIP', 'Strip', 'Strip texture paths'),
        ],
        default='ABSOLUTE',
    )

    export_details: BoolProperty(
        name="Export Details (JSON)",
        description="Export a JSON file with export details",
        default=False,
    )

    allow_out_of_range: BoolProperty(
        name="Allow Out of Range",
        description="Export objects outside the 1000x1000x1000 range",
        default=False,
    )

    export_duplicates: BoolProperty(
        name="Export Duplicates",
        description="Export duplicates of detected blocks to a 'Duplicates' subfolder (ignores UV/range filters)",
        default=False,
    )

    export_processed_duplicates: BoolProperty(
        name="Export Processed Duplicates",
        description="After duplication, export the processed objects using current export settings (filters, folder, etc.)",
        default=False,
    )

    def draw(self, context):
        """Draw the operator UI panel."""
        layout = self.layout

        draw_help_buttons(layout)

        # Selection & Block Types section
        box = layout.box()
        box.label(text="Selection & Block Types", icon='OBJECT_DATA')
        box.prop(self, "use_selection")
        col = box.column()
        col.prop(self, "export_quadblocks")
        col.prop(self, "export_triblocks")

        # Export Settings section
        box = layout.box()
        box.label(text="Export Settings", icon='EXPORT')
        box.prop(self, "export_colors")
        box.prop(self, "export_details")

        # Range Filtering section
        box = layout.box()
        box.label(text="Range Filtering", icon='SHADERFX')
        box.prop(self, "allow_out_of_range")
        if not self.allow_out_of_range:
            box.label(text="Fixed 1000x1000x1000 cube", icon='INFO')
            box.label(text="Center: (0,0,0)", icon='INFO')
        else:
            box.label(text="Ignore Range", icon='INFO')

        # UV Issues Handling section
        box = layout.box()
        box.label(text="UV Issues Handling", icon='UV')
        col = box.column()
        col.prop(self, "export_invalid_uvs", text="Invalid UVs")
        col.prop(self, "export_degenerated_uvs", text="Degenerated UVs")

        # Pre-Processing section
        box = layout.box()
        box.label(text="Pre-Processing", icon='MODIFIER')
        col = box.column()
        col.prop(self, "apply_modifiers")
        col.prop(self, "separate_loose_parts")

        # Folder Organization section
        box = layout.box()
        box.label(text="Folder Organization", icon='FILE_FOLDER')
        box.prop(self, "export_to_folder")

        if self.export_to_folder:
            col = box.column()
            col.prop(self, "include_textures")

            if self.include_textures:
                col.prop(self, "remap_textures")

            col.prop(self, "folder_behavior")

        # Scale section
        box = layout.box()
        box.label(text="Scale", icon='ARROW_LEFTRIGHT')
        box.prop(self, "global_scale")

        # Quick Export Status section
        if context.scene.last_export_path:
            layout.separator()
            box = layout.box()
            box.label(text="Quick Export Status", icon='INFO')
            col = box.column(align=True)
            col.label(text=f"Last project: {os.path.basename(context.scene.last_export_path)}")
            col.label(text=f"Location: {context.scene.last_export_path}")
            col.label(text="Quick Export: Ctrl+Shift+E", icon='EVENT_CTRL')

        # Duplicate Export section
        layout.separator()
        box = layout.box()
        box.label(text="Duplicate Export", icon='DUPLICATE')
        col = box.column(align=True)

        col.prop(self, "export_duplicates")

        if self.export_duplicates:
            col.prop(self, "export_processed_duplicates")
            col.label(text="Duplicates will be saved in a 'Duplicates' subfolder", icon='INFO')

    def invoke(self, context, event):
        """Initialize operator properties from scene settings."""
        self.folder_behavior = context.scene.folder_behavior
        self.use_selection = context.scene.use_selection
        self.export_duplicates = context.scene.export_duplicates
        self.export_processed_duplicates = context.scene.export_processed_duplicates
        return super().invoke(context, event)

    def _save_export_settings(self, context):
        """Save current export settings to scene properties."""
        context.scene.use_selection = self.use_selection
        context.scene.export_quadblocks = self.export_quadblocks
        context.scene.export_triblocks = self.export_triblocks
        context.scene.export_colors = self.export_colors
        context.scene.export_to_folder = self.export_to_folder
        context.scene.include_textures = self.include_textures
        context.scene.remap_textures = self.remap_textures
        context.scene.folder_behavior = self.folder_behavior
        context.scene.apply_modifiers = self.apply_modifiers
        context.scene.separate_loose_parts = self.separate_loose_parts
        context.scene.global_scale = self.global_scale
        context.scene.export_invalid_uvs = self.export_invalid_uvs
        context.scene.export_degenerated_uvs = self.export_degenerated_uvs
        context.scene.path_mode = self.path_mode
        context.scene.export_details = self.export_details
        context.scene.allow_out_of_range = self.allow_out_of_range
        context.scene.export_duplicates = self.export_duplicates
        context.scene.export_processed_duplicates = self.export_processed_duplicates

    def _handle_textures(self, settings, export_paths, valid_objects):
        """Copy and remap textures if requested."""
        texture_remapper = None
        if settings.include_textures and export_paths['texture_dir']:
            try:
                os.makedirs(export_paths['texture_dir'], exist_ok=True)
            except OSError:
                export_paths['texture_dir'] = None

        if settings.include_textures and export_paths['texture_dir']:
            if self.remap_textures:
                texture_remapper = TextureRemapper()
                success = texture_remapper.execute_remapping(
                    settings.filepath,
                    export_paths['texture_dir'],
                    valid_objects,
                    remap_in_blender=True
                )
                if not success:
                    pass  # Warning already shown

        return texture_remapper

    def _export_additional_details(self, context, manager, valid_objects, stats, settings, export_paths):
        """Export JSON details file if requested."""
        export_index = context.scene.export_index
        context.scene.export_index += 1

        json_path = manager.export_details_if_needed(
            valid_objects, stats, settings, export_paths['obj_filepath'],
            self.export_details, export_index
        )
        if json_path:
            export_data = manager.details_exporter.collect_export_details(
                valid_objects, stats, settings, export_paths['obj_filepath'], export_index
            )
            detailed_report = manager.details_exporter.get_summary_report(export_data, max_objects_per_list=10)
            print(detailed_report)

    def _export_processed_duplicates(self, context, duplicates_dir):
        """Export post‑processed duplicate objects using current user settings."""
        processed_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not processed_objs:
            self.report({'WARNING'}, "No processed objects found to export")
            return

        proc_settings = ExportSettings.from_operator(self)
        proc_settings.export_to_folder = False  # Already inside a specific folder
        proc_settings.filepath = os.path.join(duplicates_dir, "processed_duplicates.obj")

        temp_manager = ExportManager(context)
        valid_objs, stats = temp_manager.validate_objects(processed_objs, proc_settings)
        if not valid_objs:
            self.report({'WARNING'}, "No processed objects passed the current filters")
            return

        old_sel = context.selected_objects[:]
        old_active = context.view_layer.objects.active

        bpy.ops.object.select_all(action='DESELECT')
        for obj in valid_objs:
            obj.select_set(True)
        if valid_objs:
            context.view_layer.objects.active = valid_objs[0]

        temp_manager.prepare_export_operation(valid_objs)
        result = temp_manager.execute_export(proc_settings, valid_objs)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in old_sel:
            if obj.name in bpy.data.objects:
                obj.select_set(True)
        if old_active and old_active.name in bpy.data.objects:
            context.view_layer.objects.active = old_active

        if 'FINISHED' in result:
            self.report({'INFO'}, f"Processed duplicates exported to {proc_settings.filepath}")
        else:
            self.report({'WARNING'}, "Failed to export processed duplicates")

    def _find_block_object(self, context):
        """Find an object that contains quadblock or triblock data."""
        # If in edit mode, use the edit object
        if context.mode == 'EDIT_MESH' and context.edit_object:
            return context.edit_object

        # Check active object
        obj = context.object
        if obj and obj.type == 'MESH':
            if "quad_group_members" in obj or "tri_group_members" in obj:
                return obj

        # Scan all mesh objects
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if "quad_group_members" in obj or "tri_group_members" in obj:
                    return obj

        return None

    def _export_duplicates(self, context, export_paths):
        """Execute duplicate export to a 'Duplicates' subfolder."""
        original_mode = context.mode
        original_active = context.object
        original_active_name = original_active.name if original_active else None

        try:
            base_dir = export_paths.get('export_subfolder') or os.path.dirname(export_paths['obj_filepath'])
            duplicates_dir = os.path.join(base_dir, "Duplicates")
            os.makedirs(duplicates_dir, exist_ok=True)

            block_obj = self._find_block_object(context)
            if not block_obj:
                self.report({'WARNING'}, "No object with block data found. Run 'Find Blocks' first.")
                return

            # Switch to object mode if necessary, then to edit mode on the block object
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            context.view_layer.objects.active = block_obj
            bpy.ops.object.mode_set(mode='EDIT')

            bpy.ops.navigator.duplicate_all_blocks_by_group(
                'EXEC_DEFAULT',
                directory=duplicates_dir
            )

            self.report({'INFO'}, f"Duplicates exported to: {duplicates_dir}")

            if self.export_processed_duplicates:
                self._export_processed_duplicates(context, duplicates_dir)

        except Exception as e:
            self.report({'WARNING'}, f"Duplicate export failed: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            # Restore original mode and active object
            if original_mode != context.mode:
                # Map context mode strings to valid mode_set enum values
                mode_map = {
                    'EDIT_MESH': 'EDIT',
                    'EDIT_CURVE': 'EDIT',
                    'EDIT_SURFACE': 'EDIT',
                    'EDIT_METABALL': 'EDIT',
                    'EDIT_TEXT': 'EDIT',
                    'EDIT_ARMATURE': 'EDIT',
                    'EDIT_LATTICE': 'EDIT',
                    'EDIT_POINTCLOUD': 'EDIT',
                    'EDIT_GREASE_PENCIL': 'EDIT',
                }
                target_mode = mode_map.get(original_mode, original_mode)
                allowed_modes = {'OBJECT', 'EDIT', 'SCULPT', 'VERTEX_PAINT', 'WEIGHT_PAINT', 'TEXTURE_PAINT'}
                if target_mode in allowed_modes:
                    bpy.ops.object.mode_set(mode=target_mode)
                else:
                    bpy.ops.object.mode_set(mode='OBJECT')
            if original_active_name:
                obj = bpy.data.objects.get(original_active_name)
                if obj:
                    context.view_layer.objects.active = obj

    def execute(self, context):
        """Main execution method for the export operator."""
        # Validate block types
        if not self.export_quadblocks and not self.export_triblocks:
            self.report({'ERROR'}, "Must select at least one block type")
            return {'CANCELLED'}

        settings = ExportSettings.from_operator(self)
        self._save_export_settings(context)

        manager = ExportManager(context)

        # Prepare paths early so they are available even if main export fails
        export_paths = manager.prepare_export_paths(self.filepath, settings, is_quick_export=False)
        settings.filepath = export_paths['obj_filepath']

        try:
            initial_objects = manager.prepare_objects(settings)
            if not initial_objects:
                self.report({'ERROR'}, "No objects to export")
                return {'CANCELLED'}

            processed_objects = manager.preprocess_objects(initial_objects, settings)
            valid_objects, stats = manager.validate_objects(processed_objects, settings)

            if not valid_objects:
                error_msg = manager.get_no_objects_error(settings, stats)
                self.report({'ERROR'}, error_msg)
                # Continue to duplicates if requested
            else:
                if settings.include_textures and not export_paths['texture_dir']:
                    self.report({'WARNING'}, "Could not create texture directory")

                texture_remapper = self._handle_textures(settings, export_paths, valid_objects)
                manager.prepare_export_operation(valid_objects)
                export_result = manager.execute_export(settings, valid_objects)

                if texture_remapper:
                    texture_remapper.restore_blender_texture_paths()

                if 'FINISHED' not in export_result:
                    self.report({'ERROR'}, "Export failed")
                else:
                    if self.export_details:
                        self._export_additional_details(context, manager, valid_objects, stats, settings, export_paths)

                    stats_obj = ExportStats.from_dict(stats)
                    if settings.export_to_folder and export_paths['export_subfolder']:
                        stats_obj.exported_folder = os.path.basename(export_paths['export_subfolder'])

                    self.report({'INFO'}, stats_obj.get_report_message())

        except Exception as e:
            self.report({'ERROR'}, f"Error during export: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            manager.restore_state()

        # Duplicate export (if requested) runs even if main export failed
        if self.export_duplicates:
            self._export_duplicates(context, export_paths)

        return {'FINISHED'}


def menu_func_export(self, context):
    """Add export operator to Blender's File > Export menu."""
    self.layout.operator(QB_TB_OT_ExportQuadTriBlocks.bl_idname, text="Qb/Tb (.obj)")