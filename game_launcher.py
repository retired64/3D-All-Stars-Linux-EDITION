# -*- coding: utf-8 -*-
import os
import subprocess
import threading
import pygame
from pathlib import Path

def execute_game(game, music_loaded_flag):
    try:
        ruta = Path(game["ruta_ejecutable"])
        os.chmod(ruta, 0o755)
        print(f"🚀 Ejecutando: {ruta}")
        
        # --- FIX: LIMPIEZA DE ENTORNO PARA PYINSTALLER ---
        env = os.environ.copy()
        if 'LD_LIBRARY_PATH_ORIG' in env:
            env['LD_LIBRARY_PATH'] = env['LD_LIBRARY_PATH_ORIG']
        elif 'LD_LIBRARY_PATH' in env:
            del env['LD_LIBRARY_PATH']
        # ------------------------------------------------
        
        proc = subprocess.Popen([str(ruta)], cwd=str(ruta.parent), env=env)
        
        def monitor():
            proc.wait()
            if music_loaded_flag: pygame.mixer.music.set_volume(0.22)
            
        threading.Thread(target=monitor, daemon=True).start()
    except Exception as e:
        print(f"❌ Error lanzando: {e}")
