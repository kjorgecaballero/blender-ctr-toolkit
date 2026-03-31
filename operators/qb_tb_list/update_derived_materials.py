import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty


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
        layout.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")

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


classes = [LIST_OT_UpdateAllFromBase]