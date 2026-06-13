"""
Selection Operator for Quadblock/Triblock List
"""

import bpy
import bmesh
from bpy.types import Operator

from ..qb_tb_list.list_multi_selection import _get_filtered_display_items

ITEMS_PER_PAGE = 10


def _scroll_to_item(context, obj, scene, target_item_name):
    """Scroll the list to make the specified item visible."""
    if not target_item_name:
        return

    # Get current visible items (respects filters, search, etc.)
    items = _get_filtered_display_items(context, obj, scene)
    if not items:
        return

    # Apply current sort settings (same as in list_panel)
    reverse_type = (scene.list_sort_type_direction == 'DESC')
    reverse_name = (scene.list_sort_name_direction == 'DESC')

    def sort_key(item):
        type_order = 0 if item['block_type'] == 'quadblock' else 1
        if reverse_type:
            type_order = 1 - type_order
        name_key = item['name'].lower()
        return (type_order, name_key)

    items.sort(key=sort_key)
    if reverse_name:
        items.reverse()

    # Find target item index
    target_index = -1
    for idx, it in enumerate(items):
        if it['name'] == target_item_name:
            target_index = idx
            break

    if target_index == -1:
        return

    # Calculate page start
    page_start = (target_index // ITEMS_PER_PAGE) * ITEMS_PER_PAGE
    max_scroll = max(0, len(items) - ITEMS_PER_PAGE)
    new_scroll = min(page_start, max_scroll)

    scene.list_vertical_scroll = new_scroll
    scene.list_list_index = target_index

    # Force UI redraw
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


class LIST_OT_SelectListFromBlock(Operator):
    bl_idname = "list.select_list_from_block"
    bl_label = "Select in List"
    bl_description = "Add selected quadblocks/triblocks to checklist and show all checked blocks in 3D"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def execute(self, context):
        obj = context.edit_object
        scene = context.scene

        if scene.list_display_type == 'CONSTANT_MATERIALS':
            # Constant Materials mode: use material names from selected faces
            if "constant_materials" not in obj:
                self.report({'WARNING'}, "No constant materials found.")
                return {'CANCELLED'}

            const_dict = obj["constant_materials"]
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
                    if mat and mat.name in const_dict:          # only constant materials
                        if mat.name not in added:
                            added.append(mat.name)

            if not added:
                self.report({'WARNING'}, "Selected faces have no constant material.")
                return {'CANCELLED'}

            # Mark in multi_selected_items
            if "multi_selected_items" not in obj:
                obj["multi_selected_items"] = {}
            multi = obj["multi_selected_items"]
            for mat_name in added:
                multi[mat_name] = True
            obj["multi_selected_items"] = multi

            # Scroll to the LAST added item (most recent selection)
            if added:
                _scroll_to_item(context, obj, scene, added[-1])

            # Select the checked items in 3D view
            bpy.ops.list.select_multi_checked(select_all=False)
            self.report({'INFO'}, f"Added {len(added)} constant material(s) to checklist")
            return {'FINISHED'}

        else:
            # VERTEX_GROUPS mode: uses block indices and face maps
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

            # Scroll to the LAST added item (most recent selection)
            if found_blocks:
                last_block_name = found_blocks[-1][2]  # (type, id, name)
                _scroll_to_item(context, obj, scene, last_block_name)

            bpy.ops.list.select_multi_checked(select_all=False)
            self.report({'INFO'}, f"Added {len(found_blocks)} blocks to checklist")
            return {'FINISHED'}


classes = [LIST_OT_SelectListFromBlock]