import unittest
import bpy

class AddonRegistrationTest(unittest.TestCase):
    """Tests for addon registration and unregistration (no UI required)."""

    ADDON_NAME = "blender_ctr_toolkit"

    def setUp(self):
        # Ensure addon is disabled before each test
        if self.ADDON_NAME in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_disable(module=self.ADDON_NAME)

    def test_addon_enable_without_errors(self):
        """Enable the addon and check basic registration."""
        bpy.ops.preferences.addon_enable(module=self.ADDON_NAME)
        self.assertIn(self.ADDON_NAME, bpy.context.preferences.addons)

        # Check that a known operator exists (by string id)
        self.assertTrue(hasattr(bpy.ops, 'navigator.find_blocks'),
                        "Navigator operator not registered")
        self.assertTrue(hasattr(bpy.ops, 'export_scene.qb_tb_obj'),
                        "Export operator not registered")
        self.assertTrue(hasattr(bpy.ops, 'qb_tb.quick_export'),
                        "Quick export operator not registered")

        # Check that the main panel class is registered
        from blender_ctr_toolkit.ui.ctr_main_panel import CTR_PT_MainPanel
        self.assertTrue(hasattr(bpy.types, CTR_PT_MainPanel.bl_idname),
                        "Main panel not registered")

    def test_addon_disable_without_errors(self):
        """Disable the addon and verify cleanup."""
        bpy.ops.preferences.addon_enable(module=self.ADDON_NAME)
        self.assertIn(self.ADDON_NAME, bpy.context.preferences.addons)

        bpy.ops.preferences.addon_disable(module=self.ADDON_NAME)
        self.assertNotIn(self.ADDON_NAME, bpy.context.preferences.addons)


        # Just check that the addon is not in preferences.
        # No further assertions needed.

    def test_enable_twice_idempotent(self):
        """Enabling twice should not raise errors."""
        bpy.ops.preferences.addon_enable(module=self.ADDON_NAME)
        bpy.ops.preferences.addon_enable(module=self.ADDON_NAME)  # second time
        self.assertIn(self.ADDON_NAME, bpy.context.preferences.addons)

    def test_disable_twice_idempotent(self):
        """Disabling twice should not raise errors."""
        if self.ADDON_NAME in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_disable(module=self.ADDON_NAME)
        bpy.ops.preferences.addon_disable(module=self.ADDON_NAME)  # already disabled
        self.assertNotIn(self.ADDON_NAME, bpy.context.preferences.addons)

if __name__ == "__main__":
    unittest.main(exit=False)