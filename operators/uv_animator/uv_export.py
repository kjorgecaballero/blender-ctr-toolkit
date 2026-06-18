import bpy
import os
import json
import re
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from ...utils.uv_animator.uv_animator_utils import apply_uvs_to_object
from ...utils.compat import execute_obj_export
from ...utils.export_helpers import temporary_disable_ps1_render, restore_ps1_render


def sanitize_name(name):
    """Replace any non-alphanumeric character (except underscore) with underscore."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


def set_texture_to_material(material, texture_path):
    """
    Assign a texture image to the first TEX_IMAGE node in the material.
    If no TEX_IMAGE node exists, create one.
    """
    if not material or not material.use_nodes:
        return

    # Look for existing TEX_IMAGE node
    tex_node = None
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            tex_node = node
            break

    # If no TEX_IMAGE node, create one
    if not tex_node:
        tex_node = material.node_tree.nodes.new('ShaderNodeTexImage')
        # Connect to Principled BSDF base color if exists
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                material.node_tree.links.new(tex_node.outputs['Color'], node.inputs['Base Color'])
                break

    # Load the image and assign it
    if texture_path and os.path.exists(texture_path):
        try:
            img = bpy.data.images.load(texture_path, check_existing=True)
            tex_node.image = img
        except Exception as e:
            print(f"Warning: Could not load texture {texture_path}: {e}")
    elif texture_path:
        print(f"Warning: Texture file not found: {texture_path}")


class UV_OT_ExportAnimation(Operator, ExportHelper):
    """Export UV animation frames as separate objects in a single OBJ file per object"""
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
        # Determine which objects to export
        if context.selected_objects:
            objects = [obj for obj in context.selected_objects
                       if obj.type == 'MESH' and obj.is_uv_animated and len(obj.uv_animation_frames) > 0]
        else:
            objects = [obj for obj in bpy.data.objects
                       if obj.type == 'MESH' and obj.is_uv_animated and len(obj.uv_animation_frames) > 0]

        if not objects:
            self.report({'WARNING'}, "No animated objects with frames found.")
            return {'CANCELLED'}

        # Save current state
        original_selection = [obj for obj in context.selected_objects]
        original_active = context.view_layer.objects.active
        original_mode = context.mode

        # Ensure we are in Object mode for safe operations
        if original_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        export_dir = os.path.dirname(self.filepath)
        if not export_dir:
            export_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.path.expanduser("~")

        ps1_was_active = temporary_disable_ps1_render(context)

        exported_count = 0
        for obj in objects:
            frames = obj.uv_animation_frames
            num_frames = len(frames)
            if num_frames == 0:
                continue

            base_name = sanitize_name(obj.name)

            # Create main collection 'uv_anim' if it doesn't exist
            main_collection = bpy.data.collections.get("uv_anim")
            if not main_collection:
                main_collection = bpy.data.collections.new("uv_anim")
                context.scene.collection.children.link(main_collection)

            # Remove existing sub-collection for this object if it exists
            obj_collection = bpy.data.collections.get(base_name)
            if obj_collection:
                for child in list(obj_collection.objects):
                    bpy.data.objects.remove(child, do_unlink=True)
                bpy.data.collections.remove(obj_collection)

            # Create new sub-collection for this object
            obj_collection = bpy.data.collections.new(base_name)
            main_collection.children.link(obj_collection)

            # Duplicate object for each frame and apply UVs + texture
            duplicated_objects = []
            for idx, frame in enumerate(frames):
                # Duplicate object and mesh data
                dup = obj.copy()
                dup.data = obj.data.copy()

                # Create a unique material for this duplicate
                if obj.active_material:
                    # Copy the active material
                    original_mat = obj.active_material
                    new_mat = original_mat.copy()
                    new_mat.name = f"{base_name}_frame{idx+1:02d}_mat"

                    # Assign the new material to the duplicate
                    if dup.data.materials:
                        # Replace the first material slot
                        dup.data.materials[0] = new_mat
                    else:
                        dup.data.materials.append(new_mat)
                    dup.active_material = new_mat

                    # Assign the specific texture for this frame
                    tex_path = frame.texture_path
                    if tex_path:
                        set_texture_to_material(new_mat, tex_path)

                # Clear animation properties from duplicate to avoid contamination
                dup.uv_animation_frames.clear()
                dup.uv_texture_items.clear()
                dup.is_uv_animated = False
                dup.uv_animator_playback_enabled = False
                dup.name = f"{base_name}_frame{idx+1:02d}"
                obj_collection.objects.link(dup)

                # Apply UVs from frame (this also updates the mesh)
                uvs = json.loads(frame.uv_data)
                apply_uvs_to_object(dup, uvs, None)  # Texture already assigned via material

                duplicated_objects.append(dup)

            # Export this object's frames
            # Deselect all objects (manual, no bpy.ops)
            for ob in bpy.data.objects:
                ob.select_set(False)

            # Select only this object's duplicates
            for dup in duplicated_objects:
                dup.select_set(True)

            if duplicated_objects:
                context.view_layer.objects.active = duplicated_objects[0]

            # Build unique filepath for this object
            obj_filename = f"{base_name}_anim.obj"
            export_path = os.path.join(export_dir, obj_filename)

            # Prepare export parameters
            class TempExportProps:
                def __init__(self, filepath):
                    self.filepath = filepath
                    self.use_selection = True
                    self.export_colors = True
                    self.apply_modifiers = False
                    self.global_scale = 1.0
                    self.path_mode = 'ABSOLUTE'  # Use absolute paths for textures
                    self.export_quadblocks = False
                    self.export_triblocks = False
                    self.export_invalid_uvs = False
                    self.export_degenerated_uvs = False
                    self.export_textures = True  # Export textures in MTL

            temp_props = TempExportProps(export_path)
            result = execute_obj_export(temp_props, duplicated_objects)

            # Deselect after export
            for dup in duplicated_objects:
                dup.select_set(False)

            if 'FINISHED' in result:
                exported_count += 1
                self.report({'INFO'}, f"Exported {base_name} with {num_frames} frames to {export_path}")
            else:
                self.report({'WARNING'}, f"Failed to export {base_name}")

            # Cleanup
            # Always remove duplicated objects (they are temporary)
            for dup in duplicated_objects:
                if dup.name in bpy.data.objects:
                    bpy.data.objects.remove(dup, do_unlink=True)

            # Remove sub-collection if empty
            if obj_collection and not obj_collection.objects:
                if obj_collection.name in bpy.data.collections:
                    bpy.data.collections.remove(obj_collection)

            # If clean_after_export, also remove main collection if empty
            if self.clean_after_export:
                if main_collection and not main_collection.objects and not main_collection.children:
                    if main_collection.name in bpy.data.collections:
                        bpy.data.collections.remove(main_collection)

        # Restore PS1 render state
        restore_ps1_render(context, ps1_was_active)

        # Restore original selection and active object (manual)
        for ob in bpy.data.objects:
            ob.select_set(False)
        for ob in original_selection:
            if ob.name in bpy.data.objects:
                ob.select_set(True)
        if original_active and original_active.name in bpy.data.objects:
            context.view_layer.objects.active = original_active

        # Restore original mode if possible
        if original_mode != context.mode:
            try:
                bpy.ops.object.mode_set(mode=original_mode)
            except:
                pass

        if exported_count == 0:
            self.report({'WARNING'}, "No animations exported.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Exported {exported_count} animation(s) to {export_dir}")
        return {'FINISHED'}

    def invoke(self, context, event):
        if not self.filepath:
            if bpy.data.filepath:
                scene_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                self.filepath = os.path.join(os.path.dirname(bpy.data.filepath), f"{scene_name}_anim.obj")
            else:
                self.filepath = os.path.join(os.path.expanduser("~"), "animation_export.obj")
        return super().invoke(context, event)