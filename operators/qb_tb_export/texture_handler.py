"""
Texture handling for QB/TB export
"""

import os
import shutil
import bpy


class TextureHandler:
    """Handles texture copying and management"""
    
    def __init__(self):
        self.textures_processed = set()
        self.textures_copied = 0
    
    def copy_textures_to_folder(self, texture_dir, objects):
        """Copy textures used by objects to destination folder"""
        
        for obj in objects:
            if obj.type == 'MESH':
                for material_slot in obj.material_slots:
                    if material_slot.material:
                        material = material_slot.material
                        if material.use_nodes:
                            for node in material.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image:
                                    self._process_texture_image(node.image, texture_dir)
        
        print(f"Total textures copied: {self.textures_copied} to {texture_dir}")
        return self.textures_processed
    
    def _process_texture_image(self, texture_image, texture_dir):
        """Process a single texture image"""
        texture_path = bpy.path.abspath(texture_image.filepath_raw)
        
        # Handle packed textures
        if texture_image.packed_file:
            self._save_packed_texture(texture_image, texture_dir)
        
        # Handle external textures
        elif texture_path and os.path.exists(texture_path):
            self._copy_external_texture(texture_path, texture_dir)
    
    def _save_packed_texture(self, texture_image, texture_dir):
        """Save packed texture to file"""
        try:
            texture_name = texture_image.name + os.path.splitext(texture_image.filepath_raw)[1]
            if not texture_name:
                texture_name = texture_image.name + ".png"
            
            dest_path = os.path.join(texture_dir, texture_name)
            texture_image.save_render(dest_path)
            
            self.textures_processed.add(texture_image.name)
            self.textures_copied += 1
            print(f"Packed texture saved: {texture_name}")
        except Exception as e:
            print(f"Error saving packed texture {texture_image.name}: {e}")
    
    def _copy_external_texture(self, texture_path, texture_dir):
        """Copy external texture file"""
        if texture_path not in self.textures_processed:
            try:
                texture_name = os.path.basename(texture_path)
                dest_path = os.path.join(texture_dir, texture_name)
                
                shutil.copy2(texture_path, dest_path)
                self.textures_processed.add(texture_path)
                self.textures_copied += 1
                print(f"Texture copied: {texture_name}")
            except Exception as e:
                print(f"Error copying texture {texture_name}: {e}")