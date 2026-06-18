import bpy
import json
import os
from bpy.types import Panel
from ...utils.uv_animator.uv_animator_utils import get_target_object
from ...operators.uv_animator.uv_animation import UV_OT_PlayPreview

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

    def _get_ungrouped_objects(self, all_animated, groups):
        grouped_names = set()
        for members in groups.values():
            grouped_names.update(members)
        return [obj for obj in all_animated if obj.name not in grouped_names]

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Main controls
        row = layout.row(align=True)
        row.operator("uv_animator.new_animation", text="New", icon='FILE_NEW')
        row.operator("uv_animator.delete_animation", text="Delete All", icon='TRASH')

        row = layout.row(align=True)
        row.operator("uv_animator.assign_frame", text="Assign Frame", icon='UV')

        # Play / Stop
        if UV_OT_PlayPreview.is_playing():
            row.operator("uv_animator.stop_preview", text="Stop", icon='PAUSE')
        else:
            play_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.is_uv_animated and obj.uv_animator_playback_enabled]
            has_frames = any(len(obj.uv_animation_frames) > 0 for obj in play_objects)
            if has_frames:
                row.operator("uv_animator.play_preview", text="Play", icon='PLAY')
            else:
                sub = row.row()
                sub.enabled = False
                sub.operator("uv_animator.play_preview", text="Play", icon='PLAY')

        # Export animation
        row = layout.row(align=True)
        row.operator("uv_animator.export_animation", text="Export Animation", icon='EXPORT')

        # Group filter
        row = layout.row(align=True)
        active_group = scene.uv_animator_active_group
        button_text = active_group if active_group else "Group"
        row.operator("uv_animator.group_management_dialog", text=button_text, icon='GROUP')
        if active_group:
            row.operator("uv_animator.clear_active_group_filter", text="", icon='X', emboss=False)

        # Get all animated objects
        all_animated = [obj for obj in bpy.data.objects if obj.type == 'MESH' and obj.is_uv_animated]
        if not all_animated:
            layout.label(text="No animated objects. Select mesh(es) and press 'New'.", icon='INFO')
            return

        groups = self._get_groups_dict(scene)
        expanded = json.loads(scene.uv_animator_expanded)
        toggles = json.loads(scene.uv_animator_group_toggles)

        # Decide what to display
        if active_group:
            if active_group not in groups:
                scene.uv_animator_active_group = ""
                self.draw_all_groups(layout, scene, all_animated, groups, expanded, toggles)
            else:
                group_members = set(groups[active_group])
                objects_in_group = [obj for obj in all_animated if obj.name in group_members]
                if not objects_in_group:
                    layout.label(text=f"Group '{active_group}' is empty.", icon='INFO')
                else:
                    self.draw_group_section(layout, active_group, objects_in_group, expanded, toggles, scene)
        else:
            self.draw_all_groups(layout, scene, all_animated, groups, expanded, toggles)

        # Active target indicator
        layout.separator()
        target = get_target_object(context)
        if target:
            layout.label(text=f"Active target: {target.name}", icon='OBJECT_DATA')
        else:
            layout.label(text="No active target", icon='ERROR')

    def draw_all_groups(self, layout, scene, all_animated, groups, expanded, toggles):
        for group_name, members in groups.items():
            objects_in_group = [obj for obj in all_animated if obj.name in members]
            if objects_in_group:
                self.draw_group_section(layout, group_name, objects_in_group, expanded, toggles, scene)
        
        ungrouped = self._get_ungrouped_objects(all_animated, groups)
        if ungrouped:
            self.draw_group_section(layout, "Ungrouped", ungrouped, expanded, toggles, scene, is_ungrouped=True)

    def draw_group_section(self, layout, group_name, objects, expanded, toggles, scene, is_ungrouped=False):
        key = f"_group_{group_name}"
        is_expanded = expanded.get(key, True)

        box = layout.box()
        header = box.row(align=True)

        # Expand / collapse
        icon = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
        op = header.operator("uv_animator.toggle_group_section", text="", icon=icon, emboss=False)
        op.group_name = group_name

        # Group toggle (radio button) - only for real groups
        is_active = toggles.get(group_name, False)
        toggle_icon = 'RADIOBUT_ON' if is_active else 'RADIOBUT_OFF'
        if not is_ungrouped:
            op = header.operator("uv_animator.toggle_group_active", text="", icon=toggle_icon, emboss=False)
            op.group_name = group_name
        else:
            header.label(text="", icon='RADIOBUT_OFF')

        # Label
        if is_ungrouped:
            header.label(text=f"{group_name} ({len(objects)} objects)", icon='OBJECT_DATA')
        else:
            header.label(text=f"{group_name} ({len(objects)} objects)", icon='GROUP')

        # Group playback button (only for real groups)
        if not is_ungrouped and objects:
            all_enabled = all(obj.uv_animator_playback_enabled for obj in objects)
            playback_icon = 'PLAY' if all_enabled else 'PAUSE'
            op_play = header.operator("uv_animator.toggle_group_playback", text="", icon=playback_icon, emboss=False)
            op_play.group_name = group_name

        # Group duration (only for real groups)
        if not is_ungrouped and objects:
            duration = objects[0].uv_frame_duration
            op_clock = header.operator("uv_animator.group_set_frame_duration", text=f"{duration}", icon='TIME')
            op_clock.group_name = group_name

        # Only for real groups
        if not is_ungrouped:
            op_gear = header.operator("uv_animator.group_texture_settings", text="", icon='PREFERENCES')
            op_gear.group_name = group_name

        if not is_expanded:
            return

        for obj in objects:
            self.draw_object_row(box, scene, obj, expanded)

    def draw_object_row(self, layout, scene, obj, expanded):
        box = layout.box()
        is_expanded = expanded.get(obj.name, False)

        header = box.row(align=True)

        # Expand toggle for frames
        icon = 'TRIA_DOWN' if is_expanded else 'TRIA_RIGHT'
        op_exp = header.operator("uv_animator.toggle_expand", text="", icon=icon, emboss=False)
        op_exp.object_name = obj.name

        # Active radio (object name)
        is_active = (scene.active_uv_object_name == obj.name)
        active_icon = 'RADIOBUT_ON' if is_active else 'RADIOBUT_OFF'
        op_act = header.operator("uv_animator.set_active_uv_object", text=obj.name, icon=active_icon, emboss=False)
        op_act.object_name = obj.name

        # Frame count
        header.label(text=f"({len(obj.uv_animation_frames)} frames)")

        # Playback toggle
        playback_enabled = obj.uv_animator_playback_enabled
        tv_icon = 'PLAY' if playback_enabled else 'PAUSE'
        op_tv = header.operator("uv_animator.toggle_playback", text="", icon=tv_icon, emboss=False)
        op_tv.object_name = obj.name

        # Duration per frame
        duration = obj.uv_frame_duration
        op_clock = header.operator("uv_animator.set_frame_duration", text=f"{duration}", icon='TIME')
        op_clock.object_name = obj.name

        # Selection checkbox (group check)
        sel_icon = 'CHECKBOX_HLT' if obj.uv_selected_for_group else 'CHECKBOX_DEHLT'
        op_sel = header.operator("uv_animator.toggle_group_selection", text="", icon=sel_icon, emboss=False)
        op_sel.object_name = obj.name

        if is_expanded:
            # Frame list
            frames = obj.uv_animation_frames
            if len(frames) > 0:
                col = box.column(align=True)
                for idx, frame in enumerate(frames):
                    row2 = col.row(align=True)
                    row2.label(text=f"Frame {idx}")
                    
                    # Start frame marker 
                    is_start = (obj.uv_start_frame == idx)
                    start_icon = 'MARKER_HLT' if is_start else 'MARKER'
                    op_start = row2.operator("uv_animator.set_start_frame", text="", icon=start_icon, emboss=False)
                    op_start.object_name = obj.name
                    op_start.frame_index = idx
                    
                    # Texture icon button -> shows popup with path
                    op_tex = row2.operator("uv_animator.show_frame_texture", text="", icon='TEXTURE')
                    op_tex.object_name = obj.name
                    op_tex.frame_index = idx
                    
                    # Delete button
                    op_del = row2.operator("uv_animator.delete_frame", text="", icon='X')
                    op_del.object_name = obj.name
                    op_del.frame_index = idx
            else:
                box.label(text="No frames. Enter Edit Mode and click 'Assign'.", icon='INFO')

            # Texture section (collapsible)
            self.draw_texture_section(box, scene, obj, expanded)

    def draw_texture_section(self, layout, scene, obj, expanded):
        key = f"_textures_{obj.name}"
        is_texture_expanded = expanded.get(key, False)

        row = layout.row(align=True)
        icon = 'TRIA_DOWN' if is_texture_expanded else 'TRIA_RIGHT'
        op = row.operator("uv_animator.toggle_texture_section", text="", icon=icon, emboss=False)
        op.object_name = obj.name
        row.label(text="Textures", icon='TEXTURE')

        if not is_texture_expanded:
            return

        col = layout.column(align=True)
        col.separator()

        if len(obj.uv_texture_items) == 0:
            col.label(text="No textures used in frames.", icon='INFO')
            return

        for item in obj.uv_texture_items:
            safe_path = item.texture_path.replace(os.sep, '_').replace(':', '_')
            sub_key = f"_tex_sub_{obj.name}_{safe_path}"
            is_sub_expanded = expanded.get(sub_key, False)

            box = col.box()
            header = box.row(align=True)

            icon_sub = 'TRIA_DOWN' if is_sub_expanded else 'TRIA_RIGHT'
            op_sub = header.operator("uv_animator.toggle_texture_subsection", text="", icon=icon_sub, emboss=False)
            op_sub.object_name = obj.name
            op_sub.texture_path = item.texture_path

            header.label(text=os.path.basename(item.texture_path), icon='FILE_IMAGE')

            op_change = header.operator("uv_animator.change_texture_path", text="", icon='FILE_FOLDER')
            op_change.object_name = obj.name
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