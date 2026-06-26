"""
Material Family Separation Operator
First separates by material (native behavior), then joins objects
that share the same constant material family (ctr_original_material).
"""

import bpy
from bpy.types import Operator


class MATERIAL_OT_SeparateByFamily(Operator):
    """Separate by material, then join objects that share the same constant material family"""
    bl_idname = "material.separate_by_family"
    bl_label = "Separate by Family"
    bl_description = "Separates by material (native) then joins objects that share the same constant material base"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.mode == 'EDIT_MESH'

    def execute(self, context):
        obj = context.active_object
        original_name = obj.name

        # 1. Use native "Separate by Material"
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        
        # Enter edit mode and separate by material
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.separate(type='MATERIAL')
        bpy.ops.object.mode_set(mode='OBJECT')

        # 2. Collect all objects that were created
        separated_objs = [ob for ob in context.selected_objects if ob.type == 'MESH']

        # 3. Build family groups based on material metadata
        # Key: family_name (base material name), Value: list of objects
        family_groups = {}
        objects_by_material = {}  # material_name -> object

        for ob in separated_objs:
            if len(ob.data.materials) > 0:
                mat = ob.data.materials[0]
                if mat:
                    # If it's a constant material, get its original base
                    if mat.get("ctr_block_type") is not None:
                        family_key = mat.get("ctr_original_material", mat.name)
                    else:
                        family_key = mat.name
                    
                    objects_by_material[mat.name] = ob
                    family_groups.setdefault(family_key, []).append(ob)
            else:
                # Object with no material - keep separate
                family_groups.setdefault("No_Material", []).append(ob)

        # 4. If there's only one family, nothing to do
        if len(family_groups) <= 1:
            self.report({'INFO'}, "Objects already grouped by material family.")
            return {'FINISHED'}

        # 5. Join objects that belong to the same family
        joined_objects = []
        for family_key, objects in family_groups.items():
            if len(objects) <= 1:
                # Single object, just rename it
                if objects:
                    objects[0].name = family_key
                    joined_objects.append(objects[0])
                continue

            # Select all objects in this family and join them
            bpy.ops.object.select_all(action='DESELECT')
            for ob in objects:
                ob.select_set(True)
            context.view_layer.objects.active = objects[0]
            bpy.ops.object.join()
            
            joined_obj = context.active_object
            joined_obj.name = family_key
            joined_objects.append(joined_obj)

        # 6. Clean unused material slots from all joined objects
        for ob in joined_objects:
            self.clean_material_slots(ob)

        # 7. Select all resulting objects
        bpy.ops.object.select_all(action='DESELECT')
        for ob in joined_objects:
            ob.select_set(True)
        if joined_objects:
            context.view_layer.objects.active = joined_objects[0]

        self.report({'INFO'}, f"Separated '{original_name}' into {len(joined_objects)} objects by material family.")
        return {'FINISHED'}

    def clean_material_slots(self, obj):
        """Remove unused material slots from the object."""
        if obj.type != 'MESH':
            return
        
        # Get set of material indices actually used by polygons
        used_indices = set()
        for poly in obj.data.polygons:
            used_indices.add(poly.material_index)
        
        # Remove slots in reverse order to avoid index shifting issues
        for i in range(len(obj.material_slots) - 1, -1, -1):
            if i not in used_indices:
                obj.data.materials.pop(index=i)
        
        obj.data.update()


def register():
    bpy.utils.register_class(MATERIAL_OT_SeparateByFamily)


def unregister():
    bpy.utils.unregister_class(MATERIAL_OT_SeparateByFamily)