"""
Selection Operator for Quadblock/Triblock List
Moved from ui/qb_tb_list/selection_list.py
"""

import bpy
import bmesh
from bpy.types import Operator


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

        # Faces -> qb & tb
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

        # Quadblock centers
        for vert in selected_verts:
            if "quadblock_centers" in obj and vert.index in obj["quadblock_centers"]:
                name = f"QB_{vert.index}"
                if name not in found_block_names:
                    found_blocks.append(('quadblock', vert.index, name))
                    found_block_names.add(name)

        if not found_blocks:
            self.report({'WARNING'}, "No blocks found in selection.")
            return {'CANCELLED'}

        # Check in multi selected items
        if "multi_selected_items" not in obj:
            obj["multi_selected_items"] = {}
        multi = obj["multi_selected_items"]

        for bt, bid, bname in found_blocks:
            if scene.list_display_type == 'VERTEX_GROUPS':
                if bname not in multi:
                    multi[bname] = True
            elif scene.list_display_type == 'CONSTANT_MATERIALS':
                const_prop = f"constant_name_{bt}_{bid}"
                if const_prop in obj:
                    mat_name = obj[const_prop]
                    if mat_name not in multi:
                        multi[mat_name] = True
                else:
                    if bname not in multi:
                        multi[bname] = True

        obj["multi_selected_items"] = multi

        # Sync index list
        self._sync_list_index(context, obj, scene, found_blocks)

        bpy.ops.list.select_multi_checked(select_all=False)
        self.report({'INFO'}, f"Added {len(found_blocks)} blocks to checklist")
        return {'FINISHED'}

    def _sync_list_index(self, context, obj, scene, found_blocks):
        """Adjust the scroll to show the first block found."""
        # Build visible items
        items = []
        if scene.list_display_type == 'VERTEX_GROUPS':
            for vg in obj.vertex_groups:
                if vg.name.startswith("QB_") and scene.list_filter_show_qb:
                    items.append(vg.name)
                elif vg.name.startswith("TB_") and scene.list_filter_show_tb:
                    items.append(vg.name)
        else:
            if "constant_materials" in obj:
                for mat_name, info in obj["constant_materials"].items():
                    bt = info.get("block_type", "")
                    if (bt == "quadblock" and scene.list_filter_cm_qb) or \
                       (bt == "triblock" and scene.list_filter_cm_tb):
                        items.append(mat_name)

        search = scene.list_search_text.lower()
        if search:
            items = [it for it in items if search in it.lower()]


        def sort_key(name):
            is_qb = name.startswith("QB_")
            return (0 if is_qb else 1, name.lower())
        items.sort(key=sort_key)
        if scene.list_sort_name_direction == 'DESC':
            items.reverse()

        if not items:
            return

        target = None
        bt, bid, bname = found_blocks[0]
        if scene.list_display_type == 'VERTEX_GROUPS':
            target = bname
        else:
            const_prop = f"constant_name_{bt}_{bid}"
            if const_prop in obj:
                target = obj[const_prop]
            else:
                target = bname

        if target and target in items:
            idx = items.index(target)
            scene.list_list_index = idx
            per_page = scene.list_items_per_page
            page_start = (idx // per_page) * per_page
            max_scroll = max(0, len(items) - per_page)
            scene.list_vertical_scroll = min(page_start, max_scroll)


classes = [LIST_OT_SelectListFromBlock]