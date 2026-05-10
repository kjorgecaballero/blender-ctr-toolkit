import unittest
import bpy


class ValidatorTest(unittest.TestCase):
    """Tests for the Validator module (mesh type detection, issues)."""

    @classmethod
    def setUpClass(cls):
        bpy.ops.preferences.addon_enable(module="blender_ctr_toolkit")

    def setUp(self):
        bpy.ops.wm.read_homefile(use_empty=True)

    def test_get_mesh_type_on_cube(self):
        """A simple cube should not be identified as a quadblock or triblock."""
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.active_object
        from blender_ctr_toolkit.utils.qb_tb_validator.qb_tb_analyzer import get_mesh_type
        self.assertIsNone(get_mesh_type(obj), "Cube should return None")

    def test_object_issues_on_cube(self):
        """get_object_issues should return a list (possibly empty)."""
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.active_object
        from blender_ctr_toolkit.utils.qb_tb_validator.qb_tb_analyzer import get_object_issues
        issues = get_object_issues(obj)
        self.assertIsInstance(issues, list)

    def test_range_box_creation(self):
        """The range box operator should add an empty named 'Range'."""
        bpy.ops.ctr.add_range_box()
        self.assertIn("Range", bpy.data.objects, "Range box not created")
        range_obj = bpy.data.objects["Range"]
        self.assertEqual(range_obj.type, 'EMPTY')


if __name__ == "__main__":
    unittest.main(exit=False)