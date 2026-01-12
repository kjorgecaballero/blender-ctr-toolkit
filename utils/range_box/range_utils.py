"""
Range utilities for CTR Toolkit
Handles validation of objects within the 1000x1000x1000 range box
"""

import bpy
from mathutils import Vector

RANGE_BOX_SIZE = 1000

def get_range_box_object():
    """Retrieve the Range Box object from the Blender scene"""
    return bpy.data.objects.get("Range")

def get_range_dimensions():
    """Calculate the dimensions of the range box"""
    half_size = RANGE_BOX_SIZE / 2
    return {
        'min': [-half_size, -half_size, -half_size],
        'max': [half_size, half_size, half_size],
        'size': [RANGE_BOX_SIZE, RANGE_BOX_SIZE, RANGE_BOX_SIZE]
    }

def is_object_in_range(obj):
    """Check if an object is completely within the range box boundaries"""
    if obj.type != 'MESH':
        return False
    
    dimensions = get_range_dimensions()
    
    # Calculate object's bounding box corners in world space
    bbox_corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    obj_min = [min(c[i] for c in bbox_corners) for i in range(3)]
    obj_max = [max(c[i] for c in bbox_corners) for i in range(3)]
    
    # Check if object exceeds range boundaries in any axis
    for i in range(3):
        if obj_min[i] < dimensions['min'][i] or obj_max[i] > dimensions['max'][i]:
            return False
    return True

def get_out_of_range_objects(objects):
    """Separate objects into in-range and out-of-range lists"""
    in_range = []
    out_of_range = []
    
    for obj in objects:
        if is_object_in_range(obj):
            in_range.append(obj)
        else:
            out_of_range.append(obj)
    
    return in_range, out_of_range