import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper


class LIST_OT_UpdateAllFromBase(Operator):
    """Update all constant materials that share the same base material"""
    bl_idname = "list.update_all_from_base"
    bl_label = "Update Derived"
    bl_description = "Change the texture image of all constant materials derived from the same base material"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(name="Constant Material")
    new_image_name: StringProperty(name="New Image", default="")
    update_base_material: BoolProperty(
        name="Also Update Base Material",
        description="If enabled, the original base material will also be updated",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS')

    def invoke(self, context, event):
        obj = context.edit_object
        if self.material_name not in obj.get("constant_materials", {}):
            self.report({'ERROR'}, "Constant material not found")
            return {'CANCELLED'}

        const_info = obj["constant_materials"][self.material_name]
        base_mat_name = const_info.get("original_material", "")

        if not base_mat_name:
            self.report({'ERROR'}, "Could not determine base material")
            return {'CANCELLED'}

        # Pre-load list of available images
        images = [img.name for img in bpy.data.images]

        # Show dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        obj = context.edit_object

        const_info = obj["constant_materials"].get(self.material_name, {})
        base_mat_name = const_info.get("original_material", "unknown")

        layout.label(text=f"Base material: {base_mat_name}")

        # Row with prop_search + folder button
        row = layout.row(align=True)
        row.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        # Button to load new image from disk
        op = row.operator("list.update_from_file", text="", icon='FILE_FOLDER')
        op.material_name = self.material_name
        op.update_base_material = self.update_base_material

        # Option to also update the base material
        layout.prop(self, "update_base_material")

        # Count how many constant materials will be updated
        count = 0
        for mat_name, info in obj["constant_materials"].items():
            if info.get("original_material") == base_mat_name:
                count += 1
        layout.label(text=f"{count} constant material(s) will be updated")
        if self.update_base_material:
            layout.label(text="The original base material will also be updated", icon='INFO')

    def execute(self, context):
        obj = context.edit_object
        const_info = obj["constant_materials"][self.material_name]
        base_mat_name = const_info.get("original_material", "")

        if not self.new_image_name:
            self.report({'ERROR'}, "Please select an image")
            return {'CANCELLED'}

        new_image = bpy.data.images.get(self.new_image_name)
        if not new_image:
            self.report({'ERROR'}, f"Image '{self.new_image_name}' not found")
            return {'CANCELLED'}

        updated = 0

        # 1. Update all derived constant materials
        for const_name, info in obj["constant_materials"].items():
            if info.get("original_material") == base_mat_name:
                mat = bpy.data.materials.get(const_name)
                if mat and mat.use_nodes:
                    # Find the first TexImage node and replace its image
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image is not None:
                            node.image = new_image
                            updated += 1
                            break

        # 2. Optionally update the original base material
        if self.update_base_material:
            base_mat = bpy.data.materials.get(base_mat_name)
            if base_mat and base_mat.use_nodes:
                for node in base_mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        node.image = new_image
                        updated += 1
                        break

        if updated:
            self.report({'INFO'}, f"Image updated in {updated} material(s)")
        else:
            self.report({'WARNING'}, "None of the materials had a TexImage node")
        return {'FINISHED'}


class LIST_OT_UpdateFromFile(Operator, ImportHelper):
    """Load a new image from disk and update all derived materials"""
    bl_idname = "list.update_from_file"
    bl_label = "Update from Image File"
    bl_description = "Select an image file from disk, load it, and update all derived materials"
    bl_options = {'REGISTER', 'UNDO'}

    # Properties from the calling operator
    material_name: StringProperty(name="Constant Material")
    update_base_material: BoolProperty(
        name="Also Update Base Material",
        default=True
    )

    # ImportHelper filter properties
    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.tga",
        options={'HIDDEN'}
    )

    def execute(self, context):
        # Load the image from the selected filepath
        filepath = self.filepath
        if not filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}

        # Try to load or reuse an image with the same filepath
        image = None
        for img in bpy.data.images:
            if img.filepath == filepath or (img.filepath and img.filepath == bpy.path.relpath(filepath)):
                image = img
                break

        if image is None:
            try:
                image = bpy.data.images.load(filepath)
                self.report({'INFO'}, f"Loaded new image: {image.name}")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to load image: {str(e)}")
                return {'CANCELLED'}

        # Now perform the same update as LIST_OT_UpdateAllFromBase
        obj = context.edit_object
        if self.material_name not in obj.get("constant_materials", {}):
            self.report({'ERROR'}, "Constant material not found")
            return {'CANCELLED'}

        const_info = obj["constant_materials"][self.material_name]
        base_mat_name = const_info.get("original_material", "")

        if not base_mat_name:
            self.report({'ERROR'}, "Could not determine base material")
            return {'CANCELLED'}

        updated = 0

        # Update all derived constant materials
        for const_name, info in obj["constant_materials"].items():
            if info.get("original_material") == base_mat_name:
                mat = bpy.data.materials.get(const_name)
                if mat and mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image is not None:
                            node.image = image
                            updated += 1
                            break

        # Optionally update the base material
        if self.update_base_material:
            base_mat = bpy.data.materials.get(base_mat_name)
            if base_mat and base_mat.use_nodes:
                for node in base_mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        node.image = image
                        updated += 1
                        break

        if updated:
            self.report({'INFO'}, f"Image updated in {updated} material(s)")
        else:
            self.report({'WARNING'}, "None of the materials had a TexImage node")
        return {'FINISHED'}


classes = [LIST_OT_UpdateAllFromBase, LIST_OT_UpdateFromFile]