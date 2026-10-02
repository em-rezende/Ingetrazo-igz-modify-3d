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
# Extension: igz_scale3d (Subpasta modify3d)
# =========================================================================
from __future__ import annotations

import copy
import os
import sys
import traceback

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QMatrix4x4, QVector3D, QPen, QColor
from PySide6.QtWidgets import QMessageBox, QToolBar, QSizePolicy

from tools.base import Tool, ToolContext
from core.group import Group, transformed_mesh
from core.mesh import Face, Edge
from core.history import SnapshotImport

DEBUG = True

def _log(s):
    if DEBUG:
        print(f"[igz_scale3d] {s}", file=sys.stderr, flush=True)

try:
    from core.i18n import tr, current_language
except Exception:
    def tr(s, **kw):
        return s.format(**kw) if kw else s
    def current_language():
        return "en"

_LOCAL = {
    "pt-BR": {
        "Scale 3D": "Escalar 3D",
        "Scale by 3 Points": "Escalar por 3 Pontos",
        "Select objects before starting Scale 3D.": "Selecione os objetos antes de iniciar a Escala 3D.",
        "Scale 3D — click base point (P1)": "Escalar 3D — clique no ponto base (P1)",
        "P1 captured — click reference point (P2)": "P1 capturado — clique no ponto de referência (P2)",
        "P2 captured — move and click target point (P3)": "P2 capturado — mova e clique no ponto de destino (P3)",
        "Points must not coincide.": "Os pontos não podem coincidir.",
        "Scale completed.": "Escala concluída."
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

def _scale_matrix(p1, p2, p3):
    v1 = QVector3D(p2) - QVector3D(p1)
    v2 = QVector3D(p3) - QVector3D(p1)
    l1 = v1.length()
    l2 = v2.length()
    if l1 <= _EPS or l2 <= _EPS:
        return None
    s = l2 / l1
    m = QMatrix4x4()
    m.translate(p1)
    m.scale(s, s, s)
    m.translate(-p1)
    return m

class Scale3dTool(Tool):
    name = "Scale by 3 Points"
    shortcut = None
    description = "Scale the selected objects using three reference points with bounding box preview."
    uses_snap = True
    wireframe_color = (0.08, 0.47, 0.84, 0.95)
    wireframe_depth_tested = False
    _instance = None

    def __init__(self):
        Scale3dTool._instance = self
        self.points = []
        self.selection = set()
        self.current_mouse_pos = None
        self.bbox_min = None
        self.bbox_max = None

    def on_activate(self, vp):
        self.points = []
        self.current_mouse_pos = None
        self.bbox_min = None
        self.bbox_max = None
        self.selection = set(getattr(vp.scene, "selection", set()))
        if not self.selection:
            vp.flash_status(_t("Select objects before starting Scale 3D."), 4000)
            vp.set_active_tool(None)
            return
        vp.flash_status(_t("Scale 3D — click base point (P1)"), 5000)
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
        self.bbox_max = None
        vp.flash_status("", 0)

    def on_hover(self, ctx: ToolContext):
        if len(self.points) == 2:
            self.current_mouse_pos = QVector3D(ctx.world)

    def on_click(self, ctx: ToolContext):
        self.points.append(QVector3D(ctx.world))
        vp = ctx.viewport
        if len(self.points) == 1:
            vp.flash_status(_t("P1 captured — click reference point (P2)"), 5000)
            return
        if len(self.points) == 2:
            try:
                self.bbox_min, self.bbox_max = vp.scene.selection_bounds()
            except Exception as exc:
                self.bbox_min, self.bbox_max = None, None
                _log(f"selection_bounds() failed: {exc}")

            self.current_mouse_pos = QVector3D(self.points[1])
            vp.update()
            vp.flash_status(_t("P2 captured — move and click target point (P3)"), 5000)
            _log(f"bbox={self.bbox_min} -> {self.bbox_max}")
            return
        
        self.current_mouse_pos = None
        m = _scale_matrix(*self.points)
        if m is None:
            vp.flash_status(_t("Points must not coincide."), 4000)
            self.points = []
            vp.flash_status(_t("Scale 3D — click base point (P1)"), 5000)
            return
        self._finish(vp, m)

    def rubber_band_lines(self):
        if (len(self.points) != 2 or self.current_mouse_pos is None
                or self.bbox_min is None or self.bbox_max is None):
            return []

        try:
            m = _scale_matrix(self.points[0], self.points[1],
                              self.current_mouse_pos)
            if m is None:
                return []

            lo = QVector3D(self.bbox_min)
            hi = QVector3D(self.bbox_max)
            corners = [
                QVector3D(lo.x(), lo.y(), lo.z()),
                QVector3D(hi.x(), lo.y(), lo.z()),
                QVector3D(hi.x(), hi.y(), lo.z()),
                QVector3D(lo.x(), hi.y(), lo.z()),
                QVector3D(lo.x(), lo.y(), hi.z()),
                QVector3D(hi.x(), lo.y(), hi.z()),
                QVector3D(hi.x(), hi.y(), hi.z()),
                QVector3D(lo.x(), hi.y(), hi.z()),
            ]
            corners = [m.map(p) for p in corners]

            edges = (
                (0, 1), (1, 2), (2, 3), (3, 0),
                (4, 5), (5, 6), (6, 7), (7, 4),
                (0, 4), (1, 5), (2, 6), (3, 7),
            )
            lines = [(corners[i], corners[j]) for i, j in edges]

            lines.append((QVector3D(self.points[0]),
                          QVector3D(self.points[1])))
            lines.append((QVector3D(self.points[0]),
                          QVector3D(self.current_mouse_pos)))
            return lines
        except Exception:
            traceback.print_exc()
            return []

    def _finish(self, vp, m):
        selected = set(self.selection)
        def mutate(scene):
            for x in selected:
                if isinstance(x, Group):
                    if x.xform is not None:
                        x.xform = QMatrix4x4(m) * x.xform
                    else:
                        x.mesh = transformed_mesh(x.mesh, m)
                        if getattr(x, "axes", None) is not None:
                            x.axes = QMatrix4x4(m) * x.axes
            scene.selection.clear()

        try:
            vp.history.execute(SnapshotImport(mutate))
            if vp.history.last_error:
                vp.flash_status(f"Scale failed: {vp.history.last_error}", 6000)
                _log(vp.history.last_error)
            else:
                vp.notify_scene_changed()
                vp.update()
                vp.flash_status(_t("Scale completed."), 3000)
        except Exception:
            traceback.print_exc()
            vp.flash_status("Scale failed — see the IngeTrazo log.", 6000)
        finally:
            self.points = []
            self.current_mouse_pos = None
            self.bbox_min = None
            self.bbox_max = None
            try:
                from tools.select import SelectTool
                vp.set_active_tool(SelectTool())
            except Exception:
                vp.set_active_tool(None)

def setup(app):
    pass

__all__ = ["Scale3dTool", "setup"]