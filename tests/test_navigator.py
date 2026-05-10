import unittest
import bpy
import bmesh


class NavigatorTest(unittest.TestCase):
    """Tests for the Navigator module (quadblock/triblock detection)."""

    def setUp(self):
        """Start with a fresh scene and a simple cube."""
        bpy.ops.wm.read_homefile(use_empty=True)
        bpy.ops.mesh.primitive_cube_add()
        self.obj = bpy.context.active_object
        self.obj.name = "TestCube"

    def test_quadblock_center_detection(self):
        """A plain cube should have no quadblock centers."""
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(self.obj.data)
        from blender_ctr_toolkit.utils.qb_tb_navigator import is_quadblock_center
        for vert in bm.verts:
            self.assertFalse(is_quadblock_center(vert),
                             f"Vertex {vert.index} should not be a quadblock center")
        bpy.ops.object.mode_set(mode='OBJECT')

    def test_find_blocks_operator(self):
        """The find_blocks operator should not crash on a non‑block mesh."""
        bpy.ops.object.mode_set(mode='EDIT')
        result = bpy.ops.navigator.find_blocks()
        self.assertIn('CANCELLED', result)
        bpy.ops.object.mode_set(mode='OBJECT')

    def test_clear_cache_operator(self):
        """The clear_cache operator should run without errors."""
        bpy.ops.object.mode_set(mode='EDIT')
        result = bpy.ops.navigator.clear_block_cache()
        self.assertIn('FINISHED', result)
        bpy.ops.object.mode_set(mode='OBJECT')