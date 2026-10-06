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
# Extension: igz_mirror3d (Subpasta modify3d)
# Author: Ezequiel M Rezende
# Version: 1.0.1
# License: GPL-3.0-or-later (same as IngeTrazo)
# =========================================================================
from __future__ import annotations
import copy, os, sys, traceback
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMatrix4x4, QVector3D, QVector4D, QPen, QColor
from PySide6.QtWidgets import QMessageBox
from tools.base import Tool, ToolContext
from core.group import Group, copy_group, transformed_mesh
from core.mesh import Face, Edge
from core.history import SnapshotImport
from igz_xform_command import XformGroupsCommand, CompositeCommand

DEBUG = True

def _log(s):
    if DEBUG: print(f"[igz_mirror3d] {s}", file=sys.stderr, flush=True)
try:
    from core.i18n import tr, current_language
except Exception:
    def tr(s, **kw): return s.format(**kw) if kw else s
    def current_language(): return "en"
_LOCAL={"pt-BR":{"Mirror 3D":"Espelhar 3D","Mirror by 3 Points":"Espelhar por 3 Pontos","Select objects before starting Mirror 3D.":"Selecione os objetos antes de iniciar o Espelhamento 3D.","Mirror 3D — click P1":"Espelhar 3D — clique em P1","P1 captured — click P2":"P1 capturado — clique em P2","P2 captured — click P3":"P2 capturado — clique em P3","Three points must not be collinear.":"Os três pontos não podem ser colineares.","Do you want to delete the original objects?":"Deseja apagar os objetos originais?","Mirror completed.":"Espelhamento concluído."}}
def _t(s):
    try:
        x=tr(s)
        if x!=s:return x
    except Exception:pass
    return _LOCAL.get(current_language(),{}).get(s,s)

_EPS=1e-8
def _reflection_matrix(p1,p2,p3):
    u=QVector3D(p2)-QVector3D(p1); v=QVector3D(p3)-QVector3D(p1)
    n=QVector3D.crossProduct(u,v)
    if n.length()<=_EPS:return None
    n.normalize(); x,y,z=n.x(),n.y(),n.z()
    r=[[1-2*x*x,-2*x*y,-2*x*z],[-2*y*x,1-2*y*y,-2*y*z],[-2*z*x,-2*z*y,1-2*z*z]]
    px,py,pz=p1.x(),p1.y(),p1.z()
    t=[px-(r[0][0]*px+r[0][1]*py+r[0][2]*pz),py-(r[1][0]*px+r[1][1]*py+r[1][2]*pz),pz-(r[2][0]*px+r[2][1]*py+r[2][2]*pz)]
    m=QMatrix4x4()
    for i in range(3): m.setRow(i,QVector4D(*r[i],t[i]))
    m.setRow(3,QVector4D(0,0,0,1))
    return m

def _copy_group(g,m):
    out=copy_group(g); out.name=f"{g.name} (Espelho)"
    if out.xform is not None:
        out.xform=QMatrix4x4(m)*out.xform
    else:
        out.mesh=transformed_mesh(out.mesh,m)
        if getattr(out,"axes",None) is not None: out.axes=QMatrix4x4(m)*out.axes
    return out

def _copy_loose(scene,items,m):
    mesh=scene.mesh
    for f in (x for x in items if isinstance(x,Face)):
        outer=[m.map(QVector3D(p)) for p in f.vertices]; outer.reverse()
        holes=[]
        for h in (getattr(f,"holes",None) or []):
            q=[m.map(QVector3D(p)) for p in h]; q.reverse(); holes.append(q)
        nf=mesh.add_face(outer,holes or None)
        if f.attrs:nf.attrs.update(copy.deepcopy(f.attrs))
    for e in (x for x in items if isinstance(x,Edge)):
        ne=mesh.add_edge(m.map(QVector3D(e.a)),m.map(QVector3D(e.b)))
        ne.soft=getattr(e,"soft",False); ne.curve=getattr(e,"curve",None)

class Mirror3dTool(Tool):
    name="Mirror by 3 Points"
    shortcut=None
    description="Reflect the selected objects across a plane defined by three points."
    uses_snap=True
    _instance=None
    def __init__(self):
        Mirror3dTool._instance=self
        self.points=[]
        self.selection=set()
        self.current_mouse_pos=None
        self.selection_bbox=None
        self.preview_matrix=None
        self.preview_visible=False
    def on_activate(self,vp):
        self.points=[]
        self.current_mouse_pos=None
        self.preview_matrix=None
        self.preview_visible=False
        self.selection=set(getattr(vp.scene,"selection",set()))
        if not self.selection:
            self.selection_bbox=None
            vp.flash_status(_t("Select objects before starting Mirror 3D."),4000)
            vp.set_active_tool(None)
            return
        try:
            lo, hi = vp.scene.selection_bounds()
            self.selection_bbox=(QVector3D(lo),QVector3D(hi)) if lo is not None and hi is not None else None
        except Exception:
            self.selection_bbox=None
        vp.flash_status(_t("Mirror 3D — click P1"),5000)
        _log(f"selection={len(self.selection)} bbox={self.selection_bbox is not None}")

    def on_deactivate(self,vp):
        self.points=[]
        self.current_mouse_pos=None
        self.selection_bbox=None
        self.preview_matrix=None
        self.preview_visible=False

    def on_cancel(self,vp):
        self.points=[]
        self.current_mouse_pos=None
        self.selection_bbox=None
        self.preview_matrix=None
        vp.flash_status("",0)

    def on_mousemove(self,ctx:ToolContext):
        if len(self.points)>=2:
            self.current_mouse_pos=QVector3D(ctx.world)
            ctx.viewport.update()

    def on_draw(self,painter,vp):
        if len(self.points)<2:
            return
        if self.preview_visible and self.preview_matrix is None:
            return
        painter.save()
        try:
            painter.setPen(QPen(QColor(0,120,215),2,Qt.DashLine))
            project=vp.project_point

            a=project(self.points[0]); b=project(self.points[1])
            if a is not None and b is not None:
                painter.drawLine(a,b)

            if self.current_mouse_pos is not None and a is not None:
                c=project(self.current_mouse_pos)
                if c is not None:
                    painter.drawLine(a,c)

            if self.selection_bbox is not None:
                lo,hi=self.selection_bbox
                x0,y0,z0=lo.x(),lo.y(),lo.z()
                x1,y1,z1=hi.x(),hi.y(),hi.z()
                corners=[
                    QVector3D(x0,y0,z0), QVector3D(x1,y0,z0),
                    QVector3D(x1,y1,z0), QVector3D(x0,y1,z0),
                    QVector3D(x0,y0,z1), QVector3D(x1,y0,z1),
                    QVector3D(x1,y1,z1), QVector3D(x0,y1,z1)]
                if self.preview_matrix is not None:
                    corners=[self.preview_matrix.map(c) for c in corners]
                edges=((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))
                for i,j in edges:
                    p0,p1=project(corners[i]),project(corners[j])
                    if p0 is not None and p1 is not None:
                        painter.drawLine(p0,p1)
        finally:
            painter.restore()

    def rubber_band_lines(self):
        if self.selection_bbox is None:
            return []
        if self.preview_matrix is None:
            return []
        try:
            lo,hi=self.selection_bbox
            x0,y0,z0=lo.x(),lo.y(),lo.z()
            x1,y1,z1=hi.x(),hi.y(),hi.z()
            corners=[
                QVector3D(x0,y0,z0), QVector3D(x1,y0,z0),
                QVector3D(x1,y1,z0), QVector3D(x0,y1,z0),
                QVector3D(x0,y0,z1), QVector3D(x1,y0,z1),
                QVector3D(x1,y1,z1), QVector3D(x0,y1,z1)]
            corners=[self.preview_matrix.map(c) for c in corners]
            edges=((0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7))
            lines=[(corners[i],corners[j]) for i,j in edges]
            if len(self.points)>=2:
                lines.append((QVector3D(self.points[0]),QVector3D(self.points[1])))
            if len(self.points)>=3:
                lines.append((QVector3D(self.points[0]),QVector3D(self.points[2])))
            return lines
        except Exception:
            traceback.print_exc()
            return []

    def on_click(self,ctx:ToolContext):
        self.points.append(QVector3D(ctx.world)); vp=ctx.viewport
        if len(self.points)==1: vp.flash_status(_t("P1 captured — click P2"),5000); return
        if len(self.points)==2: vp.flash_status(_t("P2 captured — click P3"),5000); return
        m=_reflection_matrix(*self.points)
        if m is None:
            vp.flash_status(_t("Three points must not be collinear."),4000); self.points=[]; vp.flash_status(_t("Mirror 3D — click P1"),5000); return

        self.preview_matrix=QMatrix4x4(m)
        self.preview_visible=True
        try:
            vp.update()
            vp.repaint()
        except Exception:
            pass
        QTimer.singleShot(80, lambda: self._finish(vp,m))
    def _finish(self, vp, m):
        try:
            ans = QMessageBox.question(
                vp.window(),
                _t("Mirror 3D"),
                _t("Do you want to delete the original objects?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            delete = ans == QMessageBox.Yes
            selected = set(self.selection)

            # 1. SnapshotImport — adição das cópias espelhadas.
            def add_mirrored(scene):
                for x in selected:
                    if isinstance(x, Group):
                        scene.groups.append(_copy_group(x, m))
                loose = [x for x in selected if isinstance(x, (Face, Edge))]
                if loose:
                    _copy_loose(scene, loose, m)

            # NÃO passe label= — SnapshotImport não aceita esse kwarg.
            add_cmd = SnapshotImport(add_mirrored)

            # 2. Remoção opcional dos originais (undo-aware).
            groups_to_remove = [x for x in selected if isinstance(x, Group)]

            if delete and groups_to_remove:
                def noop(_g):
                    pass

                remove_cmd = XformGroupsCommand(
                    noop,
                    groups_to_remove,
                    remove_after=True,
                    label=_t("Mirror 3D (delete originals)"),
                )
                cmd = CompositeCommand(
                    add_cmd, remove_cmd, label=_t("Mirror 3D")
                )
            else:
                cmd = add_cmd

            vp.history.execute(cmd)
            if vp.history.last_error:
                vp.flash_status(
                    f"Mirror failed: {vp.history.last_error}", 6000
                )
                _log(vp.history.last_error)
            else:
                vp.scene.selection.clear()
                vp.notify_scene_changed()
                vp.update()
                vp.flash_status(_t("Mirror completed."), 3000)
        except Exception:
            traceback.print_exc()
            vp.flash_status(
                "Mirror failed — see the IngeTrazo log.", 6000
            )
        finally:
            # Limpa preview SEMPRE, mesmo se o try falhou.
            self.points = []
            self.current_mouse_pos = None
            self.selection_bbox = None
            self.preview_matrix = None
            self.preview_visible = False
            try:
                vp.update()
            except Exception:
                pass
            try:
                from tools.select import SelectTool
                vp.set_active_tool(SelectTool())
            except Exception:
                vp.set_active_tool(None)

def setup(app):
    pass

__all__=["Mirror3dTool","setup"]