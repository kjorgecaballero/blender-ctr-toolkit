import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from ...utils.material_utils import update_derived_materials


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
        layout.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        layout.operator("material.remap_from_file", text="", icon='FILE_FOLDER')

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

        if base_materials:
            updated = update_derived_materials(obj, list(base_materials), new_image, update_base_material=True)
            self.report({'INFO'}, f"Remapped {updated} materials (base + constants)")
        else:
            mat = bpy.data.materials.get(self.selected_mat_name)
            if not mat:
                self.report({'ERROR'}, f"Material '{self.selected_mat_name}' not found")
                return {'CANCELLED'}
            if mat.use_nodes:
                found = False
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        node.image = new_image
                        found = True
                if found:
                    self.report({'INFO'}, f"Remapped texture for '{mat.name}'")
                else:
                    self.report({'WARNING'}, "No texture image node found")
            else:
                self.report({'WARNING'}, "Material does not use nodes")
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

        if base_materials:
            updated = update_derived_materials(obj, list(base_materials), image, update_base_material=True)
            self.report({'INFO'}, f"Remapped {updated} materials")
        else:
            mat = bpy.data.materials.get(selected_mat_name)
            if mat and mat.use_nodes:
                found = False
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        node.image = image
                        found = True
                if found:
                    self.report({'INFO'}, f"Remapped texture for '{mat.name}'")
                else:
                    self.report({'WARNING'}, "No texture image node found")
            else:
                self.report({'WARNING'}, "Material not found or does not use nodes")
        return {'FINISHED'}


classes = [MATERIAL_OT_RemapMaterial, MATERIAL_OT_RemapFromFile]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)