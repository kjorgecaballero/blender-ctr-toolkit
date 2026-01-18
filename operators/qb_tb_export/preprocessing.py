import bpy
import bmesh


class QB_TB_Preprocessor:
    """
    Preprocesses objects before export validation.
    
    Handles operations like:
    - Applying modifiers
    - Separating loose parts
    - Managing object visibility and selection state
    """
    
    def __init__(self, context):
        """
        Initialize preprocessor with Blender context.
        
        Args:
            context: Blender context for scene operations
        """
        self.context = context
        self.processed_objects = []
        self.linked_objects = []
        self.original_collections_map = {}
    
    def ensure_object_in_view_layer(self, obj):
        """
        Ensure object is visible in the active view layer.
        
        Args:
            obj: Blender object to check/activate
            
        Returns:
            bool: True if object was linked, False if already present
        """
        if obj.name not in self.context.view_layer.objects:
            if bpy.context.scene.collection.name not in [c.name for c in obj.users_collection]:
                bpy.context.scene.collection.objects.link(obj)
                self.linked_objects.append(obj)
                print(f"Temporarily linked {obj.name} to view layer")
            return True
        return False
    
    def apply_modifiers_to_objects(self, objects):
        """
        Apply all modifiers to specified objects.
        
        Args:
            objects: List of objects to process
            
        Returns:
            int: Number of modifiers applied
        """
        applied_count = 0
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        original_selection = [obj for obj in self.context.selected_objects.copy()]
        original_active = self.context.view_layer.objects.active
        
        print(f"DEBUG apply_modifiers_to_objects: Processing {len(objects)} objects")
        
        for obj in objects:
            if obj.modifiers:
                # Store original collections for restoration
                original_collections = self.original_collections_map.get(obj.name, [])
                if not original_collections:
                    original_collections = list(obj.users_collection)
                    self.original_collections_map[obj.name] = original_collections
                
                # Ensure object is in view layer
                if not self.ensure_object_in_view_layer(obj):
                    obj.hide_viewport = False
                    obj.hide_set(False)
                
                # Select only this object
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                self.context.view_layer.objects.active = obj
                
                # Make object visible and selectable
                obj.hide_viewport = False
                obj.hide_set(False)
                obj.hide_select = False
                
                self.context.view_layer.update()
                
                # Apply all modifiers
                for modifier in list(obj.modifiers):
                    try:
                        if obj and obj.name in bpy.data.objects:
                            bpy.ops.object.modifier_apply(modifier=modifier.name)
                            applied_count += 1
                            print(f"Applied modifier {modifier.name} to {obj.name}")
                    except Exception as e:
                        print(f"Error applying modifier {modifier.name} to {obj.name}: {e}")
                
                # Restore original collection membership
                current_collections = list(obj.users_collection)
                if set(original_collections) != set(current_collections):
                    for coll in current_collections:
                        if coll not in original_collections:
                            try:
                                coll.objects.unlink(obj)
                            except Exception as e:
                                print(f"Error unlinking {obj.name} from collection {coll.name}: {e}")
                    for coll in original_collections:
                        if coll not in current_collections:
                            try:
                                coll.objects.link(obj)
                            except Exception as e:
                                print(f"Error linking {obj.name} to collection {coll.name}: {e}")
                
                obj.select_set(False)
        
        # Restore original selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            if obj and obj.name in bpy.data.objects:
                try:
                    obj.select_set(True)
                except:
                    pass
        
        if original_active and original_active.name in bpy.data.objects:
            self.context.view_layer.objects.active = original_active
        
        print(f"DEBUG: Restored original selection of {len(original_selection)} objects")
        return applied_count
    
    def separate_by_loose_parts(self, objects):
        """
        Separate meshes by connected components (loose parts).
        
        Args:
            objects: List of objects to separate
            
        Returns:
            tuple: (new_objects_list, separated_count)
        """
        separated_count = 0
        
        if self.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        original_selection = [obj for obj in self.context.selected_objects.copy()]
        original_active = self.context.view_layer.objects.active
        
        new_objects_list = []
        
        print(f"DEBUG separate_by_loose_parts: Processing {len(objects)} selected objects")
        
        for obj in list(objects):
            if obj.type == 'MESH':
                # Store original collections
                original_collections = self.original_collections_map.get(obj.name, [])
                if not original_collections:
                    original_collections = list(obj.users_collection)
                    self.original_collections_map[obj.name] = original_collections
                
                collection_names = [c.name for c in original_collections]
                print(f"  Original object {obj.name} is in collections: {collection_names}")
                
                # Ensure object is in view layer
                if not self.ensure_object_in_view_layer(obj):
                    obj.hide_viewport = False
                    obj.hide_set(False)
                
                # Select object
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                self.context.view_layer.objects.active = obj
                
                obj.hide_viewport = False
                obj.hide_set(False)
                obj.hide_select = False
                
                self.context.view_layer.update()
                
                # Enter edit mode and analyze mesh connectivity
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                
                bm = bmesh.from_edit_mesh(obj.data)
                
                # Find connected components
                connected_components = []
                visited = set()
                
                for vert in bm.verts:
                    if vert.index not in visited:
                        component = []
                        stack = [vert]
                        while stack:
                            current = stack.pop()
                            if current.index not in visited:
                                visited.add(current.index)
                                component.append(current)
                                for edge in current.link_edges:
                                    other_vert = edge.other_vert(current)
                                    if other_vert.index not in visited:
                                        stack.append(other_vert)
                        connected_components.append(component)
                
                bm.free()
                
                # Separate if multiple components found
                if len(connected_components) > 1:
                    original_object_name = obj.name
                    
                    bpy.ops.mesh.separate(type='LOOSE')
                    separated_count += 1
                    print(f"Separated {obj.name} by loose parts ({len(connected_components)} components)")
                    
                    bpy.ops.object.mode_set(mode='OBJECT')
                    
                    selected_objects = list(self.context.selected_objects)
                    print(f"  Selected objects after separation: {[o.name for o in selected_objects]}")
                    
                    # Process newly created objects
                    for selected_obj in selected_objects:
                        if selected_obj.name == original_object_name:
                            continue
                        
                        print(f"  Processing separated object: {selected_obj.name}")
                        
                        # Restore collection membership for new objects
                        current_collections = list(selected_obj.users_collection)
                        for coll in current_collections:
                            try:
                                coll.objects.unlink(selected_obj)
                            except Exception as e:
                                print(f"    Error unlinking {selected_obj.name} from collection {coll.name}: {e}")
                        
                        for coll in original_collections:
                            try:
                                coll.objects.link(selected_obj)
                                print(f"    Added {selected_obj.name} to collection: {coll.name}")
                            except Exception as e:
                                print(f"    Error adding {selected_obj.name} to collection {coll.name}: {e}")
                        
                        if selected_obj not in new_objects_list:
                            new_objects_list.append(selected_obj)
                else:
                    print(f"No loose parts to separate in {obj.name}")
                    bpy.ops.object.mode_set(mode='OBJECT')
        
        # Restore original selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            if obj and obj.name in bpy.data.objects:
                try:
                    obj.select_set(True)
                except:
                    pass
        
        if original_active and original_active.name in bpy.data.objects:
            self.context.view_layer.objects.active = original_active
        
        return new_objects_list, separated_count
    
    def preprocess_objects(self, objects, apply_modifiers=True, separate_loose=False, use_selection=False):
        """
        Main preprocessing pipeline for objects.
        
        Args:
            objects: List of objects to preprocess
            apply_modifiers: Whether to apply modifiers
            separate_loose: Whether to separate by loose parts
            use_selection: Whether processing only selected objects
            
        Returns:
            list: Processed objects ready for validation
        """
        print("=" * 50)
        print("Starting QB/TB pre-processing...")
        
        print(f"Processing {len(objects)} objects (selection filtering already applied)")
        
        processed_objects = list(objects)
        
        # Store original collection information
        self.original_collections_map.clear()
        for obj in processed_objects:
            self.original_collections_map[obj.name] = list(obj.users_collection)
        
        # Step 1: Apply modifiers if requested
        if apply_modifiers:
            print("\n--- Step 1: Applying modifiers ---")
            applied = self.apply_modifiers_to_objects(processed_objects)
            print(f"Applied {applied} modifiers")
        
        # Step 2: Separate loose parts if requested
        if separate_loose:
            print("\n--- Step 2: Separating by loose parts ---")
            new_objects, separated = self.separate_by_loose_parts(processed_objects)
            
            processed_objects.extend(new_objects)
            print(f"Separated {separated} meshes, created {len(new_objects)} new objects")
            
            print(f"DEBUG: Total objects after separation: {len(processed_objects)}")
            for obj in processed_objects:
                print(f"  - {obj.name}")
        
        print(f"\nTotal processed objects: {len(processed_objects)}")
        print("=" * 50)
        
        self.processed_objects = processed_objects
        return processed_objects
    
    def cleanup(self):
        """
        Clean up temporary object links and restore state.
        """
        for obj in self.linked_objects:
            try:
                if obj and obj.name in bpy.data.objects:
                    collections = obj.users_collection
                    if len(collections) > 1:
                        bpy.context.scene.collection.objects.unlink(obj)
                        print(f"Unlinked {obj.name} from temporary view layer")
            except Exception as e:
                print(f"Error unlinking object: {e}")
        
        self.linked_objects = []