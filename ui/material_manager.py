"""
CTR Material Manager – Custom scrollable list with preview icons,
top action buttons, filter bar, search, and pagination.
Uses checkboxes for single selection.
"""

import bpy
import bmesh
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import StringProperty, IntProperty, EnumProperty, CollectionProperty

from .qb_tb_list.list_helpers import get_material_image_icon


# Get material categories (global)

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



# Properties for the material list

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
        # Reset selection and scroll
        self.selected_index = -1
        self.scroll = 0


# Operators for assign / select / deselect (top buttons)

class MATERIAL_OT_AssignSelected(Operator):
    """Assign the selected material to selected faces"""
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

        if mat.name not in obj.data.materials:
            obj.data.materials.append(mat)
        mat_index = obj.data.materials.find(mat.name)

        bm = bmesh.from_edit_mesh(obj.data)
        for face in bm.faces:
            if face.select:
                face.material_index = mat_index
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Assigned {mat.name} to selected faces")
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



# Refresh operator – manually rebuild list

class MATERIAL_OT_RefreshList(Operator):
    bl_idname = "material.refresh_list"
    bl_label = "Refresh"
    bl_description = "Rebuild the material list (after adding/renaming materials)"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.ctr_material_list._update_items(context)
        return {'FINISHED'}



# Scroll / Pagination operators (with range limiting)

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



# Operator to select an item from the list (checkbox)

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



# Main Panel inside Material Properties

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

        # Filter row (expand buttons)
        row = layout.row(align=True)
        row.prop(props, "filter_type", expand=True)

        # Search bar + Refresh button 
        row = layout.row(align=True)
        row.prop(props, "search_text", text="", icon='VIEWZOOM')
        row.operator("material.refresh_list", text="", icon='FILE_REFRESH')

        # Action buttons (top)
        row = layout.row(align=True)
        row.operator("material.assign_selected", text="Assign", icon='CHECKMARK')
        row.operator("material.select_by_material", text="Select", icon='RESTRICT_SELECT_OFF')
        row.operator("material.deselect_by_material", text="Deselect", icon='RESTRICT_SELECT_ON')

        # List data (read-only) 
        total = len(props.items)
        if total == 0:
            layout.box().label(text="No materials match the filter", icon='INFO')
            return

        ITEMS_PER_PAGE = 10
        max_scroll = max(0, total - ITEMS_PER_PAGE)
        # Clamp scroll locally without modifying the property during draw
        safe_scroll = min(props.scroll, max_scroll)
        start = safe_scroll
        end = min(start + ITEMS_PER_PAGE, total)

        # Box for the list
        box = layout.box()
        # Counter
        count_row = box.row()
        count_row.alignment = 'CENTER'
        count_row.label(text=f"Materials: {total}  (page {(safe_scroll // ITEMS_PER_PAGE) + 1} of {max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)})")

        # Draw visible items
        for idx in range(start, end):
            item = props.items[idx]
            mat_name = item.name
            row = box.row(align=True)

            # Checkbox
            is_sel = (idx == props.selected_index)
            icon = 'CHECKBOX_HLT' if is_sel else 'CHECKBOX_DEHLT'
            op = row.operator("material.toggle_selection", text="", icon=icon, emboss=False)
            op.index = idx

            # Material preview icon
            icon_id = get_material_image_icon(mat_name)
            if isinstance(icon_id, int) and icon_id != 0:
                row.label(text=mat_name, icon_value=icon_id)
            else:
                row.label(text=mat_name, icon='MATERIAL')

            if is_sel:
                row.alert = True

        # Pagination controls (always show if more than one page) ---
        if total > ITEMS_PER_PAGE:
            pagination_row = box.row(align=True)
            pagination_row.alignment = 'CENTER'

            current_page = (safe_scroll // ITEMS_PER_PAGE) + 1
            total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

            # Up (previous page)
            up = pagination_row.operator("material.vertical_scroll", text="", icon='TRIA_UP')
            up.direction = 'UP'

            # First page
            first = pagination_row.operator("material.jump_to_page", text="<<", icon='REW')
            first.page = 1

            # Previous page
            prev = pagination_row.operator("material.jump_to_page", text="<", icon='PREV_KEYFRAME')
            prev.page = current_page - 1 if current_page > 1 else 1

            # Page indicator
            pagination_row.label(text=f"[{current_page}/{total_pages}]")

            # Next page
            nxt = pagination_row.operator("material.jump_to_page", text=">", icon='NEXT_KEYFRAME')
            nxt.page = current_page + 1 if current_page < total_pages else total_pages

            # Last page
            last = pagination_row.operator("material.jump_to_page", text=">>", icon='FF')
            last.page = total_pages

            # Down (next page)
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