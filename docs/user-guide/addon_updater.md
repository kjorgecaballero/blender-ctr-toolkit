# Addon Updater – User Guide

The **Addon Updater** automatically checks for new versions of the CTR Toolkit and allows you to install updates with a single click. It is integrated into Blender's addon preferences and the CTR panel header.

---

## Accessing Updater Settings

1. Go to **Edit -> Preferences -> Add ons**.
2. Find **Blender CTR Toolkit** in the list.
3. Expand the addon preferences (the triangle next to the name).
4. Scroll to the **Update Settings** section.

---

## Update Settings UI

The preferences panel shows two columns.

### Left Column – Auto check Interval

| Option                          | Description                                         |
| ------------------------------- | --------------------------------------------------- |
| Auto check for Update           | Enable/disable automatic background checks.         |
| Months / Days / Hours / Minutes | How often to check for updates (e.g. every 7 days). |

### Right Column – Status and Info

| Field      | Description                                                                              |
| ---------- | ---------------------------------------------------------------------------------------- |
| Status     | Shows: `Up to date`, `Update available -> x.x.x`, `Checking for updates...`, or `Error`. |
| Last check | Date and time of the most recent update check.                                           |

### Action Buttons (below)

| Button                   | Action                                                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------- |
| Check for Updates        | Manually check immediately.                                                                 |
| Install [version]        | Appears when an update is available – downloads and installs it.                            |
| Ignore                   | Dismiss the current update notification (won't remind again for this version).              |
| Install Specific Version | Opens a dropdown to choose an older release or branch.                                      |
| Restore Backup           | Reverts to a previous version if the update caused issues (available only after an update). |

---

## How the Updater Works

1. **Background checks** – if enabled, the addon quietly checks for updates at the set interval.
2. **Update ready** – the Blender logo button in the CTR panel header turns red.
3. **Click the red button** – opens a popup asking you to:
   - **Update Now** – installs the new version.
   - **Ignore** – stops notifications for this version.
   - **Defer** – reminds you next time you start Blender.
4. **Installation** – the addon downloads the latest ZIP, backs up the current version, replaces files, and prompts you to restart Blender.
5. **Restore** – if something breaks, go to preferences and click **Restore Backup** to revert.

---

## Manual Fallback

If automatic installation fails (e.g. network error or permission issue):

- The updater shows a **Manual Install** dialog.
- Click **Direct download** to get the ZIP file.
- Install it like any other Blender addon (Preferences -> Add ons -> Install...).

---

## Important Notes

- **Restart required** – after an update, restart Blender to fully reload the addon.
- **Backup location** – previous versions are stored in `<addon_folder>_updater/backup`.
- **Fake install** – developers can enable `fake_install` for testing (does not actually change files).
- **Private repositories** – not supported; the updater works only with public GitHub repos.

---

## Troubleshooting

| Issue                               | Solution                                                                        |
| ----------------------------------- | ------------------------------------------------------------------------------- |
| Update button never appears         | Check that auto check is enabled and your internet connection works.            |
| Installation fails with "SSL error" | Your Blender may have outdated certificates – use the manual download link.     |
| Addon disappears after update       | Restart Blender. If still missing, manually re install from the downloaded ZIP. |
| Restore Backup is greyed out        | No backup exists (first update or backup was deleted).                          |
