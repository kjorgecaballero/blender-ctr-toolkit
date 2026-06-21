import bpy
import bmesh

from ...utils.qb_tb_navigator import is_valid_navigation_point


def gather_objects_navigation_data(context):
    """
    Gather navigation point data from all selected mesh objects.
    Prints a detailed report to the system console and returns a summary for UI.

    Returns:
        tuple: (nav_data_dict, summary_lines, collections_data)
            nav_data_dict: {object_name: [list_of_valid_nav_material_names]}
            summary_lines: list of strings for UI reporting
            collections_data: {object_name: [list_of_collection_names]}
    """
    selected_objs = [obj for obj in context.selected_objects if obj.type == 'MESH']
    if not selected_objs:
        msg = "No mesh objects selected."
        print(msg)
        return {}, [msg], {}

    report_lines = []
    report_lines.append("\n" + "="*60)
    report_lines.append("MULTIPLE OBJECTS NAVIGATION DATA (BEFORE JOIN)")
    report_lines.append("="*60)

    nav_data = {}
    collections_data = {}
    total_valid = 0

    for obj in selected_objs:
        obj_name = obj.name
        nav_materials = []
        report_lines.append(f"\n--- Object: {obj_name} ---")

        # Store original collections
        collections_data[obj_name] = [coll.name for coll in obj.users_collection]

        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            if mat.get("ctr_block_type") is not None and mat.get("ctr_is_navigation_point", False):
                is_valid, error_msg, center, block_type = is_valid_navigation_point(obj, mat.name, bm=None)
                if is_valid:
                    nav_materials.append(mat.name)
                    report_lines.append(f" Valid Nav Point: {mat.name} (type: {block_type})")
                else:
                    report_lines.append(f" Invalid Nav Point: {mat.name} - {error_msg}")

        nav_data[obj_name] = nav_materials
        total_valid += len(nav_materials)
        report_lines.append(f"  Total valid navigation points: {len(nav_materials)}")

    report_lines.append("\n" + "="*60 + "\n")
    full_report = "\n".join(report_lines)
    print(full_report)

    summary_lines = []
    summary_lines.append(f"Gathered navigation data from {len(selected_objs)} object(s).")
    for obj_name, mats in nav_data.items():
        if mats:
            summary_lines.append(f"  {obj_name}: {len(mats)} valid nav point(s)")
        else:
            summary_lines.append(f"  {obj_name}: no valid nav points")
    summary_lines.append(f"Total valid navigation points across all objects: {total_valid}")
    summary_lines.append("(Detailed log printed to the system console)")

    return nav_data, summary_lines, collections_data


def join_selected_objects(context):
    """
    Join all selected mesh objects into one object.
    Returns the joined object, or None if no valid meshes are selected.
    The joined object is renamed with a '_joined' suffix to avoid name conflicts.
    """
    if context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    selected = context.selected_objects
    if not selected:
        return None

    meshes = [obj for obj in selected if obj.type == 'MESH']
    if not meshes:
        return None

    if len(meshes) == 1:
        # Even with a single object, we rename it with '_joined' to keep consistency
        obj = meshes[0]
        # Ensure it has a unique name
        new_name = obj.name + "_joined"
        # If that name already exists, add a number
        if new_name in bpy.data.objects:
            i = 1
            while f"{obj.name}_joined_{i:03d}" in bpy.data.objects:
                i += 1
            new_name = f"{obj.name}_joined_{i:03d}"
        obj.name = new_name
        return obj

    active = context.active_object
    if active not in meshes:
        context.view_layer.objects.active = meshes[0]
        active = meshes[0]

    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    context.view_layer.objects.active = active

    bpy.ops.object.join()

    joined_obj = context.active_object
    # Rename the joined object with a suffix to avoid name collisions with originals
    base_name = active.name  # name before join
    new_name = base_name + "_joined"
    # Ensure the new name is unique
    if new_name in bpy.data.objects:
        i = 1
        while f"{base_name}_joined_{i:03d}" in bpy.data.objects:
            i += 1
        new_name = f"{base_name}_joined_{i:03d}"
    joined_obj.name = new_name

    return joined_obj


def restore_original_objects(context, joined_obj, nav_data, original_names, collections_data):
    """
    Restore original objects from joined mesh using navigation points.
    Uses select_linked to capture connected components, separates them,
    and restores each object to its original collection(s).

    Args:
        context: Blender context
        joined_obj: The joined mesh object
        nav_data: {original_name: [list_of_nav_material_names]}
        original_names: list of original object names
        collections_data: {original_name: [list_of_collection_names]}

    Returns:
        list: Restored objects
    """
    if not joined_obj or joined_obj.type != 'MESH':
        print("No valid joined object to restore from.")
        return []

    print("\n" + "="*60)
    print("RESTORING ORIGINAL OBJECTS FROM JOINED MESH")
    print("="*60)

    # Ensure we are in OBJECT mode
    if context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    # Select and activate the joined object
    bpy.ops.object.select_all(action='DESELECT')
    joined_obj.select_set(True)
    context.view_layer.objects.active = joined_obj

    restored_objects = []

    for obj_name in original_names:
        nav_mats = nav_data.get(obj_name, [])
        if not nav_mats:
            print(f"  No navigation materials for {obj_name}, skipping.")
            continue

        print(f"\n  Restoring {obj_name}...")

        # Collect material indices for all navigation materials of this object
        material_indices = set()
        for mat_name in nav_mats:
            # Find the material in the joined object (by exact name or by original reference)
            found_mat = None
            for mat in bpy.data.materials:
                if mat.name == mat_name:
                    found_mat = mat
                    break
                # Check if this material is a constant derived from this mat_name
                if mat.get("ctr_original_material") == mat_name:
                    found_mat = mat
                    break
            if not found_mat:
                print(f"    Material {mat_name} not found, skipping.")
                continue

            # Get the material index in the joined object
            mat_index = -1
            for i, slot in enumerate(joined_obj.material_slots):
                if slot.material == found_mat:
                    mat_index = i
                    break
            if mat_index == -1:
                print(f"    Material {mat_name} not assigned to any face, skipping.")
                continue

            material_indices.add(mat_index)
            print(f"    Found material: {mat_name} (index {mat_index})")

        if not material_indices:
            print(f"  No valid materials found for {obj_name}, skipping.")
            continue

        # Enter edit mode and select faces with these material indices
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')

        # Use bmesh to select faces by material index (SAFE VERSION)
        bm = bmesh.from_edit_mesh(joined_obj.data)
        bm.faces.ensure_lookup_table()

        # Count selected faces (no references stored)
        selected_count = 0
        for face in bm.faces:
            if face.material_index in material_indices:
                face.select = True
                selected_count += 1

        bmesh.update_edit_mesh(joined_obj.data)
        bm.free()   # Release immediately after updating

        if selected_count == 0:
            print(f"  No faces selected for {obj_name}, skipping separation.")
            continue

        # EXPAND SELECTION TO THE ENTIRE CONNECTED PIECE
        bpy.ops.mesh.select_linked()

        # Record objects selected BEFORE separation
        selected_before = set(context.selected_objects)

        # Separate selected faces
        bpy.ops.mesh.separate(type='SELECTED')

        # Exit edit mode to get the new object
        bpy.ops.object.mode_set(mode='OBJECT')

        # Find the newly created object: it is selected after but was not selected before
        selected_after = set(context.selected_objects)
        new_objs = selected_after - selected_before
        new_obj = None
        for obj in new_objs:
            if obj.type == 'MESH' and obj != joined_obj:
                new_obj = obj
                break

        if new_obj:
            new_obj.name = obj_name

            # COLLECTION RESTORATION
            # Get the original collection names for this object
            coll_names = collections_data.get(obj_name, [])

            # Safety fallback: if no original collection is found, use the root collection
            if not coll_names:
                coll_names = [context.scene.collection.name]

            # Get current collections the object belongs to
            current_coll_names = {coll.name for coll in new_obj.users_collection}

            # Only perform the move if the object is NOT already in the exact target collections
            if set(coll_names) != current_coll_names:
                # Unlink from all current collections
                for coll in list(new_obj.users_collection):
                    coll.objects.unlink(new_obj)

                # Link to the original collections
                linked_to_any = False
                for coll_name in coll_names:
                    if coll_name in bpy.data.collections:
                        bpy.data.collections[coll_name].objects.link(new_obj)
                        linked_to_any = True

                # If none of the target collections exist (e.g., renamed/deleted), fallback to root
                if not linked_to_any:
                    context.scene.collection.objects.link(new_obj)
            else:
                pass

            print(f"  Restored object: {obj_name} (collections: {coll_names})")
            restored_objects.append(new_obj)
        else:
            print(f"  Failed to separate object for {obj_name}")

        # Deselect all and re-select joined object for next iteration
        bpy.ops.object.select_all(action='DESELECT')
        # Verify that joined_obj still exists
        if joined_obj.name not in bpy.data.objects:
            print(f"  Joined object '{joined_obj.name}' no longer exists. Stopping restoration.")
            break
        joined_obj.select_set(True)
        context.view_layer.objects.active = joined_obj

    # Exit edit mode (just in case)
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"\nRestored {len(restored_objects)} objects.")
    print("="*60 + "\n")

    # AUTO-DELETE JOINED OBJECT IF EMPTY (with existence check)
    if joined_obj.name in bpy.data.objects:
        if joined_obj.data.polygons:
            print(f"Joined object '{joined_obj.name}' still has {len(joined_obj.data.polygons)} faces. "
                  f"These faces do not belong to any navigation point and were not restored. Keeping it.")
        else:
            print(f"Joined object '{joined_obj.name}' is now empty. Deleting it automatically.")
            bpy.data.objects.remove(joined_obj, do_unlink=True)
            print(f"  Removed empty joined object.")
    else:
        print(f"Joined object '{joined_obj.name}' has already been removed.")

    return restored_objects