"""
Selection Operator for Quadblock/Triblock List
"""

import bpy
import bmesh
from bpy.types import Operator
from .list_multi_selection import _get_filtered_display_items
from ...ui.qb_tb_list.list_helpers import get_list_sort_key

ITEMS_PER_PAGE = 10

def _scroll_to_item(context, obj, scene, target_item_name):
    """Scroll the list to make the specified item visible."""
    if not target_item_name:
        return
    items = _get_filtered_display_items(context, obj, scene)
    if not items:
        return

    items.sort(key=lambda item: get_list_sort_key(item, scene))
    if scene.list_sort_name_direction == 'DESC':
        items.reverse()

    target_index = -1
    for idx, it in enumerate(items):
        if it['name'] == target_item_name:
            target_index = idx
            break

    if target_index == -1:
        return

    page_start = (target_index // ITEMS_PER_PAGE) * ITEMS_PER_PAGE
    max_scroll = max(0, len(items) - ITEMS_PER_PAGE)
    new_scroll = min(page_start, max_scroll)

    scene.list_vertical_scroll = new_scroll
    scene.list_list_index = target_index

    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def _select_from_face_maps(obj, target_names):
    """Helper to select faces using face maps."""
    quad_map = obj.get("quadblock_faces_map", {})
    tri_map = obj.get("triblock_faces_map", {})
    face_indices = set()
    for name in target_names:
        if name.startswith("QB_"):
            try:
                block_id = int(name[3:])
                faces = quad_map.get(str(block_id), [])
                face_indices.update(faces)
            except ValueError:
                continue
        elif name.startswith("TB_"):
            try:
                block_id = int(name[3:])
                faces = tri_map.get(str(block_id), [])
                face_indices.update(faces)
            except ValueError:
                continue
    if face_indices:
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        for f_idx in face_indices:
            if f_idx < len(bm.faces):
                bm.faces[f_idx].select = True
        bmesh.update_edit_mesh(obj.data)
        return len(face_indices)
    return 0


class LIST_OT_SelectListFromBlock(Operator):
    bl_idname = "list.select_list_from_block"
    bl_label = "Select in List"
    bl_description = "Add selected quadblocks/triblocks to checklist and show all checked blocks in 3D"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None and context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.edit_object
        scene = context.scene

        if scene.list_display_type == 'CONSTANT_MATERIALS':
            bm = bmesh.from_edit_mesh(obj.data)
            selected_faces = [f for f in bm.faces if f.select]
            if not selected_faces:
                self.report({'WARNING'}, "No faces selected.")
                return {'CANCELLED'}

            added = []
            for face in selected_faces:
                mat_idx = face.material_index
                if mat_idx < len(obj.material_slots):
                    mat = obj.material_slots[mat_idx].material
                    if mat and mat.get("ctr_block_type") is not None:
                        if mat.name not in added:
                            added.append(mat.name)

            if not added:
                self.report({'WARNING'}, "Selected faces have no constant material.")
                return {'CANCELLED'}

            if "multi_selected_items" not in obj:
                obj["multi_selected_items"] = {}
            multi = obj["multi_selected_items"]
            for mat_name in added:
                multi[mat_name] = True
            obj["multi_selected_items"] = multi

            if added:
                _scroll_to_item(context, obj, scene, added[-1])

            bpy.ops.list.select_multi_checked(select_all=False)
            self.report({'INFO'}, f"Added {len(added)} constant material(s) to checklist")
            return {'FINISHED'}

        else:
            if "face_to_quadblock" not in obj and "face_to_triblock" not in obj:
                self.report({'WARNING'}, "No block data found. Run 'Find All Blocks' first.")
                return {'CANCELLED'}

            bm = bmesh.from_edit_mesh(obj.data)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            selected_faces = [f for f in bm.faces if f.select]
            selected_verts = [v for v in bm.verts if v.select]

            found_blocks = []
            found_block_names = set()

            face_to_quad = obj.get("face_to_quadblock", {})
            face_to_tri = obj.get("face_to_triblock", {})

            for face in selected_faces:
                idx = str(face.index)
                if idx in face_to_quad:
                    bid = int(face_to_quad[idx])
                    name = f"QB_{bid}"
                    if name not in found_block_names:
                        found_blocks.append(('quadblock', bid, name))
                        found_block_names.add(name)
                elif idx in face_to_tri:
                    bid = int(face_to_tri[idx])
                    name = f"TB_{bid}"
                    if name not in found_block_names:
                        found_blocks.append(('triblock', bid, name))
                        found_block_names.add(name)

            for vert in selected_verts:
                if "quadblock_centers" in obj and vert.index in obj["quadblock_centers"]:
                    name = f"QB_{vert.index}"
                    if name not in found_block_names:
                        found_blocks.append(('quadblock', vert.index, name))
                        found_block_names.add(name)

            if not found_blocks:
                self.report({'WARNING'}, "No blocks found in selection.")
                return {'CANCELLED'}

            if "multi_selected_items" not in obj:
                obj["multi_selected_items"] = {}
            multi = obj["multi_selected_items"]

            for bt, bid, bname in found_blocks:
                if scene.list_display_type == 'VERTEX_GROUPS':
                    if bname not in multi:
                        multi[bname] = True

            obj["multi_selected_items"] = multi

            if found_blocks:
                last_block_name = found_blocks[-1][2]
                _scroll_to_item(context, obj, scene, last_block_name)

            target_names = [bname for _, _, bname in found_blocks]
            selected_count = _select_from_face_maps(obj, target_names)
            if selected_count == 0:
                bpy.ops.list.select_multi_checked(select_all=False)
            else:
                self.report({'INFO'}, f"Added {len(found_blocks)} blocks to checklist and selected {selected_count} faces.")
            return {'FINISHED'}


classes = [LIST_OT_SelectListFromBlock]