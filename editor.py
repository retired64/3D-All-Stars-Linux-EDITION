#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3D All Stars Game Editor
---------------------------------------------------
"""

import sys
import os
import json
import shutil
import re
import stat
import logging
import subprocess
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QDialog, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QFrame, QGroupBox, QScrollArea, QSplitter,
    QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QAction

# =============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA Y LOGGING
# =============================================================================

# Definir BASE_DIR: Ubicación del script/ejecutable actual
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).parent.resolve()

# Directorios de soporte
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backups"
LOG_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# Configuración de Logging
logging.basicConfig(
    filename=LOG_DIR / "editor.log",
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    encoding="utf-8"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)
logger = logging.getLogger(__name__)

# Configuración Visual (Tema Oscuro Professional)
THEME = {
    "bg_main": "#0f172a",       # Slate 900
    "bg_surface": "#1e293b",    # Slate 800
    "bg_card": "#334155",       # Slate 700
    "input_bg": "#0f172a",
    "accent": "#38bdf8",        # Sky 400
    "accent_hover": "#0ea5e9",  # Sky 500
    "text_main": "#f1f5f9",     # Slate 100
    "text_dim": "#94a3b8",      # Slate 400
    "success": "#22c55e",       # Green 500
    "danger": "#ef4444",        # Red 500
    "warning": "#eab308",       # Yellow 500
    "border": "#475569"         # Slate 600
}

# =============================================================================
# 2. MODELO DE DATOS (Data Class)
# =============================================================================

@dataclass
class Game:
    """Representación estricta del esquema games.json."""
    nombre: str
    tipo: str = "binario"
    ruta_ejecutable: str = ""
    icon: str = ""
    logo: str = ""
    sound: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'Game':
        valid_keys = cls.__annotations__.keys()
        clean_d = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**clean_d)

    def validate(self) -> Tuple[bool, List[str]]:
        """Verifica integridad referencial y PERMISOS para el Launcher."""
        errors = []
        if not self.nombre:
            errors.append("El nombre es obligatorio.")
        
        # Verificar archivos requeridos
        checks = [("Script", self.ruta_ejecutable), ("Icono", self.icon), ("Logo", self.logo)]
        for lbl, path in checks:
            if not path:
                errors.append(f"Falta ruta para: {lbl}")
                continue
            
            full_path = BASE_DIR / path
            if not full_path.exists():
                errors.append(f"Archivo no encontrado: {path}")
            
            # [CRÍTICO] Verificar permisos de ejecución para el script
            if lbl == "Script" and full_path.exists():
                if not os.access(full_path, os.X_OK):
                    errors.append(f"El script NO es ejecutable (+x): {path}")
                    logger.warning(f"Permisos insuficientes en: {full_path}")
        
        return len(errors) == 0, errors

# =============================================================================
# 3. GESTOR DE EMULADORES Y ESTRUCTURA
# =============================================================================

class EmulatorManager:
    """Detecta emuladores y genera comandos de lanzamiento."""
    
    def __init__(self):
        self.templates = {
            "Vacio (Solo estructura)": {
                "cmd": "# Comando manual aquí",
                "desc": "Plantilla en blanco"
            },
            "Wine (Windows EXE)": {
                "cmd": "wine \"./game.exe\"",
                "desc": "Contenedor Wine"
            }
        }
        self.detect_local_emulators()

    def detect_local_emulators(self):
        """
        Escanea carpetas dentro del proyecto en busca de emuladores.
        Usa rutas relativas ../../ para que funcionen desde games/juego/run
        """
        
        # LISTA MAESTRA DE POSIBLES UBICACIONES
        # Formato: (Nombre, Ruta relativa desde ROOT, Argumentos Típicos)
        candidates = [
            ("Dolphin (GameCube/Wii)", "dolphin-emulator/dolphin-emu", "-b -e \"./game.iso\""),
            ("Citra/Azahar (3DS)", "3ds/azahar.AppImage", "\"./game.3ds\""),
            ("MelonDS (NDS)", "nds/melonDS", "\"./game.nds\""),
            ("Ryujinx (Switch)", "ryujinx/Ryujinx", "\"./game.nsp\""),
            ("PCSX2 (PS2)", "pcsx2/pcsx2-qt", "-batch \"./game.iso\""),
            ("PPSSPP (PSP)", "ppsspp/PPSSPPSDL", "\"./game.iso\"")
        ]

        logger.info("--- Iniciando escaneo de emuladores ---")
        
        for name, rel_path, args in candidates:
            # 1. Verificar existencia física (Desde la raíz del proyecto)
            full_check_path = BASE_DIR / rel_path
            
            if full_check_path.exists():
                # 2. Generar comando relativo para el script 'run' (Sube 2 niveles)
                script_cmd_path = f"../../{rel_path}"
                
                self.templates[name] = {
                    "cmd": f"{script_cmd_path} {args}",
                    "desc": f"Auto-detectado en: {rel_path}"
                }
                
                # [DEBUG CRÍTICO] Logs solicitados
                logger.info(f"📍 Emulador: {name}")
                logger.info(f"   - Ruta física: {full_check_path}")
                logger.info(f"   - Comando run: {script_cmd_path} {args}")
                logger.info("")
            else:
                logger.debug(f"No encontrado: {rel_path}")

class StructureHelper:
    """Manejo seguro del sistema de archivos."""

    @staticmethod
    def sanitize(name: str) -> str:
        s = name.lower().strip()
        s = re.sub(r'[^\w\s-]', '', s)
        return re.sub(r'[\s_-]+', '_', s)

    @staticmethod
    def create_game_files(name: str, template: dict) -> Dict[str, str]:
        safe_name = StructureHelper.sanitize(name)
        
        # Rutas absolutas para crear carpetas
        game_dir = BASE_DIR / "games" / safe_name
        assets_dir = BASE_DIR / "assets" / safe_name
        
        game_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear script RUN
        run_path = game_dir / "run"
        content = (
            "#!/bin/sh\n"
            "cd \"$(dirname \"$0\")\" || exit 1\n"
            f"# Generado por Editor - {template['desc']}\n"
            f"{template['cmd']}\n"
        )
        
        with open(run_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Permisos +x (CRÍTICO para Launcher)
        os.chmod(run_path, os.stat(run_path).st_mode | stat.S_IEXEC)
        
        # Rutas relativas para el JSON
        return {
            "ruta_ejecutable": f"games/{safe_name}/run",
            "icon": f"assets/{safe_name}/icon.png",
            "logo": f"assets/{safe_name}/logo.png",
            "sound": f"assets/{safe_name}/sound.wav"
        }

# =============================================================================
# 4. GESTOR DE BASE DE DATOS (JSON)
# =============================================================================

class GameManager:
    def __init__(self, filename="games.json"):
        self.filepath = BASE_DIR / filename
        self.games: List[Game] = []
        self.emulator_mgr = EmulatorManager()

    def load(self):
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.games = [Game.from_dict(x) for x in data]
            return self.games
        except Exception as e:
            logger.error(f"Error cargando JSON: {e}")
            return []

    def save(self):
        # 1. Backup
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.filepath.exists():
            shutil.copy2(self.filepath, BACKUP_DIR / f"games_backup_{timestamp}.json")
        
        # 2. Guardar
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump([g.to_dict() for g in self.games], f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.critical(f"Fallo al guardar: {e}")
            return False

    def delete_game_assets(self, game: Game):
        """Elimina carpetas físicas."""
        safe = StructureHelper.sanitize(game.nombre)
        paths = [BASE_DIR / "games" / safe, BASE_DIR / "assets" / safe]
        deleted = []
        for p in paths:
            if p.exists():
                shutil.rmtree(p)
                deleted.append(p.name)
        return deleted

# =============================================================================
# 5. COMPONENTES DE UI PERSONALIZADOS
# =============================================================================

class ModernButton(QPushButton):
    def __init__(self, text, variant="primary", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.variant = variant
        self.update_style()
        
    def update_style(self):
        colors = {
            "primary": (THEME["accent"], THEME["bg_main"]),
            "secondary": (THEME["bg_card"], THEME["text_main"]),
            "danger": (THEME["danger"], "#ffffff"),
            "success": (THEME["success"], "#ffffff")
        }
        bg, txt = colors.get(self.variant, colors["secondary"])
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {txt};
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
        """)

class AssetDropZone(QLabel):
    """Widget para previsualizar imágenes."""
    def __init__(self, text="Sin Imagen"):
        super().__init__(text)
        self.setFixedSize(120, 100)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                border: 2px dashed {THEME['border']};
                border-radius: 8px;
                color: {THEME['text_dim']};
                background: {THEME['input_bg']};
            }}
        """)
        self.setScaledContents(True)

    def load_path(self, rel_path):
        full = BASE_DIR / rel_path
        if full.exists() and full.suffix.lower() in ['.png', '.jpg']:
            pix = QPixmap(str(full))
            self.setPixmap(pix)
        else:
            self.setText("No encontrado")
            self.setStyleSheet(f"border: 2px solid {THEME['danger']}; color: {THEME['danger']};")

# =============================================================================
# 6. DIÁLOGOS Y VENTANAS
# =============================================================================

class GameDialog(QDialog):
    def __init__(self, parent, manager, game=None):
        super().__init__(parent)
        self.mgr = manager
        self.result_game = None
        self.setup_ui()
        if game: self.load_game(game)

    def setup_ui(self):
        self.setWindowTitle("Editor de Juego")
        self.resize(850, 650)
        self.setStyleSheet(f"background: {THEME['bg_main']}; color: {THEME['text_main']};")
        
        # [MEJORA CRÍTICA] Usar ScrollArea para evitar desbordamiento
        main_layout = QVBoxLayout(self)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # --- Nombre y Tipo ---
        row1 = QHBoxLayout()
        self.name_inp = QLineEdit()
        self.name_inp.setPlaceholderText("Nombre del Juego")
        self.name_inp.setStyleSheet(f"background: {THEME['input_bg']}; border: 1px solid {THEME['border']}; padding: 8px; color: {THEME['text_main']};")
        
        self.type_cmb = QComboBox()
        self.type_cmb.addItems(["binario", "script", "appimage"])
        self.type_cmb.setStyleSheet(self.name_inp.styleSheet())
        
        row1.addWidget(QLabel("Nombre:"))
        row1.addWidget(self.name_inp, 2)
        row1.addWidget(QLabel("Tipo:"))
        row1.addWidget(self.type_cmb, 1)
        layout.addLayout(row1)

        # --- Asistente de Estructura ---
        grp = QGroupBox("⚡ Configuración Automática")
        grp.setStyleSheet(f"QGroupBox {{ border: 1px solid {THEME['border']}; margin-top: 10px; padding: 15px; font-weight: bold; color: {THEME['accent']}; }}")
        gl = QHBoxLayout()
        
        self.tmpl_cmb = QComboBox()
        for k in self.mgr.emulator_mgr.templates.keys():
            self.tmpl_cmb.addItem(k)
        
        gen_btn = ModernButton("Generar Estructura", "success")
        gen_btn.clicked.connect(self.generate_files)
        
        gl.addWidget(QLabel("Plantilla:"))
        gl.addWidget(self.tmpl_cmb, 1)
        gl.addWidget(gen_btn)
        grp.setLayout(gl)
        layout.addWidget(grp)

        # --- Archivos ---
        files_grp = QGroupBox("📁 Rutas de Archivos")
        files_grp.setStyleSheet(grp.styleSheet())
        fl = QVBoxLayout()
        
        self.inputs = {}
        fields = [("ruta_ejecutable", "Script"), ("icon", "Icono"), ("logo", "Logo"), ("sound", "Audio")]
        
        for key, lbl in fields:
            h = QHBoxLayout()
            inp = QLineEdit()
            inp.setPlaceholderText(f"Ruta relativa a {lbl}")
            inp.setStyleSheet(self.name_inp.styleSheet())
            
            btn = QPushButton("...")
            btn.setFixedWidth(30)
            btn.setStyleSheet(f"background: {THEME['bg_card']}; color: white; border: none;")
            btn.clicked.connect(lambda _, k=key: self.browse(k))
            
            h.addWidget(QLabel(f"{lbl}:"))
            h.addWidget(inp)
            h.addWidget(btn)
            fl.addLayout(h)
            self.inputs[key] = inp
            
        files_grp.setLayout(fl)
        layout.addWidget(files_grp)
        
        # Añadir contenido al scroll
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # --- Footer (Fuera del Scroll) ---
        footer = QHBoxLayout()
        save_btn = ModernButton("Guardar", "primary")
        save_btn.clicked.connect(self.save)
        cancel_btn = ModernButton("Cancelar", "danger")
        cancel_btn.clicked.connect(self.reject)
        
        footer.addStretch()
        footer.addWidget(cancel_btn)
        footer.addWidget(save_btn)
        main_layout.addLayout(footer)

    def generate_files(self):
        name = self.name_inp.text()
        if not name:
            QMessageBox.warning(self, "Error", "Escribe un nombre primero")
            return
            
        tmpl_name = self.tmpl_cmb.currentText()
        tmpl = self.mgr.emulator_mgr.templates[tmpl_name]
        
        try:
            paths = StructureHelper.create_game_files(name, tmpl)
            for k, v in paths.items():
                self.inputs[k].setText(v)
            QMessageBox.information(self, "Éxito", "Carpetas y Script RUN creados correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def browse(self, key):
        start = str(BASE_DIR)
        path, _ = QFileDialog.getOpenFileName(self, "Buscar", start)
        if path:
            try:
                rel = Path(path).relative_to(BASE_DIR)
                self.inputs[key].setText(str(rel))
            except ValueError:
                self.inputs[key].setText(path)

    def load_game(self, game):
        self.name_inp.setText(game.nombre)
        self.type_cmb.setCurrentText(game.tipo)
        self.inputs["ruta_ejecutable"].setText(game.ruta_ejecutable)
        self.inputs["icon"].setText(game.icon)
        self.inputs["logo"].setText(game.logo)
        self.inputs["sound"].setText(game.sound)

    def save(self):
        g = Game(
            nombre=self.name_inp.text(),
            tipo=self.type_cmb.currentText(),
            ruta_ejecutable=self.inputs["ruta_ejecutable"].text(),
            icon=self.inputs["icon"].text(),
            logo=self.inputs["logo"].text(),
            sound=self.inputs["sound"].text()
        )
        ok, errs = g.validate()
        if not ok:
            msg = "\n".join(errs)
            r = QMessageBox.warning(self, "Validación", f"Problemas detectados:\n{msg}\n\n¿Guardar igual?", QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.No: return
            
        self.result_game = g
        self.accept()

# =============================================================================
# 7. VENTANA PRINCIPAL
# =============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.mgr = GameManager()
        self.init_ui()
        self.refresh()

    def init_ui(self):
        self.setWindowTitle("3D All Stars - Game Editor")
        self.resize(1000, 700)
        
        # Widget Central
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        central.setStyleSheet(f"background: {THEME['bg_main']};")

        # --- Panel Izquierdo (Lista) ---
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setStyleSheet(f"background: {THEME['bg_surface']}; border-right: 1px solid {THEME['border']};")
        
        title = QLabel("BIBLIOTECA")
        title.setStyleSheet(f"color: {THEME['accent']}; font-weight: bold; font-size: 16px; letter-spacing: 2px;")
        left_layout.addWidget(title)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ border: none; background: transparent; color: {THEME['text_main']}; }}
            QListWidget::item {{ padding: 12px; border-radius: 6px; margin-bottom: 4px; }}
            QListWidget::item:selected {{ background: {THEME['accent']}; color: black; }}
            QListWidget::item:hover {{ background: {THEME['bg_card']}; }}
        """)
        self.list_widget.currentRowChanged.connect(self.on_select)
        left_layout.addWidget(self.list_widget)
        
        add_btn = ModernButton("+ NUEVO JUEGO", "success")
        add_btn.clicked.connect(self.add_game)
        left_layout.addWidget(add_btn)
        
        main_layout.addWidget(left_panel, 1)

        # --- Panel Derecho (Detalles) ---
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_panel.hide()
        
        # Info Header
        self.lbl_title = QLabel()
        self.lbl_title.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {THEME['text_main']};")
        self.right_layout.addWidget(self.lbl_title)
        
        self.lbl_path = QLabel()
        self.lbl_path.setStyleSheet(f"font-family: monospace; color: {THEME['text_dim']};")
        self.right_layout.addWidget(self.lbl_path)
        
        # Previews
        prev_layout = QHBoxLayout()
        self.prev_icon = AssetDropZone("Icono")
        self.prev_logo = AssetDropZone("Logo")
        self.prev_logo.setFixedSize(200, 100)
        prev_layout.addWidget(self.prev_icon)
        prev_layout.addWidget(self.prev_logo)
        prev_layout.addStretch()
        self.right_layout.addLayout(prev_layout)
        
        self.right_layout.addStretch()
        
        # Botones Acción
        act_layout = QHBoxLayout()
        test_btn = ModernButton("▶ Probar", "primary")
        test_btn.clicked.connect(self.test_game)
        edit_btn = ModernButton("✎ Editar", "secondary")
        edit_btn.clicked.connect(self.edit_game)
        del_btn = ModernButton("🗑 Eliminar", "danger")
        del_btn.clicked.connect(self.del_game)
        
        act_layout.addWidget(test_btn)
        act_layout.addWidget(edit_btn)
        act_layout.addWidget(del_btn)
        self.right_layout.addLayout(act_layout)
        
        main_layout.addWidget(self.right_panel, 2)
        
        # Mensaje Bienvenida
        self.msg_label = QLabel("Selecciona o crea un juego")
        self.msg_label.setAlignment(Qt.AlignCenter)
        self.msg_label.setStyleSheet(f"color: {THEME['text_dim']}; font-size: 18px;")
        main_layout.addWidget(self.msg_label, 2)

    def refresh(self):
        self.list_widget.clear()
        games = self.mgr.load()
        for g in games:
            self.list_widget.addItem(g.nombre)
        
        if self.right_panel.isVisible():
            self.right_panel.hide()
            self.msg_label.show()

    def on_select(self, idx):
        if idx < 0: return
        self.msg_label.hide()
        self.right_panel.show()
        
        game = self.mgr.games[idx]
        self.lbl_title.setText(game.nombre)
        self.lbl_path.setText(f"CMD: {game.ruta_ejecutable}")
        self.prev_icon.load_path(game.icon)
        self.prev_logo.load_path(game.logo)

    def add_game(self):
        d = GameDialog(self, self.mgr)
        if d.exec():
            self.mgr.games.append(d.result_game)
            self.mgr.save()
            self.refresh()

    def edit_game(self):
        idx = self.list_widget.currentRow()
        if idx < 0: return
        
        g = self.mgr.games[idx]
        d = GameDialog(self, self.mgr, g)
        if d.exec():
            self.mgr.games[idx] = d.result_game
            self.mgr.save()
            self.refresh()
            self.list_widget.setCurrentRow(idx)

    def del_game(self):
        idx = self.list_widget.currentRow()
        if idx < 0: return
        
        g = self.mgr.games[idx]
        if QMessageBox.question(self, "Eliminar", f"¿Borrar {g.nombre} y sus archivos?") == QMessageBox.Yes:
            self.mgr.delete_game_assets(g)
            del self.mgr.games[idx]
            self.mgr.save()
            self.refresh()

    def test_game(self):
        idx = self.list_widget.currentRow()
        g = self.mgr.games[idx]
        script = BASE_DIR / g.ruta_ejecutable
        
        if not script.exists():
            QMessageBox.critical(self, "Error", "El script RUN no existe")
            return
            
        try:
            subprocess.Popen([str(script)], cwd=script.parent)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al ejecutar: {e}")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    # Paleta oscura global
    p = QPalette()
    p.setColor(QPalette.Window, QColor(THEME['bg_main']))
    p.setColor(QPalette.WindowText, QColor(THEME['text_main']))
    app.setPalette(p)
    
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
