import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper
from ...utils.material_utils import update_derived_materials


class LIST_OT_UpdateAllFromBase(Operator):
    bl_idname = "list.update_all_from_base"
    bl_label = "Update Derived"
    bl_description = "Sync the texture image of all materials derived from the current base material"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty()
    new_image_name: StringProperty()
    update_base_material: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS')

    def invoke(self, context, event):
        obj = context.edit_object
        mat = bpy.data.materials.get(self.material_name)
        if not mat or mat.get("ctr_block_type") is None:
            self.report({'ERROR'}, "Not a constant material.")
            return {'CANCELLED'}

        self.base_mat_name = mat.get("ctr_original_material", "")
        if not self.base_mat_name:
            self.report({'ERROR'}, "Could not determine base material.")
            return {'CANCELLED'}

        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Base material: {self.base_mat_name}")
        row = layout.row(align=True)
        row.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        op = row.operator("list.update_from_file", text="", icon='FILE_FOLDER')
        op.material_name = self.material_name
        op.update_base_material = self.update_base_material
        layout.prop(self, "update_base_material")

        count = sum(1 for m in bpy.data.materials if m.get("ctr_original_material") == self.base_mat_name)
        layout.label(text=f"{count} materials will be synchronized")

    def execute(self, context):
        if not self.new_image_name:
            self.report({'ERROR'}, "Please select an image")
            return {'CANCELLED'}

        new_image = bpy.data.images.get(self.new_image_name)
        if not new_image:
            self.report({'ERROR'}, f"Image '{self.new_image_name}' not found")
            return {'CANCELLED'}

        obj = context.edit_object
        updated = update_derived_materials(obj, [self.base_mat_name], new_image, self.update_base_material)

        self.report({'INFO'}, f"Updated {updated} materials.")
        return {'FINISHED'}


class LIST_OT_UpdateFromFile(Operator, ImportHelper):
    bl_idname = "list.update_from_file"
    bl_label = "Update from Image File"
    bl_description = "Load a file and apply it to all materials derived from this specific item"
    bl_options = {'REGISTER', 'UNDO'}

    material_name: StringProperty()
    update_base_material: BoolProperty(default=True)
    filter_glob: StringProperty(default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.tga", options={'HIDDEN'})

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
                self.report({'INFO'}, f"File loaded: {image.name}")
            except Exception as e:
                self.report({'ERROR'}, f"Loading failed: {str(e)}")
                return {'CANCELLED'}

        obj = context.edit_object
        mat = bpy.data.materials.get(self.material_name)
        if not mat or mat.get("ctr_block_type") is None:
            self.report({'ERROR'}, "Not a constant material.")
            return {'CANCELLED'}

        base_mat_name = mat.get("ctr_original_material", "")
        if not base_mat_name:
            self.report({'ERROR'}, "Could not determine base material.")
            return {'CANCELLED'}

        updated = update_derived_materials(obj, [base_mat_name], image, self.update_base_material)

        self.report({'INFO'}, f"Updated {updated} materials.")
        return {'FINISHED'}


class LIST_OT_UpdateDerivedFromChecked(Operator):
    bl_idname = "list.update_derived_from_checked"
    bl_label = "Update Derived (Checked)"
    bl_description = "Batch process all materials derived from currently checked items"
    bl_options = {'REGISTER', 'UNDO'}

    new_image_name: StringProperty()
    update_base_material: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS' and
                "multi_selected_items" in obj and obj["multi_selected_items"])

    def invoke(self, context, event):
        obj = context.edit_object
        multi = dict(obj["multi_selected_items"])
        self.unique_bases = set()
        for mat_name in multi.keys():
            mat = bpy.data.materials.get(mat_name)
            if mat and mat.get("ctr_block_type") is not None:
                base = mat.get("ctr_original_material", "")
                if base:
                    self.unique_bases.add(base)

        if not self.unique_bases:
            self.report({'WARNING'}, "No valid material references in selection.")
            return {'CANCELLED'}

        self.unique_bases = list(self.unique_bases)
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Total unique base materials: {len(self.unique_bases)}")
        row = layout.row(align=True)
        row.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        op = row.operator("list.update_derived_from_file", text="", icon='FILE_FOLDER')
        op.update_base_material = self.update_base_material
        layout.prop(self, "update_base_material")

    def execute(self, context):
        obj = context.edit_object
        new_image = bpy.data.images.get(self.new_image_name)
        if not new_image:
            self.report({'ERROR'}, "Please select an image.")
            return {'CANCELLED'}

        updated = update_derived_materials(obj, self.unique_bases, new_image, self.update_base_material)
        self.report({'INFO'}, f"Batch update: {updated} materials affected.")
        return {'FINISHED'}


class LIST_OT_UpdateDerivedFromFile(Operator, ImportHelper):
    bl_idname = "list.update_derived_from_file"
    bl_label = "Update from Image File (Checked)"
    bl_description = "Bulk import and application of texture files to checked items"
    bl_options = {'REGISTER', 'UNDO'}

    update_base_material: BoolProperty(default=True)
    filter_glob: StringProperty(default="*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.bmp;*.tga", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS' and
                "multi_selected_items" in obj and obj["multi_selected_items"])

    def execute(self, context):
        filepath = self.filepath
        if not filepath:
            self.report({'ERROR'}, "No file selected.")
            return {'CANCELLED'}

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
        multi = dict(obj["multi_selected_items"])
        unique_bases = set()
        for mat_name in multi.keys():
            mat = bpy.data.materials.get(mat_name)
            if mat and mat.get("ctr_block_type") is not None:
                base = mat.get("ctr_original_material", "")
                if base:
                    unique_bases.add(base)

        if not unique_bases:
            self.report({'WARNING'}, "No valid material references.")
            return {'CANCELLED'}

        updated = update_derived_materials(obj, list(unique_bases), image, self.update_base_material)
        self.report({'INFO'}, f"Batch update: {updated} materials affected.")
        return {'FINISHED'}


classes = [
    LIST_OT_UpdateAllFromBase,
    LIST_OT_UpdateFromFile,
    LIST_OT_UpdateDerivedFromChecked,
    LIST_OT_UpdateDerivedFromFile,
]