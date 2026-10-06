# =========================================================================
# Copyright (C) 2026 IngeTrazo Contributors / 2026 - Ezequiel M Rezende
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# =========================================================================

# =========================================================================
# Extension: igz_xform_command — undo-aware in-place transform / removal
# Author: Ezequiel M Rezende
# Version: 1.0.1
# License: GPL-3.0-or-later (same as IngeTrazo)
#
# SnapshotImport only tracks additions (loose mesh + groups appended to
# scene.groups). It cannot undo:
#   * in-place mutation of g.xform / g.mesh / g.axes
#   * removal of a group from scene.groups
#
# XformGroupsCommand stores, for every group it touches, the exact
# pre-state (xform, mesh, axes) and/or the index it occupied in
# scene.groups, and restores all of it on undo().
# =========================================================================
from __future__ import annotations

import copy
from typing import Callable, Iterable, List, Optional, Tuple

from PySide6.QtGui import QMatrix4x4

from core.group import Group, transformed_mesh

class CompositeCommand:
    """Executa comandos em ordem em do(); desfaz em ordem inversa."""

    def __init__(self, *commands, label: str = "Composite"):
        self._commands = list(commands)
        self.label = label

    def do(self, scene) -> None:
        applied = []
        try:
            for c in self._commands:
                c.do(scene)
                applied.append(c)
        except Exception:
            # Reverte o que já foi aplicado para não deixar estado sujo.
            for c in reversed(applied):
                try:
                    c.undo(scene)
                except Exception:
                    pass
            raise

    def undo(self, scene) -> None:
        for c in reversed(self._commands):
            try:
                c.undo(scene)
            except Exception:
                import traceback
                traceback.print_exc()

class XformGroupsCommand:
    """Undoable in-place transform (and optional removal) of groups.

    Parameters
    ----------
    transform:
        ``f(group) -> None``. Called in ``do()`` for every group in
        ``groups``. Must mutate the group **in place** (xform / mesh /
        axes). It is *not* called on undo; undo restores the captured
        pre-state instead.
    groups:
        Iterable of ``Group`` instances to transform.
    remove_after:
        If True, the groups are removed from ``scene.groups`` after
        being transformed, and restored at their original index on
        undo. This is what Mirror-with-delete needs.
    label:
        Optional human-readable name for history UI.
    """

    def __init__(
        self,
        transform: Callable[[Group], None],
        groups: Iterable[Group],
        remove_after: bool = False,
        label: str = "Transform groups",
    ) -> None:
        self._transform = transform
        self._groups: List[Group] = list(groups)
        self._remove_after = bool(remove_after)
        self.label = label

        # Pre-state captured on first do() (or on construction, so a
        # command instance can safely be constructed before execute).
        self._states: List[Tuple[Group, Optional[QMatrix4x4], object, object]] = []
        self._removed_indices: List[Tuple[Group, int]] = []
        self._scene = None

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    def _capture(self) -> None:
        self._states = []
        for g in self._groups:
            old_xform = QMatrix4x4(g.xform) if g.xform is not None else None
            old_mesh = copy.deepcopy(g.mesh) if g.xform is None else None
            old_axes = None
            if getattr(g, "axes", None) is not None and g.xform is None:
                old_axes = QMatrix4x4(g.axes)
            self._states.append((g, old_xform, old_mesh, old_axes))

    def _restore(self) -> None:
        for g, old_xform, old_mesh, old_axes in self._states:
            if old_xform is not None:
                g.xform = QMatrix4x4(old_xform)
            else:
                g.xform = None
                if old_mesh is not None:
                    g.mesh = copy.deepcopy(old_mesh)
                if old_axes is not None:
                    g.axes = QMatrix4x4(old_axes)

    # ------------------------------------------------------------------ #
    # Command API
    # ------------------------------------------------------------------ #
    def do(self, scene) -> None:
        self._scene = scene
        if not self._states:
            self._capture()

        # If this is a redo, groups may have been re-inserted by undo().
        # Ensure they are present in the scene before transforming.
        for g, _, _, _ in self._states:
            if g not in scene.groups:
                scene.groups.append(g)

        for g in self._groups:
            self._transform(g)

        if self._remove_after:
            self._removed_indices = []
            for g in self._groups:
                try:
                    idx = scene.groups.index(g)
                except ValueError:
                    continue
                self._removed_indices.append((g, idx))
                scene.groups.remove(g)

    def undo(self, scene) -> None:
        # Re-insert removed groups at their original index (ascending)
        for g, idx in sorted(self._removed_indices, key=lambda t: t[1]):
            if g not in scene.groups:
                idx = min(idx, len(scene.groups))
                scene.groups.insert(idx, g)

        # Restore in-place mutations
        self._restore()


__all__ = ["XformGroupsCommand", "CompositeCommand"]