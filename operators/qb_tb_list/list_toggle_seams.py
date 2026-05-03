import bpy
import bmesh
from bpy.types import Operator


class LIST_OT_ToggleBlockSeams(Operator):
    """Mark/unmark seams on the external edges of all quadblocks and triblocks"""
    bl_idname = "list.toggle_block_seams"
    bl_label = "Toggle Block Seams"
    bl_description = "Mark/unmark seams on block borders (quadblocks/triblocks) for all detected blocks"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.edit_object
        if not obj or obj.type != 'MESH':
            return False
        # Require block face maps (Navigate must have been run)
        return ("quadblock_faces_map" in obj or "triblock_faces_map" in obj) and context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.edit_object
        mesh = obj.data

        # Switch to OBJECT mode to safely edit seams
        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        block_edges = set()

        # Quadblocks
        if "quadblock_faces_map" in obj:
            for faces_idx_list in obj["quadblock_faces_map"].values():
                face_set = set(faces_idx_list)
                for f_idx in face_set:
                    if f_idx >= len(bm.faces):
                        continue
                    face = bm.faces[f_idx]
                    if not face.is_valid:
                        continue
                    for edge in face.edges:
                        shared = 0
                        for linked_face in edge.link_faces:
                            if linked_face.index in face_set:
                                shared += 1
                        if shared == 1:
                            block_edges.add(edge)

        # Triblocks
        if "triblock_faces_map" in obj:
            for faces_idx_list in obj["triblock_faces_map"].values():
                face_set = set(faces_idx_list)
                for f_idx in face_set:
                    if f_idx >= len(bm.faces):
                        continue
                    face = bm.faces[f_idx]
                    if not face.is_valid:
                        continue
                    for edge in face.edges:
                        shared = 0
                        for linked_face in edge.link_faces:
                            if linked_face.index in face_set:
                                shared += 1
                        if shared == 1:
                            block_edges.add(edge)

        if not block_edges:
            self.report({'WARNING'}, "No block edges found. Run 'Navigate' first.")
            bm.free()
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
            return {'CANCELLED'}

        # Toggle seam state (if any edge already has seam, clear; otherwise mark)
        any_seamed = any(edge.seam for edge in block_edges)
        new_state = not any_seamed

        for edge in block_edges:
            edge.seam = new_state

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')

        self.report({'INFO'}, f"Seams {'marked' if new_state else 'cleared'} on {len(block_edges)} edges")
        return {'FINISHED'}


classes = [LIST_OT_ToggleBlockSeams]