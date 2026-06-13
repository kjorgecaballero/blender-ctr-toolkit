"""
QB/TB Constant Material Operators
Operators for assigning constant names to blocks via material duplication
Includes navigation point functionality and invalid material cleanup
Reindex‑safe selection and clearing using material names only.
"""

import bpy
import bmesh
import time
import random

from ...utils.qb_tb_navigator import get_faces_by_material_name
from ...utils.qb_tb_navigator.constant_material_utils import clear_all_constant_materials
from ...utils.material_utils import is_constant_id_unique
from ...utils.qb_tb_navigator.qb_tb_navigation_utils import detect_block_from_selection


class LIST_OT_ConfirmDeletePending(bpy.types.Operator):
    """Popup to confirm deletion of constant materials that failed fallback restoration"""
    bl_idname = "list.confirm_delete_pending"
    bl_label = "Delete Constant Materials Without Restoration?"
    bl_options = {'REGISTER', 'INTERNAL'}

    pending_materials: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        obj = context.edit_object
        if not obj or "constant_materials" not in obj:
            return {'CANCELLED'}

        pending_list = self.pending_materials.split(',')
        const_dict = dict(obj["constant_materials"])
        removed = 0

        for mat_name in pending_list:
            if mat_name not in const_dict:
                continue
            block_info = const_dict[mat_name]
            block_type = block_info.get("block_type", "")
            block_id = block_info.get("block_id", 0)

            # Remove from constant_materials dict
            if mat_name in obj["constant_materials"]:
                del obj["constant_materials"][mat_name]
            const_prop_name = f"constant_name_{block_type}_{block_id}"
            if const_prop_name in obj:
                del obj[const_prop_name]

            # Delete material if unused
            if mat_name in bpy.data.materials:
                mat = bpy.data.materials[mat_name]
                if mat.users == 0:
                    bpy.data.materials.remove(mat)
            removed += 1

        try:
            bpy.ops.object.material_slot_remove_unused()
        except Exception:
            pass

        self.report({'INFO'}, f"Deleted {removed} constant materials without restoration.")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        pending = self.pending_materials.split(',')
        layout.label(text="Could not create fallback materials for:", icon='ERROR')
        for name in pending[:5]:
            layout.label(text=f"  - {name}")
        if len(pending) > 5:
            layout.label(text=f"  ... and {len(pending) - 5} more")
        layout.separator()
        layout.label(text="Delete these constant materials without restoring any material?")
        layout.label(text="Affected faces will keep the constant material (may appear pink).")


class LIST_OT_AssignConstantMaterial(bpy.types.Operator):
    """Assign a constant name to the selected block(s) by duplicating its material.
    Supports single block (with custom ID) or multiple blocks (with Base ID + unique suffix).
    Multi-assign only allowed if all selected blocks share the same base material.
    """
    bl_idname = "list.assign_constant_material"
    bl_label = "Assign/Set Constant Name"
    bl_description = "Assign a constant name to the selected block(s). Single or multi-assign."
    bl_options = {'REGISTER', 'UNDO'}

    base_name: bpy.props.StringProperty(
        name="Base Material",
        description="Fixed base material name (non-editable)",
        default=""
    )

    id_value: bpy.props.StringProperty(
        name="ID Value",
        description="Custom value after 'ID' (single assign mode)",
        default=""
    )

    multi_assign: bpy.props.BoolProperty(
        name="Multi-Assign",
        description="Assign constant materials to all selected blocks at once",
        default=False
    )
    base_id: bpy.props.StringProperty(
        name="Base ID",
        description="Base identifier used for all selected blocks (will be combined with a unique suffix)",
        default=""
    )

    # Internal property to store multi-material block count for warning
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

            # Collect all unique blocks in the selection
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

            # Pre‑validation: check for existing constant materials
            const_dict = obj.get("constant_materials", {})
            blocks_with_const = []
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
                            if mat and mat.name in const_dict:
                                blocks_with_const.append((block_type, block_id))
                                break
            if blocks_with_const:
                self.report({'WARNING'}, "Some selected blocks already have constant materials. Clear them first.")
                bm.free()
                return {'CANCELLED'}

            # For single assign, we need the first block's material for the dialog
            first_block_type, first_block_id = self.blocks_to_assign[0]
            if first_block_type == "quadblock":
                face_indices = quadblock_faces_map.get(str(first_block_id), [])
            else:
                face_indices = triblock_faces_map.get(str(first_block_id), [])
            if face_indices:
                first_face_idx = face_indices[0]
                mat_idx = mesh.polygons[first_face_idx].material_index
                current_material = obj.material_slots[mat_idx].material
                self.base_name = current_material.name
                self.id_value = str(first_block_id)

            # Check for multiple materials in the selected blocks (just count for warning)
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
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Base material: {self.base_name}")

        # Show warning if any selected block has multiple materials
        if self._multi_mat_count > 0:
            box = layout.box()
            box.alert = True
            box.label(text=f"Warning: {self._multi_mat_count} selected block(s) have multiple materials.", icon='ERROR')
            box.label(text="Assigning a constant material will replace all textures on those blocks.")

        layout.prop(self, "multi_assign", text="Multi-Assign (selected blocks)")

        if self.multi_assign:
            row = layout.row()
            row.prop(self, "base_id", text="Base ID")
            layout.label(text="Final names: <Base>_ID<BaseID><unique suffix>")
            layout.label(text="Example: tree_tex_IDtreemax -> tree_tex_IDtreemax5021", icon='INFO')
            if len(self.blocks_to_assign) > 50:
                box = layout.box()
                box.alert = True
                box.label(text=f"Assigning {len(self.blocks_to_assign)} blocks. May be slow.", icon='ERROR')
        else:
            row = layout.row(align=True)
            row.label(text="ID:")
            row.prop(self, "id_value", text="")
            layout.label(text=f"Final name: {self.base_name}_ID{self.id_value}")

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            mesh = obj.data
            const_dict = obj.get("constant_materials", {})
            quadblock_faces_map = obj.get("quadblock_faces_map", {})
            triblock_faces_map = obj.get("triblock_faces_map", {})

            # SINGLE ASSIGN: only allow exactly one block
            if not self.multi_assign:
                if not self.id_value.strip():
                    self.report({'ERROR'}, "ID cannot be empty.")
                    return {'CANCELLED'}
                if len(self.blocks_to_assign) > 1:
                    self.report({'WARNING'}, f"Single assign supports only 1 quadblock/triblock (found {len(self.blocks_to_assign)}). Enable Multi-Assign.")
                    return {'CANCELLED'}
                base_id = self.id_value.strip()

            # MULTI ASSIGN: validate all blocks share the same base material
            else:
                if not self.base_id.strip():
                    self.report({'ERROR'}, "Base ID cannot be empty.")
                    return {'CANCELLED'}
                base_id = self.base_id.strip()

                # Collect current material for each block
                block_materials = {}
                for block_type, block_id in self.blocks_to_assign:
                    if block_type == "quadblock":
                        face_indices = quadblock_faces_map.get(str(block_id), [])
                    else:
                        face_indices = triblock_faces_map.get(str(block_id), [])
                    if not face_indices:
                        continue
                    first_face_idx = face_indices[0]
                    if first_face_idx >= len(mesh.polygons):
                        continue
                    mat_idx = mesh.polygons[first_face_idx].material_index
                    if mat_idx < len(obj.material_slots):
                        mat = obj.material_slots[mat_idx].material
                        if mat:
                            block_materials[(block_type, block_id)] = mat.name
                unique_materials = set(block_materials.values())
                if len(unique_materials) > 1:
                    self.report({'WARNING'}, f"Multi-assign requires same material for all selected quadblocks/triblocks. Found {len(unique_materials)} different materials. Cancelled.")
                    return {'CANCELLED'}
                # All good

            # Process blocks
            processed = 0
            errors = 0
            quad_processed = 0
            tri_processed = 0

            for block_type, block_id in self.blocks_to_assign:
                # Get faces of the current block
                face_indices = []
                if block_type == "quadblock":
                    if str(block_id) in quadblock_faces_map:
                        face_indices = quadblock_faces_map[str(block_id)]
                else:
                    if str(block_id) in triblock_faces_map:
                        face_indices = triblock_faces_map[str(block_id)]

                if not face_indices:
                    self.report({'WARNING'}, f"Skipping {block_type} {block_id}: no faces.")
                    errors += 1
                    continue

                # Double-check constant material presence
                already_has = False
                for idx in face_indices:
                    if idx < len(mesh.polygons):
                        poly = mesh.polygons[idx]
                        if poly.material_index < len(obj.material_slots):
                            mat = obj.material_slots[poly.material_index].material
                            if mat and mat.name in const_dict:
                                already_has = True
                                break
                if already_has:
                    self.report({'WARNING'}, f"Skipping {block_type} {block_id}: already constant.")
                    errors += 1
                    continue

                # Verify material match
                first_face_idx = face_indices[0]
                if first_face_idx < len(mesh.polygons):
                    mat_idx = mesh.polygons[first_face_idx].material_index
                    if mat_idx < len(obj.material_slots):
                        current_mat = obj.material_slots[mat_idx].material
                        if not current_mat or current_mat.name != self.base_name:
                            self.report({'WARNING'}, f"Skipping {block_type} {block_id}: material mismatch (expected '{self.base_name}').")
                            errors += 1
                            continue

                # Generate final name
                if self.multi_assign:
                    suffix = random.randint(1000, 9999)
                    final_name = f"{self.base_name}_ID{base_id}{suffix}"
                    attempts = 0
                    while (final_name in bpy.data.materials or final_name in const_dict) and attempts < 10:
                        suffix = random.randint(1000, 9999)
                        final_name = f"{self.base_name}_ID{base_id}{suffix}"
                        attempts += 1
                    if final_name in bpy.data.materials or final_name in const_dict:
                        self.report({'ERROR'}, f"Unique name failed for {block_type} {block_id}.")
                        errors += 1
                        continue
                else:
                    final_name = f"{self.base_name}_ID{base_id}"
                    if not is_constant_id_unique(obj, base_id):
                        self.report({'ERROR'}, f"ID '{base_id}' already used.")
                        return {'CANCELLED'}
                    if final_name in bpy.data.materials:
                        self.report({'ERROR'}, f"Material '{final_name}' already exists.")
                        return {'CANCELLED'}

                base_mat = bpy.data.materials.get(self.base_name)
                if not base_mat:
                    self.report({'ERROR'}, f"Base material '{self.base_name}' not found.")
                    return {'CANCELLED'}

                new_material = base_mat.copy()
                new_material.name = final_name

                if final_name not in obj.data.materials:
                    obj.data.materials.append(new_material)

                new_mat_index = obj.data.materials.find(final_name)

                for face_idx in face_indices:
                    if face_idx < len(mesh.polygons):
                        mesh.polygons[face_idx].material_index = new_mat_index

                const_prop_name = f"constant_name_{block_type}_{block_id}"
                obj[const_prop_name] = final_name

                if "constant_materials" not in obj:
                    obj["constant_materials"] = {}
                const_dict = obj["constant_materials"]
                const_dict[final_name] = {
                    "block_type": block_type,
                    "block_id": block_id,
                    "original_material": self.base_name,
                    "assigned_time": time.time(),
                    "is_navigation_point": False
                }
                obj["constant_materials"] = const_dict

                processed += 1
                if block_type == "quadblock":
                    quad_processed += 1
                else:
                    tri_processed += 1

            mesh.update()

            try:
                bpy.ops.object.material_slot_remove_unused()
            except Exception as e:
                self.report({'WARNING'}, f"Could not remove unused slots: {e}")

            if processed > 0:
                # Build natural language message
                parts = []
                if quad_processed > 0:
                    parts.append(f"{quad_processed} quadblock{'s' if quad_processed != 1 else ''}")
                if tri_processed > 0:
                    parts.append(f"{tri_processed} triblock{'s' if tri_processed != 1 else ''}")
                
                if len(parts) == 2:
                    msg = f"Assigned constant to {parts[0]} and {parts[1]}"
                else:
                    msg = f"Assigned constant to {parts[0]}"
                
                if errors > 0:
                    msg += f" with {errors} error{'s' if errors != 1 else ''}"
                else:
                    msg += " successfully"
                
                self.report({'INFO'}, msg)
            else:
                self.report({'WARNING'}, "No quadblocks/triblocks assigned (all skipped).")

        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'CANCELLED'}
        finally:
            if original_mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}


class LIST_OT_ClearConstantMaterial(bpy.types.Operator):
    """Clear constant name from the selected quadblock/triblock, all constant materials, or only invalid constant materials (including non‑navigation)."""
    bl_idname = "list.clear_constant_material"
    bl_label = "Clear Constant Name"
    bl_description = "Clear constant name from selected block, all constants, or invalid constant materials (geometry or face count)"
    bl_options = {'REGISTER', 'UNDO'}

    clear_mode: bpy.props.EnumProperty(
        name="Clear Mode",
        description="What to clear",
        items=[
            ('SELECTED', "Clear Selected", "Clear checked items AND selected blocks"),
            ('ALL', "Clear All", "Clear all constants from this object"),
            ('INVALID_ONLY', "Clear Invalid Only", "Clear any constant material with invalid face count or geometry"),
        ],
        default='SELECTED'
    )

    @classmethod
    def poll(cls, context):
        return (context.edit_object is not None)

    def invoke(self, context, event):
        obj = context.edit_object
        if "constant_materials" in obj and obj["constant_materials"]:
            wm = context.window_manager
            return wm.invoke_props_dialog(self, width=350)
        else:
            self.report({'WARNING'}, "No constant materials found.")
            return {'CANCELLED'}

    def draw(self, context):
        layout = self.layout
        obj = context.edit_object

        if "constant_materials" in obj:
            constant_materials_dict = dict(obj["constant_materials"])
            count = len(constant_materials_dict)
            layout.label(text=f"This object has {count} constant materials.")

            # Radio buttons for clear mode
            col = layout.column(align=True)
            col.prop(self, "clear_mode", expand=True)

            # Brief info box
            box = layout.box()
            if self.clear_mode == 'SELECTED':
                box.label(text="Clears checked items AND selected blocks.", icon='INFO')
                box.label(text="Combines both selections.")
            elif self.clear_mode == 'ALL':
                box.label(text="Removes ALL constant materials.", icon='ERROR')
                box.label(text="Base materials restored automatically (if possible).")
                box.label(text="If fallback fails, you will be asked.")
            else:  # INVALID_ONLY
                # Count invalid constant materials (all, not only navigation points)
                invalid_count = 0
                if "constant_materials" in obj:
                    bm = bmesh.new()
                    bm.from_mesh(obj.data)
                    bm.faces.ensure_lookup_table()
                    const_dict = dict(obj["constant_materials"])
                    for mat_name, info in const_dict.items():
                        face_indices = get_faces_by_material_name(obj, mat_name)
                        if len(face_indices) != 4:
                            invalid_count += 1
                        else:
                            bm_faces = [bm.faces[i] for i in face_indices if i < len(bm.faces)]
                            if len(bm_faces) == 4:
                                center, _ = detect_block_from_selection(bm_faces)
                                if center is None:
                                    invalid_count += 1
                    bm.free()
                box.label(text=f"Found {invalid_count} invalid constant material(s).", icon='INFO')
                box.label(text="Removes any constant material with wrong face count or broken geometry.")

    def purge_orphan_data(self):
        """Remove unused data blocks (materials, images, textures)"""
        # Purge materials with no users
        for mat in list(bpy.data.materials):
            if mat.users == 0:
                bpy.data.materials.remove(mat)
        # Purge images with no users
        for img in list(bpy.data.images):
            if img.users == 0:
                bpy.data.images.remove(img)
        # Purge textures
        for tex in list(bpy.data.textures):
            if tex.users == 0:
                bpy.data.textures.remove(tex)

    def execute(self, context):
        obj = context.edit_object
        original_mode = context.mode

        if original_mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')

        try:
            # Helper function to process a list of material names (same logic for all modes)
            def process_materials(materials_to_clear, obj, fallback_cache):
                cleared = 0
                restored_with_fallback = 0
                failed = []
                pending_delete = []

                for mat_name in materials_to_clear:
                    const_dict = obj.get("constant_materials", {})
                    if mat_name not in const_dict:
                        # Already removed
                        continue

                    block_info = const_dict[mat_name]
                    block_type = block_info.get("block_type", "")
                    block_id = block_info.get("block_id", 0)
                    original_mat_name = block_info.get("original_material", "")
                    original_mat = bpy.data.materials.get(original_mat_name)

                    face_indices = get_faces_by_material_name(obj, mat_name)
                    if not face_indices:
                        # No faces use this material, just remove the constant entry
                        if mat_name in obj["constant_materials"]:
                            del obj["constant_materials"][mat_name]
                        const_prop_name = f"constant_name_{block_type}_{block_id}"
                        if const_prop_name in obj:
                            del obj[const_prop_name]
                        if mat_name in bpy.data.materials and bpy.data.materials[mat_name].users == 0:
                            bpy.data.materials.remove(bpy.data.materials[mat_name])
                        cleared += 1
                        continue

                    # Case 1: original material exists
                    if original_mat:
                        if original_mat_name not in obj.data.materials:
                            obj.data.materials.append(original_mat)
                        orig_idx = obj.data.materials.find(original_mat_name)
                        for idx in face_indices:
                            if idx < len(obj.data.polygons):
                                obj.data.polygons[idx].material_index = orig_idx
                        cleared += 1
                        # Remove constant data
                        if mat_name in obj["constant_materials"]:
                            del obj["constant_materials"][mat_name]
                        const_prop_name = f"constant_name_{block_type}_{block_id}"
                        if const_prop_name in obj:
                            del obj[const_prop_name]
                        if mat_name in bpy.data.materials:
                            mat = bpy.data.materials[mat_name]
                            if mat.users == 0:
                                bpy.data.materials.remove(mat)
                        continue

                    # Case 2: original material missing, try fallback
                    const_mat = bpy.data.materials.get(mat_name)
                    if const_mat:
                        base_name = mat_name.rsplit('_ID', 1)[0] if '_ID' in mat_name else mat_name
                        if base_name in fallback_cache:
                            new_mat_name, new_index = fallback_cache[base_name]
                        else:
                            from ...utils.qb_tb_navigator.constant_material_utils import _create_base_material_from_constant
                            new_mat_name, new_index = _create_base_material_from_constant(obj, mat_name)
                            if new_mat_name:
                                fallback_cache[base_name] = (new_mat_name, new_index)
                            else:
                                # Fallback creation failed -> ask user later
                                pending_delete.append(mat_name)
                                continue

                        if new_mat_name:
                            for idx in face_indices:
                                if idx < len(obj.data.polygons):
                                    obj.data.polygons[idx].material_index = new_index
                            restored_with_fallback += 1
                            # Remove constant data
                            if mat_name in obj["constant_materials"]:
                                del obj["constant_materials"][mat_name]
                            const_prop_name = f"constant_name_{block_type}_{block_id}"
                            if const_prop_name in obj:
                                del obj[const_prop_name]
                            if mat_name in bpy.data.materials:
                                mat = bpy.data.materials[mat_name]
                                if mat.users == 0:
                                    bpy.data.materials.remove(mat)
                    else:
                        # Constant material itself is missing from bpy.data.materials -> just delete entry
                        if mat_name in obj["constant_materials"]:
                            del obj["constant_materials"][mat_name]
                        const_prop_name = f"constant_name_{block_type}_{block_id}"
                        if const_prop_name in obj:
                            del obj[const_prop_name]
                        cleared += 1

                return cleared, restored_with_fallback, failed, pending_delete

            # 1) Clear only invalid constant materials (ALL constant materials, not just navigation points)
            if self.clear_mode == 'INVALID_ONLY':
                if "constant_materials" not in obj:
                    self.report({'WARNING'}, "No constant materials found.")
                    return {'CANCELLED'}

                # Detect invalid constant materials: face count != 4 OR geometry invalid
                invalid_materials = []
                const_dict = dict(obj["constant_materials"])
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                bm.faces.ensure_lookup_table()

                for mat_name, block_info in const_dict.items():
                    # Check face count first (catches duplicated materials on multiple blocks)
                    face_indices = get_faces_by_material_name(obj, mat_name)
                    if len(face_indices) != 4:
                        invalid_materials.append(mat_name)
                        continue
                    # Even with 4 faces, verify they form a valid qb/tb center
                    bm_faces = [bm.faces[i] for i in face_indices if i < len(bm.faces)]
                    if len(bm_faces) == 4:
                        center, _ = detect_block_from_selection(bm_faces)
                        if center is None:
                            invalid_materials.append(mat_name)
                bm.free()

                if not invalid_materials:
                    self.report({'INFO'}, "No invalid constant materials found.")
                    return {'FINISHED'}

                # Store before state to know what was cleared
                before_const = set(obj["constant_materials"].keys())

                fallback_cache = {}
                cleared, restored, failed, pending = process_materials(invalid_materials, obj, fallback_cache)

                # Determine which materials were actually cleared
                after_const = set(obj["constant_materials"].keys())
                cleared_names = [m for m in invalid_materials if m in before_const and m not in after_const]

                if pending:
                    pending_str = ','.join(pending)
                    bpy.ops.list.confirm_delete_pending('INVOKE_DEFAULT', pending_materials=pending_str)

                try:
                    bpy.ops.object.material_slot_remove_unused()
                except Exception:
                    pass
                self.purge_orphan_data()

                # Print full list to console for debugging
                if cleared_names:
                    print(f"Cleared invalid constant materials: {', '.join(cleared_names)}")
                    # message
                    msg = f"Cleared {len(cleared_names)} invalid constant material(s): {', '.join(cleared_names[:5])}"
                    if len(cleared_names) > 5:
                        msg += f" and {len(cleared_names)-5} more"
                    if restored > 0:
                        msg += f" (restored {restored} via fallback)"
                    if pending:
                        msg += f" | {len(pending)} require confirmation"
                    self.report({'INFO'}, msg)
                else:
                    self.report({'INFO'}, f"Processed invalid materials. Restored: {restored}, pending: {len(pending)}")

                if failed:
                    self.report({'WARNING'}, f"Failed to clear: {', '.join(failed)}")
                return {'FINISHED'}

            # 2) Clear all constant materials
            elif self.clear_mode == 'ALL':
                if "constant_materials" not in obj:
                    self.report({'WARNING'}, "No constant materials found.")
                    return {'CANCELLED'}

                all_materials = list(obj["constant_materials"].keys())
                if not all_materials:
                    self.report({'INFO'}, "No constant materials to clear.")
                    return {'FINISHED'}

                fallback_cache = {}
                cleared, restored, failed, pending = process_materials(all_materials, obj, fallback_cache)

                if pending:
                    pending_str = ','.join(pending)
                    bpy.ops.list.confirm_delete_pending('INVOKE_DEFAULT', pending_materials=pending_str)

                try:
                    bpy.ops.object.material_slot_remove_unused()
                except Exception:
                    pass
                self.purge_orphan_data()
                # Also clear multi_selected_items
                if "multi_selected_items" in obj:
                    obj["multi_selected_items"].clear()

                msg = f"Cleared all constants. Restored {cleared} original, {restored} fallback."
                if pending:
                    msg += f" {len(pending)} require confirmation."
                if failed:
                    msg += f" Failed: {', '.join(failed)}"
                self.report({'INFO'}, msg)
                return {'FINISHED'}

            # 3) Clear selected: combine checked items AND 3D selection
            else:  # SELECTED
                const_dict = obj.get("constant_materials", {})
                if not const_dict:
                    self.report({'WARNING'}, "No constant materials.")
                    return {'CANCELLED'}

                mats_to_clear = set()

                # Add checked items from the list
                if "multi_selected_items" in obj and obj["multi_selected_items"]:
                    multi = dict(obj["multi_selected_items"])
                    for mat_name in multi.keys():
                        if mat_name in const_dict:
                            mats_to_clear.add(mat_name)
                    if mats_to_clear:
                        self.report({'INFO'}, f"Adding {len(mats_to_clear)} checked material(s) from list.")

                # Add selected blocks from 3D view
                selected_polys = [p for p in obj.data.polygons if p.select]
                if selected_polys:
                    for poly in selected_polys:
                        mat_idx = poly.material_index
                        if mat_idx < len(obj.material_slots):
                            mat = obj.material_slots[mat_idx].material
                            if mat and mat.name in const_dict:
                                mats_to_clear.add(mat.name)
                    self.report({'INFO'}, f"Adding materials from 3D selected faces.")

                if not mats_to_clear:
                    self.report({'WARNING'}, "No materials to clear (no checked items and no 3D selection).")
                    return {'CANCELLED'}

                fallback_cache = {}
                cleared, restored, failed, pending = process_materials(list(mats_to_clear), obj, fallback_cache)

                if pending:
                    pending_str = ','.join(pending)
                    bpy.ops.list.confirm_delete_pending('INVOKE_DEFAULT', pending_materials=pending_str)

                try:
                    bpy.ops.object.material_slot_remove_unused()
                except Exception:
                    pass
                self.purge_orphan_data()

                if failed:
                    self.report({'WARNING'}, f"Failed to clear: {', '.join(failed)}")
                else:
                    msg = f"Cleared {cleared} constant material(s)"
                    if restored > 0:
                        msg += f", restored {restored} via fallback"
                    if pending:
                        msg += f", {len(pending)} require confirmation"
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
    LIST_OT_ConfirmDeletePending,
]