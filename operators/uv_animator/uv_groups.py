import bpy
import json
from bpy.types import Operator

_active_uv_group_dialog = None

# Group Management

class UV_OT_ToggleGroupActive(Operator):
    bl_idname = "uv_animator.toggle_group_active"
    bl_label = "Toggle Group Active"
    bl_description = "Activate/deactivate this group for batch frame assignment"
    bl_options = {'REGISTER', 'UNDO'}
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        try:
            toggles = json.loads(scene.uv_animator_group_toggles)
        except:
            toggles = {}

        toggles[self.group_name] = not toggles.get(self.group_name, False)
        scene.uv_animator_group_toggles = json.dumps(toggles)

        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.tag_redraw()

        return {'FINISHED'}

class UV_OT_GroupManagementDialog(Operator):
    """Main group management dialog (Item List style)"""
    bl_idname = "uv_animator.group_management_dialog"
    bl_label = "Manage UV Groups"
    bl_description = "Create, delete, and assign UV animation objects to groups"
    bl_options = {'REGISTER'}

    groups_collection: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    selected_group_name: bpy.props.StringProperty(name="Group", default="")
    _new_group_name: str = None

    @classmethod
    def poll(cls, context):
        return any(obj.is_uv_animated for obj in bpy.data.objects if obj.type == 'MESH')

    def invoke(self, context, event):
        global _active_uv_group_dialog
        _active_uv_group_dialog = self
        self._refresh_groups_collection(context)
        
        current_filter = context.scene.uv_animator_active_group
        if current_filter and current_filter in [item.name for item in self.groups_collection]:
            self.selected_group_name = current_filter
        else:
            self.selected_group_name = "None"
        return context.window_manager.invoke_props_dialog(self, width=350)

    def _refresh_groups_collection(self, context):
        self.groups_collection.clear()
        none_item = self.groups_collection.add()
        none_item.name = "None"
        
        groups_dict = {}
        try:
            groups_dict = json.loads(context.scene.uv_animator_groups)
        except:
            pass
        
        for name in sorted(groups_dict.keys()):
            if name == "None":
                continue
            item = self.groups_collection.add()
            item.name = name

    def draw(self, context):
        self._refresh_groups_collection(context)
        
        if self._new_group_name:
            if any(item.name == self._new_group_name for item in self.groups_collection):
                self.selected_group_name = self._new_group_name
            else:
                self.selected_group_name = "None"
            self._new_group_name = None
        else:
            if self.selected_group_name and self.selected_group_name != "None":
                if not any(item.name == self.selected_group_name for item in self.groups_collection):
                    self.selected_group_name = "None"

        layout = self.layout
        
        row = layout.row()
        row.prop_search(self, "selected_group_name", self, "groups_collection", text="Group", icon='GROUP')
        
        col = layout.column(align=True)
        col.separator()
        
        row = col.row(align=True)
        row.operator("uv_animator.new_group_simple", text="New Group", icon='COLLECTION_NEW')
        
        if self.selected_group_name and self.selected_group_name != "None":
            op = row.operator("uv_animator.delete_group_simple", text="Delete Group", icon='TRASH')
            op.group_name = self.selected_group_name
        else:
            sub = row.row(align=True)
            sub.enabled = False
            sub.operator("uv_animator.delete_group_simple", text="Delete Group", icon='TRASH')
        
        col.separator()
        
        row = col.row(align=True)
        if self.selected_group_name and self.selected_group_name != "None":
            op = row.operator("uv_animator.add_to_group", text="Add Selected", icon='ADD')
            op.group_name = self.selected_group_name
            op = row.operator("uv_animator.remove_from_group", text="Remove Selected", icon='REMOVE')
            op.group_name = self.selected_group_name
        else:
            row.enabled = False
            row.operator("uv_animator.add_to_group", text="Add Selected", icon='ADD')
            row.operator("uv_animator.remove_from_group", text="Remove Selected", icon='REMOVE')

        col.separator()
        col.label(text="Select objects using checkboxes in the list.", icon='INFO')

    def execute(self, context):
        global _active_uv_group_dialog
        if self.selected_group_name == "None":
            context.scene.uv_animator_active_group = ""
        else:
            context.scene.uv_animator_active_group = self.selected_group_name
        
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        _active_uv_group_dialog = None
        return {'FINISHED'}

class UV_OT_NewGroupSimple(Operator):
    bl_idname = "uv_animator.new_group_simple"
    bl_label = "New Group"
    bl_description = "Create a new empty group"
    bl_options = {'REGISTER'}

    group_name: bpy.props.StringProperty(name="Group Name", default="")

    def invoke(self, context, event):
        self.group_name = ""
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "group_name", text="Name")

    def execute(self, context):
        global _active_uv_group_dialog
        scene = context.scene
        name = self.group_name.strip()
        if not name:
            self.report({'ERROR'}, "Group name cannot be empty.")
            return {'CANCELLED'}
        if name.lower() == "none":
            self.report({'ERROR'}, "Cannot create a group named 'None'.")
            return {'CANCELLED'}

        groups = {}
        try:
            groups = json.loads(scene.uv_animator_groups)
        except:
            pass
        
        if name in groups:
            self.report({'ERROR'}, f"Group '{name}' already exists.")
            return {'CANCELLED'}

        groups[name] = []
        scene.uv_animator_groups = json.dumps(groups)

        if _active_uv_group_dialog:
            _active_uv_group_dialog._new_group_name = name

        self.report({'INFO'}, f"Group '{name}' created.")
        return {'FINISHED'}

class UV_OT_DeleteGroupSimple(Operator):
    bl_idname = "uv_animator.delete_group_simple"
    bl_label = "Delete Group"
    bl_description = "Delete the selected group"
    bl_options = {'REGISTER'}

    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        name = self.group_name
        if not name or name == "None":
            self.report({'WARNING'}, "No valid group selected.")
            return {'CANCELLED'}

        groups = {}
        try:
            groups = json.loads(scene.uv_animator_groups)
        except:
            pass
        
        if name not in groups:
            self.report({'WARNING'}, f"Group '{name}' not found.")
            return {'CANCELLED'}

        del groups[name]
        scene.uv_animator_groups = json.dumps(groups)
        
        if scene.uv_animator_active_group == name:
            scene.uv_animator_active_group = ""

        self.report({'INFO'}, f"Deleted group '{name}'.")
        return {'FINISHED'}

class UV_OT_AddToGroup(Operator):
    bl_idname = "uv_animator.add_to_group"
    bl_label = "Add Selected to Group"
    bl_description = "Add selected objects (checked in list) to the group"
    bl_options = {'REGISTER'}

    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        group_name = self.group_name
        if not group_name or group_name == "None":
            self.report({'WARNING'}, "No valid group selected.")
            return {'CANCELLED'}

        selected_objects = [
            obj.name for obj in bpy.data.objects 
            if obj.type == 'MESH' and obj.is_uv_animated and obj.uv_selected_for_group
        ]
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected. Use checkboxes in the list.")
            return {'CANCELLED'}

        groups = {}
        try:
            groups = json.loads(scene.uv_animator_groups)
        except:
            pass

        if group_name not in groups:
            self.report({'WARNING'}, f"Group '{group_name}' not found.")
            return {'CANCELLED'}

        current_set = set(groups[group_name])
        to_add = set(selected_objects) - current_set
        
        if not to_add:
            self.report({'WARNING'}, "All selected objects are already in this group.")
            return {'CANCELLED'}

        groups[group_name] = list(current_set | to_add)
        scene.uv_animator_groups = json.dumps(groups)

        for obj_name in to_add:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.uv_selected_for_group = False

        self.report({'INFO'}, f"Added {len(to_add)} object(s) to group '{group_name}'.")
        return {'FINISHED'}

class UV_OT_RemoveFromGroup(Operator):
    bl_idname = "uv_animator.remove_from_group"
    bl_label = "Remove Selected from Group"
    bl_description = "Remove selected objects from the group"
    bl_options = {'REGISTER'}

    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        group_name = self.group_name
        if not group_name or group_name == "None":
            self.report({'WARNING'}, "No valid group selected.")
            return {'CANCELLED'}

        selected_objects = [
            obj.name for obj in bpy.data.objects 
            if obj.type == 'MESH' and obj.is_uv_animated and obj.uv_selected_for_group
        ]
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected. Use checkboxes in the list.")
            return {'CANCELLED'}

        groups = {}
        try:
            groups = json.loads(scene.uv_animator_groups)
        except:
            pass

        if group_name not in groups:
            self.report({'WARNING'}, f"Group '{group_name}' not found.")
            return {'CANCELLED'}

        original_len = len(groups[group_name])
        new_list = [obj for obj in groups[group_name] if obj not in selected_objects]
        removed = original_len - len(new_list)

        if removed == 0:
            self.report({'WARNING'}, "None of the selected objects are in this group.")
            return {'CANCELLED'}

        if new_list:
            groups[group_name] = new_list
        else:
            del groups[group_name]
            if scene.uv_animator_active_group == group_name:
                scene.uv_animator_active_group = ""

        scene.uv_animator_groups = json.dumps(groups)

        for obj_name in selected_objects:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                obj.uv_selected_for_group = False

        self.report({'INFO'}, f"Removed {removed} object(s) from group '{group_name}'.")
        return {'FINISHED'}

class UV_OT_ClearActiveGroupFilter(Operator):
    bl_idname = "uv_animator.clear_active_group_filter"
    bl_label = "Clear Filter"
    bl_description = "Clear the active group filter to show all objects"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.uv_animator_active_group = ""
        return {'FINISHED'}