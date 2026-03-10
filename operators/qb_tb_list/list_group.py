"""
Group Management Operators for Constant Materials
Moved from ui/qb_tb_list/group_management.py
"""

import bpy
import json
from bpy.types import Operator
from bpy.props import StringProperty


class LIST_OT_SetConstantMaterialGroup(Operator):
    bl_idname = "list.set_constant_material_group"
    bl_label = "Set Constant Material Group"
    bl_description = "Select a group of constant materials to filter the list"
    bl_options = {'REGISTER'}

    group_name: StringProperty(name="Group Name", default="")

    def execute(self, context):
        context.scene.list_active_group = self.group_name
        return {'FINISHED'}


class LIST_OT_AddToGroup(Operator):
    bl_idname = "list.add_to_group"
    bl_label = "Add to Group"
    bl_description = "Add checked constant materials to a group"
    bl_options = {'REGISTER'}

    group_name: StringProperty(name="Group Name", default="")

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        return (obj is not None and
                "multi_selected_items" in obj and
                obj["multi_selected_items"] and
                context.scene.list_display_type == 'CONSTANT_MATERIALS')

    def invoke(self, context, event):
        if context.scene.list_active_group:
            self.group_name = context.scene.list_active_group
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.list_active_group:
            layout.box().label(text=f"Active Group: {scene.list_active_group}", icon='INFO')
        layout.prop(self, "group_name")
        
        # Show existing groups
        if "constant_material_groups" in scene:
            try:
                groups = json.loads(scene["constant_material_groups"])
                if groups:
                    box = layout.box()
                    box.label(text="Existing:", icon='GROUP')
                    for name in sorted(groups.keys())[:3]:
                        box.label(text=f"  • {name} ({len(groups[name])})")
            except:
                pass
        
        obj = context.edit_object
        if "multi_selected_items" in obj:
            multi = dict(obj["multi_selected_items"])
            const = [m for m in multi.keys() if m in obj.get("constant_materials", {})]
            layout.label(text=f"{len(const)} materials will be added", icon='INFO')

    def execute(self, context):
        scene = context.scene
        obj = context.edit_object
        
        if not self.group_name:
            self.report({'ERROR'}, "Group name cannot be empty")
            return {'CANCELLED'}

        if "multi_selected_items" not in obj or not obj["multi_selected_items"]:
            self.report({'WARNING'}, "No items checked")
            return {'CANCELLED'}

        multi = dict(obj["multi_selected_items"])
        checked = [m for m in multi.keys() if m in obj.get("constant_materials", {})]
        
        if not checked:
            self.report({'WARNING'}, "No constant materials checked")
            return {'CANCELLED'}

        # Load existing groups or initialize a new dictionary
        if "constant_material_groups" not in scene:
            groups = {}
        else:
            try:
                groups = json.loads(scene["constant_material_groups"])
            except:
                groups = {}

        existing = self.group_name in groups
        if existing:
            current = set(groups[self.group_name])
            current.update(checked)
            groups[self.group_name] = list(current)
            action = "added to existing"
        else:
            groups[self.group_name] = checked
            action = "created new"

        scene["constant_material_groups"] = json.dumps(groups)
        scene.list_active_group = self.group_name
        self.report({'INFO'}, f"{action} group '{self.group_name}' ({len(checked)} materials)")
        return {'FINISHED'}


class LIST_OT_RemoveFromGroup(Operator):
    bl_idname = "list.remove_from_group"
    bl_label = "Remove from Group"
    bl_description = "Remove checked constant materials from a group"
    bl_options = {'REGISTER'}

    group_name: StringProperty(name="Group Name", default="")

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        scene = context.scene
        if not obj or "multi_selected_items" not in obj or not obj["multi_selected_items"]:
            return False
        if scene.list_display_type != 'CONSTANT_MATERIALS':
            return False
        if "constant_material_groups" not in scene or not scene["constant_material_groups"]:
            return False
        return True

    def invoke(self, context, event):
        if not self.group_name and context.scene.list_active_group:
            self.group_name = context.scene.list_active_group
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        if scene.list_active_group and not self.group_name:
            layout.box().label(text=f"Active Group: {scene.list_active_group}", icon='INFO')
        
        if not scene.list_active_group or self.group_name:
            layout.prop(self, "group_name")
            
        # Show current groups
        if "constant_material_groups" in scene:
            try:
                groups = json.loads(scene["constant_material_groups"])
                if groups:
                    box = layout.box()
                    box.label(text="Existing:", icon='GROUP')
                    for name in sorted(groups.keys())[:3]:
                        if name == self.group_name or (not self.group_name and name == scene.list_active_group):
                            box.label(text=f"  • {name} ({len(groups[name])}) [TARGET]", icon='PINNED')
                        else:
                            box.label(text=f"  • {name} ({len(groups[name])})")
            except:
                pass
                
        obj = context.edit_object
        if "multi_selected_items" in obj:
            multi = dict(obj["multi_selected_items"])
            const = [m for m in multi.keys() if m in obj.get("constant_materials", {})]
            layout.label(text=f"{len(const)} materials will be removed", icon='INFO')

    def execute(self, context):
        scene = context.scene
        obj = context.edit_object
        target = self.group_name or scene.list_active_group
        
        if not target:
            self.report({'ERROR'}, "No group specified")
            return {'CANCELLED'}

        try:
            groups = json.loads(scene["constant_material_groups"])
        except:
            self.report({'ERROR'}, "Error loading groups")
            return {'CANCELLED'}

        if target not in groups:
            self.report({'WARNING'}, f"Group '{target}' not found")
            return {'CANCELLED'}

        multi = dict(obj["multi_selected_items"])
        checked = [m for m in multi.keys() if m in obj.get("constant_materials", {})]
        
        if not checked:
            self.report({'WARNING'}, "No constant materials checked")
            return {'CANCELLED'}

        original_len = len(groups[target])
        groups[target] = [m for m in groups[target] if m not in checked]
        removed = original_len - len(groups[target])

        if not groups[target]:
            del groups[target]
            status = "deleted (empty)"
            if scene.list_active_group == target:
                scene.list_active_group = ""
        else:
            status = "updated"

        scene["constant_material_groups"] = json.dumps(groups)
        self.report({'INFO'}, f"Removed {removed} materials from '{target}' ({status})")
        return {'FINISHED'}


classes = [
    LIST_OT_SetConstantMaterialGroup,
    LIST_OT_AddToGroup,
    LIST_OT_RemoveFromGroup,
]