"""
Multi-Selection Operators for Quadblock/Triblock List
"""

import bpy
import bmesh
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty

from ...ui.qb_tb_list.list_helpers import get_block_material_name


def _get_filtered_display_items(context, obj, scene):
    """Return list of dicts with visible items (quadblocks/triblocks) in current list."""
    items = []
    display_type = scene.list_display_type

    if display_type == 'VERTEX_GROUPS':
        for vg in obj.vertex_groups:
            if vg.name.startswith("QB_") and scene.list_filter_show_qb:
                try:
                    block_id = int(vg.name[3:])
                    material = get_block_material_name(obj, 'quadblock', block_id)
                    items.append({
                        'name': vg.name,
                        'material': material,
                        'block_type': 'quadblock',
                        'block_id': block_id
                    })
                except ValueError:
                    continue
            elif vg.name.startswith("TB_") and scene.list_filter_show_tb:
                try:
                    block_id = int(vg.name[3:])
                    material = get_block_material_name(obj, 'triblock', block_id)
                    items.append({
                        'name': vg.name,
                        'material': material,
                        'block_type': 'triblock',
                        'block_id': block_id
                    })
                except ValueError:
                    continue

    elif display_type == 'CONSTANT_MATERIALS' and "constant_materials" in obj:
        for mat_name, info in obj["constant_materials"].items():
            bt = info.get("block_type", "")
            if (bt == "quadblock" and scene.list_filter_cm_qb) or \
               (bt == "triblock" and scene.list_filter_cm_tb):
                items.append({
                    'name': mat_name,
                    'material': mat_name,
                    'block_type': bt,
                    'block_id': info.get("block_id", 0)
                })

    # Filter by active group (constant materials)
    if display_type == 'CONSTANT_MATERIALS' and scene.list_active_group:
        if "constant_material_groups" in scene:
            try:
                import json
                groups = json.loads(scene["constant_material_groups"])
                if scene.list_active_group in groups:
                    group_set = set(groups[scene.list_active_group])
                    items = [it for it in items if it['name'] in group_set]
            except:
                pass

    # Filter by material
    mat_filter = scene.list_material_filter_vg if display_type == 'VERTEX_GROUPS' else scene.list_material_filter_cm
    if mat_filter:
        items = [it for it in items if it['material'] == mat_filter]

    # Filter by search text
    search = scene.list_search_text.lower()
    if search:
        items = [it for it in items if
                 search in it['name'].lower() or
                 search in str(it['block_id']) or
                 search in it['block_type'].lower()]

    # Apply issue filter (only for vertex groups) 
    if display_type == 'VERTEX_GROUPS':
        issues_dict = {}
        if "vertex_group_issues" in obj:
            issues_dict = dict(obj["vertex_group_issues"])

        filtered = []
        for it in items:
            item_issues = issues_dict.get(it['name'], [])
            real_issues = [i for i in item_issues if i not in ('quadblock', 'triblock')]
            issue_filter = scene.list_issue_filter

            if issue_filter == 'ALL':
                filtered.append(it)
            elif issue_filter == 'VALID':
                has_block_marker = ('quadblock' in item_issues or 'triblock' in item_issues)
                if has_block_marker and len(real_issues) == 0:
                    filtered.append(it)
            elif issue_filter == 'INVALID':
                if len(real_issues) > 0:
                    filtered.append(it)
            elif issue_filter == 'INVALID_GEOMETRY':
                if 'invalid_geometry' in item_issues:
                    filtered.append(it)
            elif issue_filter == 'INVALID_UVS':
                if 'invalid_uvs' in item_issues:
                    filtered.append(it)
            elif issue_filter == 'INVALID_TRIBLOCK_UVS':
                if 'invalid_triblock_uvs' in item_issues:
                    filtered.append(it)
            elif issue_filter == 'DEGENERATED_UVS':
                if 'degenerated_uvs' in item_issues:
                    filtered.append(it)
            elif issue_filter == 'OUT_OF_RANGE':
                if 'out_of_range' in item_issues:
                    filtered.append(it)
        items = filtered

    return items


class LIST_OT_ToggleMultiSelection(Operator):
    bl_idname = "list.toggle_multi_selection"
    bl_label = "Toggle Multi Selection"
    bl_description = "Toggle selection of this quadblock/triblock item (automatically updates 3D view)"
    bl_options = {'REGISTER'}

    item_name: StringProperty(name="Item Name")

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def execute(self, context):
        obj = context.edit_object
        scene = context.scene

        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            if "multi_selected_items" not in obj:
                obj["multi_selected_items"] = {}

            multi_selected = obj["multi_selected_items"]
            was_selected = self.item_name in multi_selected

            if was_selected:
                del multi_selected[self.item_name]
                new_state = False
            else:
                multi_selected[self.item_name] = True
                new_state = True

            obj["multi_selected_items"] = multi_selected

        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        self.update_single_item_selection(context, obj, self.item_name, new_state)
        return {'FINISHED'}

    def update_single_item_selection(self, context, obj, item_name, select_state):
        scene = context.scene
        display_type = scene.list_display_type

        if display_type == 'VERTEX_GROUPS':
            if item_name.startswith(("QB_", "TB_")) and item_name in obj.vertex_groups:
                vg = obj.vertex_groups[item_name]

                original_mode = context.mode
                if original_mode == 'EDIT_MESH':
                    bpy.ops.object.mode_set(mode='OBJECT')

                try:
                    vertex_indices = []
                    for vert in obj.data.vertices:
                        try:
                            if vg.weight(vert.index) > 0:
                                vertex_indices.append(vert.index)
                        except RuntimeError:
                            pass

                    bpy.ops.object.mode_set(mode='EDIT')
                    bm = bmesh.from_edit_mesh(obj.data)
                    bm.verts.ensure_lookup_table()
                    bm.faces.ensure_lookup_table()

                    for idx in vertex_indices:
                        if idx < len(bm.verts):
                            bm.verts[idx].select = select_state

                    for face in bm.faces:
                        if select_state:
                            all_selected = all(v.select for v in face.verts)
                            if all_selected:
                                face.select = True
                        else:
                            face_verts_in_group = sum(1 for v in face.verts if v.index in vertex_indices)
                            if face_verts_in_group == len(face.verts):
                                face.select = False

                    bmesh.update_edit_mesh(obj.data)

                finally:
                    if original_mode == 'OBJECT':
                        bpy.ops.object.mode_set(mode='OBJECT')

        elif display_type == 'CONSTANT_MATERIALS':
            if "constant_materials" in obj and item_name in obj["constant_materials"]:
                original_mode = context.mode
                if original_mode != 'EDIT_MESH':
                    bpy.ops.object.mode_set(mode='EDIT')

                try:
                    material_index = -1
                    for i, slot in enumerate(obj.material_slots):
                        if slot.material and slot.material.name == item_name:
                            material_index = i
                            break

                    if material_index != -1:
                        bpy.ops.object.mode_set(mode='OBJECT')
                        faces_with_material = [i for i, p in enumerate(obj.data.polygons)
                                               if p.material_index == material_index]

                        bpy.ops.object.mode_set(mode='EDIT')
                        bm = bmesh.from_edit_mesh(obj.data)
                        bm.faces.ensure_lookup_table()

                        for face_idx in faces_with_material:
                            if face_idx < len(bm.faces):
                                bm.faces[face_idx].select = select_state

                        bmesh.update_edit_mesh(obj.data)

                finally:
                    if original_mode != 'EDIT_MESH':
                        bpy.ops.object.mode_set(mode=original_mode)


class LIST_OT_ClearMultiSelection(Operator):
    bl_idname = "list.clear_multi_selection"
    bl_label = "Clear All Checks"
    bl_description = "Clear all multi-selected items (all items, not just current list)"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            if "multi_selected_items" in obj and obj["multi_selected_items"]:
                obj["multi_selected_items"].clear()
            self.report({'INFO'}, "Cleared all checks")
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        return {'FINISHED'}


class LIST_OT_SelectMultiChecked(Operator):
    bl_idname = "list.select_multi_checked"
    bl_label = "Select Multi Checked"
    bl_description = "Select all checked quadblocks/triblocks in the 3D view"
    bl_options = {'REGISTER', 'UNDO'}

    select_all: BoolProperty(default=False)
    clear_existing: BoolProperty(default=True)

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object
        scene = context.scene
        display_type = scene.list_display_type

        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        if display_type == 'VERTEX_GROUPS':
            target_vg_names = []
            if self.select_all:
                for vg in obj.vertex_groups:
                    if vg.name.startswith("QB_") and scene.list_filter_show_qb:
                        target_vg_names.append(vg.name)
                    elif vg.name.startswith("TB_") and scene.list_filter_show_tb:
                        target_vg_names.append(vg.name)
            else:
                if "multi_selected_items" not in obj or not obj["multi_selected_items"]:
                    self.report({'WARNING'}, "No items checked. Use 'Select ALL'.")
                    return {'CANCELLED'}
                multi_selected = dict(obj["multi_selected_items"])
                target_vg_names = list(multi_selected.keys())

            if not target_vg_names:
                self.report({'WARNING'}, "No vertex groups to select.")
                return {'CANCELLED'}

            vg_indices = [vg.index for vg in obj.vertex_groups if vg.name in target_vg_names]
            if not vg_indices:
                self.report({'WARNING'}, "No matching vertex groups.")
                return {'CANCELLED'}

            original_mode = context.mode
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='OBJECT')

            try:
                mesh = obj.data
                bm = bmesh.new()
                bm.from_mesh(mesh)
                bm.verts.ensure_lookup_table()
                deform_layer = bm.verts.layers.deform.active
                if not deform_layer:
                    bm.free()
                    self.report({'WARNING'}, "No vertex group data found.")
                    return {'CANCELLED'}

                target_set = set(vg_indices)
                vertex_indices = set()
                for vert in bm.verts:
                    deform = vert[deform_layer]
                    for vg_idx in deform.keys():
                        if vg_idx in target_set and deform[vg_idx] > 0:
                            vertex_indices.add(vert.index)
                            break
                bm.free()

                bpy.ops.object.mode_set(mode='EDIT')
                bm_edit = bmesh.from_edit_mesh(obj.data)
                bm_edit.verts.ensure_lookup_table()
                bm_edit.faces.ensure_lookup_table()

                if self.clear_existing:
                    for v in bm_edit.verts:
                        v.select = False
                    for f in bm_edit.faces:
                        f.select = False

                for idx in vertex_indices:
                    if idx < len(bm_edit.verts):
                        bm_edit.verts[idx].select = True

                selected_vert_indices = vertex_indices
                for face in bm_edit.faces:
                    if all(v.index in selected_vert_indices for v in face.verts):
                        face.select = True

                bmesh.update_edit_mesh(obj.data)
                count = len(vertex_indices)
                self.report({'INFO'}, f"Selected {len(target_vg_names)} groups ({count} vertices)")

            finally:
                if original_mode == 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

        elif display_type == 'CONSTANT_MATERIALS':
            if "constant_materials" not in obj or not obj["constant_materials"]:
                self.report({'WARNING'}, "No constant materials found.")
                return {'CANCELLED'}

            const_dict = dict(obj["constant_materials"])
            target_mats = []
            if self.select_all:
                for mat_name, info in const_dict.items():
                    bt = info.get("block_type", "")
                    if (bt == "quadblock" and scene.list_filter_cm_qb) or \
                       (bt == "triblock" and scene.list_filter_cm_tb):
                        target_mats.append(mat_name)
            else:
                if "multi_selected_items" not in obj or not obj["multi_selected_items"]:
                    self.report({'WARNING'}, "No items checked.")
                    return {'CANCELLED'}
                multi = dict(obj["multi_selected_items"])
                target_mats = [m for m in multi.keys() if m in const_dict]

            if not target_mats:
                self.report({'WARNING'}, "No materials to select.")
                return {'CANCELLED'}

            original_mode = context.mode
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='OBJECT')

            try:
                if self.clear_existing:
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='DESELECT')
                    bpy.ops.object.mode_set(mode='OBJECT')

                mat_indices = {}
                for i, slot in enumerate(obj.material_slots):
                    if slot.material and slot.material.name in target_mats:
                        mat_indices[slot.material.name] = i

                face_count = 0
                selected_verts = set()
                for poly in obj.data.polygons:
                    if poly.material_index < len(obj.material_slots):
                        slot = obj.material_slots[poly.material_index]
                        if slot.material and slot.material.name in target_mats:
                            poly.select = True
                            face_count += 1
                            for v_idx in poly.vertices:
                                selected_verts.add(v_idx)

                for v_idx in selected_verts:
                    if v_idx < len(obj.data.vertices):
                        obj.data.vertices[v_idx].select = True

                for edge in obj.data.edges:
                    if edge.vertices[0] in selected_verts and edge.vertices[1] in selected_verts:
                        edge.select = True

                obj.data.update()
                bpy.ops.object.mode_set(mode='EDIT')
                self.report({'INFO'}, f"Selected {len(target_mats)} materials ({face_count} faces)")

            finally:
                if original_mode == 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}


class LIST_OT_CheckAll(Operator):
    bl_idname = "list.check_all"
    bl_label = "Check All"
    bl_description = "Check all items (quadblocks/triblocks) in the current list (applies filters and search)"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def execute(self, context):
        obj = context.edit_object
        scene = context.scene
        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            if "multi_selected_items" not in obj:
                obj["multi_selected_items"] = {}

            multi = obj["multi_selected_items"]
            display_items = _get_filtered_display_items(context, obj, scene)

            newly_marked = 0
            for item in display_items:
                name = item['name']
                if name not in multi:
                    multi[name] = True
                    newly_marked += 1

            if newly_marked > 0:
                obj["multi_selected_items"] = multi

            self.report({'INFO'}, f"Marked {newly_marked} new items")

        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.list.select_multi_checked(select_all=False, clear_existing=False)
        return {'FINISHED'}


class LIST_OT_ClearChecksInCurrentList(Operator):
    bl_idname = "list.clear_checks_in_current_list"
    bl_label = "Clear Checks in Current List"
    bl_description = "Clear checks only for items (quadblocks/triblocks) in the current filtered list"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def execute(self, context):
        obj = context.edit_object
        scene = context.scene
        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            if "multi_selected_items" not in obj or not obj["multi_selected_items"]:
                return {'FINISHED'}

            multi = obj["multi_selected_items"]
            items = _get_filtered_display_items(context, obj, scene)

            removed = 0
            for it in items:
                name = it['name']
                if name in multi:
                    del multi[name]
                    removed += 1

            obj["multi_selected_items"] = multi
            self.report({'INFO'}, f"Cleared {removed} checks")

        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        if "multi_selected_items" in obj and obj["multi_selected_items"]:
            bpy.ops.list.select_multi_checked(select_all=False, clear_existing=True)

        return {'FINISHED'}


class LIST_OT_ShowVertexGroupIssues(Operator):
    """Show detailed issues for a vertex group in a popup dialog"""
    bl_idname = "list.show_vertex_group_issues"
    bl_label = "Vertex Group Issues"
    bl_description = "Show detailed issues for this vertex group"
    bl_options = {'REGISTER'}

    group_name: StringProperty(name="Group Name")

    def execute(self, context):
        obj = context.edit_object
        if not obj or "vertex_group_issues" not in obj:
            self.report({'WARNING'}, "No issue data found for this object.")
            return {'CANCELLED'}

        issues_dict = dict(obj["vertex_group_issues"])
        issues = issues_dict.get(self.group_name, [])

        if not issues:
            self.report({'INFO'}, f"No issues for vertex group '{self.group_name}'.")
            return {'FINISHED'}

        lines = []
        lines.append(f"Issues for vertex group: {self.group_name}")
        lines.append("-" * 30)

        issue_map = {
            'quadblock': ("Valid Quadblock", 'INFO'),
            'triblock': ("Valid Triblock", 'INFO'),
            'invalid_geometry': ("Invalid Geometry", 'ERROR'),
            'invalid_uvs': ("UVs outside 0-1 range", 'UV'),
            'invalid_triblock_uvs': ("Invalid Triblock UV arrangement", 'ERROR'),
            'degenerated_uvs': ("Degenerated UVs (all UVs identical)", 'GROUP_UVS'),
            'out_of_range': ("Vertices outside range box (500 units)", 'BOUNDS'),
        }

        for issue in issues:
            msg, icon = issue_map.get(issue, (f"Unknown: {issue}", 'QUESTION'))
            lines.append(f"• {msg}")

        def draw_popup(self, context):
            layout = self.layout
            for line in lines:
                if line.startswith("-"):
                    layout.separator()
                elif line.startswith("Issues for"):
                    row = layout.row()
                    row.label(text=line, icon='ERROR')
                else:
                    row = layout.row()
                    issue_key = None
                    for key in issue_map:
                        if key in line:
                            issue_key = key
                            break
                    icon = issue_map.get(issue_key, (None, 'INFO'))[1] if issue_key else 'INFO'
                    row.label(text=line, icon=icon)

        context.window_manager.popup_menu(draw_popup, title="Vertex Group Issues", icon='ERROR')
        return {'FINISHED'}


classes = [
    LIST_OT_ToggleMultiSelection,
    LIST_OT_ClearMultiSelection,
    LIST_OT_SelectMultiChecked,
    LIST_OT_CheckAll,
    LIST_OT_ClearChecksInCurrentList,
    LIST_OT_ShowVertexGroupIssues,
]