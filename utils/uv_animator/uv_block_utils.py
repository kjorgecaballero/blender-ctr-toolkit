import bpy
import bmesh
import json
from mathutils import Vector

def get_faces_with_material(obj, material_name):
    """Return a list of face indices that use the given material, in natural polygon order."""
    if obj.type != 'MESH':
        return []
    mesh = obj.data
    mat_index = -1
    for i, slot in enumerate(obj.material_slots):
        if slot.material and slot.material.name == material_name:
            mat_index = i
            break
    if mat_index == -1:
        return []
    face_indices = []
    for poly in mesh.polygons:
        if poly.material_index == mat_index:
            face_indices.append(poly.index)
    return face_indices

def get_uvs_from_material_block(obj, material_name):
    """Capture UVs from faces using the given material, in natural polygon order."""
    if obj.type != 'MESH':
        return None, "Not a mesh"
    face_indices = get_faces_with_material(obj, material_name)
    if not face_indices:
        return None, f"No faces found with material '{material_name}'"

    mesh = obj.data
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active
        if not uv_layer:
            return None, "No active UV map in edit mode"
        faces = sorted([f for f in bm.faces if f.index in face_indices], key=lambda f: f.index)
        uvs = []
        for face in faces:
            uvs.append([(loop[uv_layer].uv.x, loop[uv_layer].uv.y) for loop in face.loops])
        return uvs, None
    else:
        uv_layer = mesh.uv_layers.active
        if not uv_layer:
            if mesh.uv_layers:
                uv_layer = mesh.uv_layers[0]
            else:
                return None, "No UV layers found"
        uv_data = uv_layer.data
        if len(uv_data) == 0:
            return None, "UV data is empty"
        uvs = []
        for fi in face_indices:
            if fi >= len(mesh.polygons):
                return None, f"Face index {fi} out of range"
            poly = mesh.polygons[fi]
            face_uvs = []
            for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
                if li >= len(uv_data):
                    return None, f"Loop {li} out of range (UV data size {len(uv_data)})"
                uv = uv_data[li].uv
                face_uvs.append((uv.x, uv.y))
            uvs.append(face_uvs)
        return uvs, None

def get_face_center_world(obj, face_index):
    """
    Calculate the world-space centroid of a face.
    Uses the object's world matrix to transform local coordinates.
    """
    if obj.type != 'MESH':
        return None
    mesh = obj.data
    if face_index >= len(mesh.polygons):
        return None
    poly = mesh.polygons[face_index]
    verts = [mesh.vertices[i].co for i in poly.vertices]
    local_center = sum(verts, Vector((0, 0, 0))) / len(verts)
    world_center = obj.matrix_world @ local_center
    return world_center

def apply_uvs_to_material(obj, material_name, uvs_data, centers_ordered=None):
    """
    Apply UVs to faces using the specified material.
    If centers_ordered is provided (list of (x,y,z) tuples in WORLD space),
    it will reorder uvs_data to match the current face order by comparing
    world-space face centroids.
    This guarantees correct matching even after object duplication/transformation.
    """
    if obj.type != 'MESH':
        return
    face_indices = get_faces_with_material(obj, material_name)
    if not face_indices:
        if obj.data.materials:
            first_mat = obj.data.materials[0]
            if first_mat and first_mat.name != material_name:
                face_indices = get_faces_with_material(obj, first_mat.name)
                if face_indices:
                    material_name = first_mat.name
        if not face_indices:
            print(f"Warning: No faces found with material '{material_name}'")
            return

    original_mode = obj.mode
    if original_mode != 'OBJECT':
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')

    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if not uv_layer:
        if original_mode == 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        return
    uv_data = uv_layer.data

    # REORDER UVs USING WORLD-SPACE CENTERS
    if centers_ordered is not None and len(centers_ordered) == len(face_indices):
        # Calculate world centroids of destination faces (in the order of face_indices)
        dest_centers = []
        for fi in face_indices:
            if fi >= len(mesh.polygons):
                continue
            poly = mesh.polygons[fi]
            verts = [mesh.vertices[i].co for i in poly.vertices]
            local_center = sum(verts, Vector((0, 0, 0))) / len(verts)
            world_center = obj.matrix_world @ local_center
            dest_centers.append(world_center)

        # Reorder uvs_data to match the destination face order
        reordered_uvs = []
        for d_center in dest_centers:
            best_idx = -1
            best_dist = 1e6
            for j, orig_center_tuple in enumerate(centers_ordered):
                orig_center = Vector(orig_center_tuple)
                dist = (d_center - orig_center).length
                if dist < best_dist:
                    best_dist = dist
                    best_idx = j
            if best_idx != -1:
                reordered_uvs.append(uvs_data[best_idx])
            else:
                # Fallback: keep the first UV (should never happen if centers match)
                print(f"Warning: No match found for center {d_center}, using fallback UV")
                reordered_uvs.append(uvs_data[0])
        uvs_data = reordered_uvs

    if len(face_indices) != len(uvs_data):
        print(f"Warning: face count ({len(face_indices)}) != UV count ({len(uvs_data)})")
        if len(uvs_data) > len(face_indices):
            uvs_data = uvs_data[:len(face_indices)]
        else:
            pass

    for fi, face_uvs in zip(face_indices, uvs_data):
        if fi >= len(mesh.polygons):
            continue
        poly = mesh.polygons[fi]
        if len(face_uvs) != poly.loop_total:
            continue
        for i, (u, v) in enumerate(face_uvs):
            uv_data[poly.loop_start + i].uv = (u, v)
    mesh.update()
    if original_mode == 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

def get_active_texture_from_material(mat):
    if not mat or not mat.use_nodes:
        return ""
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            return bpy.path.abspath(node.image.filepath)
    return ""

def get_constant_materials_on_object(obj):
    result = []
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.get("ctr_block_type") is not None:
            block_type = mat.get("ctr_block_type")
            block_id = mat.get("ctr_block_id", 0)
            result.append((mat.name, block_type, block_id))
    return result

def is_valid_block(obj, material_name, block_type, block_id):
    from ..qb_tb_navigator.constant_material_utils import is_valid_navigation_point
    valid, _, _, _ = is_valid_navigation_point(obj, material_name, bm=None)
    return valid