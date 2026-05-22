import bpy
from bpy.types import Operator
from ...utils.render import (
    ensure_all_objects_have_color_attributes,
    apply_ps1_compositing,
    remove_ps1_compositing,
    PS1MaterialFactory
)
from ...utils.render.material_setup import AdditiveTranslucentMaterialSetup

def detect_ps1_mode_from_suffix(material_name):
    """Detects PS1 mode based on material name suffix (for backward compatibility)"""
    if material_name.endswith("_0"):
        return 'HALF_TRANSPARENT'
    elif material_name.endswith("_1"):
        return 'ADDITIVE'
    elif material_name.endswith("_2"):
        return 'SUBTRACTIVE'
    else:
        return 'ADDITIVE_TRANSLUCENT'

def save_current_material_modes():
    """Saves the CURRENT modes of all materials before turning off PS1 Render"""
    saved_count = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        if hasattr(mat, 'ps1_blend_mode') and mat.ps1_blend_mode != 'NONE':
            mat.ps1_last_active_mode = mat.ps1_blend_mode
            saved_count += 1
    print(f"Saved current modes for {saved_count} materials before turning off PS1 Render")
    return saved_count

def restore_last_material_modes():
    """Restores the last saved active modes for all materials"""
    restored_count = 0
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        if hasattr(mat, 'ps1_last_active_mode') and mat.ps1_last_active_mode != 'NONE':
            last_mode = mat.ps1_last_active_mode
            mat.ps1_blend_mode = last_mode
            restored_count += 1
    print(f"Restored last active modes for {restored_count} materials when turning on PS1 Render")
    return restored_count

def setup_ps1_materials_for_all_objects(context=None):
    """Configures materials for PS1 rendering - FOR ALL OBJECTS IN THE SCENE"""
    if context is None:
        context = bpy.context
    scene = context.scene

    created_count = ensure_all_objects_have_color_attributes("VertexColor")
    if created_count > 0:
        print(f"Created {created_count} new color attributes for objects without attributes")

    processed_materials = set()
    processed_count = 0

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            if not slot.material or not slot.material.use_nodes or not slot.material.node_tree:
                continue
            if slot.material in processed_materials:
                continue
            processed_materials.add(slot.material)

            if hasattr(slot.material, 'ps1_blend_mode') and slot.material.ps1_blend_mode != 'NONE':
                detected_mode = slot.material.ps1_blend_mode
            else:
                detected_mode = 'ADDITIVE_TRANSLUCENT'
                slot.material.ps1_blend_mode = detected_mode

            try:
                setup = PS1MaterialFactory.get_material_setup(slot.material, detected_mode)
                success = setup.apply_setup()
                if success:
                    print(f"Material '{slot.material.name}': Applied mode {detected_mode}")
                    processed_count += 1
            except Exception as e:
                print(f"Error applying PS1 material to '{slot.material.name}': {e}")

    context.view_layer.update()
    print(f"PS1 materials setup completed. Processed {processed_count} materials from all objects in scene.")
    return processed_count

def restore_standard_materials_for_all_objects(context=None):
    """Restores materials to standard Blender materials for ALL objects"""
    if context is None:
        context = bpy.context
    processed = set()
    processed_count = 0

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            if not slot.material or not slot.material.use_nodes or not slot.material.node_tree:
                continue
            if slot.material in processed:
                continue
            processed.add(slot.material)
            nodes = slot.material.node_tree.nodes
            links = slot.material.node_tree.links

            image_node = next((n for n in nodes if n.type == 'TEX_IMAGE'), None)
            output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

            if not output_node:
                output_node = nodes.get("Material Output")
            if not output_node:
                continue

            for node in list(nodes):
                if node not in [image_node, output_node]:
                    nodes.remove(node)

            if image_node:
                principled = nodes.new(type='ShaderNodeBsdfPrincipled')
                principled.location = (0, 0)
                try:
                    if 'Specular' in principled.inputs:
                        principled.inputs['Specular'].default_value = 0.0
                except Exception as e:
                    print(f"Warning: Could not set Specular for {slot.material.name}: {e}")
                try:
                    links.new(image_node.outputs['Color'], principled.inputs['Base Color'])
                    links.new(principled.outputs['BSDF'], output_node.inputs['Surface'])
                except Exception as e:
                    print(f"Warning: Could not connect nodes for {slot.material.name}: {e}")

            slot.material.blend_method = 'OPAQUE'
            slot.material.use_backface_culling = False
            processed_count += 1

    context.view_layer.update()
    print(f"Standard materials restored for all objects. Processed {processed_count} materials.")
    return processed_count

def set_all_image_textures_interpolation(interpolation='Closest'):
    """Sets the interpolation of all image textures in all materials."""
    count = 0
    for mat in bpy.data.materials:
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    if node.interpolation != interpolation:
                        node.interpolation = interpolation
                        count += 1
    print(f"Interpolation of {count} textures changed to {interpolation}")
    return count

class TogglePS1Resolution(Operator):
    bl_idname = "psx.toggle_ps1_resolution"
    bl_label = "Toggle PS1 Resolution"
    bl_description = "Enable/disable low-resolution compositing (512x216) with pixelation effect"
    
    def execute(self, context):
        scene = context.scene
        new_state = not scene.ps1_resolution
        scene.ps1_resolution = new_state
        if new_state:
            apply_ps1_compositing(context)
            self.report({'INFO'}, "PS1 Resolution activated")
        else:
            remove_ps1_compositing(context)
            self.report({'INFO'}, "PS1 Resolution deactivated")
        return {'FINISHED'}

class ToggleCTRRender(Operator):
    bl_idname = "psx.toggle_ctr_render"
    bl_label = "Toggle CTR Render"
    bl_description = "Activate/deactivate full PS1-style material override, vertex color attributes, and compositing"
    
    def execute(self, context):
        scene = context.scene
        if scene.ps1_render_active:
            saved_count = save_current_material_modes()
            print(f"Saved {saved_count} material modes before turning off PS1 Render")
            processed_count = restore_standard_materials_for_all_objects(context)
            set_all_image_textures_interpolation('Linear')
            if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'use_shadows'):
                scene.eevee.use_shadows = scene.ps1_prev_shadow_state
            scene.ps1_render_active = False
            scene.psx_render_state = False
            scene.view_settings.view_transform = 'Standard'
            scene.view_settings.look = 'None'
            context.view_layer.update()
            self.report({'INFO'}, f"CTR Render deactivated. {processed_count} materials restored, Color Management: Standard")
        else:
            detected_count = 0
            for mat in bpy.data.materials:
                if hasattr(mat, 'ps1_blend_mode') and mat.ps1_blend_mode == 'NONE':
                    suffix_mode = detect_ps1_mode_from_suffix(mat.name)
                    if suffix_mode != 'ADDITIVE_TRANSLUCENT':
                        mat.ps1_blend_mode = suffix_mode
                        detected_count += 1
                        print(f"Auto-detected mode '{suffix_mode}' for material '{mat.name}' from suffix")
            
            restored_count = restore_last_material_modes()
            created_count = ensure_all_objects_have_color_attributes("VertexColor")
            processed_count = setup_ps1_materials_for_all_objects(context)
            set_all_image_textures_interpolation('Closest')
            scene.view_settings.view_transform = 'Standard'
            scene.view_settings.look = 'None'
            if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'use_shadows'):
                scene.ps1_prev_shadow_state = scene.eevee.use_shadows
                scene.eevee.use_shadows = False
            if context.area and context.area.type == 'VIEW_3D':
                for space in context.area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'RENDERED'
                        space.overlay.show_overlays = False
            scene.ps1_render_active = True
            scene.psx_render_state = True
            context.view_layer.update()
            self.report({'INFO'}, f"CTR Render activated. {detected_count} materials detected from suffixes, {restored_count} restored, {processed_count} processed")
        return {'FINISHED'}