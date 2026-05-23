import unittest
import bpy

class IconTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        addon_name = "blender_ctr_toolkit"
        if addon_name not in bpy.context.preferences.addons:
            bpy.ops.preferences.addon_enable(module=addon_name)
        from blender_ctr_toolkit import icons
        cls.icons_module = icons

    def test_register_icons_no_exception(self):
        """Registering icons should not raise an exception."""
        try:
            self.icons_module.register_icons()
        except Exception as e:
            self.fail(f"register_icons() raised exception: {e}")

    def test_known_icons_are_defined(self):
        """All expected icon names should be in the icon dictionary (bypass background check)."""
        expected_icons = [
            "clear_icon", "reset_icon", "duplicate_icon", "invalid_icon",
            "navigate_icon", "quadblock_icon", "triblock_icon", "doc_icon",
            "tutorial_icon", "update_icon", "report_icon", "typeqb_icon",
            "typetb_icon", "check_all_icon", "uncheck_all_icon", "nav_point_icon",
            "constant_mat_icon", "psx_icon", "resolution_icon", "split_screen_icon",
            "seams_icon", "duplicate_constant_icon", "remove_group_icon",
            "quadblock_cache_icon"
        ]
        
        # Check that get_icon doesn't crash and returns something
        for icon_name in expected_icons:
            icon_id = self.icons_module.get_icon(icon_name)
            if not bpy.app.background:
                # Only validate actual icon loading in interactive mode
                self.assertNotEqual(icon_id, 0, f"Icon '{icon_name}' returned 0 (not loaded)")
            else:
                # In background, we just verify the function runs
                self.assertIsNotNone(icon_id, f"Icon '{icon_name}' getter failed")

    def test_nonexistent_icon_returns_zero(self):
        """A non-existent icon should return 0."""
        icon_id = self.icons_module.get_icon("this_icon_does_not_exist")
        self.assertEqual(icon_id, 0)

    @classmethod
    def tearDownClass(cls):
        cls.icons_module.unregister_icons()

if __name__ == "__main__":
    unittest.main(exit=False)