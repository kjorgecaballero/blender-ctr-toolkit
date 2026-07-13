import bpy
import os
import json
import re
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from ...utils.uv_animator.uv_animator_utils import apply_uvs_to_object
from ...utils.uv_animator.uv_block_utils import (
    apply_uvs_to_material
)
from ...utils.compat import execute_obj_export
from ...utils.export_helpers import temporary_disable_ps1_render, restore_ps1_render

def sanitize_name(name):
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

def assign_texture_to_duplicate(dup, desired_texture, texture_materials, obj_name, frame_key):
    """
    Assign a texture to the duplicate object, reusing materials if the texture is already used.
    This avoids creating a new material for every frame if the texture is the same.
    """
    if not desired_texture or desired_texture == "No Texture":
        return

    # Check if the current material already has the desired texture
    if dup.data.materials:
        current_mat = dup.data.materials[0]
        if current_mat.use_nodes:
            for node in current_mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    current_path = bpy.path.abspath(node.image.filepath).replace("\\", "/")
                    if current_path == desired_texture:
                        return  # Already has the correct texture

    # If not, look in the material cache
    if desired_texture in texture_materials:
        new_mat = texture_materials[desired_texture]
    else:
        # Create a new material with the texture
        new_mat = bpy.data.materials.new(name=f"Mat_{obj_name}_frame_{frame_key}")
        new_mat.use_nodes = True
        nodes = new_mat.node_tree.nodes
        links = new_mat.node_tree.links

        # Clear default nodes
        for node in list(nodes):
            nodes.remove(node)

        # Create nodes
        tex_node = nodes.new(type='ShaderNodeTexImage')
        bsdf_node = nodes.new(type='ShaderNodeBsdfPrincipled')
        output_node = nodes.new(type='ShaderNodeOutputMaterial')

        # Load image
        try:
            img = bpy.data.images.load(desired_texture, check_existing=True)
            tex_node.image = img
        except Exception as e:
            print(f"Could not load image: {desired_texture}, error: {e}")

        # Connect nodes
        links.new(tex_node.outputs['Color'], bsdf_node.inputs['Base Color'])
        links.new(bsdf_node.outputs['BSDF'], output_node.inputs['Surface'])

        texture_materials[desired_texture] = new_mat

    # Assign the material to the object
    dup.data.materials.clear()
    dup.data.materials.append(new_mat)

def export_block_animation(context, dup_obj, block, export_dir, clean_after_export=True):
    frames = block.frames
    num_frames = len(frames)
    if num_frames == 0:
        return None
    if dup_obj.name not in bpy.data.objects:
        return None

    material_name = None
    if dup_obj.data.materials:
        material_name = dup_obj.data.materials[0].name
    if not material_name:
        material_name = block.material_name

    base_name = sanitize_name(block.block_id)
    frame_collection_name = f"uv_anim_{base_name}"
    frame_collection = bpy.data.collections.get(frame_collection_name)
    if frame_collection:
        for child in list(frame_collection.objects):
            if child.name in bpy.data.objects:
                bpy.data.objects.remove(child, do_unlink=True)
        bpy.data.collections.remove(frame_collection)

    frame_collection = bpy.data.collections.new(frame_collection_name)
    context.scene.collection.children.link(frame_collection)

    frame_objects = []
    texture_materials = {}  # Cache materials by texture path

    for idx, frame in enumerate(frames):
        dup = dup_obj.copy()
        dup.data = dup_obj.data.copy()
        dup.name = f"{base_name}_frame{idx+1:02d}"
        frame_collection.objects.link(dup)

        uvs = json.loads(frame.uv_data)
        centers = json.loads(frame.face_centers) if frame.face_centers else None
        apply_uvs_to_material(dup, material_name, uvs, centers_ordered=centers)

        # Assign texture if available
        if frame.texture_path:
            assign_texture_to_duplicate(dup, frame.texture_path, texture_materials, base_name, idx)

        frame_objects.append(dup)

    exported_path = None
    if frame_objects:
        for ob in bpy.data.objects:
            ob.select_set(False)
        for ob in frame_objects:
            if ob.name in bpy.data.objects:
                ob.select_set(True)
        active_candidate = None
        for ob in frame_objects:
            if ob.name in bpy.data.objects:
                active_candidate = ob
                break
        if active_candidate:
            context.view_layer.objects.active = active_candidate

            obj_filename = f"{base_name}_anim.obj"
            export_path = os.path.join(export_dir, obj_filename)

            class TempExportProps:
                def __init__(self, filepath):
                    self.filepath = filepath
                    self.use_selection = True
                    self.export_colors = True
                    self.apply_modifiers = False
                    self.global_scale = 1.0
                    self.path_mode = 'ABSOLUTE'
                    self.export_textures = True

            temp_props = TempExportProps(export_path)
            result = execute_obj_export(temp_props, frame_objects)

            if 'FINISHED' in result:
                exported_path = export_path

    for ob in list(frame_objects):
        if ob.name in bpy.data.objects:
            bpy.data.objects.remove(ob, do_unlink=True)
    if frame_collection.name in bpy.data.collections:
        bpy.data.collections.remove(frame_collection)

    return exported_path

class UV_OT_ExportAnimation(Operator, ExportHelper):
    bl_idname = "uv_animator.export_animation"
    bl_label = "Export UV Animation"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".obj"
    filter_glob: bpy.props.StringProperty(default="*.obj", options={'HIDDEN'})

    clean_after_export: bpy.props.BoolProperty(
        name="Clean Duplicates",
        description="Remove temporary duplicate objects and collections after export",
        default=True
    )

    export_preset: bpy.props.BoolProperty(
        name="Export Preset",
        description="Generate a single JSON preset file containing all exported animations",
        default=False
    )
    associate: bpy.props.BoolProperty(
        name="Associate",
        description="Include the object name in the 'quads' field of the preset",
        default=True
    )

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Export Options", icon='EXPORT')
        box.prop(self, "clean_after_export")
        box.prop(self, "export_preset")
        if self.export_preset:
            box.prop(self, "associate")
            box.label(text="A single JSON file will be created with all animations.", icon='INFO')

    def _collect_animation_data(self, obj, obj_filepath, frames, texture_items, associate=True):
        """
        Build the animation data dictionary for a single object.
        blendModes is per UNIQUE texture, in order of first appearance in frames.
        """
        # Gather unique textures in order of first appearance
        unique_textures = []
        seen = set()
        for frame in frames:
            tex_path = frame.texture_path
            if tex_path and tex_path not in seen:
                unique_textures.append(tex_path)
                seen.add(tex_path)
            elif not tex_path and '' not in seen:
                # Treat empty texture as a special case
                unique_textures.append('')
                seen.add('')

        # For each unique texture, find its blend mode
        blend_modes = []
        for tex_path in unique_textures:
            blend_mode = 0  # default
            if tex_path:
                for item in texture_items:
                    if item.texture_path == tex_path:
                        try:
                            blend_mode = int(item.blend_mode)
                        except ValueError:
                            blend_mode = 0
                        break
            # If no texture path or no match, blend_mode stays 0
            blend_modes.append(blend_mode)

        quads = [obj.name] if associate else []

        return {
            "blendModes": blend_modes,
            "duration": obj.uv_frame_duration,
            "horMirror": False,
            "name": obj.name,  # Use object name as the animation name
            "path": os.path.abspath(obj_filepath),
            "quads": quads,
            "rotation": 0,
            "startAt": obj.uv_start_frame,
            "verMirror": False
        }

    def _write_consolidated_preset(self, export_dir, base_filename, animations_data):
        """
        Write a single JSON file containing all animations.
        """
        if not animations_data:
            return

        preset = {}
        for idx, anim_data in enumerate(animations_data):
            preset[f"anim{idx}"] = anim_data
        preset["animCount"] = len(animations_data)
        preset["header"] = 5

        json_path = os.path.join(export_dir, f"{base_filename}.json")
        with open(json_path, 'w') as f:
            json.dump(preset, f, indent=2)

        self.report({'INFO'}, f"Consolidated preset JSON saved to {json_path} with {len(animations_data)} animations.")

    def execute(self, context):
        selected_objs = context.selected_objects if context.selected_objects else bpy.data.objects
        objects_with_blocks = []
        objects_legacy = []

        for obj in selected_objs:
            if obj.type != 'MESH':
                continue
            if obj.name not in bpy.data.objects:
                continue
            if hasattr(obj, 'uv_animated_blocks') and obj.uv_animated_blocks and any(b.is_animated for b in obj.uv_animated_blocks):
                objects_with_blocks.append(obj.name)
            elif obj.is_uv_animated and len(obj.uv_animation_frames) > 0:
                objects_legacy.append(obj.name)

        if not objects_with_blocks and not objects_legacy:
            self.report({'WARNING'}, "No animated objects or blocks found.")
            return {'CANCELLED'}

        original_selection = [obj.name for obj in context.selected_objects if obj.name in bpy.data.objects]
        original_active = context.view_layer.objects.active.name if context.view_layer.objects.active else None
        original_mode = context.mode

        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        export_dir = os.path.dirname(self.filepath)
        if not export_dir:
            export_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.path.expanduser("~")

        ps1_was_active = temporary_disable_ps1_render(context)
        exported_files = []

        # This will hold all animation data for the consolidated JSON
        all_animations_data = []

        # 1. Handle Constant Materials
        if objects_with_blocks:
            bpy.ops.object.select_all(action='DESELECT')
            for obj_name in objects_with_blocks:
                if obj_name in bpy.data.objects:
                    bpy.data.objects[obj_name].select_set(True)
            if objects_with_blocks and objects_with_blocks[0] in bpy.data.objects:
                context.view_layer.objects.active = bpy.data.objects[objects_with_blocks[0]]

            temp_dir = os.path.join(export_dir, "temp_duplicates")
            os.makedirs(temp_dir, exist_ok=True)

            try:
                bpy.ops.navigator.duplicate_all_blocks_by_group(
                    multiple_objects=True,
                    directory=temp_dir
                )
            except Exception as e:
                self.report({'ERROR'}, f"Block duplication failed: {str(e)}")
                return {'CANCELLED'}

            processed_collection = bpy.data.collections.get("Processed_Blocks")
            if not processed_collection:
                self.report({'ERROR'}, "Processed_Blocks collection not found.")
                return {'CANCELLED'}

            uv_anim_collection = bpy.data.collections.get("uv_anim")
            if not uv_anim_collection:
                uv_anim_collection = bpy.data.collections.new("uv_anim")
                context.scene.collection.children.link(uv_anim_collection)

            for obj in list(processed_collection.objects):
                if obj.name in bpy.data.objects:
                    processed_collection.objects.unlink(obj)
                    uv_anim_collection.objects.link(obj)

            if processed_collection.name in bpy.data.collections:
                bpy.data.collections.remove(processed_collection)

            for dup_obj in list(uv_anim_collection.objects):
                if dup_obj.name not in bpy.data.objects:
                    continue

                block_id = dup_obj.name

                orig_obj = None
                block = None
                for obj_name in objects_with_blocks:
                    if obj_name not in bpy.data.objects:
                        continue
                    obj = bpy.data.objects[obj_name]
                    for b in obj.uv_animated_blocks:
                        if b.block_id == block_id:
                            orig_obj = obj
                            block = b
                            break
                    if orig_obj:
                        break

                if not orig_obj or not block:
                    self.report({'WARNING'}, f"No block found for duplicated object '{dup_obj.name}'")
                    continue

                exported_path = export_block_animation(
                    context, dup_obj, block, export_dir, self.clean_after_export
                )
                if exported_path:
                    exported_files.append(exported_path)

            if self.clean_after_export:
                for obj in list(uv_anim_collection.objects):
                    if obj.name in bpy.data.objects:
                        bpy.data.objects.remove(obj, do_unlink=True)
                if uv_anim_collection.name in bpy.data.collections:
                    bpy.data.collections.remove(uv_anim_collection)

            try:
                os.rmdir(temp_dir)
            except OSError:
                pass

        # 2. Handle Legacy Objects (with full preset support)
        for obj_name in objects_legacy:
            if obj_name not in bpy.data.objects:
                continue
            obj = bpy.data.objects[obj_name]
            frames = obj.uv_animation_frames
            num_frames = len(frames)
            if num_frames == 0:
                continue

            base_name = sanitize_name(obj.name)

            main_collection = bpy.data.collections.get("uv_anim")
            if not main_collection:
                main_collection = bpy.data.collections.new("uv_anim")
                context.scene.collection.children.link(main_collection)

            obj_collection = bpy.data.collections.get(base_name)
            if obj_collection:
                for child in list(obj_collection.objects):
                    if child.name in bpy.data.objects:
                        bpy.data.objects.remove(child, do_unlink=True)
                bpy.data.collections.remove(obj_collection)

            obj_collection = bpy.data.collections.new(base_name)
            main_collection.children.link(obj_collection)

            duplicated_objects = []
            texture_materials = {}  # Cache materials by texture path

            for idx, frame in enumerate(frames):
                dup = obj.copy()
                dup.data = obj.data.copy()

                # Copy the original material without renaming it
                if obj.active_material:
                    original_mat = obj.active_material
                    new_mat = original_mat.copy()
                    # Keep the base name (Blender will add .001, .002 etc.)
                    new_mat.name = original_mat.name
                    if dup.data.materials:
                        dup.data.materials[0] = new_mat
                    else:
                        dup.data.materials.append(new_mat)
                    dup.active_material = new_mat

                    tex_path = frame.texture_path
                    if tex_path:
                        assign_texture_to_duplicate(dup, tex_path, texture_materials, base_name, idx)

                dup.uv_animation_frames.clear()
                dup.uv_texture_items.clear()
                dup.is_uv_animated = False
                dup.uv_animator_playback_enabled = False
                dup.name = f"{base_name}_frame{idx+1:02d}"
                obj_collection.objects.link(dup)

                uvs = json.loads(frame.uv_data)
                apply_uvs_to_object(dup, uvs, None)
                duplicated_objects.append(dup)

            if duplicated_objects:
                for ob in bpy.data.objects:
                    ob.select_set(False)
                for dup in duplicated_objects:
                    if dup.name in bpy.data.objects:
                        dup.select_set(True)
                if duplicated_objects and duplicated_objects[0].name in bpy.data.objects:
                    context.view_layer.objects.active = duplicated_objects[0]

                obj_filename = f"{base_name}_anim.obj"
                export_path = os.path.join(export_dir, obj_filename)

                class TempExportProps:
                    def __init__(self, filepath):
                        self.filepath = filepath
                        self.use_selection = True
                        self.export_colors = True
                        self.apply_modifiers = False
                        self.global_scale = 1.0
                        self.path_mode = 'ABSOLUTE'
                        self.export_textures = True

                temp_props = TempExportProps(export_path)
                result = execute_obj_export(temp_props, duplicated_objects)

                for dup in duplicated_objects:
                    if dup.name in bpy.data.objects:
                        dup.select_set(False)

                if 'FINISHED' in result:
                    exported_files.append(export_path)
                    self.report({'INFO'}, f"Exported {base_name} with {num_frames} frames to {export_path}")

                    # Collect animation data for the consolidated JSON (if preset is enabled)
                    if self.export_preset:
                        anim_data = self._collect_animation_data(
                            obj,
                            export_path,
                            frames,
                            obj.uv_texture_items,
                            associate=self.associate
                        )
                        all_animations_data.append(anim_data)
                else:
                    self.report({'WARNING'}, f"Failed to export {base_name}")

                for dup in duplicated_objects:
                    if dup.name in bpy.data.objects:
                        bpy.data.objects.remove(dup, do_unlink=True)

                if obj_collection and not obj_collection.objects:
                    if obj_collection.name in bpy.data.collections:
                        bpy.data.collections.remove(obj_collection)

                if self.clean_after_export:
                    if main_collection and not main_collection.objects and not main_collection.children:
                        if main_collection.name in bpy.data.collections:
                            bpy.data.collections.remove(main_collection)

        # Write the consolidated preset JSON if we have animations
        if self.export_preset and all_animations_data:
            if exported_files:
                first_obj_path = exported_files[0]
                base_name = os.path.splitext(os.path.basename(first_obj_path))[0]
                if base_name.endswith('_anim'):
                    base_name = base_name[:-5]
                self._write_consolidated_preset(export_dir, base_name, all_animations_data)
            else:
                base_name = os.path.basename(export_dir)
                self._write_consolidated_preset(export_dir, base_name, all_animations_data)

        restore_ps1_render(context, ps1_was_active)

        for ob in bpy.data.objects:
            ob.select_set(False)
        for name in original_selection:
            if name in bpy.data.objects:
                bpy.data.objects[name].select_set(True)
        if original_active and original_active in bpy.data.objects:
            context.view_layer.objects.active = bpy.data.objects[original_active]

        if original_mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except:
                pass

        if exported_files:
            self.report({'INFO'}, f"Exported {len(exported_files)} animation(s) to {export_dir}")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No animations exported.")
            return {'CANCELLED'}

    def invoke(self, context, event):
        if not self.filepath:
            if bpy.data.filepath:
                scene_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                self.filepath = os.path.join(os.path.dirname(bpy.data.filepath), f"{scene_name}_anim.obj")
            else:
                self.filepath = os.path.join(os.path.expanduser("~"), "animation_export.obj")
        return super().invoke(context, event)