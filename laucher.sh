#!/bin/bash

# Obtener el directorio donde está este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cambiar al directorio del proyecto
cd "$SCRIPT_DIR" || exit 1

# Verificar Python y dependencias
if ! command -v python3 &> /dev/null; then
    zenity --error --text="Python 3 no está instalado" --title="Error" 2>/dev/null || \
    notify-send "Error" "Python 3 no está instalado"
    exit 1
fi

# Crear entorno virtual si no existe
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$SCRIPT_DIR/requirements.txt"
else
    source "$VENV_DIR/bin/activate"
fi

# Ejecutar la aplicación
python3 "$SCRIPT_DIR/main.py" "$@"
