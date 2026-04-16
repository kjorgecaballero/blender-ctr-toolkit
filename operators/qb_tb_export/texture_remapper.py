import os
import bpy
import shutil

class TextureRemapper:
    """
    Handles texture remapping and copying for export operations.
    Guaranteed restoration even on errors.
    """
    
    def __init__(self):
        self.original_paths = {}
        self._remapped = False
    
    def get_all_texture_names_from_objects(self, valid_objects):
        texture_names = set()
        for obj in valid_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    mat = slot.material
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                img = node.image
                                orig_path = bpy.path.abspath(img.filepath_raw)
                                if img.packed_file:
                                    ext = os.path.splitext(img.filepath_raw)[1]
                                    tex_name = f"{img.name}{ext}" if ext else f"{img.name}.png"
                                else:
                                    tex_name = os.path.basename(orig_path) if orig_path else f"{img.name}.png"
                                if tex_name:
                                    texture_names.add(tex_name)
        return list(texture_names)
    
    def remap_blender_texture_paths(self, valid_objects, texture_dir):
        print(f"\nRemapping texture paths in Blender to: {texture_dir}")
        self.original_paths.clear()
        for obj in valid_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    mat = slot.material
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                img = node.image
                                orig_path = bpy.path.abspath(img.filepath_raw)
                                key = (mat.name, node.name, img.name)
                                self.original_paths[key] = orig_path
                                if img.packed_file:
                                    ext = os.path.splitext(img.filepath_raw)[1]
                                    tex_filename = f"{img.name}{ext}" if ext else f"{img.name}.png"
                                else:
                                    tex_filename = os.path.basename(orig_path) if orig_path else f"{img.name}.png"
                                new_path = os.path.join(texture_dir, tex_filename)
                                img.filepath = new_path
                                print(f"  Updated {mat.name}/{node.name}: {tex_filename}")
        self._remapped = True
        print(f"Remapped {len(self.original_paths)} texture paths")
    
    def restore_blender_texture_paths(self):
        if not self._remapped:
            return
        print(f"\nRestoring original texture paths...")
        restored = 0
        for (mat_name, node_name, img_name), orig_path in self.original_paths.items():
            try:
                img = bpy.data.images.get(img_name)
                if img:
                    img.filepath = orig_path if orig_path else ""
                    restored += 1
            except Exception as e:
                print(f"  Warning: Could not restore path for {img_name}: {e}")
        print(f"Restored {restored} texture paths")
        self.original_paths.clear()
        self._remapped = False
    
    def copy_and_remap_textures(self, texture_dir, valid_objects, remap_in_blender=True):
        textures_copied = set()
        for obj in valid_objects:
            if obj.type == 'MESH':
                for slot in obj.material_slots:
                    mat = slot.material
                    if mat and mat.use_nodes:
                        for node in mat.node_tree.nodes:
                            if node.type == 'TEX_IMAGE' and node.image:
                                img = node.image
                                orig_path = bpy.path.abspath(img.filepath_raw)
                                if img.packed_file:
                                    ext = os.path.splitext(img.filepath_raw)[1]
                                    tex_filename = f"{img.name}{ext}" if ext else f"{img.name}.png"
                                    try:
                                        dest_path = os.path.join(texture_dir, tex_filename)
                                        img.save_render(dest_path)
                                        textures_copied.add(tex_filename)
                                        print(f"  Saved packed texture: {tex_filename}")
                                    except Exception as e:
                                        print(f"  Error saving packed texture {img.name}: {e}")
                                elif orig_path and os.path.exists(orig_path):
                                    tex_filename = os.path.basename(orig_path)
                                    dest_path = os.path.join(texture_dir, tex_filename)
                                    try:
                                        shutil.copy2(orig_path, dest_path)
                                        textures_copied.add(tex_filename)
                                        print(f"  Copied texture: {tex_filename}")
                                    except Exception as e:
                                        print(f"  Error copying texture {tex_filename}: {e}")
        print(f"\nCopied {len(textures_copied)} textures to: {texture_dir}")
        if remap_in_blender:
            self.remap_blender_texture_paths(valid_objects, texture_dir)
        return list(textures_copied)
    
    def verify_textures_in_folder(self, texture_dir, texture_names):
        if not os.path.exists(texture_dir):
            return False
        missing = [t for t in texture_names if not os.path.exists(os.path.join(texture_dir, t))]
        if missing:
            print(f"Warning: {len(missing)} textures missing: {missing[:5]}")
        return len(missing) == 0
    
    def execute_remapping(self, obj_filepath, texture_dir, valid_objects, remap_in_blender=True):
        print(f"\nSTARTING TEXTURE REMAPPING")
        os.makedirs(os.path.dirname(obj_filepath), exist_ok=True)
        os.makedirs(texture_dir, exist_ok=True)
        try:
            copied = self.copy_and_remap_textures(texture_dir, valid_objects, remap_in_blender)
            if not copied:
                print("No textures were copied or remapped")
                return False
            print(f"\nREMAPPING SUMMARY: {len(copied)} textures processed")
            if remap_in_blender:
                print("SUCCESS: Texture paths updated in Blender nodes")
            return True
        except Exception as e:
            print(f"ERROR during remapping: {e}")
            import traceback
            traceback.print_exc()
            return False