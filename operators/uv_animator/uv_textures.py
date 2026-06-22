import bpy
import json
import os
from bpy.types import Operator
from ...properties.uv_animator.uv_texture_item import UVTextureItem

def _get_frames_and_textures(context, obj_name, block_id=""):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return None, None, None
    if block_id:
        for block in obj.uv_animated_blocks:
            if block.block_id == block_id:
                return obj, block.frames, block.texture_items
        return obj, None, None
    else:
        return obj, obj.uv_animation_frames, obj.uv_texture_items

class UV_OT_ShowFrameTexturePopup(Operator):
    bl_idname = "uv_animator.show_frame_texture"
    bl_label = "Show Frame Texture"
    bl_options = {'REGISTER'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")
    frame_index: bpy.props.IntProperty()

    def execute(self, context):
        obj, frames, _ = _get_frames_and_textures(context, self.object_name, self.block_id)
        if not obj or frames is None:
            return {'CANCELLED'}
        if self.frame_index >= len(frames):
            return {'CANCELLED'}
        frame = frames[self.frame_index]
        path = frame.texture_path if frame.texture_path else "No texture assigned"
        def draw_popup(self, context):
            layout = self.layout
            layout.label(text=path, icon='FILE_IMAGE')
        context.window_manager.popup_menu(draw_popup, title=f"Texture for Frame {self.frame_index}", icon='INFO')
        return {'FINISHED'}

class UV_OT_ChangeTexturePath(Operator):
    bl_idname = "uv_animator.change_texture_path"
    bl_label = "Change Texture"
    bl_options = {'REGISTER', 'UNDO'}
    object_name: bpy.props.StringProperty()
    block_id: bpy.props.StringProperty(default="")
    old_texture_path: bpy.props.StringProperty()
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        obj, frames, texture_items = _get_frames_and_textures(context, self.object_name, self.block_id)
        if not obj or frames is None or texture_items is None:
            self.report({'ERROR'}, "Object or block not found")
            return {'CANCELLED'}
        new_path = self.filepath
        if not new_path:
            return {'CANCELLED'}
        old_path = self.old_texture_path
        existing_item = None
        for item in texture_items:
            if item.texture_path == new_path:
                existing_item = item
                break
        if existing_item:
            for frame in frames:
                if frame.texture_path == old_path:
                    frame.texture_path = new_path
            for i, item in enumerate(texture_items):
                if item.texture_path == old_path:
                    texture_items.remove(i)
                    break
            self.report({'INFO'}, f"Merged texture into existing entry: {os.path.basename(new_path)}")
        else:
            for item in texture_items:
                if item.texture_path == old_path:
                    item.texture_path = new_path
                    break
            for frame in frames:
                if frame.texture_path == old_path:
                    frame.texture_path = new_path
            self.report({'INFO'}, f"Texture updated to: {os.path.basename(new_path)}")
        return {'FINISHED'}

class UV_OT_GroupTextureSettings(Operator):
    bl_idname = "uv_animator.group_texture_settings"
    bl_label = "Group Texture Settings"
    bl_options = {'REGISTER'}
    group_name: bpy.props.StringProperty()
    temp_textures: bpy.props.CollectionProperty(type=UVTextureItem)

    def invoke(self, context, event):
        self.temp_textures.clear()
        scene = context.scene
        groups_dict = json.loads(scene.uv_animator_groups)
        if self.group_name not in groups_dict:
            self.report({'WARNING'}, f"Group '{self.group_name}' not found")
            return {'CANCELLED'}
        keys = groups_dict[self.group_name]
        self._group_items = []
        for key in keys:
            if scene.uv_animator_mode == 'LEGACY':
                obj = bpy.data.objects.get(key)
                if obj and obj.type == 'MESH' and obj.is_uv_animated:
                    self._group_items.append({'obj': obj, 'block': None, 'texture_items': obj.uv_texture_items})
            else:
                parts = key.split(":", 1)
                if len(parts) == 2:
                    obj = bpy.data.objects.get(parts[0])
                    if obj:
                        for block in obj.uv_animated_blocks:
                            if block.block_id == parts[1] and block.is_animated:
                                self._group_items.append({'obj': obj, 'block': block, 'texture_items': block.texture_items})
                                break
        if not self._group_items:
            self.report({'WARNING'}, f"Group '{self.group_name}' has no valid items")
            return {'CANCELLED'}
        texture_map = {}
        for item in self._group_items:
            for tex_item in item['texture_items']:
                if tex_item.texture_path not in texture_map:
                    texture_map[tex_item.texture_path] = tex_item.blend_mode
        if not texture_map:
            self.report({'WARNING'}, f"No textures found in group '{self.group_name}'")
            return {'CANCELLED'}
        for path, blend in texture_map.items():
            new_item = self.temp_textures.add()
            new_item.texture_path = path
            new_item.blend_mode = blend
        return context.window_manager.invoke_props_dialog(self, width=550)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Group: {self.group_name} ({len(self._group_items)} items)", icon='GROUP')
        layout.separator()
        if len(self.temp_textures) == 0:
            layout.label(text="No textures found", icon='INFO')
            return
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
            icon = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
            op = header.operator("uv_animator.group_toggle_texture_subsection", text="", icon=icon, emboss=False)
            op.group_name = self.group_name
            op.texture_path = tex_path
            op.index = idx
            header.label(text=os.path.basename(tex_path), icon='FILE_IMAGE')
            header.prop(item, "blend_mode", text="")
            op_img = header.operator("uv_animator.group_change_texture_image", text="", icon='FILE_FOLDER')
            op_img.group_name = self.group_name
            op_img.texture_path = tex_path
            if is_expanded:
                sub_col = box.column(align=True)
                sub_col.separator()
                sub_col.label(text=f"Path: {tex_path}", icon='FILE_IMAGE')

    def execute(self, context):
        for temp_item in self.temp_textures:
            tex_path = temp_item.texture_path
            blend_mode = temp_item.blend_mode
            for item in self._group_items:
                for tex_item in item['texture_items']:
                    if tex_item.texture_path == tex_path:
                        tex_item.blend_mode = blend_mode
                        break
        self.report({'INFO'}, f"Applied texture settings to {len(self._group_items)} item(s)")
        return {'FINISHED'}

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

class UV_OT_GroupChangeTextureImage(Operator):
    bl_idname = "uv_animator.group_change_texture_image"
    bl_label = "Change Texture Image for Group"
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
                if not obj or obj.type != 'MESH':
                    continue
                frames = obj.uv_animation_frames
                texture_items = obj.uv_texture_items
            else:
                parts = key.split(":", 1)
                if len(parts) != 2:
                    continue
                obj = bpy.data.objects.get(parts[0])
                if not obj:
                    continue
                block = None
                for b in obj.uv_animated_blocks:
                    if b.block_id == parts[1]:
                        block = b
                        break
                if not block or not block.is_animated:
                    continue
                frames = block.frames
                texture_items = block.texture_items
            existing_item = None
            for item in texture_items:
                if item.texture_path == new_path:
                    existing_item = item
                    break
            if existing_item:
                for frame in frames:
                    if frame.texture_path == old_path:
                        frame.texture_path = new_path
                for i, item in enumerate(texture_items):
                    if item.texture_path == old_path:
                        texture_items.remove(i)
                        break
            else:
                for item in texture_items:
                    if item.texture_path == old_path:
                        item.texture_path = new_path
                        break
                for frame in frames:
                    if frame.texture_path == old_path:
                        frame.texture_path = new_path
            updated += 1
        self.report({'INFO'}, f"Updated texture for {updated} item(s)")
        return {'FINISHED'}