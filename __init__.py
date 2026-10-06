# =========================================================================
# Copyright (C) 2026 IngeTrazo Contributors / 2026 - Ezequiel M Rezende
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
# =========================================================================

# =========================================================================
# Extension: IGZ Modify 3D — package entry point
# Author: Ezequiel M Rezende
# Version: 1.0.1
# Date: 2026-10-06
# License: GPL-3.0-or-later (same as IngeTrazo)
#
# IngeTrazo — "3D Modifiers" toolbar (Mirror, Scale, Rotate, Align, Array,
# Polar Array).
#
# IngeTrazo loads a plugin package through this __init__.py and calls its
# setup(app). The main module (igz_tb_modify3d.py) is loaded explicitly by
# file path, so this package works whether IngeTrazo imports it as a package
# or as a plain file — the docs warn that plugins must not assume the plugin
# folder is on sys.path nor that they are importable by package name.
# =========================================================================
from __future__ import annotations

import importlib.util
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))

_DEBUG = True


def _log(msg: str) -> None:
    if _DEBUG:
        print(f"[igz_modify3d] {msg}", file=sys.stderr, flush=True)


def _load_main_module():
    """Load ``igz_tb_modify3d.py`` from this package's folder, by path."""
    path = os.path.join(_HERE, "igz_tb_modify3d.py")
    spec = importlib.util.spec_from_file_location("igz_modify3d_main", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


try:
    _MAIN = _load_main_module()
except Exception:
    _MAIN = None
    traceback.print_exc()


def setup(app):
    """Called once by IngeTrazo when the main window is built."""
    if _MAIN is None:
        _log("igz_tb_modify3d could not be loaded; nothing to set up")
        return
    return _MAIN.setup(app)


__all__ = ["setup"]