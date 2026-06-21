"""
QB/TB Constant Material Operators
Assign constant names to blocks via material duplication.
Stores metadata on the material itself.
"""

import bpy
import bmesh
import time
import random

from ...utils.qb_tb_navigator import get_faces_by_material_name
from ...utils.material_utils import is_constant_id_unique
from ...utils.qb_tb_navigator.qb_tb_navigation_utils import detect_block_from_selection


class LIST_OT_AssignConstantMaterial(bpy.types.Operator):
    bl_idname = "list.assign_constant_material"
    bl_label = "Assign/Set Constant Name"
    bl_description = "Assign a constant name to the selected block(s). Single or multi-assign."
    bl_options = {'REGISTER', 'UNDO'}

    base_name: bpy.props.StringProperty(name="Base Material", default="")
    id_value: bpy.props.StringProperty(name="ID Value", default="")
    multi_assign: bpy.props.BoolProperty(name="Multi-Assign", default=False)
    base_id: bpy.props.StringProperty(name="Base ID", default="")
    _multi_mat_count = 0

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None and context.mode == 'EDIT_MESH')

    def invoke(self, context, event):
        obj = context.edit_object
        original_mode = context.mode
        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            mesh = obj.data
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            bm.faces.ensure_lookup_table()

            selected_faces_bm = [f for f in bm.faces if f.select]
            selected_verts_bm = [v for v in bm.verts if v.select]

            if not selected_faces_bm and not selected_verts_bm:
                self.report({'WARNING'}, "No quadblock/triblock selected.")
                bm.free()
                return {'CANCELLED'}

            if not ("face_to_quadblock" in obj and "face_to_triblock" in obj):
                self.report({'WARNING'}, "Run 'Find All Blocks' first.")
                bm.free()
                return {'CANCELLED'}

            face_to_quadblock = obj["face_to_quadblock"]
            face_to_triblock = obj["face_to_triblock"]
            quadblock_faces_map = obj.get("quadblock_faces_map", {})
            triblock_faces_map = obj.get("triblock_faces_map", {})

            found_blocks = set()
            for face in selected_faces_bm:
                face_index = str(face.index)
                if face_index in face_to_quadblock:
                    found_blocks.add(("quadblock", int(face_to_quadblock[face_index])))
                elif face_index in face_to_triblock:
                    found_blocks.add(("triblock", int(face_to_triblock[face_index])))

            for vert in selected_verts_bm:
                if "quadblock_centers" in obj and vert.index in obj["quadblock_centers"]:
                    found_blocks.add(("quadblock", vert.index))

            if not found_blocks:
                self.report({'WARNING'}, "Selection contains no valid quadblock/triblock.")
                bm.free()
                return {'CANCELLED'}

            self.blocks_to_assign = list(found_blocks)

            # Check if any selected block already has a constant material
            for block_type, block_id in self.blocks_to_assign:
                if block_type == "quadblock":
                    face_indices = quadblock_faces_map.get(str(block_id), [])
                else:
                    face_indices = triblock_faces_map.get(str(block_id), [])
                for fidx in face_indices:
                    if fidx < len(mesh.polygons):
                        mat_idx = mesh.polygons[fidx].material_index
                        if mat_idx < len(obj.material_slots):
                            mat = obj.material_slots[mat_idx].material
                            if mat and mat.get("ctr_block_type") is not None:
                                self.report({'WARNING'}, "Some selected blocks already have constants. Clear them first.")
                                bm.free()
                                return {'CANCELLED'}

            # Get first block's material for the dialog
            first_block_type, first_block_id = self.blocks_to_assign[0]
            if first_block_type == "quadblock":
                face_indices = quadblock_faces_map.get(str(first_block_id), [])
            else:
                face_indices = triblock_faces_map.get(str(first_block_id), [])
            if face_indices:
                first_face_idx = face_indices[0]
                if first_face_idx >= len(mesh.polygons):
                    self.report({'ERROR'}, "Invalid face index.")
                    bm.free()
                    return {'CANCELLED'}
                mat_idx = mesh.polygons[first_face_idx].material_index
                if mat_idx >= len(obj.material_slots) or not obj.material_slots[mat_idx].material:
                    self.report({'ERROR'}, "Selected block has no material.")
                    bm.free()
                    return {'CANCELLED'}
                self.base_name = obj.material_slots[mat_idx].material.name
                self.id_value = str(first_block_id)

            # Count blocks with multiple materials (warning only)
            multi_mat_count = 0
            for block_type, block_id in self.blocks_to_assign:
                if block_type == "quadblock":
                    face_indices = quadblock_faces_map.get(str(block_id), [])
                else:
                    face_indices = triblock_faces_map.get(str(block_id), [])
                unique_mats = set()
                for fidx in face_indices:
                    if fidx < len(mesh.polygons):
                        mat_idx = mesh.polygons[fidx].material_index
                        if mat_idx < len(obj.material_slots):
                            mat = obj.material_slots[mat_idx].material
                            if mat:
                                unique_mats.add(mat.name)
                if len(unique_mats) > 1:
                    multi_mat_count += 1
            self._multi_mat_count = multi_mat_count

            bm.free()

        except Exception as e:
            self.report({'ERROR'}, f"Error preparing dialog: {str(e)}")
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Base material: {self.base_name}")
        if self._multi_mat_count > 0:
            box = layout.box()
            box.alert = True
            box.label(text=f"Warning: {self._multi_mat_count} selected block(s) have multiple materials.", icon='ERROR')
        layout.prop(self, "multi_assign", text="Multi-Assign (selected blocks)")
        if self.multi_assign:
            layout.prop(self, "base_id", text="Base ID")
            layout.label(text="Final names: <Base>_ID<BaseID><unique suffix>")
            if len(self.blocks_to_assign) > 50:
                box = layout.box()
                box.alert = True
                box.label(text=f"Assigning {len(self.blocks_to_assign)} blocks. May be slow.", icon='ERROR')
        else:
            row = layout.row(align=True)
            row.label(text="ID:")
            row.prop(self, "id_value", text="")

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            mesh = obj.data
            quadblock_faces_map = obj.get("quadblock_faces_map", {})
            triblock_faces_map = obj.get("triblock_faces_map", {})

            if not self.multi_assign:
                if not self.id_value.strip():
                    self.report({'ERROR'}, "ID cannot be empty.")
                    return {'CANCELLED'}
                if len(self.blocks_to_assign) > 1:
                    self.report({'WARNING'}, "Single assign supports only 1 block. Enable Multi-Assign.")
                    return {'CANCELLED'}
                base_id = self.id_value.strip()
            else:
                if not self.base_id.strip():
                    self.report({'ERROR'}, "Base ID cannot be empty.")
                    return {'CANCELLED'}
                base_id = self.base_id.strip()
                # Verify all blocks share same base material
                block_materials = {}
                for block_type, block_id in self.blocks_to_assign:
                    if block_type == "quadblock":
                        face_indices = quadblock_faces_map.get(str(block_id), [])
                    else:
                        face_indices = triblock_faces_map.get(str(block_id), [])
                    if face_indices:
                        first_face_idx = face_indices[0]
                        if first_face_idx < len(mesh.polygons):
                            mat_idx = mesh.polygons[first_face_idx].material_index
                            if mat_idx < len(obj.material_slots):
                                mat = obj.material_slots[mat_idx].material
                                if mat:
                                    block_materials[(block_type, block_id)] = mat.name
                unique_mats = set(block_materials.values())
                if len(unique_mats) > 1:
                    self.report({'WARNING'}, "Multi-assign requires same material for all blocks. Found multiple.")
                    return {'CANCELLED'}

            processed = 0
            errors = 0
            quad_processed = 0
            tri_processed = 0

            for block_type, block_id in self.blocks_to_assign:
                face_indices = []
                if block_type == "quadblock":
                    face_indices = quadblock_faces_map.get(str(block_id), [])
                else:
                    face_indices = triblock_faces_map.get(str(block_id), [])

                if not face_indices:
                    errors += 1
                    continue

                # Check if already constant
                already_constant = False
                for fidx in face_indices:
                    if fidx < len(mesh.polygons):
                        mat_idx = mesh.polygons[fidx].material_index
                        if mat_idx < len(obj.material_slots):
                            mat = obj.material_slots[mat_idx].material
                            if mat and mat.get("ctr_block_type") is not None:
                                already_constant = True
                                break
                if already_constant:
                    self.report({'WARNING'}, f"Skipping {block_type} {block_id}: already constant.")
                    errors += 1
                    continue

                # Generate new name
                if self.multi_assign:
                    suffix = random.randint(1000, 9999)
                    final_name = f"{self.base_name}_ID{base_id}{suffix}"
                    attempts = 0
                    while final_name in bpy.data.materials and attempts < 10:
                        suffix = random.randint(1000, 9999)
                        final_name = f"{self.base_name}_ID{base_id}{suffix}"
                        attempts += 1
                    if final_name in bpy.data.materials:
                        self.report({'ERROR'}, f"Unique name failed for {block_type} {block_id}.")
                        errors += 1
                        continue
                else:
                    final_name = f"{self.base_name}_ID{base_id}"
                    if not is_constant_id_unique(obj, base_id):
                        self.report({'ERROR'}, f"ID '{base_id}' already used on this object.")
                        return {'CANCELLED'}
                    if final_name in bpy.data.materials:
                        self.report({'ERROR'}, f"Material '{final_name}' already exists.")
                        return {'CANCELLED'}

                base_mat = bpy.data.materials.get(self.base_name)
                if not base_mat:
                    self.report({'ERROR'}, f"Base material '{self.base_name}' not found.")
                    return {'CANCELLED'}

                # Create constant material
                new_mat = base_mat.copy()
                new_mat.name = final_name
                # Store metadata on the material
                new_mat["ctr_block_type"] = block_type
                new_mat["ctr_block_id"] = block_id
                new_mat["ctr_original_material"] = self.base_name
                new_mat["ctr_is_navigation_point"] = False

                if final_name not in obj.data.materials:
                    obj.data.materials.append(new_mat)

                new_mat_index = obj.data.materials.find(final_name)

                for fidx in face_indices:
                    if fidx < len(mesh.polygons):
                        mesh.polygons[fidx].material_index = new_mat_index

                processed += 1
                if block_type == "quadblock":
                    quad_processed += 1
                else:
                    tri_processed += 1

            mesh.update()

            try:
                bpy.ops.object.material_slot_remove_unused()
            except Exception:
                pass

            if processed > 0:
                parts = []
                if quad_processed > 0:
                    parts.append(f"{quad_processed} quadblock{'s' if quad_processed != 1 else ''}")
                if tri_processed > 0:
                    parts.append(f"{tri_processed} triblock{'s' if tri_processed != 1 else ''}")
                msg = f"Assigned constant to {' and '.join(parts)}"
                if errors > 0:
                    msg += f" with {errors} error{'s' if errors != 1 else ''}"
                else:
                    msg += " successfully"
                self.report({'INFO'}, msg)
            else:
                self.report({'WARNING'}, "No assignments made.")

        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


class LIST_OT_ClearConstantMaterial(bpy.types.Operator):
    bl_idname = "list.clear_constant_material"
    bl_label = "Clear Constant Name"
    bl_description = "Clear constant name from selected block, all constants, or invalid constants."
    bl_options = {'REGISTER', 'UNDO'}

    clear_mode: bpy.props.EnumProperty(
        name="Clear Mode",
        items=[
            ('SELECTED', "Clear Selected", "Clear checked items AND selected blocks"),
            ('ALL', "Clear All", "Clear all constants from this object"),
            ('INVALID_ONLY', "Clear Invalid Only", "Clear any constant material with invalid face count or geometry"),
        ],
        default='SELECTED'
    )

    @classmethod
    def poll(cls, context):
        return context.edit_object is not None

    def invoke(self, context, event):
        obj = context.edit_object
        has_const = any(slot.material and slot.material.get("ctr_block_type") is not None for slot in obj.material_slots)
        if has_const:
            return context.window_manager.invoke_props_dialog(self, width=350)
        else:
            self.report({'WARNING'}, "No constant materials found.")
            return {'CANCELLED'}

    def draw(self, context):
        layout = self.layout
        obj = context.edit_object
        const_count = sum(1 for slot in obj.material_slots if slot.material and slot.material.get("ctr_block_type") is not None)
        layout.label(text=f"This object has {const_count} constant materials.")
        col = layout.column(align=True)
        col.prop(self, "clear_mode", expand=True)

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            def process_material(mat, obj, fallback_cache, fallback_duplicate=True):
                """Restore original material for a single constant material."""
                # mat is a Material object
                mat_name = mat.name
                face_indices = get_faces_by_material_name(obj, mat_name)
                if not face_indices:
                    return False, "No faces found"

                original_mat_name = mat.get("ctr_original_material", "")
                original_mat = bpy.data.materials.get(original_mat_name) if original_mat_name else None

                if original_mat:
                    if original_mat_name not in obj.data.materials:
                        obj.data.materials.append(original_mat)
                    orig_idx = obj.data.materials.find(original_mat_name)
                    for idx in face_indices:
                        if idx < len(obj.data.polygons):
                            obj.data.polygons[idx].material_index = orig_idx
                    # Remove the constant if it has no users left
                    # But only if it's not used by any other object
                    if mat.users <= 1:
                        bpy.data.materials.remove(mat)
                    return True, "Restored original"
                else:
                    if fallback_duplicate:
                        base_name = mat_name.rsplit('_ID', 1)[0] if '_ID' in mat_name else mat_name
                        if base_name not in fallback_cache:
                            new_mat = mat.copy()
                            new_mat.pop("ctr_block_type", None)
                            new_mat.pop("ctr_block_id", None)
                            new_mat.pop("ctr_original_material", None)
                            new_mat.pop("ctr_is_navigation_point", None)
                            new_mat.name = base_name
                            if new_mat.name not in obj.data.materials:
                                obj.data.materials.append(new_mat)
                            fallback_cache[base_name] = (new_mat.name, obj.data.materials.find(new_mat.name))
                        fb_name, fb_idx = fallback_cache[base_name]
                        for idx in face_indices:
                            if idx < len(obj.data.polygons):
                                obj.data.polygons[idx].material_index = fb_idx
                        if mat.users <= 1:
                            bpy.data.materials.remove(mat)
                        return True, "Fallback created"
                    return False, "No fallback"

            # Determine which materials to clear
            mats_to_clear = []

            if self.clear_mode == 'ALL':
                for slot in obj.material_slots:
                    if slot.material and slot.material.get("ctr_block_type") is not None:
                        mats_to_clear.append(slot.material)

            elif self.clear_mode == 'INVALID_ONLY':
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bm.faces.ensure_lookup_table()
                for slot in obj.material_slots:
                    mat = slot.material
                    if mat and mat.get("ctr_block_type") is not None:
                        face_indices = get_faces_by_material_name(obj, mat.name)
                        if len(face_indices) != 4:
                            mats_to_clear.append(mat)
                        else:
                            bm_faces = [bm.faces[i] for i in face_indices if i < len(bm.faces)]
                            if len(bm_faces) == 4:
                                center, _ = detect_block_from_selection(bm_faces)
                                if center is None:
                                    mats_to_clear.append(mat)
                bm.free()

            else:  # SELECTED
                checked_names = set()
                if "multi_selected_items" in obj:
                    checked_names = set(dict(obj["multi_selected_items"]).keys())

                selected_polys = [p for p in obj.data.polygons if p.select]
                selected_mats = set()
                for poly in selected_polys:
                    mat_idx = poly.material_index
                    if mat_idx < len(obj.material_slots):
                        mat = obj.material_slots[mat_idx].material
                        if mat and mat.get("ctr_block_type") is not None:
                            selected_mats.add(mat)

                for name in checked_names:
                    mat = bpy.data.materials.get(name)
                    if mat and mat.get("ctr_block_type") is not None:
                        selected_mats.add(mat)

                mats_to_clear = list(selected_mats)

            if not mats_to_clear:
                self.report({'WARNING'}, "No materials to clear.")
                return {'CANCELLED'}

            fallback_cache = {}
            cleared = 0
            restored = 0
            failed = []

            for mat in mats_to_clear:
                # mat is a Material object; ensure it still exists
                if mat is None or mat.name not in bpy.data.materials:
                    continue
                success, msg = process_material(mat, obj, fallback_cache, fallback_duplicate=True)
                if success:
                    if "Restored" in msg:
                        restored += 1
                    else:
                        cleared += 1
                else:
                    failed.append(mat.name)

            try:
                bpy.ops.object.material_slot_remove_unused()
            except Exception:
                pass

            if failed:
                self.report({'WARNING'}, f"Failed to clear: {', '.join(failed)}")
            else:
                msg = f"Cleared {cleared+restored} constants (restored {restored})"
                self.report({'INFO'}, msg)

        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


classes = [
    LIST_OT_AssignConstantMaterial,
    LIST_OT_ClearConstantMaterial,
]