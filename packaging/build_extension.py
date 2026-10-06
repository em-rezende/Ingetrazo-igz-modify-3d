#!/usr/bin/env python3
# =========================================================================
# Copyright (C) 2026 Ezequiel M Rezende
# License: GPL-3.0-or-later (same as IngeTrazo)
# =========================================================================
# Build the distributable ``igz_modify3d.zip`` for the IngeTrazo extension
# catalog (https://github.com/ingelibre/ingetrazo-extensions).
#
# The catalog installs ONE file per entry: a .py file, or a .zip holding a
# single folder with an __init__.py (see TEMPLATE.toml in that repository).
# This plugin is a package (a root __init__.py plus the igz_*.py modules and
# the icons/ folder), so it needs the zip form.
#
# The archive is built deterministically on purpose: fixed timestamps,
# sorted entries and a fixed create-system, so its SHA-256 changes ONLY when
# the content changes. That is what lets the catalog fingerprint (``sha256``
# in ``extensions/<id>.toml``) be verified and reproduced.
#
# Usage:
#     python packaging/build_extension.py
#
# Output:
#     dist/igz_modify3d.zip
#     dist/igz_modify3d.zip.sha256
# =========================================================================
from __future__ import annotations

import hashlib
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "dist")

#: Single top-level folder inside the zip (required by the catalog).
PACKAGE = "igz_modify3d"
ZIP_NAME = f"{PACKAGE}.zip"

#: Fixed files copied from the repository root into the package folder.
ROOT_FILES = ["__init__.py", "LICENSE", "README.md"]

#: Folder copied recursively (SVG icon assets).
ICONS_DIR = "icons"

#: Fixed timestamp so the archive is byte-for-byte reproducible.
FIXED_DATE = (2026, 1, 1, 0, 0, 0)


def read_version() -> str:
    """Read the version from the module header, so it never drifts."""
    with open(os.path.join(ROOT, "igz_tb_modify3d.py"), encoding="utf-8") as fh:
        for line in fh:
            match = re.match(r"#\s*Version:\s*(\S+)", line)
            if match:
                return match.group(1)
    return "0.0.0"


def _read(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def collect_entries() -> list[tuple[str, bytes]]:
    """Return ``(arcname, data)`` for every file, sorted by name."""
    entries: list[tuple[str, bytes]] = []

    for name in ROOT_FILES:
        path = os.path.join(ROOT, name)
        if os.path.isfile(path):
            entries.append((f"{PACKAGE}/{name}", _read(path)))

    # Every igz_*.py module at the repository root (loader + tools).
    for name in sorted(os.listdir(ROOT)):
        if name.startswith("igz_") and name.endswith(".py"):
            path = os.path.join(ROOT, name)
            if os.path.isfile(path):
                entries.append((f"{PACKAGE}/{name}", _read(path)))

    # The icons/ folder (SVG assets), recursively.
    icons = os.path.join(ROOT, ICONS_DIR)
    for base, _dirs, files in os.walk(icons):
        if "__pycache__" in base:
            continue
        for name in files:
            path = os.path.join(base, name)
            rel = os.path.relpath(path, icons).replace(os.sep, "/")
            entries.append((f"{PACKAGE}/{ICONS_DIR}/{rel}", _read(path)))

    entries.sort(key=lambda item: item[0])
    return entries


def build() -> str:
    os.makedirs(DIST, exist_ok=True)
    out_zip = os.path.join(DIST, ZIP_NAME)

    with zipfile.ZipFile(out_zip, "w") as zf:
        for arcname, data in collect_entries():
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3          # 3 = Unix: stable across OSes
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)

    digest = hashlib.sha256(_read(out_zip)).hexdigest()

    with open(out_zip + ".sha256", "w", encoding="ascii") as fh:
        fh.write(f"{digest}  {ZIP_NAME}\n")

    return digest


def main() -> None:
    version = read_version()
    digest = build()
    print(f"igz_modify3d {version}")
    print(f"  dist/{ZIP_NAME}")
    print(f"  sha256 = \"{digest}\"")
    print("")
    print("  Paste that sha256 into extensions/igz_modify3d.toml and upload")
    print(f"  dist/{ZIP_NAME} to the GitHub Release of the tag in `download`.")


if __name__ == "__main__":
    main()
