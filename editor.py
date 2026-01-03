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
    QFileDialog, QMessageBox, QFrame, QGroupBox, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, QSize, QUrl, QTimer
from PySide6.QtGui import QFont, QPixmap, QImage, QDesktopServices, QColor

# =============================================================================
# LOGGING & CONFIGURATION
# =============================================================================

# Definir rutas base relativas al ejecutable/script
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).parent.resolve()

# Crear directorio de logs
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
BACKUP_DIR = BASE_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "editor.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger("").addHandler(console)

logger = logging.getLogger(__name__)

# Configuración Visual
THEME = {
    "bg_main": "#0a0e14",
    "bg_surface": "#101520",
    "bg_card": "#151b26",
    "bg_hover": "#1a2332",
    "accent": "#00d9ff",
    "accent_hover": "#00b8d9",
    "accent_dark": "#008ca8",
    "text_primary": "#e8eaed",
    "text_secondary": "#9aa0a6",
    "text_disabled": "#5f6368",
    "success": "#34d399",
    "warning": "#fbbf24",
    "danger": "#f87171",
    "border": "#1f2937",
}

# =============================================================================
# CORE: DATA MODEL
# =============================================================================

@dataclass
class Game:
    """Modelo de datos estricto compatible con games.json del Launcher."""
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
        # Filtra claves extrañas para evitar corrupción del JSON
        valid_keys = cls.__annotations__.keys()
        clean_d = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**clean_d)

    def is_valid_for_launcher(self) -> Tuple[bool, List[str]]:
        """Valida que el juego funcionará en main.py."""
        errors = []
        
        # 1. Validar campos obligatorios
        if not self.nombre:
            errors.append("El nombre es obligatorio.")
        
        # 2. Validar existencia de archivos (Rutas relativas a BASE_DIR)
        check_files = [
            ("Ejecutable", self.ruta_ejecutable),
            ("Icono", self.icon),
            ("Logo", self.logo),
            # El sonido es opcional en algunos casos, pero el launcher lo usa
            ("Sonido", self.sound) 
        ]

        for label, rel_path in check_files:
            if not rel_path:
                errors.append(f"{label} no definido.")
                continue
            
            full_path = BASE_DIR / rel_path
            if not full_path.exists():
                errors.append(f"{label} no encontrado en: {rel_path}")
            elif label == "Ejecutable":
                if not os.access(full_path, os.X_OK) and not full_path.suffix == '.sh':
                    # Warning leve, el launcher usa subprocess que a veces maneja permisos
                    logger.warning(f"El ejecutable {rel_path} podría no tener permisos de ejecución (+x).")

        return len(errors) == 0, errors

# =============================================================================
# CORE: EMULATOR & STRUCTURE MANAGER
# =============================================================================

class EmulatorManager:
    """Detecta emuladores instalados y gestiona plantillas."""
    
    DEFAULT_TEMPLATES = {
        "Vacio (Solo estructura)": {
            "cmd": "# Comando personalizado aquí",
            "desc": "Estructura vacía"
        },
        "Wine (Windows .exe)": {
            "cmd": "wine \"./game.exe\"",
            "desc": "Wine Wrapper"
        }
    }

    def __init__(self):
        self.templates = self.DEFAULT_TEMPLATES.copy()
        self.detect_emulators()

    def detect_emulators(self):
        """Escanea rutas relativas comunes usadas por el proyecto."""
        # Definición de rutas relativas comunes (subir dos niveles desde bin/games)
        checks = [
            ("Dolphin (GameCube/Wii)", "../../dolphin-emulator/dolphin-emu", "-b -e \"./game.iso\""),
            ("Citra/Azahar (3DS)", "../../3ds/azahar.AppImage", "\"./game.3ds\""),
            ("MelonDS (NDS)", "../../nds/melonDS", "\"./game.nds\""),
            ("Ryujinx (Switch)", "../../ryujinx/Ryujinx", "\"./game.nsp\"")
        ]

        logger.info("Escaneando emuladores...")
        for name, rel_path, args in checks:
            # Construir ruta absoluta para verificar existencia
            # Asumimos que BASE_DIR está al nivel de main.py
            full_path = (BASE_DIR / rel_path).resolve()
            
            if full_path.exists():
                logger.info(f"Emulador detectado: {name} en {rel_path}")
                self.templates[name] = {
                    "cmd": f"{rel_path} {args}",
                    "desc": f"Auto-detectado: {name}"
                }
            else:
                # Opcional: Agregar plantilla genérica aunque no exista el binario
                # para permitir configuración manual
                self.templates[f"{name} (No detectado)"] = {
                    "cmd": f"{rel_path} {args}",
                    "desc": "Binario no encontrado automáticamente"
                }

class StructureHelper:
    """Maneja la creación de archivos y carpetas de forma segura."""

    @staticmethod
    def sanitize_name(name: str) -> str:
        """Sanitiza el nombre para uso en rutas de archivo."""
        s = name.lower().strip()
        s = re.sub(r'[^\w\s-]', '', s)
        return re.sub(r'[\s_-]+', '_', s)

    @staticmethod
    def create_game_structure(game_name: str, template_data: dict) -> Dict[str, str]:
        """
        Crea la estructura standard:
        games/{safe_name}/run
        assets/{safe_name}/{icon,logo,sound}
        """
        safe_name = StructureHelper.sanitize_name(game_name)
        
        # Rutas absolutas
        game_dir = BASE_DIR / "games" / safe_name
        assets_dir = BASE_DIR / "assets" / safe_name
        
        try:
            game_dir.mkdir(parents=True, exist_ok=True)
            assets_dir.mkdir(parents=True, exist_ok=True)
            
            # Crear script RUN
            run_script_path = game_dir / "run"
            with open(run_script_path, "w", encoding="utf-8") as f:
                f.write(
                    "#!/bin/sh\n"
                    "cd \"$(dirname \"$0\")\" || exit 1\n"
                    f"# Generado por Game Editor - {template_data['desc']}\n"
                    f"{template_data['cmd']}\n"
                )
            
            # Dar permisos de ejecución (+x)
            st = os.stat(run_script_path)
            os.chmod(run_script_path, st.st_mode | stat.S_IEXEC)
            
            logger.info(f"Estructura creada para: {game_name}")
            
            # Retornar rutas relativas para el JSON
            return {
                "ruta_ejecutable": f"games/{safe_name}/run",
                "icon": f"assets/{safe_name}/icon.png",
                "logo": f"assets/{safe_name}/logo.png",
                "sound": f"assets/{safe_name}/sound.wav"
            }
            
        except Exception as e:
            logger.error(f"Error creando estructura: {e}")
            raise e

# =============================================================================
# LOGIC: GAME MANAGER
# =============================================================================

class GameManager:
    def __init__(self, filename="games.json"):
        self.filename = BASE_DIR / filename
        self.games: List[Game] = []
        self.emulator_manager = EmulatorManager()

    def load_games(self) -> List[Game]:
        """Carga games.json con manejo de errores robusto."""
        if not self.filename.exists():
            logger.warning(f"{self.filename} no existe. Iniciando lista vacía.")
            return []
            
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.games = [Game.from_dict(x) for x in data]
            logger.info(f"Cargados {len(self.games)} juegos.")
            return self.games
        except json.JSONDecodeError as e:
            logger.error(f"JSON corrupto: {e}")
            self.backup_config(suffix="_CORRUPT")
            return []
        except Exception as e:
            logger.critical(f"Error fatal cargando juegos: {e}")
            return []

    def save_games(self) -> bool:
        """Guarda games.json y genera backup previo."""
        try:
            # 1. Crear backup automático
            self.backup_config()
            
            # 2. Guardar nuevo archivo
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump([g.to_dict() for g in self.games], f, indent=2, ensure_ascii=False)
            
            logger.info("Base de datos guardada exitosamente.")
            return True
        except Exception as e:
            logger.error(f"Error guardando juegos: {e}")
            return False

    def backup_config(self, suffix: str = ""):
        """Crea una copia de seguridad en la carpeta backups."""
        if not self.filename.exists():
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"games_{timestamp}{suffix}.json"
        backup_path = BACKUP_DIR / backup_name
        
        try:
            shutil.copy2(self.filename, backup_path)
            
            # Mantener solo los últimos 10 backups
            backups = sorted(BACKUP_DIR.glob("games_*.json"), key=os.path.getmtime)
            while len(backups) > 10:
                os.remove(backups.pop(0))
                
            logger.info(f"Backup creado: {backup_name}")
        except Exception as e:
            logger.error(f"Fallo al crear backup: {e}")

    def delete_game_assets(self, game: Game) -> Tuple[List[str], List[str]]:
        """Elimina físicamente las carpetas asociadas."""
        safe_name = StructureHelper.sanitize_name(game.nombre)
        deleted = []
        errors = []

        paths_to_remove = [
            BASE_DIR / "assets" / safe_name,
            BASE_DIR / "games" / safe_name
        ]

        for path in paths_to_remove:
            if path.exists():
                try:
                    shutil.rmtree(path)
                    deleted.append(str(path.relative_to(BASE_DIR)))
                except Exception as e:
                    errors.append(f"Error borrando {path.name}: {e}")
        
        return deleted, errors

# =============================================================================
# UI COMPONENTS
# =============================================================================

class StyledButton(QPushButton):
    def __init__(self, text, style_type="primary", parent=None):
        super().__init__(text, parent)
        self.style_type = style_type
        self.setCursor(Qt.PointingHandCursor)
        self.apply_style()
        
    def apply_style(self):
        styles = {
            "primary": (THEME["accent"], THEME["accent_hover"], "#000000"),
            "danger": (THEME["danger"], "#dc2626", "#ffffff"),
            "success": (THEME["success"], "#10b981", "#000000"),
            "secondary": (THEME["bg_card"], THEME["bg_hover"], THEME["text_primary"]),
        }
        
        bg, bg_hover, text_color = styles.get(self.style_type, styles["secondary"])
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {THEME["accent_dark"]};
            }}
        """)

class ImagePreviewWidget(QLabel):
    def __init__(self, size=(200, 150)):
        super().__init__()
        self.setFixedSize(*size)
        self.setStyleSheet(f"border: 2px dashed {THEME['border']}; border-radius: 8px; background: {THEME['bg_surface']};")
        self.setAlignment(Qt.AlignCenter)
        self.setText("Sin Vista Previa")

    def load_image(self, path: str):
        full_path = BASE_DIR / path
        if full_path.exists() and full_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
            pixmap = QPixmap(str(full_path))
            if not pixmap.isNull():
                self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self.setText("Imagen no válida\no no encontrada")
        self.setPixmap(QPixmap()) # Clear

# =============================================================================
# DIALOGS
# =============================================================================

class GameFormDialog(QDialog):
    def __init__(self, parent, manager: GameManager, game: Optional[Game] = None):
        super().__init__(parent)
        self.manager = manager
        self.game_result = None
        self.editing_mode = game is not None
        
        self.setup_ui()
        if game:
            self.load_data(game)
            
    def setup_ui(self):
        self.setWindowTitle("Editor de Juego" if not self.editing_mode else "Editar Juego")
        self.setMinimumSize(900, 750)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {THEME["bg_main"]}; color: {THEME["text_primary"]}; }}
            QLabel {{ color: {THEME["text_primary"]}; font-size: 13px; }}
            QLineEdit, QComboBox {{
                background-color: {THEME["bg_card"]};
                color: {THEME["text_primary"]};
                border: 1px solid {THEME["border"]};
                border-radius: 4px;
                padding: 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {THEME["accent"]}; }}
            QGroupBox {{
                border: 1px solid {THEME["border"]};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 24px;
                color: {THEME["accent"]};
                font-weight: bold;
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("Configuración del Juego")
        header.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {THEME['text_primary']};")
        main_layout.addWidget(header)

        # Content Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        
        # 1. Info Básica
        self.layout.addWidget(QLabel("Nombre del Juego:"))
        self.name_input = QLineEdit()
        self.layout.addWidget(self.name_input)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Tipo:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["binario", "script", "appimage", "wine"])
        type_layout.addWidget(self.type_combo)
        self.layout.addLayout(type_layout)

        # 2. Auto Configuración
        auto_group = QGroupBox("🚀 Asistente de Estructura")
        auto_layout = QHBoxLayout()
        
        self.template_combo = QComboBox()
        # Cargar plantillas del EmulatorManager
        for name in self.manager.emulator_manager.templates.keys():
            self.template_combo.addItem(name)
            
        auto_layout.addWidget(QLabel("Plantilla:"))
        auto_layout.addWidget(self.template_combo, 1)
        
        create_btn = StyledButton("Crear Carpetas y Scripts", "success")
        create_btn.clicked.connect(self.create_structure)
        auto_layout.addWidget(create_btn)
        
        auto_group.setLayout(auto_layout)
        self.layout.addWidget(auto_group)

        # 3. Archivos (Inputs + Browsers)
        files_group = QGroupBox("📁 Archivos y Assets")
        files_layout = QVBoxLayout()
        
        self.path_inputs = {}
        self.previews = {}
        
        fields = [
            ("ruta_ejecutable", "Script Ejecutable", "file"),
            ("icon", "Icono (PNG/JPG)", "image"),
            ("logo", "Logo (PNG/JPG)", "image"),
            ("sound", "Sonido (WAV)", "audio")
        ]
        
        for key, label, ftype in fields:
            h = QHBoxLayout()
            h.addWidget(QLabel(label))
            
            inp = QLineEdit()
            inp.setPlaceholderText(f"Ruta relativa (ej: games/nombre/run)")
            self.path_inputs[key] = inp
            h.addWidget(inp, 1)
            
            browse = QPushButton("...")
            browse.setFixedWidth(40)
            browse.setStyleSheet(f"background: {THEME['bg_card']}; color: {THEME['accent']}; border: 1px solid {THEME['border']};")
            browse.clicked.connect(lambda c, k=key, t=ftype: self.browse_file(k, t))
            h.addWidget(browse)
            
            files_layout.addLayout(h)
            
            # Previsualización para imágenes
            if ftype == "image":
                prev = ImagePreviewWidget()
                h.addWidget(prev)
                self.previews[key] = prev
                inp.textChanged.connect(lambda t, k=key: self.previews[k].load_image(t))

        files_group.setLayout(files_layout)
        self.layout.addWidget(files_group)
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # Footer Buttons
        btn_layout = QHBoxLayout()
        
        self.check_btn = StyledButton("🔍 Validar Compatibilidad", "secondary")
        self.check_btn.clicked.connect(self.validate_current)
        btn_layout.addWidget(self.check_btn)
        
        btn_layout.addStretch()
        
        cancel = StyledButton("Cancelar", "danger")
        cancel.clicked.connect(self.reject)
        btn_layout.addWidget(cancel)
        
        save = StyledButton("Guardar Juego", "success")
        save.clicked.connect(self.save)
        btn_layout.addWidget(save)
        
        main_layout.addLayout(btn_layout)

    def create_structure(self):
        name = self.name_input.text()
        if not name:
            QMessageBox.warning(self, "Error", "Debes escribir un nombre primero.")
            return

        template_name = self.template_combo.currentText()
        template_data = self.manager.emulator_manager.templates.get(template_name)
        
        if not template_data:
            return

        try:
            paths = StructureHelper.create_game_structure(name, template_data)
            for key, val in paths.items():
                self.path_inputs[key].setText(val)
            QMessageBox.information(self, "Éxito", f"Estructura creada para '{name}'\nSe han generado las carpetas y el script run.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo crear la estructura: {e}")

    def browse_file(self, key, ftype):
        start_dir = str(BASE_DIR)
        if ftype == "image":
            f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Imagen", start_dir, "Images (*.png *.jpg *.jpeg)")
        elif ftype == "audio":
            f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Audio", start_dir, "Audio (*.wav *.mp3 *.ogg)")
        else:
            f, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo", start_dir, "All Files (*)")
            
        if f:
            # Intentar convertir a ruta relativa
            path_obj = Path(f)
            try:
                rel = path_obj.relative_to(BASE_DIR)
                self.path_inputs[key].setText(str(rel))
            except ValueError:
                # Si está fuera de la carpeta base, preguntar si importar
                reply = QMessageBox.question(
                    self, "Importar Archivo",
                    "El archivo está fuera de la carpeta del proyecto.\n¿Quieres copiarlo a la carpeta 'assets'?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.import_asset(path_obj, key)
                else:
                    self.path_inputs[key].setText(f) # Se queda absoluta (puede romper el launcher portable)

    def import_asset(self, src_path: Path, key: str):
        name = self.name_input.text()
        if not name:
            QMessageBox.warning(self, "Error", "Define el nombre del juego antes de importar assets.")
            return
            
        safe_name = StructureHelper.sanitize_name(name)
        dest_dir = BASE_DIR / "assets" / safe_name
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        dest_path = dest_dir / src_path.name
        try:
            shutil.copy2(src_path, dest_path)
            rel = dest_path.relative_to(BASE_DIR)
            self.path_inputs[key].setText(str(rel))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Fallo al copiar archivo: {e}")

    def load_data(self, game: Game):
        self.name_input.setText(game.nombre)
        self.type_combo.setCurrentText(game.tipo)
        self.path_inputs["ruta_ejecutable"].setText(game.ruta_ejecutable)
        self.path_inputs["icon"].setText(game.icon)
        self.path_inputs["logo"].setText(game.logo)
        self.path_inputs["sound"].setText(game.sound)

    def validate_current(self):
        """Ejecuta la validación sin cerrar el diálogo."""
        temp_game = self._build_game_object()
        ok, errors = temp_game.is_valid_for_launcher()
        
        if ok:
            QMessageBox.information(self, "Compatible", "✅ El juego parece 100% compatible con el Launcher.")
        else:
            msg = "\n".join([f"• {e}" for e in errors])
            QMessageBox.warning(self, "Problemas Detectados", f"Se encontraron problemas:\n\n{msg}")

    def _build_game_object(self) -> Game:
        return Game(
            nombre=self.name_input.text(),
            tipo=self.type_combo.currentText(),
            ruta_ejecutable=self.path_inputs["ruta_ejecutable"].text(),
            icon=self.path_inputs["icon"].text(),
            logo=self.path_inputs["logo"].text(),
            sound=self.path_inputs["sound"].text()
        )

    def save(self):
        game = self._build_game_object()
        
        # Validación crítica antes de guardar
        ok, errors = game.is_valid_for_launcher()
        if not ok:
            res = QMessageBox.warning(
                self, "Advertencia de Compatibilidad",
                "El juego tiene configuraciones que harán fallar al Launcher:\n\n" + 
                "\n".join(errors) + 
                "\n\n¿Guardar de todos modos?",
                QMessageBox.Yes | QMessageBox.No
            )
            if res == QMessageBox.No:
                return

        self.game_result = game
        self.accept()

# =============================================================================
# MAIN WINDOW
# =============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = GameManager()
        self.setup_ui()
        self.refresh_list()
        
    def setup_ui(self):
        self.setWindowTitle("3D All Stars - Gestor de Juegos")
        self.setMinimumSize(1000, 700)
        self.setWindowIcon(QIcon(str(BASE_DIR / "assets" / "vinyl_disc.png"))) # Intento de cargar icono si existe
        
        # Central Widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        
        # --- LEFT PANEL (LIST) ---
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        header_label = QLabel("BIBLIOTECA")
        header_label.setStyleSheet(f"color: {THEME['text_disabled']}; font-weight: bold; letter-spacing: 1px;")
        left_layout.addWidget(header_label)
        
        self.game_list = QListWidget()
        self.game_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {THEME['bg_surface']};
                border: 1px solid {THEME['border']};
                border-radius: 8px;
                color: {THEME['text_primary']};
                font-size: 14px;
            }}
            QListWidget::item {{ padding: 10px; }}
            QListWidget::item:selected {{ background-color: {THEME['accent']}; color: black; }}
        """)
        self.game_list.currentRowChanged.connect(self.on_selection_change)
        left_layout.addWidget(self.game_list)
        
        # Botones inferiores lista
        list_btns = QHBoxLayout()
        add_btn = StyledButton("+ Nuevo Juego", "primary")
        add_btn.clicked.connect(self.add_game)
        list_btns.addWidget(add_btn)
        left_layout.addLayout(list_btns)
        
        main_layout.addWidget(left_panel, 1) # 33% width
        
        # --- RIGHT PANEL (DETAILS) ---
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background-color: {THEME['bg_surface']}; border-radius: 12px;")
        self.right_layout = QVBoxLayout(right_panel)
        
        # Placeholder por defecto
        self.placeholder = QLabel("Selecciona un juego para ver detalles")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"color: {THEME['text_disabled']}; font-size: 16px;")
        self.right_layout.addWidget(self.placeholder)
        
        # Contenedor de detalles (Oculto inicialmente)
        self.details_container = QWidget()
        det_layout = QVBoxLayout(self.details_container)
        
        # Título del juego
        self.title_lbl = QLabel("")
        self.title_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {THEME['accent']}; margin-bottom: 10px;")
        det_layout.addWidget(self.title_lbl)
        
        # Info Grid
        info_widget = QWidget()
        info_grid = QVBoxLayout(info_widget)
        self.info_lbls = QLabel("")
        self.info_lbls.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 14px; line-height: 1.6;")
        info_grid.addWidget(self.info_lbls)
        det_layout.addWidget(info_widget)
        
        # Preview Imagen
        self.preview_img = QLabel()
        self.preview_img.setAlignment(Qt.AlignCenter)
        self.preview_img.setFixedHeight(200)
        self.preview_img.setStyleSheet(f"border: 2px solid {THEME['border']}; border-radius: 8px; background: {THEME['bg_main']};")
        det_layout.addWidget(self.preview_img)
        
        det_layout.addStretch()
        
        # Botones de Acción
        actions_layout = QHBoxLayout()
        
        self.test_btn = StyledButton("▶ Probar Script", "success")
        self.test_btn.clicked.connect(self.test_game_script)
        
        edit_btn = StyledButton("✏ Editar", "secondary")
        edit_btn.clicked.connect(self.edit_game)
        
        del_btn = StyledButton("🗑 Eliminar", "danger")
        del_btn.clicked.connect(self.delete_game)
        
        actions_layout.addWidget(self.test_btn)
        actions_layout.addWidget(edit_btn)
        actions_layout.addWidget(del_btn)
        
        det_layout.addLayout(actions_layout)
        
        self.right_layout.addWidget(self.details_container)
        self.details_container.hide()
        
        main_layout.addWidget(right_panel, 2) # 66% width

        # Status Bar
        self.statusBar().showMessage("Listo. Sistema compatible con Launcher v1.0")
        self.statusBar().setStyleSheet(f"color: {THEME['text_disabled']};")

    def refresh_list(self):
        self.game_list.clear()
        games = self.manager.load_games()
        for g in games:
            self.game_list.addItem(g.nombre)
        self.details_container.hide()
        self.placeholder.show()

    def on_selection_change(self, idx):
        if idx < 0: return
        
        game = self.manager.games[idx]
        self.placeholder.hide()
        self.details_container.show()
        
        self.title_lbl.setText(game.nombre.upper())
        
        # Validar paths para mostrar status
        ok, errors = game.is_valid_for_launcher()
        status_icon = "✅ Compatible" if ok else "⚠️ Configuración Inválida"
        status_color = THEME['success'] if ok else THEME['warning']
        
        info_text = f"""
        <b>ESTADO:</b> <span style="color:{status_color}">{status_icon}</span><br>
        <b>TIPO:</b> {game.tipo}<br>
        <b>EJECUTABLE:</b> {game.ruta_ejecutable}<br>
        <b>ASSETS:</b> {game.icon} | {game.logo}
        """
        self.info_lbls.setText(info_text)
        
        # Cargar preview (Logo preferiblemente)
        logo_path = BASE_DIR / game.logo
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            self.preview_img.setPixmap(pix.scaled(self.preview_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.preview_img.setText("Sin Logo")

    def add_game(self):
        dlg = GameFormDialog(self, self.manager)
        if dlg.exec():
            self.manager.games.append(dlg.game_result)
            if self.manager.save_games():
                self.refresh_list()
                self.statusBar().showMessage(f"Juego '{dlg.game_result.nombre}' agregado.")

    def edit_game(self):
        idx = self.game_list.currentRow()
        if idx < 0: return
        
        original_game = self.manager.games[idx]
        dlg = GameFormDialog(self, self.manager, original_game)
        if dlg.exec():
            self.manager.games[idx] = dlg.game_result
            if self.manager.save_games():
                self.refresh_list()
                self.game_list.setCurrentRow(idx)
                self.statusBar().showMessage(f"Juego actualizado.")

    def delete_game(self):
        idx = self.game_list.currentRow()
        if idx < 0: return
        
        game = self.manager.games[idx]
        confirm = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Estás seguro de eliminar '{game.nombre}'?\n\nEsto borrará la entrada del JSON y sus carpetas de assets/games.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            deleted_files, errors = self.manager.delete_game_assets(game)
            del self.manager.games[idx]
            self.manager.save_games()
            self.refresh_list()
            
            msg = f"Juego eliminado.\nArchivos borrados: {len(deleted_files)}"
            if errors:
                msg += f"\nErrores: {len(errors)}"
                logger.error(f"Errores al borrar: {errors}")
                
            self.statusBar().showMessage(msg)

    def test_game_script(self):
        """Simula la ejecución tal como lo haría el Launcher."""
        idx = self.game_list.currentRow()
        if idx < 0: return
        
        game = self.manager.games[idx]
        script_path = BASE_DIR / game.ruta_ejecutable
        
        if not script_path.exists():
            QMessageBox.critical(self, "Error", f"El script no existe:\n{script_path}")
            return
            
        try:
            # Ejecutar de manera similar a main.py
            # Usamos subprocess.Popen para no congelar la UI, pero capturamos output
            logger.info(f"Probando script: {script_path}")
            subprocess.Popen([str(script_path)], cwd=script_path.parent)
            self.statusBar().showMessage(f"Ejecutando {game.nombre}...")
        except Exception as e:
            QMessageBox.critical(self, "Fallo Ejecución", f"Error al lanzar subprocess:\n{e}")

# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    app = QApplication(sys.argv)
    
    # Fuente Global consistente
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Paleta oscura básica para integración con entorno Linux
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(THEME["bg_main"]))
    palette.setColor(QPalette.WindowText, QColor(THEME["text_primary"]))
    app.setPalette(palette)
    
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Crash no controlado: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
