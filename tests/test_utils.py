import unittest
import bpy
from blender_ctr_toolkit.utils import compat

class CompatibilityTest(unittest.TestCase):
    def test_get_blender_version(self):
        version = compat.get_blender_version()
        self.assertIsInstance(version, tuple)
        self.assertGreaterEqual(len(version), 3)

    def test_should_use_wm_obj_export(self):
        result = compat.should_use_wm_obj_export()
        self.assertIsInstance(result, bool)