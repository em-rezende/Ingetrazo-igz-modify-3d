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
# Extension: igz_array3d (Subpasta modify3d)
# =========================================================================
from __future__ import annotations

import copy
import os
import sys
import traceback

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QMatrix4x4, QVector3D, QPen, QColor
from PySide6.QtWidgets import QMessageBox, QToolBar, QSizePolicy, QInputDialog

from tools.base import Tool, ToolContext
from core.group import Group, transformed_mesh
from core.mesh import Face, Edge
from core.history import SnapshotImport

DEBUG = True

def _log(s):
    if DEBUG:
        print(f"[igz_array3d] {s}", file=sys.stderr, flush=True)

try:
    from core.i18n import tr, current_language
except Exception:
    def tr(s, **kw):
        return s.format(**kw) if kw else s
    def current_language():
        return "en"

_LOCAL = {
    "pt-BR": {
        "Array 3D": "Matriz 3D (Array)",
        "Array by 2 Points": "Matriz por 2 Pontos",
        "Select objects before starting Array 3D.": "Selecione os objetos antes de iniciar a Matriz 3D.",
        "Array 3D — click base point (P1)": "Matriz 3D — clique no ponto base (P1)",
        "P1 captured — click step offset point (P2)": "P1 capturado — clique no ponto de espaçamento (P2)",
        "Points must not coincide.": "Os pontos não podem coincidir.",
        "Number of copies:": "Número de cópias:",
        "Array completed.": "Matriz concluída."
    }
}

def _t(s):
    try:
        x = tr(s)
        if x != s:
            return x
    except Exception:
        pass
    return _LOCAL.get(current_language(), {}).get(s, s)

_EPS = 1e-8

class Array3dTool(Tool):
    name = "Array by 2 Points"
    shortcut = None
    description = "Create multiple copies of selected objects using a base point and an offset vector with preview."
    uses_snap = True
    _instance = None

    def __init__(self):
        Array3dTool._instance = self
        self.points = []
        self.selection = set()
        self.current_mouse_pos = None
        self.bbox_min = None
        self.bbox_max = None
        self.copies_count = 3

    def on_activate(self, vp):
        self.points = []
        self.current_mouse_pos = None
        self.bbox_min = None
        self.bbox_max = None
        self.selection = set(getattr(vp.scene, "selection", set()))
        if not self.selection:
            vp.flash_status(_t("Select objects before starting Array 3D."), 4000)
            vp.set_active_tool(None)
            return
        vp.flash_status(_t("Array 3D — click base point (P1)"), 5000)
        _log(f"selection={len(self.selection)}")

    def on_deactivate(self, vp):
        self.points = []
        self.current_mouse_pos = None
        self.bbox_min = None
        self.bbox_max = None

    def on_cancel(self, vp):
        self.points = []
        self.current_mouse_pos = None
        self.bbox_min = None
        vp.flash_status("", 0)

    def on_hover(self, ctx: ToolContext):
        if len(self.points) == 1:
            self.current_mouse_pos = QVector3D(ctx.world)

    def on_click(self, ctx: ToolContext):
        self.points.append(QVector3D(ctx.world))
        vp = ctx.viewport
        
        if len(self.points) == 1:
            try:
                self.bbox_min, self.bbox_max = vp.scene.selection_bounds()
            except Exception as exc:
                self.bbox_min, self.bbox_max = None, None
                _log(f"selection_bounds() failed: {exc}")

            vp.flash_status(_t("P1 captured — click step offset point (P2)"), 5000)
            return
        
        # P2 capturado: Temos o vetor de passo completo (P1 -> P2)
        self.current_mouse_pos = None
        p1, p2 = self.points[0], self.points[1]
        v_step = p2 - p1

        if v_step.length() <= _EPS:
            vp.flash_status(_t("Points must not coincide."), 4000)
            self.points = []
            vp.flash_status(_t("Array 3D — click base point (P1)"), 5000)
            return

        # Pergunta o número de cópias
        val, ok = QInputDialog.getInt(vp.window(), _t("Array 3D"), _t("Number of copies:"), self.copies_count, 1, 100, 1)
        if not ok:
            self.points = []
            vp.set_active_tool(None)
            return
        
        self.copies_count = val
        self._finish(vp, v_step, self.copies_count)

    def rubber_band_lines(self):
        if (len(self.points) != 1 or self.current_mouse_pos is None
                or self.bbox_min is None or self.bbox_max is None):
            return []

        try:
            p1 = QVector3D(self.points[0])
            p2 = QVector3D(self.current_mouse_pos)
            v_step = p2 - p1
            
            if v_step.length() <= _EPS:
                return []

            lines = []
            lo = QVector3D(self.bbox_min)
            hi = QVector3D(self.bbox_max)
            
            corners = [
                QVector3D(lo.x(), lo.y(), lo.z()), QVector3D(hi.x(), lo.y(), lo.z()),
                QVector3D(hi.x(), hi.y(), lo.z()), QVector3D(lo.x(), hi.y(), lo.z()),
                QVector3D(lo.x(), lo.y(), hi.z()), QVector3D(hi.x(), lo.y(), hi.z()),
                QVector3D(hi.x(), hi.y(), hi.z()), QVector3D(lo.x(), hi.y(), hi.z()),
            ]
            edges = (
                (0, 1), (1, 2), (2, 3), (3, 0),
                (4, 5), (5, 6), (6, 7), (7, 4),
                (0, 4), (1, 5), (2, 6), (3, 7),
            )

            # Preview em tempo real simulando 3 cópias enquanto arrasta o mouse
            for i in range(1, 4):
                translation = v_step * i
                m = QMatrix4x4()
                m.translate(translation)
                
                transformed_corners = [m.map(c) for c in corners]
                for edge_a, edge_b in edges:
                    lines.append((transformed_corners[edge_a], transformed_corners[edge_b]))

            lines.append((p1, p2))
            return lines
        except Exception:
            traceback.print_exc()
            return []

    def _finish(self, vp, v_step, count):
        selected = set(self.selection)
        
        def mutate(scene):
            for i in range(1, count + 1):
                translation = v_step * i
                m = QMatrix4x4()
                m.translate(translation)

                for x in selected:
                    if isinstance(x, Group):
                        new_g = copy.deepcopy(x)
                        new_g.name = f"{x.name} (Array {i})"
                        if new_g.xform is not None:
                            new_g.xform = m * new_g.xform
                        else:
                            new_g.mesh = transformed_mesh(new_g.mesh, m)
                            if getattr(new_g, "axes", None) is not None:
                                new_g.axes = m * new_g.axes
                        scene.groups.append(new_g)
            scene.selection.clear()

        try:
            vp.history.execute(SnapshotImport(mutate))
            if vp.history.last_error:
                vp.flash_status(f"Array failed: {vp.history.last_error}", 6000)
                _log(vp.history.last_error)
            else:
                vp.notify_scene_changed()
                vp.update()
                vp.flash_status(_t("Array completed."), 3000)
        except Exception:
            traceback.print_exc()
            vp.flash_status("Array failed — see the IngeTrazo log.", 6000)
        finally:
            self.points = []
            self.current_mouse_pos = None
            try:
                from tools.select import SelectTool
                vp.set_active_tool(SelectTool())
            except Exception:
                vp.set_active_tool(None)

def setup(app):
    pass

__all__ = ["Array3dTool", "setup"]