import bpy
from bpy.types import Operator
from bpy.props import FloatProperty

VXSNAP_NODE_GROUP_NAME = "VX_WorldSnap"

def vxsnap_build_node_group():
    tree = bpy.data.node_groups.new(VXSNAP_NODE_GROUP_NAME, 'GeometryNodeTree')
    iface = tree.interface
    iface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    grid_sock = iface.new_socket("Grid Size", in_out='INPUT', socket_type='NodeSocketFloat')
    grid_sock.default_value = 0.1
    grid_sock.min_value = 0.001
    iface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    group_in = nodes.new('NodeGroupInput')
    group_in.location = (-1200, 0)
    group_out = nodes.new('NodeGroupOutput')
    group_out.location = (1400, 0)

    self_obj = nodes.new('GeometryNodeSelfObject')
    self_obj.location = (-1200, -400)
    obj_info = nodes.new('GeometryNodeObjectInfo')
    obj_info.location = (-1000, -400)
    obj_info.transform_space = 'ORIGINAL'
    links.new(self_obj.outputs["Self Object"], obj_info.inputs["Object"])

    pos_in = nodes.new('GeometryNodeInputPosition')
    pos_in.location = (-1000, 200)

    # Local to World
    s_mul = nodes.new('ShaderNodeVectorMath')
    s_mul.operation = 'MULTIPLY'
    s_mul.location = (-800, 100)
    links.new(pos_in.outputs["Position"], s_mul.inputs[0])
    links.new(obj_info.outputs["Scale"], s_mul.inputs[1])

    rot = nodes.new('ShaderNodeVectorRotate')
    rot.rotation_type = 'EULER_XYZ'
    rot.location = (-600, 100)
    links.new(s_mul.outputs["Vector"], rot.inputs["Vector"])
    links.new(obj_info.outputs["Rotation"], rot.inputs["Rotation"])

    add = nodes.new('ShaderNodeVectorMath')
    add.operation = 'ADD'
    add.location = (-400, 100)
    links.new(rot.outputs["Vector"], add.inputs[0])
    links.new(obj_info.outputs["Location"], add.inputs[1])
    world_pos = add.outputs["Vector"]

    # Snap
    combine = nodes.new('ShaderNodeCombineXYZ')
    combine.location = (-600, -200)
    links.new(group_in.outputs["Grid Size"], combine.inputs["X"])
    links.new(group_in.outputs["Grid Size"], combine.inputs["Y"])
    links.new(group_in.outputs["Grid Size"], combine.inputs["Z"])

    snap = nodes.new('ShaderNodeVectorMath')
    snap.operation = 'SNAP'
    snap.location = (-400, -50)
    links.new(world_pos, snap.inputs[0])
    links.new(combine.outputs["Vector"], snap.inputs[1])
    snapped_world = snap.outputs["Vector"]

    # World to Local
    sub = nodes.new('ShaderNodeVectorMath')
    sub.operation = 'SUBTRACT'
    sub.location = (-200, 100)
    links.new(snapped_world, sub.inputs[0])
    links.new(obj_info.outputs["Location"], sub.inputs[1])

    inv_rot = nodes.new('ShaderNodeVectorRotate')
    inv_rot.rotation_type = 'EULER_XYZ'
    inv_rot.invert = True
    inv_rot.location = (0, 100)
    links.new(sub.outputs["Vector"], inv_rot.inputs["Vector"])
    links.new(obj_info.outputs["Rotation"], inv_rot.inputs["Rotation"])

    div = nodes.new('ShaderNodeVectorMath')
    div.operation = 'DIVIDE'
    div.location = (200, 100)
    links.new(inv_rot.outputs["Vector"], div.inputs[0])
    links.new(obj_info.outputs["Scale"], div.inputs[1])
    final_local = div.outputs["Vector"]

    set_pos = nodes.new('GeometryNodeSetPosition')
    set_pos.location = (800, 0)
    links.new(group_in.outputs["Geometry"], set_pos.inputs["Geometry"])
    links.new(final_local, set_pos.inputs["Position"])
    links.new(set_pos.outputs["Geometry"], group_out.inputs["Geometry"])

    return tree

def vxsnap_get_node_group():
    grp = bpy.data.node_groups.get(VXSNAP_NODE_GROUP_NAME)
    return grp if grp else vxsnap_build_node_group()

def vxsnap_update_modifier_inputs(mod, grid_size):
    if mod.node_group is None:
        return
    for item in mod.node_group.interface.items_tree:
        if item.in_out == 'INPUT' and item.name == "Grid Size":
            mod[item.identifier] = grid_size
            break
    mod.show_viewport = False
    mod.show_viewport = True
    if mod.id_data:
        mod.id_data.update_tag()

class VXSNAP_OT_add(Operator):
    bl_idname = "vxsnap.add_snap"
    bl_label = "Add World Snap"
    bl_description = "Adds vertex snapping modifier (world grid) to selected meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        group = vxsnap_get_node_group()
        added = 0
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            for m in list(obj.modifiers):
                if m.type == 'NODES' and m.node_group and m.node_group.name == VXSNAP_NODE_GROUP_NAME:
                    obj.modifiers.remove(m)
            mod = obj.modifiers.new("VX_WorldSnap", 'NODES')
            mod.node_group = group
            vxsnap_update_modifier_inputs(mod, scene.vxsnap_grid_size)
            added += 1
        if added:
            context.view_layer.update()
            for area in context.screen.areas:
                area.tag_redraw()
            self.report({'INFO'}, f"Snap added to {added} object(s)")
        else:
            self.report({'WARNING'}, "No mesh objects selected")
        return {'FINISHED'}

class VXSNAP_OT_remove(Operator):
    bl_idname = "vxsnap.remove_snap"
    bl_label = "Remove World Snap"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed = 0
        for obj in context.selected_objects:
            for m in list(obj.modifiers):
                if m.type == 'NODES' and m.node_group and m.node_group.name == VXSNAP_NODE_GROUP_NAME:
                    obj.modifiers.remove(m)
                    removed += 1
        if removed:
            self.report({'INFO'}, f"Removed from {removed} object(s)")
        else:
            self.report({'WARNING'}, "No vertex snap modifier found")
        return {'FINISHED'}

class VXSNAP_OT_update(Operator):
    bl_idname = "vxsnap.update_snap"
    bl_label = "Update Grid Size"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        grid = scene.vxsnap_grid_size
        updated = 0
        for obj in context.selected_objects:
            for m in obj.modifiers:
                if m.type == 'NODES' and m.node_group and m.node_group.name == VXSNAP_NODE_GROUP_NAME:
                    vxsnap_update_modifier_inputs(m, grid)
                    updated += 1
        if updated:
            self.report({'INFO'}, f"Updated {updated} modifier(s)")
        else:
            self.report({'WARNING'}, "No vertex snap modifier found")
        return {'FINISHED'}