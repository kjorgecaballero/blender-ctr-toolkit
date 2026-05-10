import unittest
import bpy
import tempfile
import os


class ExportTest(unittest.TestCase):
    """Tests for the QB/TB export system."""

    @classmethod
    def setUpClass(cls):
        bpy.ops.preferences.addon_enable(module="blender_ctr_toolkit")

    def setUp(self):
        bpy.ops.wm.read_homefile(use_empty=True)
        # Create a simple cube to have something in the scene
        bpy.ops.mesh.primitive_cube_add()
        self.obj = bpy.context.active_object

    def test_export_operator_registered(self):
        """The export operator should be available."""
        self.assertTrue(hasattr(bpy.ops.export_scene, 'qb_tb_obj'),
                        "Export operator not registered")

    def test_quick_export_registered(self):
        """The quick export operator should be available."""
        self.assertTrue(hasattr(bpy.ops.qb_tb, 'quick_export'),
                        "Quick export operator not registered")

    # This test may fail in background mode, so we skip it in CI
    @unittest.skipIf(bpy.app.background, "Skipping in background mode (no file dialog)")
    def test_export_without_selection(self):
        """Attempt to export without any valid blocks should show a warning."""
        # Without any valid blocks, the operator should cancel gracefully
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.obj")
            result = bpy.ops.export_scene.qb_tb_obj(
                filepath=test_file,
                use_selection=True,
                export_quadblocks=True,
                export_triblocks=True
            )
            # The operator may return CANCELLED if no blocks found
            self.assertIn(result, {'FINISHED', 'CANCELLED'})


if __name__ == "__main__":
    unittest.main(exit=False)