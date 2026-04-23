import bpy
from ..compat import is_blender_ge_5_0


def set_viewport_compositor(state):
    """Enable/disable viewport compositor across all 3D views."""
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D' and hasattr(space.shading, 'use_compositor'):
                    if bpy.app.version >= (3, 5, 0):
                        space.shading.use_compositor = state
                    else:
                        space.shading.use_compositor = bool(state)


def create_ps1_compositor_node_group():
    """Create a node group for PS1 pixelation effect (Blender 5.0+)."""
    group_name = "PS1_Compositor"
    if group_name in bpy.data.node_groups:
        ng = bpy.data.node_groups[group_name]
        for node in list(ng.nodes):
            ng.nodes.remove(node)
    else:
        ng = bpy.data.node_groups.new(group_name, 'CompositorNodeTree')

    ng.interface.new_socket(name="Image", in_out='INPUT', socket_type='NodeSocketColor')
    ng.interface.new_socket(name="Image", in_out='OUTPUT', socket_type='NodeSocketColor')

    nodes = ng.nodes
    links = ng.links

    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-400, 0)

    scale_down = nodes.new('CompositorNodeScale')
    scale_down.location = (-200, 0)
    if hasattr(scale_down, 'space'):
        scale_down.space = 'RELATIVE'
    scale_down.inputs['X'].default_value = 0.5
    scale_down.inputs['Y'].default_value = 0.5

    pixelate = nodes.new('CompositorNodePixelate')
    pixelate.location = (0, 0)

    scale_up = nodes.new('CompositorNodeScale')
    scale_up.location = (200, 0)
    if hasattr(scale_up, 'space'):
        scale_up.space = 'RELATIVE'
    scale_up.inputs['X'].default_value = 2.0
    scale_up.inputs['Y'].default_value = 2.0

    group_output = nodes.new('NodeGroupOutput')
    group_output.location = (400, 0)

    links.new(group_input.outputs['Image'], scale_down.inputs['Image'])
    links.new(scale_down.outputs['Image'], pixelate.inputs['Color'])
    links.new(pixelate.outputs['Color'], scale_up.inputs['Image'])
    links.new(scale_up.outputs['Image'], group_output.inputs['Image'])

    return ng


def apply_ps1_compositing(context):
    scene = context.scene
    scene.render.resolution_x = 512
    scene.render.resolution_y = 216
    scene.render.resolution_percentage = 100
    scene.render.filter_size = 0.0
    if hasattr(scene, 'eevee'):
        scene.eevee.taa_render_samples = 1
        scene.eevee.taa_samples = 1
        scene.eevee.use_taa_reprojection = False
    set_viewport_compositor('ALWAYS' if bpy.app.version >= (3, 5, 0) else True)
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'

    if is_blender_ge_5_0():
        scene.render.use_compositing = True
        ng = create_ps1_compositor_node_group()
        scene.compositing_node_group = ng
        print("PS1 compositing applied (Blender 5.0+ method)")
    elif hasattr(scene, 'node_tree'):
        scene.use_nodes = True
        tree = scene.node_tree
        for node in list(tree.nodes):
            tree.nodes.remove(node)
        rlayer = tree.nodes.new('CompositorNodeRLayers')
        rlayer.location = (-100, 0)
        scale_down = tree.nodes.new('CompositorNodeScale')
        scale_down.location = (100, 0)
        if hasattr(scale_down, 'space'):
            scale_down.space = 'RELATIVE'
        scale_down.inputs['X'].default_value = 0.5
        scale_down.inputs['Y'].default_value = 0.5
        pixelate = tree.nodes.new('CompositorNodePixelate')
        pixelate.location = (300, 0)
        scale_up = tree.nodes.new('CompositorNodeScale')
        scale_up.location = (500, 0)
        if hasattr(scale_up, 'space'):
            scale_up.space = 'RELATIVE'
        scale_up.inputs['X'].default_value = 2.0
        scale_up.inputs['Y'].default_value = 2.0
        composite = tree.nodes.new('CompositorNodeComposite')
        composite.location = (700, 0)
        links = tree.links
        links.new(rlayer.outputs['Image'], scale_down.inputs['Image'])
        links.new(scale_down.outputs['Image'], pixelate.inputs['Color'])
        links.new(pixelate.outputs['Color'], scale_up.inputs['Image'])
        links.new(scale_up.outputs['Image'], composite.inputs['Image'])
        print("PS1 compositing applied (classic scene.node_tree)")
    else:
        print("PS1 compositing could not be set up – no compatible compositor API found")


def remove_ps1_compositing(context):
    scene = context.scene
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.filter_size = 1.0
    if hasattr(scene, 'eevee'):
        scene.eevee.taa_render_samples = 64
        scene.eevee.taa_samples = 64
        scene.eevee.use_taa_reprojection = True
    set_viewport_compositor('DISABLED' if bpy.app.version >= (3, 5, 0) else False)
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    if is_blender_ge_5_0():
        if hasattr(scene, 'compositing_node_group'):
            scene.render.use_compositing = False
            scene.compositing_node_group = None
            print("PS1 compositing removed (Blender 5.0+)")
    elif hasattr(scene, 'node_tree'):
        scene.use_nodes = False
        if scene.node_tree:
            for node in list(scene.node_tree.nodes):
                scene.node_tree.nodes.remove(node)
        print("PS1 compositing removed (classic)")