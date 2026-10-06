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

- The `download` URL points at the **v1.0.1** GitHub Release asset
  `igz_modify3d.zip`, so create that tag/release in this repository first and
  upload `dist/igz_modify3d.zip` as the asset with that exact name.
- The `sha256` in the entry must match that asset byte-for-byte:
  `7ae197f031c258e61db197dcdf2d83f74a52f597509e8e679614d6d432e6adf1`.
  Rebuild with `packaging/build_extension.ps1` (or
  `packaging/build_extension.py`) if the code changed, and paste the value it
  prints. (If it is wrong, the catalog's automatic check tells you the right
  one.)

Full, step-by-step instructions are in [`../PUBLISHING.md`](../PUBLISHING.md).

## Update for the existing pull request (#41)

This submission is now **v1.0.1**, which fixes the undo problem raised in the
review of <https://github.com/ingelibre/ingetrazo-extensions/pull/41>: **Ctrl+Z**
now fully reverts **Scale**, **Rotate**, **Align** and **Mirror with
delete-the-originals** (the in-place / removal tools now commit an undo-aware
`XformGroupsCommand`). To refresh the open PR:

1. Replace `extensions/igz_modify3d.toml` with the file in this bundle (it already
   points at `v1.0.1` with the new `sha256`).
2. Re-upload `screenshots/igz_modify3d.png` (unchanged location).
3. Reply on the PR, for example:

   > Undo/redo is fixed in **v1.0.1**. Scale, Rotate, Align and
   > Mirror-with-delete now restore the exact previous state on Ctrl+Z, and the
   > mirrored originals come back. The entry now points at the `v1.0.1` release
   > asset — `sha256`
   > `7ae197f031c258e61db197dcdf2d83f74a52f597509e8e679614d6d432e6adf1`.
