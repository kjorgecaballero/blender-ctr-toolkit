import bpy
import json
import os
from bpy.types import Operator
from ...properties.uv_animator.uv_animator_props import UVTextureItem


# FRAME TEXTURE POPUP

class UV_OT_ShowFrameTexturePopup(Operator):
    bl_idname = "uv_animator.show_frame_texture"
    bl_label = "Show Frame Texture"
    bl_description = "Show the texture path of this frame"
    bl_options = {'REGISTER'}
    object_name: bpy.props.StringProperty()
    frame_index: bpy.props.IntProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}
        if self.frame_index >= len(obj.uv_animation_frames):
            return {'CANCELLED'}
        
        frame = obj.uv_animation_frames[self.frame_index]
        path = frame.texture_path if frame.texture_path else "No texture assigned"
        
        def draw_popup(self, context):
            layout = self.layout
            layout.label(text=path, icon='FILE_IMAGE')
        
        context.window_manager.popup_menu(draw_popup, title=f"Texture for Frame {self.frame_index}", icon='INFO')
        return {'FINISHED'}


# CHANGE TEXTURE PATH (per object)


class UV_OT_ChangeTexturePath(Operator):
    bl_idname = "uv_animator.change_texture_path"
    bl_label = "Change Texture"
    bl_description = "Select a new image for all frames using this texture"
    bl_options = {'REGISTER', 'UNDO'}
    
    object_name: bpy.props.StringProperty()
    old_texture_path: bpy.props.StringProperty()
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            self.report({'ERROR'}, "Object not found")
            return {'CANCELLED'}
        
        new_path = self.filepath
        if not new_path:
            return {'CANCELLED'}
        
        old_path = self.old_texture_path
        
        # Check if the new path already exists in another texture item
        existing_item = None
        for item in obj.uv_texture_items:
            if item.texture_path == new_path:
                existing_item = item
                break
        
        if existing_item:
            # Merge: update all frames to point to the existing item's path
            for frame in obj.uv_animation_frames:
                if frame.texture_path == old_path:
                    frame.texture_path = new_path
            # Remove the old item
            for i, item in enumerate(obj.uv_texture_items):
                if item.texture_path == old_path:
                    obj.uv_texture_items.remove(i)
                    break
            self.report({'INFO'}, f"Merged texture into existing entry: {os.path.basename(new_path)}")
        else:
            # Update the item's path
            for item in obj.uv_texture_items:
                if item.texture_path == old_path:
                    item.texture_path = new_path
                    break
            # Update all frames
            for frame in obj.uv_animation_frames:
                if frame.texture_path == old_path:
                    frame.texture_path = new_path
            self.report({'INFO'}, f"Texture updated to: {os.path.basename(new_path)}")
        
        return {'FINISHED'}


# GROUP TEXTURE SETTINGS with collapsible subsections


class UV_OT_GroupTextureSettings(Operator):
    bl_idname = "uv_animator.group_texture_settings"
    bl_label = "Group Texture Settings"
    bl_description = "Modify texture settings for all objects in this group"
    bl_options = {'REGISTER'}
    
    group_name: bpy.props.StringProperty()
    
    # Temporary collection to hold unique textures from the group
    temp_textures: bpy.props.CollectionProperty(type=UVTextureItem)
    
    def invoke(self, context, event):
        # Reset temp data
        self.temp_textures.clear()
        
        # Collect all objects in the group
        groups_dict = json.loads(context.scene.uv_animator_groups)
        if self.group_name not in groups_dict:
            self.report({'WARNING'}, f"Group '{self.group_name}' not found")
            return {'CANCELLED'}
        
        object_names = groups_dict[self.group_name]
        self._group_objects = [obj for obj in bpy.data.objects if obj.name in object_names and obj.type == 'MESH']
        
        if not self._group_objects:
            self.report({'WARNING'}, f"Group '{self.group_name}' has no valid mesh objects")
            return {'CANCELLED'}
        
        # Build a unified list of textures from all objects
        texture_map = {}  # path -> blend_mode (use first encountered)
        for obj in self._group_objects:
            for item in obj.uv_texture_items:
                if item.texture_path not in texture_map:
                    texture_map[item.texture_path] = item.blend_mode
        
        if not texture_map:
            self.report({'WARNING'}, f"No textures found in group '{self.group_name}'")
            return {'CANCELLED'}
        
        # Populate temp_textures
        for path, blend in texture_map.items():
            new_item = self.temp_textures.add()
            new_item.texture_path = path
            new_item.blend_mode = blend
        
        return context.window_manager.invoke_props_dialog(self, width=550)
    
    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Group: {self.group_name} ({len(self._group_objects)} objects)", icon='GROUP')
        layout.separator()
        
        if len(self.temp_textures) == 0:
            layout.label(text="No textures found", icon='INFO')
            return
        
        # Parse expanded state from scene property
        try:
            expanded_dict = json.loads(context.scene.uv_group_texture_expanded)
        except:
            expanded_dict = {}
        
        for idx, item in enumerate(self.temp_textures):
            tex_path = item.texture_path
            safe_path = tex_path.replace(os.sep, '_').replace(':', '_')
            is_expanded = expanded_dict.get(safe_path, False)
            
            box = layout.box()
            header = box.row(align=True)
            
            # Collapse toggle
            icon = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
            op = header.operator("uv_animator.group_toggle_texture_subsection", text="", icon=icon, emboss=False)
            op.group_name = self.group_name
            op.texture_path = tex_path
            op.index = idx
            
            # Texture name
            header.label(text=os.path.basename(tex_path), icon='FILE_IMAGE')
            
            # Blend mode dropdown (editable directly, updates temp item automatically)
            header.prop(item, "blend_mode", text="")
            
            # Change image button
            op_img = header.operator("uv_animator.group_change_texture_image", text="", icon='FILE_FOLDER')
            op_img.group_name = self.group_name
            op_img.texture_path = tex_path
            
            if is_expanded:
                sub_col = box.column(align=True)
                sub_col.separator()
                sub_col.label(text=f"Path: {tex_path}", icon='FILE_IMAGE')
    
    def execute(self, context):
        # Apply all changes from the temp collection to the actual objects
        for temp_item in self.temp_textures:
            tex_path = temp_item.texture_path
            blend_mode = temp_item.blend_mode
            for obj in self._group_objects:
                # Find the texture item in the object
                for tex_item in obj.uv_texture_items:
                    if tex_item.texture_path == tex_path:
                        tex_item.blend_mode = blend_mode
                        break
        self.report({'INFO'}, f"Applied texture settings to {len(self._group_objects)} object(s)")
        return {'FINISHED'}


# GROUP TOGGLE TEXTURE SUBSECTION (inside popup)


class UV_OT_GroupToggleTextureSubsection(Operator):
    bl_idname = "uv_animator.group_toggle_texture_subsection"
    bl_label = "Toggle Texture Subsection"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name: bpy.props.StringProperty()
    texture_path: bpy.props.StringProperty()
    index: bpy.props.IntProperty()
    
    def execute(self, context):
        try:
            expanded_dict = json.loads(context.scene.uv_group_texture_expanded)
        except:
            expanded_dict = {}
        
        safe_path = self.texture_path.replace(os.sep, '_').replace(':', '_')
        expanded_dict[safe_path] = not expanded_dict.get(safe_path, False)
        context.scene.uv_group_texture_expanded = json.dumps(expanded_dict)
        
        return {'FINISHED'}


# GROUP CHANGE TEXTURE IMAGE (from popup)


class UV_OT_GroupChangeTextureImage(Operator):
    bl_idname = "uv_animator.group_change_texture_image"
    bl_label = "Change Texture Image for Group"
    bl_description = "Change the texture image for this texture across all objects in the group"
    bl_options = {'REGISTER', 'UNDO'}
    
    group_name: bpy.props.StringProperty()
    texture_path: bpy.props.StringProperty()
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        new_path = self.filepath
        if not new_path:
            return {'CANCELLED'}
        
        old_path = self.texture_path
        groups_dict = json.loads(context.scene.uv_animator_groups)
        if self.group_name not in groups_dict:
            self.report({'ERROR'}, "Group not found")
            return {'CANCELLED'}
        
        object_names = groups_dict[self.group_name]
        updated = 0
        
        for obj_name in object_names:
            obj = bpy.data.objects.get(obj_name)
            if not obj or obj.type != 'MESH':
                continue
            
            # Check if the new path already exists in this object
            existing_item = None
            for item in obj.uv_texture_items:
                if item.texture_path == new_path:
                    existing_item = item
                    break
            
            if existing_item:
                # Merge: update frames and remove old item
                for frame in obj.uv_animation_frames:
                    if frame.texture_path == old_path:
                        frame.texture_path = new_path
                for i, item in enumerate(obj.uv_texture_items):
                    if item.texture_path == old_path:
                        obj.uv_texture_items.remove(i)
                        break
            else:
                # Update the item's path
                for item in obj.uv_texture_items:
                    if item.texture_path == old_path:
                        item.texture_path = new_path
                        break
                # Update frames
                for frame in obj.uv_animation_frames:
                    if frame.texture_path == old_path:
                        frame.texture_path = new_path
            updated += 1
        
        self.report({'INFO'}, f"Updated texture for {updated} object(s)")
        return {'FINISHED'}