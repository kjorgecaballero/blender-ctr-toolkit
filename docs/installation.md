# Installation

This guide explains how to install the **Blender CTR Toolkit** addon.

---

## Requirements

- **Blender 3.3 or newer** (the addon is tested on versions 3.3, 3.4, 3.5, 3.6, 4.0, 4.2, 4.5, and 5.0)
- Windows, macOS, or Linux (all platforms supported by Blender)

---

## Download the Addon

1. Go to the [CTR Toolkit GitHub repository](https://github.com/kjorgecaballero/blender-ctr-toolkit).
2. Click on **Releases** (right sidebar) or go to [Releases page](https://github.com/kjorgecaballero/blender-ctr-toolkit/releases).
3. Download the latest `Source code (zip)` file (e.g., `blender-ctr-toolkit-0.0.1.zip`).

> Do **not** extract the zip file – Blender can install it directly.

---

## Install in Blender

1. Open Blender.
2. Go to **Edit → Preferences** (or **Blender Preferences** on macOS).
3. Select the **Add‑ons** tab.
4. Click the **Install…** button (top right).
5. In the file browser, select the downloaded `.zip` file and click **Install Add‑on**.
6. After installation, the addon appears in the list. Tick the checkbox next to **Blender CTR Toolkit** to enable it.

---

## Verify Installation

- In the 3D Viewport, press `N` to open the sidebar.
- Click the **CTR** tab.
- You should see the **Navigator**, **Validator**, and **Render** options.

If the tab is missing, try restarting Blender or check the System Console for error messages (Window → Toggle System Console on Windows).

---

## Updating the Addon

The addon includes an **automatic updater**. There are three ways to update:

### 1. From Addon Preferences (Recommended)

- Go to **Edit → Preferences → Add‑ons → Blender CTR Toolkit**.
- Expand the addon preferences (click the triangle next to the name).
- In the **Update Settings** section, enable **Auto‑check for Update**.
- The addon will check periodically. When an update is available, you will see a button to install it.
- You can also click **Check for Updates** manually.

### 2. From the CTR Panel Header

- In the 3D Viewport sidebar (CTR tab), look at the top right corner of the panel.
- Click the **Blender logo button** (it turns **red** when an update is ready).
- A popup will appear asking you to install, ignore, or defer the update.

### 3. Manual Update

- Download the latest release manually from the [GitHub Releases page](https://github.com/kjorgecaballero/blender-ctr-toolkit/releases).
- Repeat the installation steps (the old version will be replaced automatically).

After installing via any method, **restart Blender** to complete the update.

---

## Troubleshooting

| Issue                         | Solution                                                                                     |
| ----------------------------- | -------------------------------------------------------------------------------------------- |
| Addon does not appear in list | Make sure you installed the `.zip` file, not the extracted folder. Try restarting Blender.   |
| Error after enabling          | Check the System Console (Window → Toggle System Console) for error messages.                |
| Shortcuts not working         | Go to **Edit → Preferences → Keymap**, search for `qb_tb.quick_export`, and verify the keys. |

---

## Next Steps

- Read the [User Guide](./user-guide/index.md) for detailed module documentation.
