import bpy
import json
from bpy.types import Operator

def _redraw_ui(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()

_active_uv_group_dialog = None

def _get_selected_items(context):
    scene = context.scene
    if scene.uv_animator_mode == 'LEGACY':
        return [o.name for o in bpy.data.objects if o.type == 'MESH' and o.is_uv_animated and o.uv_selected_for_group]
    else:
        keys = []
        for o in bpy.data.objects:
            if o.type != 'MESH':
                continue
            for block in o.uv_animated_blocks:
                if block.is_animated and block.selected_for_group:
                    keys.append(f"{o.name}:{block.block_id}")
        return keys

class UV_OT_ToggleGroupActive(Operator):
    bl_idname = "uv_animator.toggle_group_active"
    bl_label = "Toggle Group Active"
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
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_GroupManagementDialog(Operator):
    bl_idname = "uv_animator.group_management_dialog"
    bl_label = "Manage UV Groups"
    bl_options = {'REGISTER'}
    groups_collection: bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    selected_group_name: bpy.props.StringProperty(name="Group", default="")
    _new_group_name: str = None

    @classmethod
    def poll(cls, context):
        scene = context.scene
        if scene.uv_animator_mode == 'LEGACY':
            return any(o.type == 'MESH' and o.is_uv_animated for o in bpy.data.objects)
        else:
            return any(o.type == 'MESH' and any(b.is_animated for b in o.uv_animated_blocks) for o in bpy.data.objects)

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
        col.label(text="Select items using checkboxes in the list.", icon='INFO')

    def execute(self, context):
        global _active_uv_group_dialog
        if self.selected_group_name == "None":
            context.scene.uv_animator_active_group = ""
        else:
            context.scene.uv_animator_active_group = self.selected_group_name
        _redraw_ui(context)
        _active_uv_group_dialog = None
        return {'FINISHED'}

class UV_OT_NewGroupSimple(Operator):
    bl_idname = "uv_animator.new_group_simple"
    bl_label = "New Group"
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
    bl_options = {'REGISTER'}
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        group_name = self.group_name
        if not group_name or group_name == "None":
            self.report({'WARNING'}, "No valid group selected.")
            return {'CANCELLED'}
        selected_keys = _get_selected_items(context)
        if not selected_keys:
            self.report({'WARNING'}, "No items selected. Use checkboxes in the list.")
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
        to_add = set(selected_keys) - current_set
        if not to_add:
            self.report({'WARNING'}, "All selected items are already in this group.")
            return {'CANCELLED'}
        groups[group_name] = list(current_set | to_add)
        scene.uv_animator_groups = json.dumps(groups)
        if scene.uv_animator_mode == 'LEGACY':
            for key in to_add:
                obj = bpy.data.objects.get(key)
                if obj:
                    obj.uv_selected_for_group = False
        else:
            for key in to_add:
                parts = key.split(":", 1)
                if len(parts) == 2:
                    obj = bpy.data.objects.get(parts[0])
                    if obj:
                        for block in obj.uv_animated_blocks:
                            if block.block_id == parts[1]:
                                block.selected_for_group = False
                                break
        self.report({'INFO'}, f"Added {len(to_add)} item(s) to group '{group_name}'.")
        return {'FINISHED'}

class UV_OT_RemoveFromGroup(Operator):
    bl_idname = "uv_animator.remove_from_group"
    bl_label = "Remove Selected from Group"
    bl_options = {'REGISTER'}
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        group_name = self.group_name
        if not group_name or group_name == "None":
            self.report({'WARNING'}, "No valid group selected.")
            return {'CANCELLED'}
        selected_keys = _get_selected_items(context)
        if not selected_keys:
            self.report({'WARNING'}, "No items selected. Use checkboxes in the list.")
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
        new_list = [key for key in groups[group_name] if key not in selected_keys]
        removed = original_len - len(new_list)
        if removed == 0:
            self.report({'WARNING'}, "None of the selected items are in this group.")
            return {'CANCELLED'}
        if new_list:
            groups[group_name] = new_list
        else:
            del groups[group_name]
            if scene.uv_animator_active_group == group_name:
                scene.uv_animator_active_group = ""
        scene.uv_animator_groups = json.dumps(groups)
        if scene.uv_animator_mode == 'LEGACY':
            for key in selected_keys:
                obj = bpy.data.objects.get(key)
                if obj:
                    obj.uv_selected_for_group = False
        else:
            for key in selected_keys:
                parts = key.split(":", 1)
                if len(parts) == 2:
                    obj = bpy.data.objects.get(parts[0])
                    if obj:
                        for block in obj.uv_animated_blocks:
                            if block.block_id == parts[1]:
                                block.selected_for_group = False
                                break
        self.report({'INFO'}, f"Removed {removed} item(s) from group '{group_name}'.")
        return {'FINISHED'}

class UV_OT_ClearActiveGroupFilter(Operator):
    bl_idname = "uv_animator.clear_active_group_filter"
    bl_label = "Clear Filter"
    bl_options = {'REGISTER'}
    def execute(self, context):
        context.scene.uv_animator_active_group = ""
        _redraw_ui(context)
        return {'FINISHED'}

class UV_OT_GroupSetFrameDuration(Operator):
    bl_idname = "uv_animator.group_set_frame_duration"
    bl_label = "Group Set Frame Duration"
    bl_options = {'REGISTER', 'UNDO'}
    group_name: bpy.props.StringProperty()
    duration: bpy.props.IntProperty(default=0, min=0, max=30)

    def invoke(self, context, event):
        groups_dict = json.loads(context.scene.uv_animator_groups)
        if self.group_name in groups_dict:
            keys = groups_dict[self.group_name]
            if keys:
                scene = context.scene
                if scene.uv_animator_mode == 'LEGACY':
                    obj = bpy.data.objects.get(keys[0])
                    if obj:
                        self.duration = obj.uv_frame_duration
                else:
                    parts = keys[0].split(":", 1)
                    if len(parts) == 2:
                        obj = bpy.data.objects.get(parts[0])
                        if obj:
                            for block in obj.uv_animated_blocks:
                                if block.block_id == parts[1]:
                                    self.duration = block.frame_duration
                                    break
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "duration")
        real_duration = (self.duration + 1) * 0.033
        layout.label(text=f"Duration: {real_duration:.3f}s")

    def execute(self, context):
        scene = context.scene
        groups_dict = json.loads(scene.uv_animator_groups)
        if self.group_name not in groups_dict:
            self.report({'ERROR'}, "Group not found")
            return {'CANCELLED'}
        keys = groups_dict[self.group_name]
        updated = 0
        for key in keys:
            if scene.uv_animator_mode == 'LEGACY':
                obj = bpy.data.objects.get(key)
                if obj and obj.type == 'MESH':
                    obj.uv_frame_duration = self.duration
                    updated += 1
            else:
                parts = key.split(":", 1)
                if len(parts) == 2:
                    obj = bpy.data.objects.get(parts[0])
                    if obj:
                        for block in obj.uv_animated_blocks:
                            if block.block_id == parts[1]:
                                block.frame_duration = self.duration
                                updated += 1
                                break
        self.report({'INFO'}, f"Set frame duration to {self.duration} for {updated} item(s)")
        return {'FINISHED'}

class UV_OT_ToggleGroupPlayback(Operator):
    bl_idname = "uv_animator.toggle_group_playback"
    bl_label = "Toggle Group Playback"
    bl_options = {'REGISTER', 'UNDO'}
    group_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        groups_dict = json.loads(scene.uv_animator_groups)
        group_name = self.group_name
        if group_name == "Ungrouped":
            all_items = []
            if scene.uv_animator_mode == 'LEGACY':
                all_items = [o.name for o in bpy.data.objects if o.type == 'MESH' and o.is_uv_animated]
            else:
                all_items = []
                for o in bpy.data.objects:
                    if o.type == 'MESH' and o.is_uv_animated:
                        for block in o.uv_animated_blocks:
                            if block.is_animated:
                                all_items.append(f"{o.name}:{block.block_id}")
            grouped_keys = set()
            for members in groups_dict.values():
                grouped_keys.update(members)
            items = [key for key in all_items if key not in grouped_keys]
        else:
            if group_name not in groups_dict:
                self.report({'WARNING'}, f"Group '{group_name}' not found")
                return {'CANCELLED'}
            items = groups_dict[group_name]
        if not items:
            self.report({'WARNING'}, f"No items in group '{group_name}'")
            return {'CANCELLED'}
        all_enabled = True
        for key in items:
            if scene.uv_animator_mode == 'LEGACY':
                obj = bpy.data.objects.get(key)
                if obj and not obj.uv_animator_playback_enabled:
                    all_enabled = False
                    break
            else:
                parts = key.split(":", 1)
                if len(parts) == 2:
                    obj = bpy.data.objects.get(parts[0])
                    if obj:
                        for block in obj.uv_animated_blocks:
                            if block.block_id == parts[1]:
                                if not block.playback_enabled:
                                    all_enabled = False
                                    break
                        if not all_enabled:
                            break
        new_state = not all_enabled
        for key in items:
            if scene.uv_animator_mode == 'LEGACY':
                obj = bpy.data.objects.get(key)
                if obj:
                    obj.uv_animator_playback_enabled = new_state
            else:
                parts = key.split(":", 1)
                if len(parts) == 2:
                    obj = bpy.data.objects.get(parts[0])
                    if obj:
                        for block in obj.uv_animated_blocks:
                            if block.block_id == parts[1]:
                                block.playback_enabled = new_state
                                break
        self.report({'INFO'}, f"{'Enabled' if new_state else 'Disabled'} playback for {len(items)} item(s)")
        return {'FINISHED'}