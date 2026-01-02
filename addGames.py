#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3D All Stars Game Editor - (PySide6)
---------------------------------------------------
"""

import sys
import os
import json
import shutil
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QDialog, QLineEdit, QComboBox,
    QFileDialog, QMessageBox, QFrame, QGroupBox, QSplitter, QListWidgetItem
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPalette, QColor, QIcon

# =============================================================================
# THEME CONFIG
# =============================================================================

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
# EMULATOR TEMPLATES
# =============================================================================

EMULATOR_TEMPLATES = {
    "Vacio (Solo estructura)": {
        "cmd": "# Comando personalizado aquí",
        "desc": "Estructura vacía"
    },
    "Dolphin (GameCube/Wii)": {
        "cmd": "../../dolphin-emulator/dolphin-emu -b -e \"./game.iso\"",
        "desc": "ISO/WBFS"
    },
    "Azahar/Citra (3DS)": {
        "cmd": "../../3ds/azahar.AppImage \"./game.3ds\"",
        "desc": "3DS/CCI"
    },
    "Wine (Windows)": {
        "cmd": "wine \"./game.exe\"",
        "desc": "Wine EXE"
    }
}

# =============================================================================
# DATA MODEL
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
        return cls(**{k: v for k, v in d.items() if k in cls.__annotations__})

# =============================================================================
# STRUCTURE HELPER
# =============================================================================

class StructureHelper:

    @staticmethod
    def sanitize_name(name: str) -> str:
        s = name.lower().strip()
        s = re.sub(r'[^\w\s-]', '', s)
        return re.sub(r'[\s_-]+', '_', s)

    @staticmethod
    def create_structure(base: Path, name: str, template: str):
        safe = StructureHelper.sanitize_name(name)
        gdir = base / "games" / safe
        adir = base / "assets" / safe

        gdir.mkdir(parents=True, exist_ok=True)
        adir.mkdir(parents=True, exist_ok=True)

        run = gdir / "run"
        t = EMULATOR_TEMPLATES[template]

        with open(run, "w", encoding="utf-8") as f:
            f.write(
                "#!/bin/sh\n"
                "cd \"$(dirname \"$0\")\" || exit 1\n"
                f"# {t['desc']}\n"
                f"{t['cmd']}\n"
            )

        os.chmod(run, os.stat(run).st_mode | stat.S_IEXEC)

        return {
            "ruta_ejecutable": f"games/{safe}/run",
            "icon": f"assets/{safe}/icon.png",
            "logo": f"assets/{safe}/logo.png",
            "sound": f"assets/{safe}/sound.wav"
        }

# =============================================================================
# GAME MANAGER
# =============================================================================

class GameManager:
    def __init__(self, filename="games.json"):
        self.filename = Path(filename)
        self.backup = self.filename.with_suffix(".json.backup")
        self.games: List[Game] = []

    def load_games(self):
        if not self.filename.exists():
            return []
        with open(self.filename, "r", encoding="utf-8") as f:
            self.games = [Game.from_dict(x) for x in json.load(f)]
        return self.games

    def save_games(self):
        if self.filename.exists():
            shutil.copy2(self.filename, self.backup)
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump([g.to_dict() for g in self.games], f, indent=2, ensure_ascii=False)
        return True

    def validate_game(self, game: Game):
        base = self.filename.parent
        if not game.nombre:
            return False, "Nombre obligatorio"
        if not (base / game.ruta_ejecutable).exists():
            return False, "Script no existe (CRÍTICO)"
        return True, "OK"

    def delete_game_files(self, game: Game) -> bool:
        """Elimina las carpetas assets y games del juego"""
        base = self.filename.parent
        safe_name = StructureHelper.sanitize_name(game.nombre)
        
        deleted = []
        errors = []
        
        # Eliminar carpeta de assets
        assets_path = base / "assets" / safe_name
        if assets_path.exists():
            try:
                shutil.rmtree(assets_path)
                deleted.append(f"assets/{safe_name}")
            except Exception as e:
                errors.append(f"Error en assets: {e}")
        
        # Eliminar carpeta de games
        games_path = base / "games" / safe_name
        if games_path.exists():
            try:
                shutil.rmtree(games_path)
                deleted.append(f"games/{safe_name}")
            except Exception as e:
                errors.append(f"Error en games: {e}")
        
        return deleted, errors

# =============================================================================
# STYLED WIDGETS
# =============================================================================

class StyledButton(QPushButton):
    def __init__(self, text, style_type="primary", parent=None):
        super().__init__(text, parent)
        self.style_type = style_type
        self.apply_style()
        
    def apply_style(self):
        if self.style_type == "primary":
            bg = THEME["accent"]
            bg_hover = THEME["accent_hover"]
            text_color = "#000000"
        elif self.style_type == "danger":
            bg = THEME["danger"]
            bg_hover = "#dc2626"
            text_color = "#ffffff"
        elif self.style_type == "success":
            bg = THEME["success"]
            bg_hover = "#10b981"
            text_color = "#000000"
        else:  # secondary
            bg = THEME["bg_card"]
            bg_hover = THEME["bg_hover"]
            text_color = THEME["text_primary"]
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: {bg_hover};
            }}
            QPushButton:pressed {{
                background-color: {THEME["accent_dark"]};
            }}
        """)

# =============================================================================
# GAME FORM DIALOG
# =============================================================================

class GameFormDialog(QDialog):
    def __init__(self, parent, manager, game=None):
        super().__init__(parent)
        self.manager = manager
        self.base = manager.filename.parent
        self.result = None
        self.editing = game
        
        self.setup_ui()
        if game:
            self.load_game(game)
    
    def setup_ui(self):
        self.setWindowTitle("Editor de Juego" if not self.editing else "Editar Juego")
        self.setMinimumSize(800, 700)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {THEME["bg_main"]};
            }}
            QLabel {{
                color: {THEME["text_primary"]};
                font-size: 13px;
            }}
            QLineEdit, QComboBox {{
                background-color: {THEME["bg_card"]};
                color: {THEME["text_primary"]};
                border: 2px solid {THEME["border"]};
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 2px solid {THEME["accent"]};
            }}
            QGroupBox {{
                color: {THEME["text_primary"]};
                font-size: 14px;
                font-weight: 600;
                border: 2px solid {THEME["border"]};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Título
        title = QLabel("✨ NUEVO JUEGO" if not self.editing else "✏️ EDITAR JUEGO")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {THEME['accent']};")
        layout.addWidget(title)
        
        # Nombre
        layout.addWidget(QLabel("Nombre del Juego"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ej: Super Mario Galaxy")
        layout.addWidget(self.name_input)
        
        # Tipo
        layout.addWidget(QLabel("Tipo de Ejecutable"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["binario", "appimage", "script"])
        layout.addWidget(self.type_combo)
        
        # Auto Config
        auto_group = QGroupBox("🚀 Auto Configuración")
        auto_layout = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(EMULATOR_TEMPLATES.keys()))
        auto_layout.addWidget(self.template_combo, 1)
        
        create_btn = StyledButton("Crear Estructura", "success")
        create_btn.clicked.connect(self.create_structure)
        auto_layout.addWidget(create_btn)
        
        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)
        
        # Archivos
        files_group = QGroupBox("📁 Archivos")
        files_layout = QVBoxLayout()
        
        self.file_inputs = {}
        file_configs = [
            ("ruta_ejecutable", "Script Ejecutable", "file"),
            ("icon", "Icono (PNG/JPG)", "image"),
            ("logo", "Logo (PNG/JPG)", "image"),
            ("sound", "Sonido (WAV/MP3)", "audio"),
        ]
        
        for key, label, file_type in file_configs:
            row = QHBoxLayout()
            row.addWidget(QLabel(label), 0)
            
            input_field = QLineEdit()
            input_field.setPlaceholderText(f"Ruta del {label.lower()}")
            self.file_inputs[key] = input_field
            row.addWidget(input_field, 1)
            
            browse_btn = QPushButton("📂 Buscar")
            browse_btn.setFixedWidth(100)
            browse_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME["bg_card"]};
                    color: {THEME["accent"]};
                    border: 2px solid {THEME["accent"]};
                    border-radius: 6px;
                    padding: 8px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {THEME["accent"]};
                    color: #000000;
                }}
            """)
            browse_btn.clicked.connect(lambda checked, k=key, ft=file_type: self.browse_file(k, ft))
            row.addWidget(browse_btn)
            
            files_layout.addLayout(row)
        
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Botones
        layout.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        
        save_btn = StyledButton("💾 GUARDAR", "primary")
        save_btn.clicked.connect(self.save_game)
        buttons.addWidget(save_btn)
        
        cancel_btn = StyledButton("❌ CANCELAR", "secondary")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)
        
        layout.addLayout(buttons)
    
    def create_structure(self):
        name = self.name_input.text()
        if not name:
            QMessageBox.warning(self, "Advertencia", "Primero escribe el nombre del juego")
            return
        
        paths = StructureHelper.create_structure(
            self.base, 
            name, 
            self.template_combo.currentText()
        )
        
        for key, path in paths.items():
            self.file_inputs[key].setText(path)
        
        QMessageBox.information(self, "Éxito", "✅ Estructura de carpetas creada correctamente")
    
    def browse_file(self, field_name, file_type):
        if file_type == "image":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                f"Seleccionar {field_name}",
                "",
                "Imágenes (*.png *.jpg *.jpeg *.gif *.bmp);;Todos los archivos (*.*)"
            )
            if file_path:
                self.copy_image(file_path, field_name)
        elif file_type == "audio":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar sonido",
                "",
                "Audio (*.wav *.mp3 *.ogg);;Todos los archivos (*.*)"
            )
            if file_path:
                self.file_inputs[field_name].setText(file_path)
        else:  # file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Seleccionar ejecutable",
                "",
                "Todos los archivos (*.*)"
            )
            if file_path:
                try:
                    rel_path = Path(file_path).relative_to(self.base)
                    self.file_inputs[field_name].setText(str(rel_path))
                except ValueError:
                    self.file_inputs[field_name].setText(file_path)
    
    def copy_image(self, src_path, field_name):
        game_name = self.name_input.text()
        if not game_name:
            QMessageBox.warning(self, "Advertencia", "Primero escribe el nombre del juego")
            return
        
        safe_name = StructureHelper.sanitize_name(game_name)
        assets_dir = self.base / "assets" / safe_name
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        src = Path(src_path)
        ext = src.suffix
        dest = assets_dir / f"{field_name}{ext}"
        
        try:
            shutil.copy2(src, dest)
            rel_path = f"assets/{safe_name}/{field_name}{ext}"
            self.file_inputs[field_name].setText(rel_path)
            QMessageBox.information(self, "Éxito", f"✅ Imagen copiada a:\n{rel_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo copiar la imagen:\n{str(e)}")
    
    def load_game(self, game):
        self.name_input.setText(game.nombre)
        self.type_combo.setCurrentText(game.tipo)
        self.file_inputs["ruta_ejecutable"].setText(game.ruta_ejecutable)
        self.file_inputs["icon"].setText(game.icon)
        self.file_inputs["logo"].setText(game.logo)
        self.file_inputs["sound"].setText(game.sound)
    
    def save_game(self):
        game = Game(
            self.name_input.text(),
            self.type_combo.currentText(),
            self.file_inputs["ruta_ejecutable"].text(),
            self.file_inputs["icon"].text(),
            self.file_inputs["logo"].text(),
            self.file_inputs["sound"].text()
        )
        
        ok, msg = self.manager.validate_game(game)
        if not ok:
            QMessageBox.critical(self, "Error de Validación", msg)
            return
        
        self.result = game
        self.accept()

# =============================================================================
# MAIN WINDOW
# =============================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.manager = GameManager()
        self.setup_ui()
        self.load_games()
    
    def setup_ui(self):
        self.setWindowTitle("3D All Stars Game Editor - Premium Edition")
        self.setMinimumSize(1100, 750)
        
        # Estilo global
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {THEME["bg_main"]};
            }}
            QLabel {{
                color: {THEME["text_primary"]};
            }}
            QListWidget {{
                background-color: {THEME["bg_surface"]};
                color: {THEME["text_primary"]};
                border: 2px solid {THEME["border"]};
                border-radius: 12px;
                padding: 8px;
                font-size: 15px;
            }}
            QListWidget::item {{
                padding: 14px;
                border-radius: 8px;
                margin: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {THEME["accent"]};
                color: #000000;
                font-weight: 600;
            }}
            QListWidget::item:hover {{
                background-color: {THEME["bg_hover"]};
            }}
            QFrame {{
                background-color: {THEME["bg_surface"]};
                border-radius: 12px;
            }}
        """)
        
        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Panel izquierdo - Lista
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(16, 16, 16, 16)
        
        title = QLabel("🎮 BIBLIOTECA DE JUEGOS")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {THEME['accent']};")
        left_layout.addWidget(title)
        
        self.game_list = QListWidget()
        self.game_list.currentRowChanged.connect(self.on_game_selected)
        left_layout.addWidget(self.game_list)
        
        main_layout.addWidget(left_panel, 2)
        
        # Panel derecho - Controles e info
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(12)
        
        # Botones de acción
        add_btn = StyledButton("➕ NUEVO JUEGO", "primary")
        add_btn.clicked.connect(self.add_game)
        right_layout.addWidget(add_btn)
        
        edit_btn = StyledButton("✏️ EDITAR", "secondary")
        edit_btn.clicked.connect(self.edit_game)
        right_layout.addWidget(edit_btn)
        
        delete_btn = StyledButton("🗑️ ELIMINAR", "danger")
        delete_btn.clicked.connect(self.delete_game)
        right_layout.addWidget(delete_btn)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {THEME['border']};")
        right_layout.addWidget(separator)
        
        save_btn = StyledButton("💾 GUARDAR TODO", "success")
        save_btn.clicked.connect(self.save_all)
        right_layout.addWidget(save_btn)
        
        # Panel de información
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 16, 16, 16)
        
        info_title = QLabel("ℹ️ INFORMACIÓN")
        info_title.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {THEME['accent']};")
        info_layout.addWidget(info_title)
        
        self.info_label = QLabel("Selecciona un juego para ver su información")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.info_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 13px;
            line-height: 1.6;
        """)
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()
        
        right_layout.addWidget(info_frame, 1)
        
        main_layout.addWidget(right_panel, 1)
    
    def load_games(self):
        self.game_list.clear()
        self.manager.load_games()
        for game in self.manager.games:
            self.game_list.addItem(game.nombre)
    
    def on_game_selected(self, index):
        if index < 0 or index >= len(self.manager.games):
            return
        
        game = self.manager.games[index]
        info = f"""
<b style="color: {THEME['accent']};">NOMBRE:</b> {game.nombre}<br><br>
<b style="color: {THEME['accent']};">TIPO:</b> {game.tipo}<br><br>
<b style="color: {THEME['accent']};">EJECUTABLE:</b><br>{game.ruta_ejecutable}<br><br>
<b style="color: {THEME['accent']};">ICONO:</b><br>{game.icon}<br><br>
<b style="color: {THEME['accent']};">LOGO:</b><br>{game.logo}<br><br>
<b style="color: {THEME['accent']};">SONIDO:</b><br>{game.sound}
        """
        self.info_label.setText(info)
    
    def add_game(self):
        dialog = GameFormDialog(self, self.manager)
        if dialog.exec() and dialog.result:
            self.manager.games.append(dialog.result)
            self.manager.save_games()
            self.load_games()
            QMessageBox.information(self, "Éxito", f"✅ Juego '{dialog.result.nombre}' agregado correctamente")
    
    def edit_game(self):
        index = self.game_list.currentRow()
        if index < 0:
            QMessageBox.warning(self, "Advertencia", "Selecciona un juego para editar")
            return
        
        dialog = GameFormDialog(self, self.manager, self.manager.games[index])
        if dialog.exec() and dialog.result:
            self.manager.games[index] = dialog.result
            self.manager.save_games()
            self.load_games()
            QMessageBox.information(self, "Éxito", f"✅ Juego '{dialog.result.nombre}' actualizado correctamente")
    
    def delete_game(self):
        index = self.game_list.currentRow()
        if index < 0:
            QMessageBox.warning(self, "Advertencia", "Selecciona un juego para eliminar")
            return
        
        game = self.manager.games[index]
        
        # Diálogo de confirmación personalizado
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirmar Eliminación")
        msg.setText(f"¿Eliminar '{game.nombre}'?")
        msg.setInformativeText("Esto eliminará:\n• Entrada en games.json\n• Carpeta games/juego\n• Carpeta assets/juego\n\n⚠️ Esta acción NO se puede deshacer")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        yes_btn = msg.button(QMessageBox.Yes)
        yes_btn.setText("Sí, eliminar todo")
        no_btn = msg.button(QMessageBox.No)
        no_btn.setText("Cancelar")
        
        if msg.exec() == QMessageBox.Yes:
            # Eliminar archivos
            deleted, errors = self.manager.delete_game_files(game)
            
            # Eliminar del JSON
            del self.manager.games[index]
            self.manager.save_games()
            self.load_games()
            
            # Mostrar resultado
            result_msg = f"✅ Juego '{game.nombre}' eliminado correctamente\n\n"
            if deleted:
                result_msg += "Carpetas eliminadas:\n• " + "\n• ".join(deleted)
            if errors:
                result_msg += "\n\n⚠️ Errores:\n• " + "\n• ".join(errors)
            
            QMessageBox.information(self, "Eliminación Completa", result_msg)
    
    def save_all(self):
        self.manager.save_games()
        QMessageBox.information(self, "Guardado", "✅ Todos los cambios guardados en games.json")

# =============================================================================
# MAIN
# =============================================================================

def main():
    app = QApplication(sys.argv)
    
    # Configurar fuente global
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
