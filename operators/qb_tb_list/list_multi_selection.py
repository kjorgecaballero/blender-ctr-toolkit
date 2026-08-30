"""
Multi-Selection Operators for Quadblock/Triblock List
"""

import bpy
import bmesh
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty

from ...ui.qb_tb_list.list_helpers import get_block_material_name, get_list_sort_key


def _get_filtered_display_items(context, obj, scene):
    """Return list of dicts with visible items in current list."""
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

    elif display_type == 'CONSTANT_MATERIALS':
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            block_type = mat.get("ctr_block_type")
            if block_type is None:
                continue
            if (block_type == "quadblock" and scene.list_filter_cm_qb) or \
               (block_type == "triblock" and scene.list_filter_cm_tb):
                items.append({
                    'name': mat.name,
                    'material': mat.name,
                    'block_type': block_type,
                    'block_id': mat.get("ctr_block_id", 0),
                    'is_nav_point': mat.get("ctr_is_navigation_point", False),
                })

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

    mat_filter = scene.list_material_filter_vg if display_type == 'VERTEX_GROUPS' else scene.list_material_filter_cm
    if mat_filter:
        items = [it for it in items if it['material'] == mat_filter]

    search = scene.list_search_text.lower()
    if search:
        filtered = []
        for it in items:
            if (search in it['name'].lower() or
                search in str(it['block_id']) or
                search in it['block_type'].lower()):
                filtered.append(it)
                continue
            if display_type == 'VERTEX_GROUPS' and it.get('material'):
                if search in it['material'].lower():
                    filtered.append(it)
                    continue
        items = filtered

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
                has_block = ('quadblock' in item_issues or 'triblock' in item_issues)
                if has_block and len(real_issues) == 0:
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
            elif issue_filter == 'MULTIPLE_MATERIALS':
                if 'multiple_materials' in item_issues:
                    filtered.append(it)
            elif issue_filter == 'MISSING_UVS':
                if 'missing_uvs' in item_issues:
                    filtered.append(it)
        items = filtered

    return items


class LIST_OT_ToggleMultiSelection(Operator):
    bl_idname = "list.toggle_multi_selection"
    bl_label = "Toggle Multi Selection"
    bl_description = "Toggle selection of this item (automatically updates 3D view)"
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
            if not item_name.startswith(("QB_", "TB_")):
                return

            quad_map = obj.get("quadblock_faces_map", {})
            tri_map = obj.get("triblock_faces_map", {})

            block_id = None
            face_map = None
            if item_name.startswith("QB_"):
                try:
                    block_id = int(item_name[3:])
                    face_map = quad_map.get(str(block_id), [])
                except ValueError:
                    return
            elif item_name.startswith("TB_"):
                try:
                    block_id = int(item_name[3:])
                    face_map = tri_map.get(str(block_id), [])
                except ValueError:
                    return

            if not face_map:
                self.report({'WARNING'}, f"No face map found for {item_name}. Run 'Navigate' for accurate selection.")
                if item_name in obj.vertex_groups:
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
                                if all(v.select for v in face.verts):
                                    face.select = True
                            else:
                                if all(v.index in vertex_indices for v in face.verts):
                                    face.select = False
                        bmesh.update_edit_mesh(obj.data)
                    finally:
                        if original_mode == 'OBJECT':
                            bpy.ops.object.mode_set(mode='OBJECT')
                return

            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            for f_idx in face_map:
                if f_idx < len(bm.faces):
                    bm.faces[f_idx].select = select_state
            bmesh.update_edit_mesh(obj.data)

        elif display_type == 'CONSTANT_MATERIALS':
            mat = bpy.data.materials.get(item_name)
            if mat and mat.get("ctr_block_type") is not None:
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
                        faces_with_mat = [i for i, p in enumerate(obj.data.polygons) if p.material_index == material_index]
                        bpy.ops.object.mode_set(mode='EDIT')
                        bm = bmesh.from_edit_mesh(obj.data)
                        bm.faces.ensure_lookup_table()
                        for face_idx in faces_with_mat:
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
    bl_description = "Select all checked items in the 3D view"
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

            if self.clear_existing:
                bpy.ops.mesh.select_all(action='DESELECT')

            quad_map = obj.get("quadblock_faces_map", {})
            tri_map = obj.get("triblock_faces_map", {})

            has_maps = False
            for vg_name in target_vg_names:
                if vg_name.startswith("QB_"):
                    block_id = int(vg_name[3:])
                    if quad_map.get(str(block_id)):
                        has_maps = True
                        break
                elif vg_name.startswith("TB_"):
                    block_id = int(vg_name[3:])
                    if tri_map.get(str(block_id)):
                        has_maps = True
                        break

            if not has_maps:
                self.report(
                    {'WARNING'},
                    "Block face maps not found. Please run 'Find All Blocks' (Navigate) first to enable accurate selection."
                )
                return {'CANCELLED'}

            face_indices_to_select = set()
            for vg_name in target_vg_names:
                if vg_name.startswith("QB_"):
                    try:
                        block_id = int(vg_name[3:])
                        faces = quad_map.get(str(block_id), [])
                        face_indices_to_select.update(faces)
                    except ValueError:
                        continue
                elif vg_name.startswith("TB_"):
                    try:
                        block_id = int(vg_name[3:])
                        faces = tri_map.get(str(block_id), [])
                        face_indices_to_select.update(faces)
                    except ValueError:
                        continue

            if not face_indices_to_select:
                self.report({'WARNING'}, "No faces found for selected blocks in face maps.")
                return {'CANCELLED'}

            bm = bmesh.from_edit_mesh(obj.data)
            bm.faces.ensure_lookup_table()
            selected_count = 0
            for f_idx in face_indices_to_select:
                if f_idx < len(bm.faces):
                    bm.faces[f_idx].select = True
                    selected_count += 1
            bmesh.update_edit_mesh(obj.data)

            self.report({'INFO'}, f"Selected {selected_count} faces from {len(target_vg_names)} blocks using face maps.")
            return {'FINISHED'}

        elif display_type == 'CONSTANT_MATERIALS':
            target_mats = []
            if self.select_all:
                for slot in obj.material_slots:
                    mat = slot.material
                    if mat and mat.get("ctr_block_type") is not None:
                        bt = mat.get("ctr_block_type")
                        if (bt == "quadblock" and scene.list_filter_cm_qb) or \
                           (bt == "triblock" and scene.list_filter_cm_tb):
                            target_mats.append(mat.name)
            else:
                if "multi_selected_items" not in obj or not obj["multi_selected_items"]:
                    self.report({'WARNING'}, "No items checked.")
                    return {'CANCELLED'}
                multi = dict(obj["multi_selected_items"])
                for name in multi.keys():
                    mat = bpy.data.materials.get(name)
                    if mat and mat.get("ctr_block_type") is not None:
                        target_mats.append(name)

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
    bl_description = "Check all items in the current list (applies filters and search)"
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

        bpy.ops.list.select_multi_checked(select_all=False, clear_existing=True)
        return {'FINISHED'}


class LIST_OT_ClearChecksInCurrentList(Operator):
    bl_idname = "list.clear_checks_in_current_list"
    bl_label = "Clear Checks in Current List"
    bl_description = "Clear checks only for items in the current filtered list"
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
    bl_idname = "list.show_vertex_group_issues"
    bl_label = "Vertex Group Issues"
    bl_description = "Show detailed issues for this vertex group"
    bl_options = {'REGISTER'}

    group_name: StringProperty(name="Group Name")

    def execute(self, context):
        obj = context.edit_object
        if not obj or "vertex_group_issues" not in obj:
            self.report({'WARNING'}, "No issue data found.")
            return {'CANCELLED'}

        issues_dict = dict(obj["vertex_group_issues"])
        issues = issues_dict.get(self.group_name, [])

        if not issues:
            self.report({'INFO'}, f"No issues for vertex group '{self.group_name}'.")
            return {'FINISHED'}

        lines = [f"Issues for vertex group: {self.group_name}", "-" * 30]
        issue_map = {
            'quadblock': ("Valid Quadblock", 'INFO'),
            'triblock': ("Valid Triblock", 'INFO'),
            'invalid_geometry': ("Invalid Geometry", 'ERROR'),
            'invalid_uvs': ("UVs outside 0-1 range", 'UV'),
            'invalid_triblock_uvs': ("Invalid Triblock UV arrangement", 'ERROR'),
            'degenerated_uvs': ("Degenerated UVs (all UVs identical)", 'GROUP_UVS'),
            'out_of_range': ("Vertices outside range box (500 units)", 'BOUNDS'),
            'multiple_materials': ("Multiple materials on block faces", 'MATERIAL'),
            'missing_uvs': ("Missing UV map", 'UV'),
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