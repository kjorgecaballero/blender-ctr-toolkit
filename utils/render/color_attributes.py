import bpy
import bmesh


def create_color_attribute_for_object(obj, target_name="VertexColor"):
    """Creates a white color attribute for an object that has no color attributes"""
    mesh = obj.data
    if not hasattr(mesh, "color_attributes"):
        print(f"Object '{obj.name}' does not support color attributes")
        return False
    try:
        color_attr = mesh.color_attributes.new(
            name=target_name,
            type='BYTE_COLOR',
            domain='CORNER'
        )
        apply_white_color_to_attribute(obj, target_name)
        print(f"Created new attribute '{target_name}' on '{obj.name}' with white color")
        return True
    except Exception as e:
        print(f"Error creating color attribute for '{obj.name}': {e}")
        return False


def apply_white_color_to_attribute(obj, attribute_name="VertexColor"):
    """Applies white color to all elements of the color attribute"""
    mesh = obj.data
    try:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        color_layer = bm.loops.layers.color.get(attribute_name)
        if color_layer is None:
            color_layer = bm.loops.layers.color.new(attribute_name)
        white_color = (1.0, 1.0, 1.0, 1.0)
        for face in bm.faces:
            for loop in face.loops:
                loop[color_layer] = white_color
        bm.to_mesh(mesh)
        bm.free()
        print(f"White color applied to attribute '{attribute_name}' on '{obj.name}'")
        return True
    except Exception as e:
        print(f"Error applying white color to '{obj.name}': {e}")
        return False


def ensure_attribute_exists(obj, target_name="VertexColor"):
    """Ensures the object has a color attribute with the specified name"""
    mesh = obj.data
    if not hasattr(mesh, "color_attributes"):
        return False
    if not mesh.color_attributes:
        print(f"Creating new color attribute for '{obj.name}'")
        result = create_color_attribute_for_object(obj, target_name)
        if result:
            mesh.update()
        return result
    color_attrs = mesh.color_attributes
    existing_attr = None
    for attr in color_attrs:
        if attr.name == target_name:
            existing_attr = attr
            break
    if existing_attr:
        for i, attr in enumerate(color_attrs):
            if attr.name == target_name:
                color_attrs.active_color_index = i
                print(f"Attribute '{target_name}' already exists on '{obj.name}' - set as active")
                mesh.update()
                return True
    else:
        if len(color_attrs) > 0:
            first_attr = color_attrs[0]
            old_name = first_attr.name
            first_attr.name = target_name
            color_attrs.active_color_index = 0
            apply_white_color_to_attribute(obj, target_name)
            print(f"'{obj.name}': '{old_name}' -> '{target_name}'")
            mesh.update()
            return True
        else:
            print(f"Creating new color attribute for '{obj.name}' (empty list)")
            result = create_color_attribute_for_object(obj, target_name)
            if result:
                mesh.update()
            return result


def get_current_attribute_name(obj):
    """Gets the name of the active color attribute of the object"""
    mesh = obj.data
    if not hasattr(mesh, "color_attributes") or not mesh.color_attributes:
        return None
    active_index = mesh.color_attributes.active_color_index
    if active_index < len(mesh.color_attributes):
        return mesh.color_attributes[active_index].name
    return None


def list_all_color_attributes(obj):
    """Lists all color attributes of the object"""
    mesh = obj.data
    if not hasattr(mesh, "color_attributes") or not mesh.color_attributes:
        return []
    return [attr.name for attr in mesh.color_attributes]


def rename_color_attribute(obj, old_name, new_name):
    """Renames an existing color attribute"""
    mesh = obj.data
    if not hasattr(mesh, "color_attributes"):
        return False
    for attr in mesh.color_attributes:
        if attr.name == old_name:
            attr.name = new_name
            print(f"Attribute renamed: '{old_name}' -> '{new_name}' on '{obj.name}'")
            return True
    print(f"Attribute '{old_name}' not found on '{obj.name}'")
    return False


def ensure_all_objects_have_color_attributes(target_name="VertexColor"):
    """Ensures ALL mesh objects in the scene have color attributes with the specified name"""
    created_count = 0
    renamed_count = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            current_attrs = list_all_color_attributes(obj)
            if not current_attrs:
                if create_color_attribute_for_object(obj, target_name):
                    created_count += 1
            else:
                if target_name not in current_attrs:
                    if rename_color_attribute(obj, current_attrs[0], target_name):
                        renamed_count += 1
                else:
                    ensure_attribute_exists(obj, target_name)
    print(f"Summary: {created_count} attributes created, {renamed_count} attributes renamed")
    return created_count + renamed_count


def ensure_selected_objects_have_color_attributes(context, target_name="VertexColor"):
    """Ensures selected objects have color attributes with the specified name"""
    created_count = 0
    renamed_count = 0
    for obj in context.selected_objects:
        if obj.type == 'MESH':
            current_attrs = list_all_color_attributes(obj)
            if not current_attrs:
                if create_color_attribute_for_object(obj, target_name):
                    created_count += 1
            else:
                if target_name not in current_attrs:
                    if rename_color_attribute(obj, current_attrs[0], target_name):
                        renamed_count += 1
                else:
                    ensure_attribute_exists(obj, target_name)
    print(f"Selected summary: {created_count} created, {renamed_count} renamed")
    return created_count + renamed_count


def verify_attribute_for_active_object(context, target_name="VertexColor"):
    """Verifies and ensures the active object has the correct attribute"""
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return False, "No mesh object selected"
    current_attrs = list_all_color_attributes(obj)
    if not current_attrs:
        if create_color_attribute_for_object(obj, target_name):
            obj.data.update()
            context.view_layer.update()
            return True, f"Attribute '{target_name}' created on '{obj.name}'"
        else:
            return False, f"Error creating attribute on '{obj.name}'"
    if target_name not in current_attrs:
        if rename_color_attribute(obj, current_attrs[0], target_name):
            obj.data.update()
            context.view_layer.update()
            return True, f"Attribute renamed to '{target_name}' on '{obj.name}'"
        else:
            return False, f"Error renaming attribute on '{obj.name}'"
    else:
        ensure_attribute_exists(obj, target_name)
        obj.data.update()
        context.view_layer.update()
        return True, f"Attribute '{target_name}' verified on '{obj.name}'"