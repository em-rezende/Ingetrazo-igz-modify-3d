# Submission bundle — IngeTrazo extension catalog

> **Not published yet.** Nothing here has been sent anywhere; these are the
> files to copy into a pull request of
> <https://github.com/ingelibre/ingetrazo-extensions> once you authorise it.

Copy these two things into the catalog repository:

| From here | To the catalog repository |
|---|---|
| `extensions/igz_modify3d.toml` | `extensions/igz_modify3d.toml` |
| `screenshots/igz_modify3d.png` | `screenshots/igz_modify3d.png` |

Then open the pull request (browser: *Add file ▸ Create new file* and *Add
file ▸ Upload files* → **Propose changes** → **Create pull request**) and fill
in the template checklist.

## Before you submit

- The `download` URL points at the **v1.0.0** GitHub Release asset
  `igz_modify3d.zip`, so create that tag/release in this repository first and
  upload `dist/igz_modify3d.zip` as the asset with that exact name.
- The `sha256` in the entry must match that asset byte-for-byte:
  `3709d0db78e49ebef96336bdaea2ef2ec83442a8432fe05ca229103765287c9f`.
  Rebuild with `packaging/build_extension.ps1` (or
  `packaging/build_extension.py`) if the code changed, and paste the value it
  prints. (If it is wrong, the catalog's automatic check tells you the right
  one.)

Full, step-by-step instructions are in [`../PUBLISHING.md`](../PUBLISHING.md).
