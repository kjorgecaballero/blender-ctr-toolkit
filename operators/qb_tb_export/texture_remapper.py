import os
import bpy
import shutil

class TextureRemapper:
    """
    Handles texture remapping and copying for export operations.
    
    Features:
    - Copy textures to export folder
    - Remap Blender material paths
    - Handle both packed and external textures
    - Restore original paths after export
    """
    
    def __init__(self):
        self.original_paths = {}
    
    def get_all_texture_names_from_objects(self, valid_objects):
        """
        Extract all unique texture names used by objects.
        
        Args:
            valid_objects: List of objects to analyze
            
        Returns:
            list: Unique texture filenames
        """
        texture_names = set()
        
        for obj in valid_objects:
            if obj.type == 'MESH':
                for material_slot in obj.material_slots:
                    if material_slot.material:
                        material = material_slot.material
                        if material.use_nodes:
                            for node in material.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image:
                                    texture_image = node.image
                                    original_path = bpy.path.abspath(texture_image.filepath_raw)
                                    
                                    # Handle packed textures
                                    if texture_image.packed_file:
                                        ext = os.path.splitext(texture_image.filepath_raw)[1]
                                        texture_name = f"{texture_image.name}{ext}" if ext else f"{texture_image.name}.png"
                                    else:
                                        # Handle external textures
                                        if original_path:
                                            texture_name = os.path.basename(original_path)
                                        else:
                                            texture_name = f"{texture_image.name}.png"
                                    
                                    if texture_name:
                                        texture_names.add(texture_name)
        
        return list(texture_names)
    
    def remap_blender_texture_paths(self, valid_objects, texture_dir):
        """
        Update Blender texture paths to point to export folder.
        
        Args:
            valid_objects: Objects with textures to remap
            texture_dir: Destination texture directory
        """
        print(f"\nRemapping texture paths in Blender to: {texture_dir}")
        
        for obj in valid_objects:
            if obj.type == 'MESH':
                for material_slot in obj.material_slots:
                    if material_slot.material:
                        material = material_slot.material
                        if material.use_nodes:
                            for node in material.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image:
                                    texture_image = node.image
                                    
                                    # Store original path for restoration
                                    original_path = bpy.path.abspath(texture_image.filepath_raw)
                                    texture_key = (material.name, node.name, texture_image.name)
                                    self.original_paths[texture_key] = original_path
                                    
                                    # Determine texture filename
                                    if texture_image.packed_file:
                                        ext = os.path.splitext(texture_image.filepath_raw)[1]
                                        texture_filename = f"{texture_image.name}{ext}" if ext else f"{texture_image.name}.png"
                                    else:
                                        if original_path:
                                            texture_filename = os.path.basename(original_path)
                                        else:
                                            texture_filename = f"{texture_image.name}.png"
                                    
                                    # Update path to export folder
                                    new_path = os.path.join(texture_dir, texture_filename)
                                    texture_image.filepath = new_path
                                    print(f"  Updated {material.name}/{node.name}: {texture_filename}")
        
        print(f"Remapped {len(self.original_paths)} texture paths")
    
    def restore_blender_texture_paths(self):
        """
        Restore original texture paths after export completion.
        """
        print(f"\nRestoring original texture paths...")
        
        restored_count = 0
        for (material_name, node_name, image_name), original_path in self.original_paths.items():
            try:
                image = bpy.data.images.get(image_name)
                if image:
                    image.filepath = original_path if original_path else ""
                    restored_count += 1
            except Exception as e:
                print(f"  Warning: Could not restore path for {image_name}: {e}")
        
        print(f"Restored {restored_count} texture paths")
        self.original_paths.clear()
    
    def copy_and_remap_textures(self, texture_dir, valid_objects, remap_in_blender=True):
        """
        Copy textures to export folder and optionally remap paths.
        
        Args:
            texture_dir: Destination directory for textures
            valid_objects: Objects containing textures
            remap_in_blender: Whether to update Blender paths
            
        Returns:
            list: Names of copied textures
        """
        textures_copied = set()
        
        for obj in valid_objects:
            if obj.type == 'MESH':
                for material_slot in obj.material_slots:
                    if material_slot.material:
                        material = material_slot.material
                        if material.use_nodes:
                            for node in material.node_tree.nodes:
                                if node.type == 'TEX_IMAGE' and node.image:
                                    texture_image = node.image
                                    original_path = bpy.path.abspath(texture_image.filepath_raw)
                                    
                                    # Handle packed textures (save to file)
                                    if texture_image.packed_file:
                                        ext = os.path.splitext(texture_image.filepath_raw)[1]
                                        texture_filename = f"{texture_image.name}{ext}" if ext else f"{texture_image.name}.png"
                                        
                                        try:
                                            dest_path = os.path.join(texture_dir, texture_filename)
                                            texture_image.save_render(dest_path)
                                            textures_copied.add(texture_filename)
                                            print(f"  Saved packed texture: {texture_filename}")
                                        except Exception as e:
                                            print(f"  Error saving packed texture {texture_image.name}: {e}")
                                    
                                    # Handle external textures (copy file)
                                    elif original_path and os.path.exists(original_path):
                                        texture_filename = os.path.basename(original_path)
                                        dest_path = os.path.join(texture_dir, texture_filename)
                                        
                                        try:
                                            shutil.copy2(original_path, dest_path)
                                            textures_copied.add(texture_filename)
                                            print(f"  Copied texture: {texture_filename}")
                                        except Exception as e:
                                            print(f"  Error copying texture {texture_filename}: {e}")
        
        print(f"\nCopied {len(textures_copied)} textures to: {texture_dir}")
        
        # Update Blender paths if requested
        if remap_in_blender:
            self.remap_blender_texture_paths(valid_objects, texture_dir)
        
        return list(textures_copied)
    
    def verify_textures_in_folder(self, texture_dir, texture_names):
        """
        Verify that all expected textures exist in the destination folder.
        
        Args:
            texture_dir: Directory to check
            texture_names: List of expected texture filenames
            
        Returns:
            bool: True if all textures are present
        """
        missing_textures = []
        
        if not os.path.exists(texture_dir):
            print(f"Texture directory does not exist: {texture_dir}")
            return False
        
        for texture_name in texture_names:
            texture_path = os.path.join(texture_dir, texture_name)
            if not os.path.exists(texture_path):
                missing_textures.append(texture_name)
        
        if missing_textures:
            print(f"Warning: {len(missing_textures)} textures not found in texture folder:")
            for texture in missing_textures[:5]:
                print(f"  - {texture}")
            if len(missing_textures) > 5:
                print(f"  ... and {len(missing_textures) - 5} more")
        
        return len(missing_textures) == 0
    
    def execute_remapping(self, obj_filepath, texture_dir, valid_objects, remap_in_blender=True):
        """
        Execute complete texture remapping workflow.
        
        Args:
            obj_filepath: Path to exported OBJ file
            texture_dir: Destination texture directory
            valid_objects: Objects to process
            remap_in_blender: Whether to update Blender paths
            
        Returns:
            bool: True if remapping was successful
        """
        print(f"\nSTARTING TEXTURE REMAPPING")
        
        # Ensure directories exist
        if not os.path.exists(os.path.dirname(obj_filepath)):
            os.makedirs(os.path.dirname(obj_filepath), exist_ok=True)
        
        if not os.path.exists(texture_dir):
            os.makedirs(texture_dir, exist_ok=True)
        
        print(f"OBJ path: {obj_filepath}")
        print(f"Texture dir: {texture_dir}")
        print(f"Remap in Blender: {remap_in_blender}")
        
        # Copy and remap textures
        copied_textures = self.copy_and_remap_textures(texture_dir, valid_objects, remap_in_blender)
        
        if not copied_textures:
            print("No textures were copied or remapped")
            return False
        
        # Print summary
        print(f"\nREMAPPING SUMMARY")
        print(f"Textures processed: {len(copied_textures)}")
        
        if remap_in_blender:
            print("SUCCESS: Texture paths updated in Blender nodes")
            print(f"Textures are now referenced from: {texture_dir}")
        else:
            print("SUCCESS: Textures copied but Blender paths not modified")
        
        return True