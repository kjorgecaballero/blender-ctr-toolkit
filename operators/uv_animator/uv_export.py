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

def set_texture_to_material(material, texture_path):
    if not material or not material.use_nodes:
        return
    tex_node = None
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            tex_node = node
            break
    if not tex_node:
        tex_node = material.node_tree.nodes.new('ShaderNodeTexImage')
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                material.node_tree.links.new(tex_node.outputs['Color'], node.inputs['Base Color'])
                break
    if texture_path and os.path.exists(texture_path):
        try:
            img = bpy.data.images.load(texture_path, check_existing=True)
            tex_node.image = img
        except Exception as e:
            print(f"Warning: Could not load texture {texture_path}: {e}")

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
    for idx, frame in enumerate(frames):
        dup = dup_obj.copy()
        dup.data = dup_obj.data.copy()
        dup.name = f"{base_name}_frame{idx+1:02d}"
        frame_collection.objects.link(dup)

        uvs = json.loads(frame.uv_data)
        centers = json.loads(frame.face_centers) if frame.face_centers else None
        apply_uvs_to_material(dup, material_name, uvs, centers_ordered=centers)

        if frame.texture_path and dup.active_material:
            set_texture_to_material(dup.active_material, frame.texture_path)

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

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Export Options", icon='EXPORT')
        box.prop(self, "clean_after_export")

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


        # 1. Handle Constant Materials (blocks) using duplicate_all_blocks_by_group

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


        # 2. Handle Legacy Objects

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
            for idx, frame in enumerate(frames):
                dup = obj.copy()
                dup.data = obj.data.copy()

                if obj.active_material:
                    original_mat = obj.active_material
                    new_mat = original_mat.copy()
                    new_mat.name = f"{base_name}_frame{idx+1:02d}_mat"
                    if dup.data.materials:
                        dup.data.materials[0] = new_mat
                    else:
                        dup.data.materials.append(new_mat)
                    dup.active_material = new_mat

                    tex_path = frame.texture_path
                    if tex_path:
                        set_texture_to_material(new_mat, tex_path)

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