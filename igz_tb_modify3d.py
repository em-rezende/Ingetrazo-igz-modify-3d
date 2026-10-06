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
# Extension: igz_tb_modify3d (Carregador Principal com Suporte a Ícones por Tema)
# Author: Ezequiel M Rezende
# Version: 1.0.1
# Date: 2026-10-06
# License: GPL-3.0-or-later (same as IngeTrazo)
# =========================================================================
from __future__ import annotations

import os
import sys
import traceback

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon, QPalette
from PySide6.QtWidgets import QToolBar, QSizePolicy

DEBUG = True

def _log(s):
    if DEBUG:
        print(f"[igz_tb_modify3d] {s}", file=sys.stderr, flush=True)

try:
    from core.i18n import tr, current_language
except Exception:
    def tr(s, **kw):
        return s.format(**kw) if kw else s
    def current_language():
        return "en"

_LOCAL = {
    "pt-BR": {
        "Modificadores 3D": "Modificadores 3D",
        "Mirror 3D": "Espelhar 3D",
        "Scale 3D": "Escalar 3D",
        "Rotate 3D": "Rotacionar 3D",
        "Align 3D": "Alinhar 3D",        
        "Array 3D": "Matriz 3D",
        "Polar Array 3D": "Matriz Polar 3D",
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

def _get_themed_icon(icons_dir: str, base_name: str, window) -> QIcon:
    """
    Verifica se o tema da interface é claro ou escuro através da paleta da janela
    e retorna o ícone correspondente (com sufixo _light para temas claros).
    """
    is_dark = True
    try:
        palette = window.palette()
        bg_color = palette.color(QPalette.Window)
        # Se a luminosidade de fundo for alta (> 128), consideramos tema claro
        is_dark = bg_color.lightness() < 128
    except Exception:
        pass

    # Se for tema claro, procura primeiro pela versão _light.svg
    if not is_dark:
        light_path = os.path.join(icons_dir, f"{base_name}_light.svg")
        if os.path.isfile(light_path):
            return QIcon(light_path)

    # Caso contrário (tema escuro ou se o _light não existir), usa o ícone padrão
    default_path = os.path.join(icons_dir, f"{base_name}.svg")
    if os.path.isfile(default_path):
        return QIcon(default_path)
    
    return QIcon()

_TOOLBAR = None

def setup(app):
    global _TOOLBAR
    window = getattr(app, "window", None)
    vp = getattr(app, "viewport", None)
    if window is None or vp is None:
        raise RuntimeError("ExtensionApp has no window/viewport")
    
    old = window.findChild(QToolBar, "igz_tb_modify3d")
    if old is not None:
        _TOOLBAR = old
        _TOOLBAR.show()
        return

    base_dir = os.path.dirname(os.path.abspath(__file__))
    modify3d_dir = os.path.join(base_dir, "modify3d")
    if modify3d_dir not in sys.path:
        sys.path.insert(0, modify3d_dir)

    try:
        import igz_mirror3d
        import igz_scale3d
        import igz_rotate3d
        import igz_align3d        
        import igz_array3d
        import igz_polararray3d
    except Exception as e:
        _log(f"Erro ao importar os scripts da pasta modify3d: {e}")
        traceback.print_exc(file=sys.stderr)
        return

    tb = QToolBar(_t("Modificadores 3D"), window)
    tb.setObjectName("igz_tb_modify3d")
    tb.setMovable(True)
    tb.setFloatable(True)
    tb.setAllowedAreas(Qt.AllToolBarAreas)
    tb.setIconSize(QSize(24, 24))
    tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
    tb.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    icons_dir = os.path.join(modify3d_dir, "icons")

    # --- 1. Botão Mirror 3D ---
    act_mirror = QAction(_get_themed_icon(icons_dir, "tb_mirror3d", window), igz_mirror3d._t("Mirror by 3 Points"), tb)
    act_mirror.setToolTip(igz_mirror3d._t("Mirror by 3 Points"))
    act_mirror.triggered.connect(lambda: vp.set_active_tool(igz_mirror3d.Mirror3dTool._instance or igz_mirror3d.Mirror3dTool()))
    tb.addAction(act_mirror)

    # --- 2. Botão Scale 3D ---
    act_scale = QAction(_get_themed_icon(icons_dir, "tb_scale3d", window), igz_scale3d._t("Scale by 3 Points"), tb)
    act_scale.setToolTip(igz_scale3d._t("Scale by 3 Points"))
    act_scale.triggered.connect(lambda: vp.set_active_tool(igz_scale3d.Scale3dTool._instance or igz_scale3d.Scale3dTool()))
    tb.addAction(act_scale)

    # --- 3. Botão Rotate 3D ---
    act_rotate = QAction(_get_themed_icon(icons_dir, "tb_rotate3d", window), igz_rotate3d._t("Rotate by 3 Points"), tb)
    act_rotate.setToolTip(igz_rotate3d._t("Rotate by 3 Points"))
    act_rotate.triggered.connect(lambda: vp.set_active_tool(igz_rotate3d.Rotate3dTool._instance or igz_rotate3d.Rotate3dTool()))
    tb.addAction(act_rotate)

    # --- 4. Botão Align 3D ---
    act_align = QAction(_get_themed_icon(icons_dir, "tb_align3d", window), igz_align3d._t("Align by Points"), tb)
    act_align.setToolTip(igz_align3d._t("Align by Points"))
    act_align.triggered.connect(lambda: vp.set_active_tool(igz_align3d.Align3dTool._instance or igz_align3d.Align3dTool()))
    tb.addAction(act_align)
    
    # --- 5. Botão Array 3D ---
    act_array = QAction(_get_themed_icon(icons_dir, "tb_array3d", window), igz_array3d._t("Array by 2 Points"), tb)
    act_array.setToolTip(igz_array3d._t("Array by 2 Points"))
    act_array.triggered.connect(lambda: vp.set_active_tool(igz_array3d.Array3dTool._instance or igz_array3d.Array3dTool()))
    tb.addAction(act_array)    

    # --- 6. Botão Polar Array 3D ---
    act_polar = QAction(_get_themed_icon(icons_dir, "tb_polararray3d", window), igz_polararray3d._t("Polar Array by Points"), tb)
    act_polar.setToolTip(igz_polararray3d._t("Polar Array by Points"))
    act_polar.triggered.connect(lambda: vp.set_active_tool(igz_polararray3d.PolarArray3dTool._instance or igz_polararray3d.PolarArray3dTool()))
    tb.addAction(act_polar)

    window.addToolBar(Qt.TopToolBarArea, tb)
    tb.show()
    _TOOLBAR = tb
    _log("Toolbar 'Modificadores 3D' com suporte a ícones temáticos carregada com sucesso.")

__all__ = ["setup"]