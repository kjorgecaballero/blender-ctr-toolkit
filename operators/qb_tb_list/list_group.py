"""
Group Management Operators for Constant Materials
Single group dropdown, no checkboxes.
Buttons: New Group, Delete Group, Add Checked Items, Remove Checked Items.
OK button sets the active group filter.
"""

import json
import bpy
from bpy.types import Operator, PropertyGroup
from bpy.props import StringProperty, CollectionProperty

# Global variable to keep a reference to the active management dialog
_active_management_dialog = None


# get checked constant materials from the object
def _get_checked_materials(context):
    obj = context.edit_object
    if not obj or "multi_selected_items" not in obj:
        return []
    multi = dict(obj["multi_selected_items"])
    const_dict = obj.get("constant_materials", {})
    return [m for m in multi.keys() if m in const_dict]


# Property group for collection items (used in dropdown)
class GroupItem(PropertyGroup):
    name: StringProperty()


# Refresh the groups collection from scene data, including a "None" option
def _refresh_groups_collection(collection, scene):
    collection.clear()
    # Add "None" option (special item to disable group filter)
    none_item = collection.add()
    none_item.name = "None"
    groups_dict = {}
    if "constant_material_groups" in scene:
        try:
            groups_dict = json.loads(scene["constant_material_groups"])
        except:
            pass
    for name in sorted(groups_dict.keys()):
        if name == "None":
            continue
        item = collection.add()
        item.name = name



# Main dialog: group dropdown + action buttons

class LIST_OT_GroupManagementDialog(Operator):
    bl_idname = "list.group_management_dialog"
    bl_label = "Manage Groups"
    bl_description = "Manage constant material groups: add/remove checked blocks, create/delete groups"
    bl_options = {'REGISTER'}

    groups_collection: CollectionProperty(type=GroupItem)
    selected_group_name: StringProperty(name="Group", default="")

    def __init__(self):
        super().__init__()
        self._new_group_name = None

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                context.scene.list_display_type == 'CONSTANT_MATERIALS' and
                obj.get("constant_materials"))

    def invoke(self, context, event):
        global _active_management_dialog
        _active_management_dialog = self
        _refresh_groups_collection(self.groups_collection, context.scene)
        current_filter = context.scene.list_active_group
        if current_filter and current_filter in [item.name for item in self.groups_collection]:
            self.selected_group_name = current_filter
        else:
            self.selected_group_name = "None"
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        _refresh_groups_collection(self.groups_collection, context.scene)

        if self._new_group_name:
            if any(item.name == self._new_group_name for item in self.groups_collection):
                self.selected_group_name = self._new_group_name
            else:
                self.selected_group_name = "None"
            self._new_group_name = None
        else:
            old_selection = self.selected_group_name
            if old_selection and old_selection != "None":
                if any(item.name == old_selection for item in self.groups_collection):
                    self.selected_group_name = old_selection
                else:
                    self.selected_group_name = "None"
            else:
                if any(item.name == "None" for item in self.groups_collection):
                    self.selected_group_name = "None"
                else:
                    self.selected_group_name = ""

        layout = self.layout

        row = layout.row()
        row.prop_search(self, "selected_group_name", self, "groups_collection", text="Group", icon='GROUP')

        col = layout.column(align=True)
        col.separator()

        row = col.row(align=True)
        row.operator("list.new_group_simple", text="New Group", icon='ADD')

        if self.selected_group_name and self.selected_group_name != "None":
            op = row.operator("list.delete_group_simple", text="Delete Group", icon='TRASH')
            op.group_name = self.selected_group_name
        else:
            sub = row.row(align=True)
            sub.enabled = False
            sub.operator("list.delete_group_simple", text="Delete Group", icon='TRASH')

        col.separator()

        row = col.row(align=True)
        if self.selected_group_name and self.selected_group_name != "None":
            op = row.operator("list.add_to_single_group", text="Add Checked Items", icon='ADD')
            op.group_name = self.selected_group_name
            op = row.operator("list.remove_from_single_group", text="Remove Checked Items", icon='REMOVE')
            op.group_name = self.selected_group_name
        else:
            row.enabled = False
            row.operator("list.add_to_single_group", text="Add Checked Items", icon='ADD')
            row.operator("list.remove_from_single_group", text="Remove Checked Items", icon='REMOVE')

    def execute(self, context):
        global _active_management_dialog
        if self.selected_group_name == "None":
            context.scene.list_active_group = ""
        else:
            context.scene.list_active_group = self.selected_group_name
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        _active_management_dialog = None
        return {'FINISHED'}


# New Group (empty field each time)

class LIST_OT_NewGroupSimple(Operator):
    bl_idname = "list.new_group_simple"
    bl_label = "New Group"
    bl_description = "Create a new empty group"
    bl_options = {'REGISTER'}

    group_name: StringProperty(name="Group Name", default="")

    def invoke(self, context, event):
        self.group_name = ""   # Reset to empty field
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "group_name", text="Name")

    def execute(self, context):
        global _active_management_dialog
        scene = context.scene
        name = self.group_name.strip()
        if not name:
            self.report({'ERROR'}, "Group name cannot be empty.")
            return {'CANCELLED'}
        if name.lower() == "none":
            self.report({'ERROR'}, "Cannot create a group named 'None'.")
            return {'CANCELLED'}

        groups = {}
        if "constant_material_groups" in scene:
            try:
                groups = json.loads(scene["constant_material_groups"])
            except:
                pass
        if name in groups:
            self.report({'ERROR'}, f"Group '{name}' already exists.")
            return {'CANCELLED'}

        groups[name] = []
        scene["constant_material_groups"] = json.dumps(groups)

        if _active_management_dialog:
            _active_management_dialog._new_group_name = name

        self.report({'INFO'}, f"Group '{name}' created.")
        return {'FINISHED'}



# Delete Group

class LIST_OT_DeleteGroupSimple(Operator):
    bl_idname = "list.delete_group_simple"
    bl_label = "Delete Group"
    bl_description = "Delete the selected group"
    bl_options = {'REGISTER'}

    group_name: StringProperty()

    def execute(self, context):
        scene = context.scene
        name = self.group_name
        if not name or name == "None":
            self.report({'WARNING'}, "No valid group selected.")
            return {'CANCELLED'}
        groups = {}
        if "constant_material_groups" in scene:
            try:
                groups = json.loads(scene["constant_material_groups"])
            except:
                pass
        if name not in groups:
            self.report({'WARNING'}, f"Group '{name}' not found.")
            return {'CANCELLED'}
        del groups[name]
        scene["constant_material_groups"] = json.dumps(groups)
        if scene.list_active_group == name:
            scene.list_active_group = ""
        self.report({'INFO'}, f"Deleted group '{name}'. The dropdown will refresh automatically.")
        return {'FINISHED'}



# Add checked materials to a single group (with verification)

class LIST_OT_AddToSingleGroup(Operator):
    bl_idname = "list.add_to_single_group"
    bl_label = "Add to Group"
    bl_description = "Add checked constant materials to the selected group"
    bl_options = {'REGISTER'}

    group_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return bool(_get_checked_materials(context))

    def execute(self, context):
        scene = context.scene
        checked = _get_checked_materials(context)
        if not checked:
            self.report({'WARNING'}, "No constant materials checked.")
            return {'CANCELLED'}

        group_name = self.group_name
        if not group_name or group_name == "None":
            self.report({'WARNING'}, "No valid group selected.")
            return {'CANCELLED'}

        groups = {}
        if "constant_material_groups" in scene:
            try:
                groups = json.loads(scene["constant_material_groups"])
            except:
                groups = {}
        if group_name not in groups:
            self.report({'WARNING'}, f"Group '{group_name}' not found.")
            return {'CANCELLED'}

        existing = set(groups[group_name])
        selected_set = set(checked)
        to_add = selected_set - existing
        already_present = selected_set & existing

        if not to_add:
            # All selected items are already in the group
            self.report({'WARNING'}, f"All selected items are already in group '{group_name}'.")
            return {'CANCELLED'}

        # Add only the new ones
        groups[group_name] = list(existing | to_add)
        scene["constant_material_groups"] = json.dumps(groups)

        msg = f"Added {len(to_add)} material(s) to group '{group_name}'."
        if already_present:
            msg += f" {len(already_present)} already present."

        self.report({'INFO'}, msg)
        return {'FINISHED'}



# Remove checked materials from a single group

class LIST_OT_RemoveFromSingleGroup(Operator):
    bl_idname = "list.remove_from_single_group"
    bl_label = "Remove from Group"
    bl_description = "Remove checked constant materials from the selected group"
    bl_options = {'REGISTER'}

    group_name: StringProperty()

    @classmethod
    def poll(cls, context):
        return bool(_get_checked_materials(context))

    def execute(self, context):
        scene = context.scene
        checked = _get_checked_materials(context)
        if not checked:
            self.report({'WARNING'}, "No constant materials checked.")
            return {'CANCELLED'}

        group_name = self.group_name
        if not group_name or group_name == "None":
            self.report({'WARNING'}, "No valid group selected.")
            return {'CANCELLED'}

        groups = {}
        if "constant_material_groups" in scene:
            try:
                groups = json.loads(scene["constant_material_groups"])
            except:
                groups = {}
        if group_name not in groups:
            self.report({'WARNING'}, f"Group '{group_name}' not found.")
            return {'CANCELLED'}

        original_len = len(groups[group_name])
        new_list = [m for m in groups[group_name] if m not in checked]
        if not new_list:
            del groups[group_name]
            if scene.list_active_group == group_name:
                scene.list_active_group = ""
        else:
            groups[group_name] = new_list
        scene["constant_material_groups"] = json.dumps(groups)
        removed = original_len - len(new_list)
        self.report({'INFO'}, f"Removed {removed} material(s) from group '{group_name}'.")
        return {'FINISHED'}


# Registration list
group_operator_classes = [
    GroupItem,
    LIST_OT_GroupManagementDialog,
    LIST_OT_NewGroupSimple,
    LIST_OT_DeleteGroupSimple,
    LIST_OT_AddToSingleGroup,
    LIST_OT_RemoveFromSingleGroup,
]