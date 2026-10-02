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
# Extension: igz_align3d (Subpasta modify3d) - Estilo AutoCAD (Pares Alternados)
# =========================================================================
from __future__ import annotations

import copy
import os
import sys
import traceback

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QMatrix4x4, QVector3D, QVector4D, QPen, QColor
from PySide6.QtWidgets import QMessageBox, QToolBar, QSizePolicy

from tools.base import Tool, ToolContext
from core.group import Group, transformed_mesh
from core.mesh import Face, Edge
from core.history import SnapshotImport

DEBUG = True

def _log(s):
    if DEBUG:
        print(f"[igz_align3d] {s}", file=sys.stderr, flush=True)

try:
    from core.i18n import tr, current_language
except Exception:
    def tr(s, **kw):
        return s.format(**kw) if kw else s
    def current_language():
        return "en"

_LOCAL = {
    "pt-BR": {
        "Align 3D": "Alinhar 3D",
        "Align by Points": "Alinhar por Pontos",
        "Select objects before starting Align 3D.": "Selecione os objetos antes de iniciar o Alinhamento 3D.",
        "Align 3D — click 1st point on object (Source 1)": "Alinhar 3D — clique no 1º ponto no objeto (Origem 1)",
        "Source 1 captured — click 1st destination point (Target 1)": "Origem 1 capturada — clique no 1º ponto de destino (Destino 1)",
        "Target 1 captured — click 2nd point on object (Source 2)": "Destino 1 capturado — clique no 2º ponto no objeto (Origem 2)",
        "Source 2 captured — click 2nd destination point (Target 2)": "Origem 2 capturada — clique no 2º ponto de destino (Destino 2)",
        "Target 2 captured — click 3rd point on object (Source 3)": "Destino 2 capturado — clique no 3º ponto no objeto (Origem 3)",
        "Source 3 captured — click 3rd destination point (Target 3)": "Origem 3 capturada — clique no 3º ponto de destino (Destino 3)",
        "Invalid points or collinear frame.": "Pontos inválidos ou eixo colinear.",
        "Alignment completed.": "Alinhamento concluído."
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

def _align_matrix_cad(s1, t1, s2, t2, s3, t3):
    """
    Calcula a matriz de transformação 4x4 baseada em 3 pares de pontos (Origem -> Destino)
    Estilo AutoCAD:
    S1, S2, S3 = Pontos no objeto (Origem)
    T1, T2, T3 = Pontos correspondentes no destino (Alvo)
    """
    # Vetores no objeto (Source)
    v1_s = s2 - s1
    v2_s = s3 - s1
    if v1_s.length() <= _EPS or v2_s.length() <= _EPS:
        return None
    xs = v1_s.normalized()
    zs = QVector3D.crossProduct(xs, v2_s)
    if zs.length() <= _EPS:
        return None
    zs.normalize()
    ys = QVector3D.crossProduct(zs, xs)

    # Vetores no destino (Target)
    v1_t = t2 - t1
    v2_t = t3 - t1
    if v1_t.length() <= _EPS or v2_t.length() <= _EPS:
        return None
    xt = v1_t.normalized()
    zt = QVector3D.crossProduct(xt, v2_t)
    if zt.length() <= _EPS:
        return None
    zt.normalize()
    yt = QVector3D.crossProduct(zt, xt)

    # Matrizes de base de rotação
    Rs = QMatrix4x4(
        xs.x(), ys.x(), zs.x(), 0,
        xs.y(), ys.y(), zs.y(), 0,
        xs.z(), ys.z(), zs.z(), 0,
        0, 0, 0, 1
    )
    Rt = QMatrix4x4(
        xt.x(), yt.x(), zt.x(), 0,
        xt.y(), yt.y(), zt.y(), 0,
        xt.z(), yt.z(), zt.z(), 0,
        0, 0, 0, 1
    )

    Rs_inv = Rs.transposed()
    R_combined = Rt * Rs_inv

    # Translação combinada levando s1 até t1
    m = QMatrix4x4()
    m.translate(t1)
    m = m * R_combined
    m.translate(-s1)
    return m

class Align3dTool(Tool):
    name = "Align by Points"
    shortcut = None
    description = "Align selected objects using point pairs (Source to Target)."
    uses_snap = True
    _instance = None

    def __init__(self):
        Align3dTool._instance = self
        self.points = []
        self.selection = set()
        self.current_mouse_pos = None

    def on_activate(self, vp):
        self.points = []
        self.current_mouse_pos = None
        self.selection = set(getattr(vp.scene, "selection", set()))
        if not self.selection:
            vp.flash_status(_t("Select objects before starting Align 3D."), 4000)
            vp.set_active_tool(None)
            return
        vp.flash_status(_t("Align 3D — click 1st point on object (Source 1)"), 5000)
        _log(f"selection={len(self.selection)}")

    def on_deactivate(self, vp):
        self.points = []
        self.current_mouse_pos = None

    def on_cancel(self, vp):
        self.points = []
        self.current_mouse_pos = None
        vp.flash_status("", 0)

    def on_hover(self, ctx: ToolContext):
        if len(self.points) in (0, 2, 4):
            self.current_mouse_pos = QVector3D(ctx.world)

    def on_click(self, ctx: ToolContext):
        self.points.append(QVector3D(ctx.world))
        vp = ctx.viewport
        n = len(self.points)

        if n == 1:
            vp.flash_status(_t("Source 1 captured — click 1st destination point (Target 1)"), 5000)
        elif n == 2:
            vp.flash_status(_t("Target 1 captured — click 2nd point on object (Source 2)"), 5000)
        elif n == 3:
            vp.flash_status(_t("Source 2 captured — click 2nd destination point (Target 2)"), 5000)
        elif n == 4:
            vp.flash_status(_t("Target 2 captured — click 3rd point on object (Source 3)"), 5000)
        elif n == 5:
            vp.flash_status(_t("Source 3 captured — click 3rd destination point (Target 3)"), 5000)
        elif n == 6:
            self.current_mouse_pos = None
            # Ordem dos pontos: S1, T1, S2, T2, S3, T3
            s1, t1, s2, t2, s3, t3 = self.points
            m = _align_matrix_cad(s1, t1, s2, t2, s3, t3)
            if m is None:
                vp.flash_status(_t("Invalid points or collinear frame."), 4000)
                self.points = []
                vp.flash_status(_t("Align 3D — click 1st point on object (Source 1)"), 5000)
                return
            self._finish(vp, m)

    def rubber_band_lines(self):
        if not self.points:
            return []
        lines = []
        # Desenha as linhas guias conectando os pares definidos
        for i in range(0, len(self.points) - 1, 2):
            lines.append((QVector3D(self.points[i]), QVector3D(self.points[i+1])))
        
        # Se estamos esperando o segundo ponto de um par, mostra linha elástica do último ponto fixo até o mouse
        if len(self.points) in (1, 3, 5) and self.current_mouse_pos is not None:
            lines.append((QVector3D(self.points[-1]), QVector3D(self.current_mouse_pos)))
            
        return lines

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
                vp.flash_status(f"Alignment failed: {vp.history.last_error}", 6000)
                _log(vp.history.last_error)
            else:
                vp.notify_scene_changed()
                vp.update()
                vp.flash_status(_t("Alignment completed."), 3000)
        except Exception:
            traceback.print_exc()
            vp.flash_status("Alignment failed — see the IngeTrazo log.", 6000)
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

__all__ = ["Align3dTool", "setup"]