import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from ...utils.material_utils import update_derived_materials


def ensure_texture_node(material, image):
    """
    Ensure the material has a texture image node with the given image.
    If a texture image node already exists, replace its image.
    If none exists, create one and assign the image.
    Also ensures material uses nodes.
    """
    if not material.use_nodes:
        material.use_nodes = True
    nodes = material.node_tree.nodes
    tex_node = None
    # Look for existing texture image node
    for node in nodes:
        if node.type == 'TEX_IMAGE':
            tex_node = node
            break
    if tex_node is None:
        # Create a new texture image node
        tex_node = nodes.new(type='ShaderNodeTexImage')
        # Try to locate the Principled BSDF to connect the texture
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                material.node_tree.links.new(tex_node.outputs['Color'], node.inputs['Base Color'])
                break
    tex_node.image = image
    return True


def material_has_texture_node(mat):
    """
    Return True if the material has at least one TEX_IMAGE node.
    Also returns True if the material has a PS1 blend mode assigned (because
    PS1 materials always contain a texture node).
    """
    if not mat:
        return False
    # If the material is already under PS1 render control, assume it has a texture node
    if hasattr(mat, 'ps1_blend_mode') and mat.ps1_blend_mode != 'NONE':
        return True
    if not mat.use_nodes or not mat.node_tree:
        return False
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            return True
    return False


def temporary_disable_ps1_render(context):
    """Disable PS1 render if active, return True if it was active."""
    scene = context.scene
    was_active = getattr(scene, 'ps1_render_active', False)
    if was_active:
        bpy.ops.psx.toggle_ctr_render()
    return was_active


def restore_ps1_render(context, was_active):
    """Restore PS1 render if it was active before."""
    if was_active and not getattr(context.scene, 'ps1_render_active', False):
        bpy.ops.psx.toggle_ctr_render()


class MATERIAL_OT_RemapMaterial(Operator):
    """Remap texture image for the selected material and all linked materials (base + constants)."""
    bl_idname = "material.remap_material"
    bl_label = "Remap"
    bl_description = "Change the texture image for this material and all derived/linked materials"
    bl_options = {'REGISTER', 'UNDO'}

    new_image_name: StringProperty(name="New Image", default="")

    @classmethod
    def poll(cls, context):
        props = context.scene.ctr_material_list
        return props.selected_index >= 0 and props.selected_index < len(props.items)

    def invoke(self, context, event):
        props = context.scene.ctr_material_list
        self.selected_mat_name = props.items[props.selected_index].name
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Material: {self.selected_mat_name}")
        row = layout.row(align=True)
        row.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        row.operator("material.remap_from_file", text="", icon='FILE_FOLDER')

    def execute(self, context):
        obj = context.active_object
        new_image = bpy.data.images.get(self.new_image_name)
        if not new_image:
            self.report({'ERROR'}, "Please select an image")
            return {'CANCELLED'}

        const_dict = obj.get("constant_materials", {}) if obj else {}
        base_materials = set()

        if self.selected_mat_name in const_dict:
            base = const_dict[self.selected_mat_name].get("original_material", "")
            if base:
                base_materials.add(base)
        else:
            for info in const_dict.values():
                if info.get("original_material") == self.selected_mat_name:
                    base_materials.add(self.selected_mat_name)
                    break

        # Gather all material names that will be updated
        materials_to_update = []
        if base_materials:
            for base in base_materials:
                materials_to_update.append(base)
                for const_name, info in const_dict.items():
                    if info.get("original_material") == base:
                        materials_to_update.append(const_name)
        else:
            materials_to_update.append(self.selected_mat_name)

        # Check if any material lacks a texture node
        need_node_creation = False
        for mat_name in materials_to_update:
            mat = bpy.data.materials.get(mat_name)
            if not material_has_texture_node(mat):
                need_node_creation = True
                # Debug: print which material is missing a texture node
                print(f"DEBUG: Material '{mat_name}' has no texture node. Need to disable PS1 render.")
                break

        # Only disable PS1 render if it's active AND we need to create nodes
        was_ps1_active = False
        ps1_was_disabled = False
        if need_node_creation and getattr(context.scene, 'ps1_render_active', False):
            was_ps1_active = temporary_disable_ps1_render(context)
            ps1_was_disabled = True
            print("DEBUG: PS1 render temporarily disabled for node creation.")
        else:
            print("DEBUG: No need to disable PS1 render.")

        try:
            if base_materials:
                updated = update_derived_materials(
                    obj, list(base_materials), new_image,
                    update_base_material=True,
                    ensure_node_callback=ensure_texture_node
                )
                self.report({'INFO'}, f"Remapped {updated} materials (base + constants)")
            else:
                mat = bpy.data.materials.get(self.selected_mat_name)
                if not mat:
                    self.report({'ERROR'}, f"Material '{self.selected_mat_name}' not found")
                    return {'CANCELLED'}
                ensure_texture_node(mat, new_image)
                self.report({'INFO'}, f"Remapped texture for '{mat.name}'")
        finally:
            if ps1_was_disabled:
                restore_ps1_render(context, was_ps1_active)

        # Refresh the material list UI
        context.scene.ctr_material_list._update_items(context)
        return {'FINISHED'}


class MATERIAL_OT_RemapFromFile(Operator, ImportHelper):
    """Load an image from disk and remap the material(s)."""
    bl_idname = "material.remap_from_file"
    bl_label = "Remap from Image File"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.tga",
        options={'HIDDEN'}
    )

    def execute(self, context):
        filepath = self.filepath
        if not filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}

        image = None
        for img in bpy.data.images:
            if img.filepath == filepath or (img.filepath and img.filepath == bpy.path.relpath(filepath)):
                image = img
                break
        if image is None:
            try:
                image = bpy.data.images.load(filepath)
                self.report({'INFO'}, f"Loaded: {image.name}")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to load: {str(e)}")
                return {'CANCELLED'}

        props = context.scene.ctr_material_list
        if props.selected_index < 0:
            return {'CANCELLED'}
        selected_mat_name = props.items[props.selected_index].name
        obj = context.active_object
        const_dict = obj.get("constant_materials", {}) if obj else {}

        base_materials = set()
        if selected_mat_name in const_dict:
            base = const_dict[selected_mat_name].get("original_material", "")
            if base:
                base_materials.add(base)
        else:
            for info in const_dict.values():
                if info.get("original_material") == selected_mat_name:
                    base_materials.add(selected_mat_name)
                    break

        # Gather all material names that will be updated
        materials_to_update = []
        if base_materials:
            for base in base_materials:
                materials_to_update.append(base)
                for const_name, info in const_dict.items():
                    if info.get("original_material") == base:
                        materials_to_update.append(const_name)
        else:
            materials_to_update.append(selected_mat_name)

        # Check if any material lacks a texture node
        need_node_creation = False
        for mat_name in materials_to_update:
            mat = bpy.data.materials.get(mat_name)
            if not material_has_texture_node(mat):
                need_node_creation = True
                print(f"DEBUG: Material '{mat_name}' has no texture node. Need to disable PS1 render.")
                break

        was_ps1_active = False
        ps1_was_disabled = False
        if need_node_creation and getattr(context.scene, 'ps1_render_active', False):
            was_ps1_active = temporary_disable_ps1_render(context)
            ps1_was_disabled = True
            print("DEBUG: PS1 render temporarily disabled for node creation.")
        else:
            print("DEBUG: No need to disable PS1 render.")

        try:
            if base_materials:
                updated = update_derived_materials(
                    obj, list(base_materials), image,
                    update_base_material=True,
                    ensure_node_callback=ensure_texture_node
                )
                self.report({'INFO'}, f"Remapped {updated} materials")
            else:
                mat = bpy.data.materials.get(selected_mat_name)
                if not mat:
                    self.report({'ERROR'}, f"Material '{selected_mat_name}' not found")
                    return {'CANCELLED'}
                ensure_texture_node(mat, image)
                self.report({'INFO'}, f"Remapped texture for '{mat.name}'")
        finally:
            if ps1_was_disabled:
                restore_ps1_render(context, was_ps1_active)

        context.scene.ctr_material_list._update_items(context)
        return {'FINISHED'}


classes = [MATERIAL_OT_RemapMaterial, MATERIAL_OT_RemapFromFile]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)