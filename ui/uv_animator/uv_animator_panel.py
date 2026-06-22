import bpy
import json
import os
from bpy.types import Panel
from ...utils.uv_animator.uv_animator_utils import get_target_object
from ...operators.uv_animator.uv_animation import get_active_block, UV_OT_PlayPreview

def _redraw_ui(context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()

class UV_ANIMATOR_PT_MainPanel(Panel):
    bl_label = "UV Animator"
    bl_idname = "UV_ANIMATOR_PT_main_panel"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "UV Anim"

    def _get_groups_dict(self, scene):
        try:
            return json.loads(scene.uv_animator_groups)
        except:
            return {}

    def _get_items(self, scene):
        items = []
        if scene.uv_animator_mode == 'LEGACY':
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.is_uv_animated:
                    items.append({'obj': obj, 'block': None, 'key': obj.name})
        else:
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.is_uv_animated:
                    for block in obj.uv_animated_blocks:
                        if block.is_animated:
                            key = f"{obj.name}:{block.block_id}"
                            items.append({'obj': obj, 'block': block, 'key': key})
        return items

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Mode selector
        row = layout.row(align=True)
        row.prop(scene, "uv_animator_mode", expand=True)

        # Main controls
        row = layout.row(align=True)
        if scene.uv_animator_mode == 'LEGACY':
            row.operator("uv_animator.new_animation", text="New", icon='FILE_NEW')
        else:
            row.operator("uv_animator.new_animation_from_constants", text="New", icon='FILE_NEW')
        row.operator("uv_animator.delete_animation", text="Delete All", icon='TRASH')

        row = layout.row(align=True)
        row.operator("uv_animator.assign_frame", text="Assign Frame", icon='UV')

        if UV_OT_PlayPreview.is_playing():
            row.operator("uv_animator.stop_preview", text="Stop", icon='PAUSE')
        else:
            has_frames = False
            if scene.uv_animator_mode == 'LEGACY':
                has_frames = any(
                    obj.type == 'MESH' and obj.is_uv_animated and len(obj.uv_animation_frames) > 0
                    for obj in bpy.data.objects
                )
            else:
                has_frames = any(
                    obj.type == 'MESH' and block.is_animated and len(block.frames) > 0
                    for obj in bpy.data.objects for block in obj.uv_animated_blocks
                )
            if has_frames:
                row.operator("uv_animator.play_preview", text="Play", icon='PLAY')
            else:
                sub = row.row()
                sub.enabled = False
                sub.operator("uv_animator.play_preview", text="Play", icon='PLAY')

        row = layout.row(align=True)
        row.operator("uv_animator.export_animation", text="Export Animation", icon='EXPORT')

        # Group filter
        row = layout.row(align=True)
        active_group = scene.uv_animator_active_group
        button_text = active_group if active_group else "Group"
        row.operator("uv_animator.group_management_dialog", text=button_text, icon='GROUP')
        if active_group:
            row.operator("uv_animator.clear_active_group_filter", text="", icon='X', emboss=False)

        items = self._get_items(scene)
        if not items:
            layout.label(text="No animated items. Select mesh(es) and press 'New'.", icon='INFO')
            return

        groups = self._get_groups_dict(scene)
        if scene.uv_animator_mode == 'LEGACY':
            expanded = json.loads(scene.uv_animator_expanded)
        else:
            expanded = json.loads(scene.uv_animator_expanded_blocks)
        toggles = json.loads(scene.uv_animator_group_toggles)

        if active_group:
            if active_group not in groups:
                scene.uv_animator_active_group = ""
                self.draw_all_groups(layout, scene, items, groups, expanded, toggles)
            else:
                group_keys = set(groups[active_group])
                filtered_items = [it for it in items if it['key'] in group_keys]
                if not filtered_items:
                    layout.label(text=f"Group '{active_group}' is empty.", icon='INFO')
                else:
                    self.draw_group_section(layout, active_group, filtered_items, expanded, toggles, scene, is_ungrouped=False)
        else:
            self.draw_all_groups(layout, scene, items, groups, expanded, toggles)

        layout.separator()
        obj, block = get_active_block(context)
        if obj:
            if scene.uv_animator_mode == 'LEGACY':
                layout.label(text=f"Active target: {obj.name}", icon='OBJECT_DATA')
            else:
                if block:
                    layout.label(text=f"Active target: {obj.name} - Block {block.block_id}", icon='OBJECT_DATA')
                else:
                    layout.label(text="No active block", icon='ERROR')
        else:
            layout.label(text="No active target", icon='ERROR')

    def draw_all_groups(self, layout, scene, items, groups, expanded, toggles):
        grouped = {}
        for it in items:
            found = False
            for gname, members in groups.items():
                if it['key'] in members:
                    grouped.setdefault(gname, []).append(it)
                    found = True
                    break
            if not found:
                grouped.setdefault("Ungrouped", []).append(it)
        for gname, group_items in grouped.items():
            self.draw_group_section(layout, gname, group_items, expanded, toggles, scene, is_ungrouped=(gname == "Ungrouped"))

    def draw_group_section(self, layout, group_name, group_items, expanded, toggles, scene, is_ungrouped=False):
        key = f"_group_{group_name}"
        is_expanded = expanded.get(key, True)
        box = layout.box()
        header = box.row(align=True)
        icon = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
        op = header.operator("uv_animator.toggle_group_section", text="", icon=icon, emboss=False)
        op.group_name = group_name

        is_active = toggles.get(group_name, False)
        toggle_icon = 'RADIOBUT_ON' if is_active else 'RADIOBUT_OFF'
        if not is_ungrouped:
            op = header.operator("uv_animator.toggle_group_active", text="", icon=toggle_icon, emboss=False)
            op.group_name = group_name
        else:
            header.label(text="", icon='RADIOBUT_OFF')

        if is_ungrouped:
            header.label(text=f"{group_name} ({len(group_items)} items)", icon='OBJECT_DATA')
        else:
            header.label(text=f"{group_name} ({len(group_items)} items)", icon='GROUP')

        if not is_ungrouped and group_items:
            all_enabled = True
            for it in group_items:
                if scene.uv_animator_mode == 'LEGACY':
                    if not it['obj'].uv_animator_playback_enabled:
                        all_enabled = False
                        break
                else:
                    if not it['block'].playback_enabled:
                        all_enabled = False
                        break
            playback_icon = 'PLAY' if all_enabled else 'PAUSE'
            op_play = header.operator("uv_animator.toggle_group_playback", text="", icon=playback_icon, emboss=False)
            op_play.group_name = group_name

        if not is_ungrouped and group_items:
            first = group_items[0]
            if scene.uv_animator_mode == 'LEGACY':
                duration = first['obj'].uv_frame_duration
            else:
                duration = first['block'].frame_duration
            op_clock = header.operator("uv_animator.group_set_frame_duration", text=f"{duration}", icon='TIME')
            op_clock.group_name = group_name

        if not is_ungrouped:
            op_gear = header.operator("uv_animator.group_texture_settings", text="", icon='PREFERENCES')
            op_gear.group_name = group_name

        if not is_expanded:
            return

        for it in group_items:
            if scene.uv_animator_mode == 'LEGACY':
                self.draw_object_row(box, scene, it['obj'], expanded)
            else:
                self.draw_block_row(box, scene, it['obj'], it['block'], expanded)

    def draw_object_row(self, layout, scene, obj, expanded):
        box = layout.box()
        is_expanded = expanded.get(obj.name, False)
        header = box.row(align=True)
        icon = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
        op_exp = header.operator("uv_animator.toggle_expand", text="", icon=icon, emboss=False)
        op_exp.object_name = obj.name
        op_exp.block_id = ""

        is_active = (scene.active_uv_object_name == obj.name)
        active_icon = 'RADIOBUT_ON' if is_active else 'RADIOBUT_OFF'
        op_act = header.operator("uv_animator.set_active_uv_object", text=obj.name, icon=active_icon, emboss=False)
        op_act.object_name = obj.name
        op_act.block_id = ""

        header.label(text=f"({len(obj.uv_animation_frames)} frames)")

        playback = obj.uv_animator_playback_enabled
        op_tv = header.operator("uv_animator.toggle_playback", text="", icon='PLAY' if playback else 'PAUSE', emboss=False)
        op_tv.object_name = obj.name
        op_tv.block_id = ""

        duration = obj.uv_frame_duration
        op_clock = header.operator("uv_animator.set_frame_duration", text=f"{duration}", icon='TIME')
        op_clock.object_name = obj.name
        op_clock.block_id = ""

        sel_icon = 'CHECKBOX_HLT' if obj.uv_selected_for_group else 'CHECKBOX_DEHLT'
        op_sel = header.operator("uv_animator.toggle_group_selection", text="", icon=sel_icon, emboss=False)
        op_sel.object_name = obj.name
        op_sel.block_id = ""

        if is_expanded:
            frames = obj.uv_animation_frames
            if frames:
                col = box.column(align=True)
                for idx, frame in enumerate(frames):
                    row2 = col.row(align=True)
                    row2.label(text=f"Frame {idx}")
                    is_start = (obj.uv_start_frame == idx)
                    start_icon = 'MARKER_HLT' if is_start else 'MARKER'
                    op_start = row2.operator("uv_animator.set_start_frame", text="", icon=start_icon, emboss=False)
                    op_start.object_name = obj.name
                    op_start.block_id = ""
                    op_start.frame_index = idx
                    op_tex = row2.operator("uv_animator.show_frame_texture", text="", icon='TEXTURE', emboss=False)
                    op_tex.object_name = obj.name
                    op_tex.block_id = ""
                    op_tex.frame_index = idx
                    op_del = row2.operator("uv_animator.delete_frame", text="", icon='X', emboss=False)
                    op_del.object_name = obj.name
                    op_del.block_id = ""
                    op_del.frame_index = idx
            else:
                box.label(text="No frames. Enter Edit Mode and click 'Assign'.", icon='INFO')
            self.draw_texture_section(box, scene, obj, expanded, "")

    def draw_block_row(self, layout, scene, obj, block, expanded):
        key = f"{obj.name}:{block.block_id}"
        is_expanded = expanded.get(key, False)
        box = layout.box()
        header = box.row(align=True)
        icon = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
        op_exp = header.operator("uv_animator.toggle_expand", text="", icon=icon, emboss=False)
        op_exp.object_name = obj.name
        op_exp.block_id = block.block_id

        is_active = (scene.active_uv_block_key == key)
        active_icon = 'RADIOBUT_ON' if is_active else 'RADIOBUT_OFF'
        op_act = header.operator("uv_animator.set_active_uv_object", text=f"{obj.name} - {block.block_id}", icon=active_icon, emboss=False)
        op_act.object_name = obj.name
        op_act.block_id = block.block_id

        header.label(text=f"({len(block.frames)} frames)")

        playback = block.playback_enabled
        op_tv = header.operator("uv_animator.toggle_playback", text="", icon='PLAY' if playback else 'PAUSE', emboss=False)
        op_tv.object_name = obj.name
        op_tv.block_id = block.block_id

        duration = block.frame_duration
        op_clock = header.operator("uv_animator.set_frame_duration", text=f"{duration}", icon='TIME')
        op_clock.object_name = obj.name
        op_clock.block_id = block.block_id

        sel_icon = 'CHECKBOX_HLT' if block.selected_for_group else 'CHECKBOX_DEHLT'
        op_sel = header.operator("uv_animator.toggle_group_selection", text="", icon=sel_icon, emboss=False)
        op_sel.object_name = obj.name
        op_sel.block_id = block.block_id

        if is_expanded:
            frames = block.frames
            if frames:
                col = box.column(align=True)
                for idx, frame in enumerate(frames):
                    row2 = col.row(align=True)
                    row2.label(text=f"Frame {idx}")
                    is_start = (block.start_frame == idx)
                    start_icon = 'MARKER_HLT' if is_start else 'MARKER'
                    op_start = row2.operator("uv_animator.set_start_frame", text="", icon=start_icon, emboss=False)
                    op_start.object_name = obj.name
                    op_start.block_id = block.block_id
                    op_start.frame_index = idx
                    op_tex = row2.operator("uv_animator.show_frame_texture", text="", icon='TEXTURE', emboss=False)
                    op_tex.object_name = obj.name
                    op_tex.block_id = block.block_id
                    op_tex.frame_index = idx
                    op_del = row2.operator("uv_animator.delete_frame", text="", icon='X', emboss=False)
                    op_del.object_name = obj.name
                    op_del.block_id = block.block_id
                    op_del.frame_index = idx
            else:
                box.label(text="No frames. Enter Edit Mode and click 'Assign'.", icon='INFO')
            self.draw_texture_section(box, scene, obj, expanded, block.block_id)

    def draw_texture_section(self, layout, scene, obj, expanded, block_id):
        if block_id:
            key = f"_textures_{obj.name}_{block_id}"
        else:
            key = f"_textures_{obj.name}"
        is_texture_expanded = expanded.get(key, False)

        row = layout.row(align=True)
        icon = 'TRIA_DOWN' if is_texture_expanded else 'TRIA_RIGHT'
        op = row.operator("uv_animator.toggle_texture_section", text="", icon=icon, emboss=False)
        op.object_name = obj.name
        op.block_id = block_id
        row.label(text="Textures", icon='TEXTURE')

        if not is_texture_expanded:
            return

        col = layout.column(align=True)
        col.separator()

        if block_id:
            block = None
            for b in obj.uv_animated_blocks:
                if b.block_id == block_id:
                    block = b
                    break
            if not block:
                return
            texture_items = block.texture_items
        else:
            texture_items = obj.uv_texture_items

        if len(texture_items) == 0:
            col.label(text="No textures used in frames.", icon='INFO')
            return

        for item in texture_items:
            safe_path = item.texture_path.replace(os.sep, '_').replace(':', '_')
            if block_id:
                sub_key = f"_tex_sub_{obj.name}_{block_id}_{safe_path}"
            else:
                sub_key = f"_tex_sub_{obj.name}_{safe_path}"
            is_sub_expanded = expanded.get(sub_key, False)

            box = col.box()
            header = box.row(align=True)
            icon_sub = 'TRIA_DOWN' if is_sub_expanded else 'TRIA_RIGHT'
            op_sub = header.operator("uv_animator.toggle_texture_subsection", text="", icon=icon_sub, emboss=False)
            op_sub.object_name = obj.name
            op_sub.block_id = block_id
            op_sub.texture_path = item.texture_path

            header.label(text=os.path.basename(item.texture_path), icon='FILE_IMAGE')

            op_change = header.operator("uv_animator.change_texture_path", text="", icon='FILE_FOLDER')
            op_change.object_name = obj.name
            op_change.block_id = block_id
            op_change.old_texture_path = item.texture_path

            if is_sub_expanded:
                sub_col = box.column(align=True)
                sub_col.separator()
                sub_col.prop(item, "blend_mode", text="")

classes = [UV_ANIMATOR_PT_MainPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)