"""
CTR Material Manager – Custom scrollable list with preview icons,
top action buttons, filter bar, search, and pagination.
Uses checkboxes for single selection.
Includes operators for synchronizing derived (constant) materials.
"""

import bpy
import bmesh
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import StringProperty, IntProperty, EnumProperty, CollectionProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

from .qb_tb_list.list_helpers import get_material_image_icon
from ..utils.material_utils import update_derived_materials


# Material categories 
def get_material_categories():
    """Return three sets: normal, constant, nav_point."""
    const_names = set()
    nav_names = set()
    for obj in bpy.data.objects:
        if "constant_materials" in obj:
            for mat_name, info in obj["constant_materials"].items():
                const_names.add(mat_name)
                if info.get("is_navigation_point", False):
                    nav_names.add(mat_name)

    normal = set()
    constant = set()
    nav_point = set()
    for mat in bpy.data.materials:
        if mat.name in const_names:
            if mat.name in nav_names:
                nav_point.add(mat.name)
            else:
                constant.add(mat.name)
        else:
            normal.add(mat.name)
    return normal, constant, nav_point


#  Properties for the material list
class CTR_MaterialListItem(PropertyGroup):
    name: StringProperty()


class CTR_MaterialListProps(PropertyGroup):
    filter_type: EnumProperty(
        name="Filter",
        items=[
            ('ALL', "All", "Show all materials"),
            ('NORMAL', "Normal", "Non‑constant materials"),
            ('CONSTANT', "Constant", "Constant materials (not nav points)"),
            ('NAV_POINT', "Nav Point", "Navigation point materials"),
        ],
        default='ALL',
        update=lambda self, ctx: self._update_items(ctx)
    )
    search_text: StringProperty(
        name="Search", default="",
        update=lambda self, ctx: self._update_items(ctx)
    )
    items: CollectionProperty(type=CTR_MaterialListItem)
    selected_index: IntProperty(default=-1, options={'SKIP_SAVE'})
    scroll: IntProperty(default=0, min=0)

    def _update_items(self, context):
        """Rebuild the items collection from current filter & search."""
        self.items.clear()
        normal, constant, nav_point = get_material_categories()
        raw = set()
        if self.filter_type == 'NORMAL':
            raw = normal
        elif self.filter_type == 'CONSTANT':
            raw = constant
        elif self.filter_type == 'NAV_POINT':
            raw = nav_point
        else:
            raw = normal | constant | nav_point

        search = self.search_text.lower()
        for name in sorted(raw):
            if search and search not in name.lower():
                continue
            item = self.items.add()
            item.name = name
        self.selected_index = -1
        self.scroll = 0


# Operators for assign / select / deselect 
class MATERIAL_OT_AssignSelected(Operator):
    """Assign the selected material to selected faces (whole blocks if any face belongs to a block)"""
    bl_idname = "material.assign_selected"
    bl_label = "Assign"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            self.report({'ERROR'}, f"Material '{mat_name}' not found")
            return {'CANCELLED'}

        # block assignment of constant or nav point materials
        if "constant_materials" in obj and mat_name in obj["constant_materials"]:
            self.report({'ERROR'}, f"Cannot assign constant/navigation material '{mat_name}' using this button. Use the 'Assign' button inside the Block List (Constant Materials mode) instead.")
            return {'CANCELLED'}

        # Ensure material is in the object's material slots
        if mat.name not in obj.data.materials:
            obj.data.materials.append(mat)
        mat_index = obj.data.materials.find(mat.name)

        # AWARE ASSIGNMENT
        # Check if the object has block detection data (from Navigator)
        has_block_data = ("face_to_quadblock" in obj and "quadblock_faces_map" in obj) or \
                         ("face_to_triblock" in obj and "triblock_faces_map" in obj)

        if not has_block_data:
            # Fallback to original behaviour: assign only to selected faces
            bm = bmesh.from_edit_mesh(obj.data)
            for face in bm.faces:
                if face.select:
                    face.material_index = mat_index
            bmesh.update_edit_mesh(obj.data)
            self.report({'INFO'}, f"Assigned {mat.name} to selected faces")
            return {'FINISHED'}

        # Get selected faces via bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            self.report({'WARNING'}, "No faces selected")
            return {'CANCELLED'}

        # Build mapping from face index to block info
        face_to_quad = obj.get("face_to_quadblock", {})
        face_to_tri = obj.get("face_to_triblock", {})
        quad_maps = obj.get("quadblock_faces_map", {})
        tri_maps = obj.get("triblock_faces_map", {})

        blocks_to_assign = set()      # (block_type, block_id)
        individual_faces = set()      # face indices that belong to no block

        for face in selected_faces:
            idx_str = str(face.index)
            if idx_str in face_to_quad:
                block_id = int(face_to_quad[idx_str])
                blocks_to_assign.add(('quadblock', block_id))
            elif idx_str in face_to_tri:
                block_id = int(face_to_tri[idx_str])
                blocks_to_assign.add(('triblock', block_id))
            else:
                individual_faces.add(face.index)

        # Collect all face indices that must receive the material
        faces_to_assign = set(individual_faces)

        for block_type, block_id in blocks_to_assign:
            if block_type == 'quadblock':
                block_faces = quad_maps.get(str(block_id), [])
            else:
                block_faces = tri_maps.get(str(block_id), [])
            faces_to_assign.update(block_faces)

        # Apply the material index to all those faces
        for face in bm.faces:
            if face.index in faces_to_assign:
                face.material_index = mat_index

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Assigned {mat.name} to {len(faces_to_assign)} faces ({len(blocks_to_assign)} blocks + {len(individual_faces)} standalone faces)")
        return {'FINISHED'}


class MATERIAL_OT_SelectByMaterial(Operator):
    """Select all faces using the selected material"""
    bl_idname = "material.select_by_material"
    bl_label = "Select"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat or mat.name not in obj.data.materials:
            self.report({'WARNING'}, f"Material '{mat_name}' not used by object")
            return {'CANCELLED'}

        mat_index = obj.data.materials.find(mat.name)
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            face.select = False
        for face in bm.faces:
            if face.material_index == mat_index:
                face.select = True
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected faces with {mat.name}")
        return {'FINISHED'}


class MATERIAL_OT_DeselectByMaterial(Operator):
    """Deselect all faces using the selected material"""
    bl_idname = "material.deselect_by_material"
    bl_label = "Deselect"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def execute(self, context):
        props = context.scene.ctr_material_list
        if props.selected_index < 0 or props.selected_index >= len(props.items):
            self.report({'WARNING'}, "No material selected")
            return {'CANCELLED'}

        mat_name = props.items[props.selected_index].name
        obj = context.active_object
        mat = bpy.data.materials.get(mat_name)
        if not mat or mat.name not in obj.data.materials:
            return {'CANCELLED'}

        mat_index = obj.data.materials.find(mat.name)
        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            if face.material_index == mat_index:
                face.select = False
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Deselected faces with {mat.name}")
        return {'FINISHED'}


# Refresh with Purge popup
class MATERIAL_OT_RefreshList(Operator):
    """Rebuild the material list (after adding/renaming materials) and optionally purge unused data blocks"""
    bl_idname = "material.refresh_list"
    bl_label = "Refresh"
    bl_description = "Rebuild the material list (after adding/renaming materials)"
    bl_options = {'REGISTER'}

    purge_unused: BoolProperty(
        name="Purge unused",
        description="Delete all unused materials, textures, and images",
        default=False
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.prop(self, "purge_unused")

    def execute(self, context):
        if self.purge_unused:
            # Purge all unused data blocks recursively
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
            self.report({'INFO'}, "Purged unused data blocks")

        # Rebuild the material list
        context.scene.ctr_material_list._update_items(context)
        self.report({'INFO'}, "Material list refreshed")
        return {'FINISHED'}


# Scroll / Pagination operators
class MATERIAL_OT_VerticalScroll(Operator):
    bl_idname = "material.vertical_scroll"
    bl_label = "Scroll"
    direction: EnumProperty(items=[('UP', 'Up', ''), ('DOWN', 'Down', '')])

    def execute(self, context):
        props = context.scene.ctr_material_list
        total = len(props.items)
        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total - ITEMS_PER_PAGE)
        if self.direction == 'UP':
            props.scroll = max(0, props.scroll - 1)
        else:
            props.scroll = min(max_scroll, props.scroll + 1)
        return {'FINISHED'}


class MATERIAL_OT_JumpToPage(Operator):
    bl_idname = "material.jump_to_page"
    bl_label = "Jump to Page"
    page: IntProperty(default=1, min=1)

    def execute(self, context):
        props = context.scene.ctr_material_list
        total = len(props.items)
        ITEMS_PER_PAGE = 10
        total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        safe_page = max(1, min(self.page, total_pages))
        props.scroll = (safe_page - 1) * ITEMS_PER_PAGE
        return {'FINISHED'}


class MATERIAL_OT_ToggleSelection(Operator):
    bl_idname = "material.toggle_selection"
    bl_label = "Select Material"
    index: IntProperty()

    def execute(self, context):
        props = context.scene.ctr_material_list
        if self.index < 0 or self.index >= len(props.items):
            return {'CANCELLED'}
        if props.selected_index == self.index:
            props.selected_index = -1
        else:
            props.selected_index = self.index
        return {'FINISHED'}


# Operators for synchronizing derived materials
class MATERIAL_OT_SyncDerivedTextures(Operator):
    """Synchronize texture of all materials derived from the selected material"""
    bl_idname = "material.sync_derived_textures"
    bl_label = "Sync Derived"
    bl_description = "Change the texture image for this material and all materials that derive from it"
    bl_options = {'REGISTER', 'UNDO'}

    new_image_name: StringProperty(name="New Image", default="")
    update_base_material: BoolProperty(
        name="Also Update Base Material",
        description="Apply the selected image to the source base material as well",
        default=True
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'MESH' and "constant_materials" in obj

    def invoke(self, context, event):
        props = context.scene.ctr_material_list
        if props.selected_index < 0:
            self.report({'WARNING'}, "No material selected in the CTR Material Manager")
            return {'CANCELLED'}

        selected_mat_name = props.items[props.selected_index].name
        obj = context.active_object

        self.base_materials = set()
        const_dict = obj.get("constant_materials", {})

        if selected_mat_name in const_dict:
            base = const_dict[selected_mat_name].get("original_material", "")
            if base:
                self.base_materials.add(base)
            else:
                self.report({'ERROR'}, "Selected constant material has no base material reference")
                return {'CANCELLED'}
        else:
            for const_name, info in const_dict.items():
                if info.get("original_material") == selected_mat_name:
                    self.base_materials.add(selected_mat_name)
                    break
            if not self.base_materials:
                self.report({'WARNING'}, f"Material '{selected_mat_name}' is not used as base for any constant material")
                return {'CANCELLED'}

        self.base_materials = list(self.base_materials)
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Base material(s): {', '.join(self.base_materials)}")

        row = layout.row(align=True)
        row.prop_search(self, "new_image_name", bpy.data, "images", text="New Image")
        op = row.operator("material.sync_derived_from_file", text="", icon='FILE_FOLDER')
        op.update_base_material = self.update_base_material

        layout.prop(self, "update_base_material")

        obj = context.active_object
        const_dict = obj.get("constant_materials", {})
        count = sum(1 for info in const_dict.values()
                    if info.get("original_material") in self.base_materials)
        layout.label(text=f"{count} constant material(s) will be updated")
        if self.update_base_material:
            layout.label(text="The base material will also be updated", icon='INFO')

    def execute(self, context):
        obj = context.active_object
        new_image = bpy.data.images.get(self.new_image_name)
        if not new_image:
            self.report({'ERROR'}, "Please select an image")
            return {'CANCELLED'}

        updated = update_derived_materials(
            obj, self.base_materials, new_image, self.update_base_material
        )
        self.report({'INFO'}, f"Updated {updated} materials")
        return {'FINISHED'}


class MATERIAL_OT_SyncDerivedFromFile(Operator, ImportHelper):
    """Load an image from disk and sync all derived materials"""
    bl_idname = "material.sync_derived_from_file"
    bl_label = "Sync from Image File"
    bl_options = {'REGISTER', 'UNDO'}

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
        const_dict = obj.get("constant_materials", {})
        base_materials = set()
        if selected_mat_name in const_dict:
            base = const_dict[selected_mat_name].get("original_material", "")
            if base:
                base_materials.add(base)
        else:
            for const_name, info in const_dict.items():
                if info.get("original_material") == selected_mat_name:
                    base_materials.add(selected_mat_name)
                    break

        if not base_materials:
            self.report({'WARNING'}, "No base materials found for the selection")
            return {'CANCELLED'}

        updated = update_derived_materials(
            obj, list(base_materials), image, self.update_base_material
        )
        self.report({'INFO'}, f"Updated {updated} materials")
        return {'FINISHED'}


# Main Panel
class CTR_PT_MaterialManager(Panel):
    bl_label = "CTR Material Manager"
    bl_idname = "CTR_PT_material_manager"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        props = context.scene.ctr_material_list
        obj = context.active_object

        # Filter row
        row = layout.row(align=True)
        row.prop(props, "filter_type", expand=True)

        # Search bar + Refresh
        row = layout.row(align=True)
        row.prop(props, "search_text", text="", icon='VIEWZOOM')
        row.operator("material.refresh_list", text="", icon='FILE_REFRESH')

        # Action buttons row (Assign, Select, Deselect, Sync Derived)
        row = layout.row(align=True)

        # Disable Assign for constant/nav point materials
        assign_disabled = False
        if props.selected_index >= 0 and props.selected_index < len(props.items):
            selected_mat_name = props.items[props.selected_index].name
            if obj and "constant_materials" in obj and selected_mat_name in obj["constant_materials"]:
                assign_disabled = True

        assign_row = row.row(align=True)
        assign_row.enabled = not assign_disabled
        assign_row.operator("material.assign_selected", text="Assign", icon='CHECKMARK')

        row.operator("material.select_by_material", text="Select", icon='RESTRICT_SELECT_OFF')
        row.operator("material.deselect_by_material", text="Deselect", icon='RESTRICT_SELECT_ON')

        # Sync Derived Textures button: disable if material is not a valid base/constant
        sync_disabled = True
        if obj and "constant_materials" in obj and props.selected_index >= 0 and props.selected_index < len(props.items):
            selected_mat_name = props.items[props.selected_index].name
            const_dict = obj["constant_materials"]
            if selected_mat_name in const_dict:
                sync_disabled = False
            else:
                for info in const_dict.values():
                    if info.get("original_material") == selected_mat_name:
                        sync_disabled = False
                        break

        sync_row = row.row(align=True)
        sync_row.enabled = not sync_disabled
        sync_row.operator("material.sync_derived_textures", text="Sync Derived", icon='FILE_REFRESH')

        # List area
        total = len(props.items)
        if total == 0:
            layout.box().label(text="No materials match the filter", icon='INFO')
            return

        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total - ITEMS_PER_PAGE)
        safe_scroll = min(props.scroll, max_scroll)
        start = safe_scroll
        end = min(start + ITEMS_PER_PAGE, total)

        box = layout.box()
        count_row = box.row()
        count_row.alignment = 'CENTER'
        count_row.label(text=f"Materials: {total}  (page {(safe_scroll // ITEMS_PER_PAGE) + 1} of {max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)})")

        for idx in range(start, end):
            item = props.items[idx]
            mat_name = item.name
            row = box.row(align=True)

            is_sel = (idx == props.selected_index)
            icon = 'CHECKBOX_HLT' if is_sel else 'CHECKBOX_DEHLT'
            op = row.operator("material.toggle_selection", text="", icon=icon, emboss=False)
            op.index = idx

            icon_id = get_material_image_icon(mat_name)
            if isinstance(icon_id, int) and icon_id != 0:
                row.label(text=mat_name, icon_value=icon_id)
            else:
                row.label(text=mat_name, icon='MATERIAL')

            if is_sel:
                row.alert = True

        if total > ITEMS_PER_PAGE:
            pagination_row = box.row(align=True)
            pagination_row.alignment = 'CENTER'
            current_page = (safe_scroll // ITEMS_PER_PAGE) + 1
            total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

            up = pagination_row.operator("material.vertical_scroll", text="", icon='TRIA_UP')
            up.direction = 'UP'
            first = pagination_row.operator("material.jump_to_page", text="<<", icon='REW')
            first.page = 1
            prev = pagination_row.operator("material.jump_to_page", text="<", icon='PREV_KEYFRAME')
            prev.page = current_page - 1 if current_page > 1 else 1
            pagination_row.label(text=f"[{current_page}/{total_pages}]")
            nxt = pagination_row.operator("material.jump_to_page", text=">", icon='NEXT_KEYFRAME')
            nxt.page = current_page + 1 if current_page < total_pages else total_pages
            last = pagination_row.operator("material.jump_to_page", text=">>", icon='FF')
            last.page = total_pages
            down = pagination_row.operator("material.vertical_scroll", text="", icon='TRIA_DOWN')
            down.direction = 'DOWN'


# Registration
classes = [
    CTR_MaterialListItem,
    CTR_MaterialListProps,
    MATERIAL_OT_AssignSelected,
    MATERIAL_OT_SelectByMaterial,
    MATERIAL_OT_DeselectByMaterial,
    MATERIAL_OT_RefreshList,
    MATERIAL_OT_VerticalScroll,
    MATERIAL_OT_JumpToPage,
    MATERIAL_OT_ToggleSelection,
    MATERIAL_OT_SyncDerivedTextures,
    MATERIAL_OT_SyncDerivedFromFile,
    CTR_PT_MaterialManager,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ctr_material_list = bpy.props.PointerProperty(type=CTR_MaterialListProps)

def unregister():
    del bpy.types.Scene.ctr_material_list
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)