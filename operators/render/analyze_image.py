import bpy
import numpy as np
from bpy.types import Operator

class AnalyzeImage(Operator):
    bl_idname = "psx.analyze_image"
    bl_label = "Analyze Image"
    def execute(self, context):
        scene = context.scene
        obj = context.active_object
        if not obj:
            scene.pixel_analysis_result = "No object selected"
            self.report({'ERROR'}, "No object selected")
            return {'CANCELLED'}
        image = None
        for mat_slot in obj.material_slots:
            if mat_slot.material:
                material = mat_slot.material
                if material.use_nodes:
                    for node in material.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image:
                            image = node.image
                            break
                        elif node.type == 'BSDF_PRINCIPLED':
                            for input in node.inputs:
                                if input.is_linked:
                                    for link in input.links:
                                        if link.from_node.type == 'TEX_IMAGE' and link.from_node.image:
                                            image = link.from_node.image
                                            break
                if image:
                    break
        if not image:
            scene.pixel_analysis_result = "No image texture found on selected object"
            self.report({'ERROR'}, "No image texture found on selected object")
            return {'CANCELLED'}
        try:
            if image.size[0] == 0 or image.size[1] == 0 or not image.pixels:
                scene.pixel_analysis_result = f"Image '{image.name}' has invalid dimensions or pixel data"
                self.report({'ERROR'}, scene.pixel_analysis_result)
                return {'CANCELLED'}
            width, height = image.size
            pixels = np.array(image.pixels).reshape(height, width, 4)
            solid_pixels = 0
            transparent_pixels = 0
            semi_transparent_pixels = 0
            ALPHA_THRESHOLD = 0.01
            ALPHA_THRESHOLD_MAX = 1
            for y in range(height):
                for x in range(width):
                    alpha = pixels[y, x, 3]
                    if alpha >= ALPHA_THRESHOLD_MAX:
                        solid_pixels += 1
                    elif alpha <= ALPHA_THRESHOLD:
                        transparent_pixels += 1
                    else:
                        semi_transparent_pixels += 1
            total_pixels = width * height
            if semi_transparent_pixels > 0:
                image_type = "CONTAINS SEMI-TRANSPARENT"
                blend_recommendation = "BLEND (or HASHED if ADDITIVE_TRANSLUCENT)"
            elif solid_pixels == total_pixels:
                image_type = "100% SOLID"
                blend_recommendation = "HASHED - 100% solid"
            elif transparent_pixels == total_pixels:
                image_type = "100% TRANSPARENT"
                blend_recommendation = "HASHED - 100% transparent"
            elif solid_pixels > 0 and transparent_pixels > 0:
                image_type = "SOLID AND TRANSPARENT (NO SEMI-TRANSPARENT)"
                blend_recommendation = "HASHED - solids + transparents (recommended)"
            else:
                image_type = "UNKNOWN TYPE"
                blend_recommendation = "HASHED - unknown case"
            result_text = f"Image: {image.name}\nType: {image_type}\nRecommended: {blend_recommendation}\nSize: {width}x{height} ({total_pixels} pixels)\nSolid: {solid_pixels} ({solid_pixels/total_pixels*100:.1f}%)\nTransparent: {transparent_pixels} ({transparent_pixels/total_pixels*100:.1f}%)\nSemi-transparent: {semi_transparent_pixels} ({semi_transparent_pixels/total_pixels*100:.1f}%)"
            scene.pixel_analysis_result = result_text
            self.report({'INFO'}, "Analysis complete")
        except Exception as e:
            scene.pixel_analysis_result = f"Error analyzing image: {str(e)}"
            self.report({'ERROR'}, f"Error analyzing image: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}