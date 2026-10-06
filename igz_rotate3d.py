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
# Extension: igz_rotate3d
# Author: Ezequiel M Rezende
# Version: 1.0.1
# License: GPL-3.0-or-later (same as IngeTrazo)
# =========================================================================
from __future__ import annotations

import copy
import os
import sys
import traceback
import math

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QMatrix4x4, QVector3D, QPen, QColor
from PySide6.QtWidgets import QMessageBox, QToolBar, QSizePolicy

from tools.base import Tool, ToolContext
from core.group import Group, transformed_mesh
from core.mesh import Face, Edge
from igz_xform_command import XformGroupsCommand

DEBUG = True

def _log(s):
    if DEBUG:
        print(f"[igz_rotate3d] {s}", file=sys.stderr, flush=True)

try:
    from core.i18n import tr, current_language
except Exception:
    def tr(s, **kw):
        return s.format(**kw) if kw else s
    def current_language():
        return "en"

_LOCAL = {
    "pt-BR": {
        "Rotate 3D": "Rotacionar 3D",
        "Rotate by 3 Points": "Rotacionar por 3 Pontos",
        "Select objects before starting Rotate 3D.": "Selecione os objetos antes de iniciar a Rotação 3D.",
        "Rotate 3D — click rotation center (P1)": "Rotacionar 3D — clique no centro de rotação (P1)",
        "P1 captured — click reference point (P2)": "P1 capturado — clique no ponto de referência (P2)",
        "P2 captured — move and click target angle point (P3)": "P2 capturado — mova e clique no ponto de ângulo de destino (P3)",
        "Points are collinear or coincide.": "Os pontos são colineares ou coincidem.",
        "Rotation completed.": "Rotação concluída."
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

def _rotation_matrix(p1, p2, p3):
    v1 = QVector3D(p2) - QVector3D(p1)
    v2 = QVector3D(p3) - QVector3D(p1)
    
    l1 = v1.length()
    l2 = v2.length()
    if l1 <= _EPS or l2 <= _EPS:
        return None

    v1.normalize()
    v2.normalize()

    axis = QVector3D.crossProduct(v1, v2)
    axis_len = axis.length()
    if axis_len <= _EPS:
        dot = QVector3D.dotProduct(v1, v2)
        if dot < 0:
            arbitrary = QVector3D(1, 0, 0)
            if abs(QVector3D.dotProduct(v1, arbitrary)) > 0.9:
                arbitrary = QVector3D(0, 1, 0)
            axis = QVector3D.crossProduct(v1, arbitrary)
            axis.normalize()
            m = QMatrix4x4()
            m.translate(p1)
            m.rotate(180.0, axis)
            m.translate(-p1)
            return m
        return QMatrix4x4()

    axis.normalize()
    dot = max(-1.0, min(1.0, QVector3D.dotProduct(v1, v2)))
    angle_rad = math.acos(dot)
    angle_deg = math.degrees(angle_rad)

    m = QMatrix4x4()
    m.translate(p1)
    m.rotate(angle_deg, axis)
    m.translate(-p1)
    return m

class Rotate3dTool(Tool):
    name = "Rotate by 3 Points"
    shortcut = None
    description = "Rotate the selected objects using three reference points with bounding box preview."
    uses_snap = True
    wireframe_color = (1.0, 0.65, 0.0, 0.95)  # laranja
    wireframe_depth_tested = False
    _instance = None

    def __init__(self):
        Rotate3dTool._instance = self
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
            vp.flash_status(_t("Select objects before starting Rotate 3D."), 4000)
            vp.set_active_tool(None)
            return
        vp.flash_status(_t("Rotate 3D — click rotation center (P1)"), 5000)
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
            vp.flash_status(_t("P2 captured — move and click target angle point (P3)"), 5000)
            return
        
        self.current_mouse_pos = None
        m = _rotation_matrix(*self.points)
        if m is None:
            vp.flash_status(_t("Points are collinear or coincide."), 4000)
            self.points = []
            vp.flash_status(_t("Rotate 3D — click rotation center (P1)"), 5000)
            return
        self._finish(vp, m)

    def rubber_band_lines(self):
        if (len(self.points) != 2 or self.current_mouse_pos is None
                or self.bbox_min is None or self.bbox_max is None):
            return []

        try:
            m = _rotation_matrix(self.points[0], self.points[1],
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
        selected = [x for x in self.selection if isinstance(x, Group)]

        def apply_transform(g: Group) -> None:
            if g.xform is not None:
                g.xform = QMatrix4x4(m) * g.xform
            else:
                g.mesh = transformed_mesh(g.mesh, m)
                if getattr(g, "axes", None) is not None:
                    g.axes = QMatrix4x4(m) * g.axes

        cmd = XformGroupsCommand(
            apply_transform, selected, label=_t("Rotate 3D")
        )

        try:
            vp.history.execute(cmd)
            if vp.history.last_error:
                vp.flash_status(f"Rotation failed: {vp.history.last_error}", 6000)
                _log(vp.history.last_error)
            else:
                vp.scene.selection.clear()
                vp.notify_scene_changed()
                vp.update()
                vp.flash_status(_t("Rotation completed."), 3000)
        except Exception:
            traceback.print_exc()
            vp.flash_status("Rotation failed — see the IngeTrazo log.", 6000)
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

__all__ = ["Rotate3dTool", "setup"]