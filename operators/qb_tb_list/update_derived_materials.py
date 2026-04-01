import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

def _update_derived_materials(obj, base_material_names, image, update_base_material):
    """
    Synchronizes the image texture across all materials linked to the specified base materials
    defined in the object's custom properties.
    """
    if not image:
        return 0

    const_dict = obj.get("constant_materials", {})
    updated_count = 0

    for base_mat_name in base_material_names:
        # Iterate through custom material definitions to find matches
        for const_name, info in const_dict.items():
            if info.get("original_material") == base_mat_name:
                mat = bpy.data.materials.get(const_name)
                if mat and mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == 'TEX_IMAGE' and node.image is not None:
                            node.image = image
                            updated_count += 1
                            break

        # Apply changes to the source material if requested
        if update_base_material:
            base_mat = bpy.data.materials.get(base_mat_name)
            if base_mat and base_mat.use_nodes:
                for node in base_mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        node.image = image
                        updated_count += 1
                        break

    return updated_count

class LIST_OT_UpdateAllFromBase(Operator):
    """Modify the texture for all constant materials sharing the same origin"""
    bl_idname = "list.update_all_from_base"
    bl_label = "Update Derived"
    bl_description = "Sync the texture image of all materials derived from the current base material"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(name="Constant Material")
    new_image_name: StringProperty(name="New Image", default="")
    update_base_material: BoolProperty(
        name="Also Update Base Material",
        description="Apply the selected image to the source base material as well",
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

        self.base_mat_name = base_mat_name
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        obj = context.edit_object

        layout.label(text=f"Base material: {self.base_mat_name}")

        row = layout.row(align=True)
        row.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        
        # Internal call to file browser for single item context
        op = row.operator("list.update_from_file", text="", icon='FILE_FOLDER')
        op.material_name = self.material_name
        op.update_base_material = self.update_base_material

        layout.prop(self, "update_base_material")

        count = sum(1 for info in obj["constant_materials"].values() 
                   if info.get("original_material") == self.base_mat_name)
        
        layout.label(text=f"{count} materials will be synchronized")
        if self.update_base_material:
            layout.label(text="The original base material is included in this operation", icon='INFO')

    def execute(self, context):
        obj = context.edit_object

        if not self.new_image_name:
            self.report({'ERROR'}, "Please select an image")
            return {'CANCELLED'}

        new_image = bpy.data.images.get(self.new_image_name)
        if not new_image:
            self.report({'ERROR'}, f"Image '{self.new_image_name}' not found")
            return {'CANCELLED'}

        updated = _update_derived_materials(obj, [self.base_mat_name], new_image, self.update_base_material)

        if updated:
            self.report({'INFO'}, f"Successful synchronization: {updated} materials")
        else:
            self.report({'WARNING'}, "No compatible Texture Image nodes found")
        return {'FINISHED'}

class LIST_OT_UpdateFromFile(Operator, ImportHelper):
    """Import an image from the local filesystem to sync derived materials"""
    bl_idname = "list.update_from_file"
    bl_label = "Update from Image File"
    bl_description = "Load a file and apply it to all materials derived from this specific item"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty(name="Constant Material")
    update_base_material: BoolProperty(default=True)

    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.tga",
        options={'HIDDEN'}
    )

    def execute(self, context):
        filepath = self.filepath
        if not filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}

        # Locate existing image data or load fresh from path
        image = None
        for img in bpy.data.images:
            if img.filepath == filepath or (img.filepath and img.filepath == bpy.path.relpath(filepath)):
                image = img
                break

        if image is None:
            try:
                image = bpy.data.images.load(filepath)
                self.report({'INFO'}, f"File loaded: {image.name}")
            except Exception as e:
                self.report({'ERROR'}, f"Loading failed: {str(e)}")
                return {'CANCELLED'}

        obj = context.edit_object
        if self.material_name not in obj.get("constant_materials", {}):
            self.report({'ERROR'}, "Constant material data missing")
            return {'CANCELLED'}

        const_info = obj["constant_materials"][self.material_name]
        base_mat_name = const_info.get("original_material", "")

        if not base_mat_name:
            self.report({'ERROR'}, "Base material reference is missing")
            return {'CANCELLED'}

        updated = _update_derived_materials(obj, [base_mat_name], image, self.update_base_material)

        if updated:
            self.report({'INFO'}, f"Synchronization complete: {updated} materials")
        else:
            self.report({'WARNING'}, "No valid node targets found")
        return {'FINISHED'}

class LIST_OT_UpdateDerivedFromChecked(Operator):
    """Synchronize materials based on multiple user-selected items"""
    bl_idname = "list.update_derived_from_checked"
    bl_label = "Update Derived (Checked)"
    bl_description = "Batch process all materials derived from the currently checked list items"
    bl_options = {'REGISTER', 'UNDO'}

    new_image_name: StringProperty(name="New Image", default="")
    update_base_material: BoolProperty(
        name="Also Update Base Material",
        description="Include source base materials in the batch operation",
        default=True
    )

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS' and
                "multi_selected_items" in obj and obj["multi_selected_items"])

    def invoke(self, context, event):
        obj = context.edit_object
        multi_selection = dict(obj["multi_selected_items"])
        const_dict = obj.get("constant_materials", {})

        # Collect unique base references from the selection set
        self.unique_bases = set()
        for mat_name in multi_selection.keys():
            if mat_name in const_dict:
                base = const_dict[mat_name].get("original_material", "")
                if base:
                    self.unique_bases.add(base)

        if not self.unique_bases:
            self.report({'WARNING'}, "The selection contains no valid material references")
            return {'CANCELLED'}

        self.unique_bases = list(self.unique_bases)
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Total unique base materials identified: {len(self.unique_bases)}")

        row = layout.row(align=True)
        row.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        
        # Batch processing trigger for file selection
        op = row.operator("list.update_derived_from_file", text="", icon='FILE_FOLDER')
        op.update_base_material = self.update_base_material

        layout.prop(self, "update_base_material")

    def execute(self, context):
        obj = context.edit_object
        new_image = bpy.data.images.get(self.new_image_name)
        if not new_image:
            self.report({'ERROR'}, "An image selection is required")
            return {'CANCELLED'}

        updated = _update_derived_materials(obj, self.unique_bases, new_image, self.update_base_material)

        self.report({'INFO'}, f"Batch update successful: {updated} materials affected")
        return {'FINISHED'}

class LIST_OT_UpdateDerivedFromFile(Operator, ImportHelper):
    """Bulk import and application of texture files to checked items"""
    bl_idname = "list.update_derived_from_file"
    bl_label = "Update from Image File (Checked)"
    bl_description = "Load a file and apply it to all materials linked to the checked selection"
    bl_options = {'REGISTER', 'UNDO'}

    update_base_material: BoolProperty(
        name="Also Update Base Material",
        description="Include source base materials in the file application",
        default=True
    )

    filter_glob: StringProperty(
        default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.tga",
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS' and
                "multi_selected_items" in obj and obj["multi_selected_items"])

    def execute(self, context):
        filepath = self.filepath
        if not filepath:
            self.report({'ERROR'}, "Operation cancelled: No file provided")
            return {'CANCELLED'}

        image = None
        for img in bpy.data.images:
            if img.filepath == filepath or (img.filepath and img.filepath == bpy.path.relpath(filepath)):
                image = img
                break

        if image is None:
            try:
                image = bpy.data.images.load(filepath)
                self.report({'INFO'}, f"Resource loaded: {image.name}")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to access file: {str(e)}")
                return {'CANCELLED'}

        obj = context.edit_object
        multi_selection = dict(obj["multi_selected_items"])
        const_dict = obj.get("constant_materials", {})

        unique_bases = set()
        for mat_name in multi_selection.keys():
            if mat_name in const_dict:
                base = const_dict[mat_name].get("original_material", "")
                if base:
                    unique_bases.add(base)

        if not unique_bases:
            self.report({'WARNING'}, "Selected items do not contain valid material data")
            return {'CANCELLED'}

        updated = _update_derived_materials(obj, list(unique_bases), image, self.update_base_material)

        if updated:
            self.report({'INFO'}, f"Batch synchronization complete: {updated} materials")
        else:
            self.report({'WARNING'}, "No nodes were modified")
        return {'FINISHED'}

classes = [
    LIST_OT_UpdateAllFromBase,
    LIST_OT_UpdateFromFile,
    LIST_OT_UpdateDerivedFromChecked,
    LIST_OT_UpdateDerivedFromFile,
]