#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3D All Stars Game Editor - Ultimate Edition
---------------------------------------------------
Combina gestión robusta de archivos, logging, backups
y una interfaz moderna de alto rendimiento.
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
from typing import List, Dict, Optional, Tuple

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QDialog, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QFrame, QGroupBox, QScrollArea, QSplitter
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QAction

# =============================================================================
# 1. CONFIGURACIÓN DEL SISTEMA Y LOGGING
# =============================================================================

# Definir BASE_DIR compatible con scripts y ejecutables congelados (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).parent.resolve()

# Directorios del sistema
DIRS = {
    "logs": BASE_DIR / "logs",
    "backups": BASE_DIR / "backups",
    "games": BASE_DIR / "games",
    "assets": BASE_DIR / "assets"
}

for d in DIRS.values():
    d.mkdir(parents=True, exist_ok=True)

# Configuración de Logging
logging.basicConfig(
    filename=DIRS["logs"] / "editor.log",
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger(__name__)

# Tema Visual (Dark Professional)
THEME = {
    "bg_main": "#0f172a",       # Slate 900
    "bg_surface": "#1e293b",    # Slate 800
    "bg_card": "#334155",       # Slate 700
    "accent": "#0ea5e9",        # Sky 500
    "accent_hover": "#38bdf8",  # Sky 400
    "text_main": "#f8fafc",     # Slate 50
    "text_dim": "#94a3b8",      # Slate 400
    "success": "#22c55e",       # Green 500
    "danger": "#ef4444",        # Red 500
    "border": "#475569"         # Slate 600
}

# =============================================================================
# 2. MODELO DE DATOS Y LÓGICA DE NEGOCIO
# =============================================================================

@dataclass
class Game:
    nombre: str
    tipo: str = "binario"
    ruta_ejecutable: str = ""
    icon: str = ""
    logo: str = ""
    sound: str = ""

    def to_dict(self):
        return self.__dict__

    @classmethod
    def from_dict(cls, d):
        # Filtra claves extrañas para evitar errores al cargar JSON antiguos
        valid_keys = cls.__annotations__.keys()
        return cls(**{k: v for k, v in d.items() if k in valid_keys})

class FileSystemHandler:
    """Maneja operaciones de archivos, copiado y limpieza."""

    @staticmethod
    def sanitize(name: str) -> str:
        """Convierte nombres en cadenas seguras para carpetas."""
        s = name.lower().strip()
        s = re.sub(r'[^\w\s-]', '', s)
        return re.sub(r'[\s_-]+', '_', s)

    @staticmethod
    def import_asset(src_path: str, game_name: str, asset_type: str) -> str:
        """
        Copia un archivo externo a la carpeta assets/juego del proyecto.
        Devuelve la ruta relativa.
        """
        safe_name = FileSystemHandler.sanitize(game_name)
        target_dir = DIRS["assets"] / safe_name
        target_dir.mkdir(parents=True, exist_ok=True)

        src = Path(src_path)
        ext = src.suffix.lower()
        
        # Nombre estandarizado: icon.png, logo.jpg, sound.wav
        target_filename = f"{asset_type}{ext}"
        dest = target_dir / target_filename
        
        try:
            shutil.copy2(src, dest)
            logger.info(f"Asset importado: {src} -> {dest}")
            return f"assets/{safe_name}/{target_filename}"
        except Exception as e:
            logger.error(f"Error importando asset: {e}")
            raise e

    @staticmethod
    def create_run_script(game_name: str, template_cmd: str, template_desc: str) -> str:
        """Crea el script de lanzamiento ejecutable."""
        safe_name = FileSystemHandler.sanitize(game_name)
        game_dir = DIRS["games"] / safe_name
        game_dir.mkdir(parents=True, exist_ok=True)
        
        run_path = game_dir / "run"
        
        content = (
            "#!/bin/sh\n"
            "cd \"$(dirname \"$0\")\" || exit 1\n"
            f"# Generado por Editor - {template_desc}\n"
            f"{template_cmd}\n"
        )
        
        with open(run_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Hacer ejecutable (chmod +x)
        st = os.stat(run_path)
        os.chmod(run_path, st.st_mode | stat.S_IEXEC)
        
        return f"games/{safe_name}/run"

    @staticmethod
    def delete_game_content(game_name: str):
        """Elimina carpetas de games y assets asociadas."""
        safe_name = FileSystemHandler.sanitize(game_name)
        paths_to_remove = [
            DIRS["games"] / safe_name,
            DIRS["assets"] / safe_name
        ]
        
        report = []
        for p in paths_to_remove:
            if p.exists():
                try:
                    shutil.rmtree(p)
                    report.append(f"Eliminado: {p.name}")
                except Exception as e:
                    logger.error(f"No se pudo borrar {p}: {e}")
        return report

class GameManager:
    def __init__(self, filename="games.json"):
        self.filepath = BASE_DIR / filename
        self.games: List[Game] = []
        
        # Plantillas de emuladores (Mezcla de estáticas y relativas)
        self.templates = {
            "Vacio (Solo estructura)": {
                "cmd": "# Comando personalizado aqui",
                "desc": "Manual"
            },
            "Dolphin (GameCube/Wii)": {
                "cmd": "../../dolphin-emulator/dolphin-emu -b -e \"./game.iso\"",
                "desc": "Dolphin Portable"
            },
            "Citra/Azahar (3DS)": {
                "cmd": "../../3ds/azahar.AppImage \"./game.3ds\"",
                "desc": "AppImage 3DS"
            },
            "Wine (Windows EXE)": {
                "cmd": "wine \"./game.exe\"",
                "desc": "Wine Wrapper"
            },
            "Ryujinx (Switch)": {
                "cmd": "../../ryujinx/Ryujinx \"./game.nsp\"",
                "desc": "Ryujinx Portable"
            }
        }

    def load(self):
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.games = [Game.from_dict(x) for x in json.load(f)]
            logger.info(f"Cargados {len(self.games)} juegos.")
        except Exception as e:
            logger.error(f"Error cargando JSON: {e}")
        return self.games

    def save(self):
        # 1. Crear Backup
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = DIRS["backups"] / f"games_{timestamp}.json"
        if self.filepath.exists():
            shutil.copy2(self.filepath, backup_path)
        
        # 2. Guardar
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump([g.to_dict() for g in self.games], f, indent=2, ensure_ascii=False)
            logger.info("Base de datos guardada correctamente.")
            return True
        except Exception as e:
            logger.critical(f"Fallo al guardar JSON: {e}")
            return False

# =============================================================================
# 3. COMPONENTES UI
# =============================================================================

class StyledButton(QPushButton):
    def __init__(self, text, variant="primary", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.variant = variant
        self.apply_style()

    def apply_style(self):
        styles = {
            "primary": (THEME["accent"], "#ffffff"),
            "secondary": (THEME["bg_card"], THEME["text_main"]),
            "danger": (THEME["danger"], "#ffffff"),
            "success": (THEME["success"], "#ffffff")
        }
        bg, txt = styles.get(self.variant, styles["secondary"])
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {txt};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
            QPushButton:pressed {{ background-color: {THEME['bg_surface']}; }}
        """)

class ImagePreview(QLabel):
    def __init__(self, title):
        super().__init__()
        self.setFixedSize(140, 100)
        self.setAlignment(Qt.AlignCenter)
        self.setText(title)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {THEME['bg_main']};
                border: 2px dashed {THEME['border']};
                border-radius: 8px;
                color: {THEME['text_dim']};
            }}
        """)
        self.setScaledContents(True)

    def set_image(self, rel_path):
        full_path = BASE_DIR / rel_path
        if full_path.exists() and full_path.is_file():
            self.setPixmap(QPixmap(str(full_path)))
            self.setStyleSheet(f"border: 2px solid {THEME['accent']}; border-radius: 8px;")
        else:
            self.setText("Sin Imagen")
            self.setStyleSheet(f"border: 2px dashed {THEME['danger']}; color: {THEME['danger']}; background: {THEME['bg_main']};")

# =============================================================================
# 4. DIÁLOGO DE EDICIÓN
# =============================================================================

class GameFormDialog(QDialog):
    def __init__(self, parent, manager: GameManager, game: Optional[Game] = None):
        super().__init__(parent)
        self.manager = manager
        self.game_data = game
        self.result_game = None
        self.setup_ui()
        if game:
            self.load_data()

    def setup_ui(self):
        self.setWindowTitle("Editor de Juego" if not self.game_data else f"Editando: {self.game_data.nombre}")
        self.resize(700, 600)
        self.setStyleSheet(f"background-color: {THEME['bg_main']}; color: {THEME['text_main']};")

        layout = QVBoxLayout(self)
        
        # Scroll Area para pantallas pequeñas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        content = QWidget()
        form_layout = QVBoxLayout(content)
        form_layout.setSpacing(15)

        # 1. Datos Básicos
        gb_info = QGroupBox("📝 Información Básica")
        gb_info.setStyleSheet(f"QGroupBox {{ border: 1px solid {THEME['border']}; margin-top: 10px; padding: 15px; font-weight: bold; color: {THEME['accent']}; }}")
        l_info = QVBoxLayout()
        
        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Nombre del Juego (Ej: Super Mario Sunshine)")
        self.inp_name.setStyleSheet(f"padding: 8px; background: {THEME['bg_card']}; border: 1px solid {THEME['border']}; color: white;")
        
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["binario", "script", "appimage"])
        self.cmb_type.setStyleSheet(self.inp_name.styleSheet())

        l_info.addWidget(QLabel("Nombre:"))
        l_info.addWidget(self.inp_name)
        l_info.addWidget(QLabel("Tipo de Ejecución:"))
        l_info.addWidget(self.cmb_type)
        gb_info.setLayout(l_info)
        form_layout.addWidget(gb_info)

        # 2. Configuración Automática
        gb_auto = QGroupBox("⚡ Auto-Configuración")
        gb_auto.setStyleSheet(gb_info.styleSheet())
        l_auto = QHBoxLayout()
        
        self.cmb_template = QComboBox()
        self.cmb_template.addItems(list(self.manager.templates.keys()))
        self.cmb_template.setStyleSheet(self.inp_name.styleSheet())
        
        btn_gen = StyledButton("Generar Estructura", "success")
        btn_gen.clicked.connect(self.generate_structure)
        
        l_auto.addWidget(self.cmb_template, 1)
        l_auto.addWidget(btn_gen)
        gb_auto.setLayout(l_auto)
        form_layout.addWidget(gb_auto)

        # 3. Archivos y Assets
        gb_files = QGroupBox("📁 Archivos y Assets")
        gb_files.setStyleSheet(gb_info.styleSheet())
        l_files = QVBoxLayout()
        
        self.inputs = {}
        # Clave, Etiqueta, Tipo
        fields = [
            ("ruta_ejecutable", "Script de Arranque (run)", "file"),
            ("icon", "Icono (PNG/JPG)", "image"),
            ("logo", "Logo (PNG/JPG)", "image"),
            ("sound", "Sonido (WAV/MP3)", "audio")
        ]

        for key, label, ftype in fields:
            row = QHBoxLayout()
            inp = QLineEdit()
            inp.setPlaceholderText(f"Ruta relativa ({label})")
            inp.setStyleSheet(self.inp_name.styleSheet())
            self.inputs[key] = inp
            
            btn = QPushButton("📂")
            btn.setFixedSize(40, 35)
            btn.setStyleSheet(f"background: {THEME['bg_card']}; color: {THEME['accent']}; border: 1px solid {THEME['accent']}; border-radius: 4px;")
            btn.clicked.connect(lambda _, k=key, t=ftype: self.browse_and_import(k, t))
            
            row.addWidget(QLabel(label))
            row.addWidget(inp, 1)
            row.addWidget(btn)
            l_files.addLayout(row)
            
        gb_files.setLayout(l_files)
        form_layout.addWidget(gb_files)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Botones Finales
        bbox = QHBoxLayout()
        btn_cancel = StyledButton("Cancelar", "danger")
        btn_cancel.clicked.connect(self.reject)
        btn_save = StyledButton("Guardar Cambios", "primary")
        btn_save.clicked.connect(self.save_game)
        
        bbox.addStretch()
        bbox.addWidget(btn_cancel)
        bbox.addWidget(btn_save)
        layout.addLayout(bbox)

    def load_data(self):
        self.inp_name.setText(self.game_data.nombre)
        self.cmb_type.setCurrentText(self.game_data.tipo)
        for key, inp in self.inputs.items():
            inp.setText(getattr(self.game_data, key))

    def generate_structure(self):
        name = self.inp_name.text()
        if not name:
            QMessageBox.warning(self, "Error", "Escribe un nombre primero.")
            return

        tmpl_key = self.cmb_template.currentText()
        tmpl = self.manager.templates[tmpl_key]

        try:
            # 1. Crear Script
            run_path = FileSystemHandler.create_run_script(name, tmpl["cmd"], tmpl["desc"])
            self.inputs["ruta_ejecutable"].setText(run_path)
            
            # 2. Pre-llenar rutas de assets (aunque no existan aún, define dónde irán)
            safe = FileSystemHandler.sanitize(name)
            self.inputs["icon"].setText(f"assets/{safe}/icon.png")
            self.inputs["logo"].setText(f"assets/{safe}/logo.png")
            self.inputs["sound"].setText(f"assets/{safe}/sound.wav")
            
            QMessageBox.information(self, "Éxito", f"✅ Estructura creada en games/{safe}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def browse_and_import(self, key, ftype):
        name = self.inp_name.text()
        if not name and ftype != "file":
            QMessageBox.warning(self, "Atención", "Escribe el nombre del juego antes de importar assets.")
            return

        filters = {
            "image": "Imágenes (*.png *.jpg *.jpeg *.bmp)",
            "audio": "Audio (*.wav *.mp3 *.ogg)",
            "file": "Todos (*.*)"
        }
        
        path, _ = QFileDialog.getOpenFileName(self, f"Seleccionar {key}", str(BASE_DIR), filters.get(ftype, "Todos (*.*)"))
        
        if path:
            # Si es asset (imagen/audio), lo importamos a la carpeta assets/juego
            if ftype in ["image", "audio"]:
                try:
                    rel_path = FileSystemHandler.import_asset(path, name, key)
                    self.inputs[key].setText(rel_path)
                    QMessageBox.information(self, "Importado", f"Archivo copiado a:\n{rel_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error de Importación", str(e))
            else:
                # Si es un script o ejecutable, intentamos usar ruta relativa
                try:
                    p = Path(path)
                    if BASE_DIR in p.parents:
                        self.inputs[key].setText(str(p.relative_to(BASE_DIR)))
                    else:
                        self.inputs[key].setText(path)
                except:
                    self.inputs[key].setText(path)

    def save_game(self):
        # Validación básica
        if not self.inp_name.text():
            QMessageBox.warning(self, "Error", "El nombre es obligatorio")
            return
            
        self.result_game = Game(
            nombre=self.inp_name.text(),
            tipo=self.cmb_type.currentText(),
            ruta_ejecutable=self.inputs["ruta_ejecutable"].text(),
            icon=self.inputs["icon"].text(),
            logo=self.inputs["logo"].text(),
            sound=self.inputs["sound"].text()
        )
        self.accept()

# =============================================================================
# 5. VENTANA PRINCIPAL
# =============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = GameManager()
        self.init_ui()
        self.refresh_list()

    def init_ui(self):
        self.setWindowTitle("3D All Stars - Ultimate Editor")
        self.setMinimumSize(1000, 700)
        
        # Widget Central
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background-color: {THEME['bg_main']};")
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- PANEL IZQUIERDO (Lista) ---
        left_panel = QFrame()
        left_panel.setFixedWidth(300)
        left_panel.setStyleSheet(f"background: {THEME['bg_surface']}; border-right: 1px solid {THEME['border']};")
        left_layout = QVBoxLayout(left_panel)
        
        lbl_title = QLabel("🎮 LIBRERÍA")
        lbl_title.setStyleSheet(f"color: {THEME['accent']}; font-weight: 900; font-size: 18px; padding: 10px;")
        left_layout.addWidget(lbl_title)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ border: none; background: transparent; color: {THEME['text_main']}; outline: none; }}
            QListWidget::item {{ padding: 12px; margin: 2px 8px; border-radius: 6px; }}
            QListWidget::item:selected {{ background: {THEME['accent']}; color: white; }}
            QListWidget::item:hover {{ background: {THEME['bg_card']}; }}
        """)
        self.list_widget.currentRowChanged.connect(self.on_game_selected)
        left_layout.addWidget(self.list_widget)
        
        btn_add = StyledButton("➕ Nuevo Juego", "success")
        btn_add.clicked.connect(self.add_game)
        left_layout.addWidget(btn_add)
        
        main_layout.addWidget(left_panel)

        # --- PANEL DERECHO (Detalles) ---
        self.right_panel = QWidget()
        self.right_panel.hide()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(40, 40, 40, 40)
        
        # Encabezado
        self.lbl_game_title = QLabel("")
        self.lbl_game_title.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {THEME['text_main']};")
        right_layout.addWidget(self.lbl_game_title)
        
        self.lbl_game_path = QLabel("")
        self.lbl_game_path.setStyleSheet(f"font-family: Consolas, monospace; color: {THEME['text_dim']}; background: {THEME['bg_card']}; padding: 5px; border-radius: 4px;")
        right_layout.addWidget(self.lbl_game_path)
        
        right_layout.addSpacing(30)
        
        # Previsualizaciones
        prev_layout = QHBoxLayout()
        self.prev_icon = ImagePreview("Icono")
        self.prev_logo = ImagePreview("Logo")
        prev_layout.addWidget(self.prev_icon)
        prev_layout.addWidget(self.prev_logo)
        prev_layout.addStretch()
        right_layout.addLayout(prev_layout)
        
        right_layout.addStretch()
        
        # Botones de Acción
        actions_layout = QHBoxLayout()
        
        btn_test = StyledButton("▶ PROBAR", "success")
        btn_test.clicked.connect(self.test_game)
        
        btn_edit = StyledButton("✏️ EDITAR", "primary")
        btn_edit.clicked.connect(self.edit_game)
        
        btn_del = StyledButton("🗑️ ELIMINAR", "danger")
        btn_del.clicked.connect(self.delete_game)
        
        actions_layout.addWidget(btn_test)
        actions_layout.addWidget(btn_edit)
        actions_layout.addStretch()
        actions_layout.addWidget(btn_del)
        
        right_layout.addLayout(actions_layout)
        
        main_layout.addWidget(self.right_panel)
        
        # Label de "Bienvenida" (cuando no hay selección)
        self.lbl_welcome = QLabel("Selecciona un juego de la lista\no crea uno nuevo.")
        self.lbl_welcome.setAlignment(Qt.AlignCenter)
        self.lbl_welcome.setStyleSheet(f"font-size: 20px; color: {THEME['text_dim']};")
        main_layout.addWidget(self.lbl_welcome)

    def refresh_list(self):
        self.list_widget.clear()
        self.manager.load()
        for g in self.manager.games:
            self.list_widget.addItem(g.nombre)
        
        # Reset view
        self.right_panel.hide()
        self.lbl_welcome.show()

    def on_game_selected(self, idx):
        if idx < 0: return
        
        self.lbl_welcome.hide()
        self.right_panel.show()
        
        game = self.manager.games[idx]
        self.lbl_game_title.setText(game.nombre)
        self.lbl_game_path.setText(f"$ {game.ruta_ejecutable}")
        
        self.prev_icon.set_image(game.icon)
        self.prev_logo.set_image(game.logo)

    def add_game(self):
        dlg = GameFormDialog(self, self.manager)
        if dlg.exec() and dlg.result_game:
            self.manager.games.append(dlg.result_game)
            self.manager.save()
            self.refresh_list()
            # Seleccionar el nuevo
            self.list_widget.setCurrentRow(len(self.manager.games) - 1)

    def edit_game(self):
        idx = self.list_widget.currentRow()
        if idx < 0: return
        
        current_game = self.manager.games[idx]
        dlg = GameFormDialog(self, self.manager, current_game)
        
        if dlg.exec() and dlg.result_game:
            self.manager.games[idx] = dlg.result_game
            self.manager.save()
            self.refresh_list()
            self.list_widget.setCurrentRow(idx)

    def delete_game(self):
        idx = self.list_widget.currentRow()
        if idx < 0: return
        
        game = self.manager.games[idx]
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar Eliminación")
        msg.setText(f"¿Estás seguro de eliminar '{game.nombre}'?")
        msg.setInformativeText("Esto borrará la entrada del JSON y las carpetas de assets/games asociadas.\nEsta acción es irreversible.")
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        if msg.exec() == QMessageBox.Yes:
            # Eliminar archivos físicos
            report = FileSystemHandler.delete_game_content(game.nombre)
            
            # Eliminar de la lista
            del self.manager.games[idx]
            self.manager.save()
            
            # Feedback
            info = "\n".join(report) if report else "No se encontraron archivos físicos."
            QMessageBox.information(self, "Eliminado", f"Juego eliminado correctamente.\n\n{info}")
            
            self.refresh_list()

    def test_game(self):
        idx = self.list_widget.currentRow()
        game = self.manager.games[idx]
        
        script_path = BASE_DIR / game.ruta_ejecutable
        
        if not script_path.exists():
            QMessageBox.critical(self, "Error", f"No se encuentra el script:\n{script_path}")
            return
            
        try:
            # Ejecutar el script manteniendo el directorio de trabajo correcto
            subprocess.Popen([str(script_path)], cwd=script_path.parent)
        except Exception as e:
            QMessageBox.critical(self, "Error de Ejecución", f"Fallo al lanzar:\n{e}")

# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    app = QApplication(sys.argv)
    
    # Fuente global moderna
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
