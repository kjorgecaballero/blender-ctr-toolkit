import bpy
import bmesh
import json

def get_all_uvs(obj):
    """
    Capture UVs from an object in Edit Mode using bmesh.
    Requires the object to be in Edit Mode.
    """
    if obj.mode != 'EDIT':
        return None, "Object must be in Edit Mode"
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        return None, "No active UV map"
    all_uvs = []
    for face in bm.faces:
        face_uvs = [(loop[uv_layer].uv.x, loop[uv_layer].uv.y) for loop in face.loops]
        all_uvs.append(face_uvs)
    return all_uvs, None

def get_current_uvs_from_mesh(obj):
    """
    Capture current UV coordinates from the given mesh object.
    Works in both Object Mode and Edit Mode.

    - In Edit Mode: reads UVs from bmesh (the live editing state).
    - In Object Mode: reads UVs from the mesh's active UV layer.

    Returns:
        (uvs_data, error_message)
        uvs_data: list of faces, each face is a list of (u, v) tuples.
        error_message: None if successful, otherwise a string describing the error.
    """
    if obj.type != 'MESH':
        return None, "Object is not a mesh"

    mesh = obj.data
    if len(mesh.polygons) == 0:
        return None, "Mesh has no faces"

    # Edit Mode: use bmesh for reliable live UV data
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active
        if uv_layer is None:
            return None, "No active UV map in bmesh"
        uvs_data = []
        for face in bm.faces:
            face_uvs = [(loop[uv_layer].uv.x, loop[uv_layer].uv.y) for loop in face.loops]
            uvs_data.append(face_uvs)
        return uvs_data, None

    # Object Mode: read directly from mesh data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return None, "No active UV map"
    
    uv_data = uv_layer.data
    if len(uv_data) == 0:
        return None, "UV map exists but has no data (no UV coordinates assigned)"

    uvs_data = []
    for poly in mesh.polygons:
        face_uvs = []
        for loop_idx in range(poly.loop_start, poly.loop_start + poly.loop_total):
            if loop_idx >= len(uv_data):
                return None, f"Loop index {loop_idx} out of range (UV data size {len(uv_data)})"
            uv = uv_data[loop_idx].uv
            face_uvs.append((uv.x, uv.y))
        uvs_data.append(face_uvs)
    return uvs_data, None

def get_active_texture_path(obj):
    """
    Get the filepath of the active image texture node in the object's active material.
    Returns an empty string if no texture is found.
    """
    if not obj.active_material or not obj.active_material.use_nodes:
        return ""
    for node in obj.active_material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image:
            return bpy.path.abspath(node.image.filepath)
    return ""

def apply_uvs_to_object(obj, uvs_data, texture_path=None):
    """
    Apply the given UV coordinates to the object and optionally set the texture.
    Handles switching modes temporarily if needed.
    """
    original_mode = obj.mode
    if original_mode != 'OBJECT':
        current_active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')

    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    if uv_layer is None:
        return
    uv_data = uv_layer.data
    for face_idx, face_uvs in enumerate(uvs_data):
        if face_idx >= len(mesh.polygons):
            break
        face = mesh.polygons[face_idx]
        if len(face_uvs) != face.loop_total:
            continue
        for i in range(face.loop_total):
            u, v = face_uvs[i]
            uv_data[face.loop_start + i].uv = (u, v)
    mesh.update()

    if texture_path:
        mat = obj.active_material
        if mat and mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    try:
                        img = bpy.data.images.load(texture_path, check_existing=True)
                        node.image = img
                    except:
                        pass
                    break

    if original_mode == 'EDIT':
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

def get_target_object(context):
    """
    Get the currently active UV target object.
    Priority: scene.active_uv_object_name, then context.active_object.
    """
    scene = context.scene
    obj_name = scene.active_uv_object_name
    if obj_name and obj_name in bpy.data.objects:
        obj = bpy.data.objects[obj_name]
        if obj.type == 'MESH':
            return obj
    obj = context.active_object
    if obj and obj.type == 'MESH':
        return obj
    return None

def sync_texture_items(obj):
    """Update uv_texture_items collection to match unique textures from frames."""
    if not obj or obj.type != 'MESH':
        return
    frame_paths = set()
    for frame in obj.uv_animation_frames:
        if frame.texture_path:
            frame_paths.add(frame.texture_path)
    
    items_to_remove = []
    for item in obj.uv_texture_items:
        if item.texture_path not in frame_paths:
            items_to_remove.append(item)
    for item in items_to_remove:
        obj.uv_texture_items.remove(obj.uv_texture_items.find(item.texture_path))
    
    existing_paths = {item.texture_path for item in obj.uv_texture_items}
    for path in frame_paths:
        if path not in existing_paths:
            new_item = obj.uv_texture_items.add()
            new_item.texture_path = path
            new_item.blend_mode = "0"