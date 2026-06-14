import bpy
import numpy as np
from .node_configs import NODE_SETUPS


class PS1MaterialSetup:
    def __init__(self, material):
        self.mat = material
        self.mat.use_nodes = True
        self.nodes = {}

    def clear_existing_nodes(self):
        self.nodes.clear()
        for node in self.mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                self.nodes['Image Texture'] = node
                break
        nodes_to_remove = []
        for node in self.mat.node_tree.nodes:
            if node.type != 'TEX_IMAGE':
                nodes_to_remove.append(node)
        for node in nodes_to_remove:
            self.mat.node_tree.nodes.remove(node)
        if 'Image Texture' not in self.nodes:
            self.nodes['Image Texture'] = self.mat.node_tree.nodes.new('ShaderNodeTexImage')
            self.nodes['Image Texture'].name = "Image Texture"
        self.nodes['Image Texture'].location = (-1000, 0)

    def build_setup(self, mode):
        setup_config = NODE_SETUPS[mode]
        if not isinstance(setup_config['nodes'], list):
            raise TypeError(f"'nodes' for mode {mode} is not a list (got {type(setup_config['nodes'])})")
        if not isinstance(setup_config['connections'], list):
            raise TypeError(f"'connections' for mode {mode} is not a list (got {type(setup_config['connections'])})")

        for node_type, name, location, width, properties in setup_config['nodes']:
            node = self.mat.node_tree.nodes.new(node_type)
            node.name = name
            node.location = location
            node.width = width
            for prop_path, value in properties.items():
                if '.' in prop_path:
                    parts = prop_path.split('.')
                    obj = node
                    for part in parts[:-1]:
                        if '[' in part and ']' in part:
                            attr_name = part.split('[')[0]
                            index = int(part.split('[')[1].split(']')[0])
                            obj = getattr(obj, attr_name)[index]
                        else:
                            obj = getattr(obj, part)
                    setattr(obj, parts[-1], value)
                else:
                    setattr(node, prop_path, value)
            self.nodes[name] = node

        for from_node_name, from_socket, to_node_name, to_socket in setup_config['connections']:
            try:
                from_node = self.nodes[from_node_name]
                to_node = self.nodes[to_node_name]
                from_socket_obj = from_node.outputs[from_socket]
                to_socket_obj = to_node.inputs[to_socket]
                self.mat.node_tree.links.new(from_socket_obj, to_socket_obj)
            except Exception as e:
                print(f"  Error connecting {from_node_name}.{from_socket} -> {to_node_name}.{to_socket}: {e}")

    def analyze_image_texture(self):
        image_node = self.nodes.get('Image Texture')
        if not image_node or not image_node.image:
            return "NO_IMAGE"
        try:
            image = image_node.image
            if image.size[0] == 0 or image.size[1] == 0 or not image.pixels:
                print(f"Image '{image.name}' has invalid dimensions or pixel data")
                return "NO_IMAGE"
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
                return "HAS_SEMI_TRANSPARENT"
            elif solid_pixels == total_pixels:
                return "ALL_SOLID"
            elif transparent_pixels == total_pixels:
                return "ALL_TRANSPARENT"
            elif solid_pixels > 0 and transparent_pixels > 0:
                return "SOLID_AND_TRANSPARENT"
            else:
                return "UNKNOWN"
        except Exception as e:
            print(f"Error analyzing texture: {e}")
            return "UNKNOWN"

    def apply_blend_mode(self, mode, pixel_type, used_additive_translucent_setup):
        print(f"  Analyzing mode: {mode}, pixel type: {pixel_type}, used AT setup: {used_additive_translucent_setup}")
        blend_override = self.mat.ps1_blend_method_override
        if blend_override != 'AUTO':
            self.mat.blend_method = blend_override
            print(f"  Using manual blend method override: {blend_override}")
        else:
            if mode == 'ADDITIVE_TRANSLUCENT' and pixel_type == "HAS_SEMI_TRANSPARENT":
                self.mat.blend_method = 'HASHED'
                print(f"  Blend mode set to HASHED (ADDITIVE_TRANSLUCENT with semi-transparency)")
            else:
                if pixel_type == "HAS_SEMI_TRANSPARENT":
                    self.mat.blend_method = 'BLEND'
                elif pixel_type == "ALL_SOLID":
                    self.mat.blend_method = 'HASHED'
                elif pixel_type == "ALL_TRANSPARENT":
                    self.mat.blend_method = 'HASHED'
                elif pixel_type == "SOLID_AND_TRANSPARENT":
                    self.mat.blend_method = 'HASHED'
                else:
                    self.mat.blend_method = 'HASHED'

        # Compute default overlap value 
        default_overlap = not used_additive_translucent_setup

        # Determine final overlap value based on user's mode
        mode_choice = getattr(self.mat, 'ps1_transparency_overlap_mode', 'DEFAULT')
        if mode_choice == 'DEFAULT':
            final_overlap = default_overlap
            print(f"  Using DEFAULT overlap: {final_overlap}")
        else:  # MANUAL
            final_overlap = getattr(self.mat, 'ps1_transparency_overlap_manual', True)
            print(f"  Using MANUAL overlap: {final_overlap}")

        # Apply to the actual Blender property
        if hasattr(self.mat, 'use_transparency_overlap'):
            self.mat.use_transparency_overlap = final_overlap
        elif hasattr(self.mat, 'show_transparent_back'):
            self.mat.show_transparent_back = final_overlap
        else:
            print("  Material has no transparency overlap property, skipping.")

        if hasattr(self.mat, 'ps1_show_backface'):
            self.mat.use_backface_culling = not self.mat.ps1_show_backface
        else:
            self.mat.use_backface_culling = True
        self.mat.update_tag()


class AdditiveMaterialSetup(PS1MaterialSetup):
    def apply_setup(self):
        print("  Building ADDITIVE material")
        self.clear_existing_nodes()
        pixel_type = self.analyze_image_texture()
        used_additive_translucent = False
        if pixel_type != "HAS_SEMI_TRANSPARENT":
            print("  Image without semi-transparency: using ADDITIVE_TRANSLUCENT setup")
            self.build_setup('ADDITIVE_TRANSLUCENT')
            used_additive_translucent = True
        else:
            self.build_setup('ADDITIVE')
        self.apply_blend_mode('ADDITIVE', pixel_type, used_additive_translucent)
        return True


class SubtractiveMaterialSetup(PS1MaterialSetup):
    def apply_setup(self):
        print("  Building SUBTRACTIVE material")
        self.clear_existing_nodes()
        pixel_type = self.analyze_image_texture()
        used_additive_translucent = False
        if pixel_type != "HAS_SEMI_TRANSPARENT":
            print("  Image without semi-transparency: using ADDITIVE_TRANSLUCENT setup")
            self.build_setup('ADDITIVE_TRANSLUCENT')
            used_additive_translucent = True
        else:
            self.build_setup('SUBTRACTIVE')
        self.apply_blend_mode('SUBTRACTIVE', pixel_type, used_additive_translucent)
        return True


class HalfTransparentMaterialSetup(PS1MaterialSetup):
    def apply_setup(self):
        print("  Building HALF_TRANSPARENT material")
        self.clear_existing_nodes()
        pixel_type = self.analyze_image_texture()
        used_additive_translucent = False
        if pixel_type != "HAS_SEMI_TRANSPARENT":
            print("  Image without semi-transparency: using ADDITIVE_TRANSLUCENT setup")
            self.build_setup('ADDITIVE_TRANSLUCENT')
            used_additive_translucent = True
        else:
            self.build_setup('HALF_TRANSPARENT')
        self.apply_blend_mode('HALF_TRANSPARENT', pixel_type, used_additive_translucent)
        return True


class AdditiveTranslucentMaterialSetup(PS1MaterialSetup):
    def apply_setup(self):
        print("  Building ADDITIVE_TRANSLUCENT material")
        self.clear_existing_nodes()
        pixel_type = self.analyze_image_texture()
        self.build_setup('ADDITIVE_TRANSLUCENT')
        self.apply_blend_mode('ADDITIVE_TRANSLUCENT', pixel_type, used_additive_translucent_setup=True)
        return True


class PS1MaterialFactory:
    @staticmethod
    def get_material_setup(material, mode):
        if mode == 'ADDITIVE':
            return AdditiveMaterialSetup(material)
        elif mode == 'SUBTRACTIVE':
            return SubtractiveMaterialSetup(material)
        elif mode == 'HALF_TRANSPARENT':
            return HalfTransparentMaterialSetup(material)
        elif mode == 'ADDITIVE_TRANSLUCENT':
            return AdditiveTranslucentMaterialSetup(material)
        else:
            return AdditiveMaterialSetup(material)