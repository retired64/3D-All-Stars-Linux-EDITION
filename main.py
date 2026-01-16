#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pygame
import cv2
import numpy as np
import sys
import webbrowser
import threading
import time

# Importaciones de los otros módulos
import config as cfg
import resource_manager as rm
import ui_components as ui
import game_launcher as launcher

# ==========================================
# 🎮 INICIALIZACIÓN PYGAME
# ==========================================
pygame.init()
pygame.mixer.quit()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Pantalla
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
screen.fill((0, 0, 0))
pygame.display.flip()

pygame.display.set_caption(cfg.WINDOW_TITLE)
clock = pygame.time.Clock()

# Joysticks
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
for j in joysticks: j.init()

# ==========================================
# 🌊 SPLASH SCREEN
# ==========================================
# Cargar imagen splash localmente para mostrarla rápido
splash_img = None
if cfg.SPLASH_IMAGE_PATH.exists():
    try:
        splash_img = pygame.image.load(str(cfg.SPLASH_IMAGE_PATH)).convert_alpha()
        splash_img = pygame.transform.smoothscale(splash_img, (WIDTH, HEIGHT))
    except: pass

if cfg.SPLASH_SOUND_PATH.exists():
    try:
        splash_sfx = pygame.mixer.Sound(str(cfg.SPLASH_SOUND_PATH))
        splash_sfx.set_volume(0.6)
        splash_sfx.play()
    except: pass

# Iniciar carga en hilo
loader = threading.Thread(target=rm.load_resources_thread, args=(WIDTH, HEIGHT))
loader.start()

splash_start_time = pygame.time.get_ticks()
splash_active = True
fade_alpha = 0
fade_direction = 1

while splash_active:
    dt = clock.tick(60)
    current_ms = pygame.time.get_ticks()
    elapsed = current_ms - splash_start_time
    
    for e in pygame.event.get():
        if e.type == pygame.QUIT: pygame.quit(); sys.exit()

    if rm.resources_loaded and elapsed > 3000:
        fade_direction = -1 
    
    if fade_direction == 1:
        fade_alpha = min(255, fade_alpha + 5)
    elif fade_direction == -1:
        fade_alpha = max(0, fade_alpha - 5)
        if fade_alpha == 0: splash_active = False 
    
    screen.fill((0, 0, 0))
    if splash_img:
        splash_img.set_alpha(fade_alpha)
        screen.blit(splash_img, (0, 0))
    
    # Barra de carga
    if rm.loading_progress < 100 and fade_direction == 1:
        bar_width = 200
        bar_height = 4
        bar_x = (WIDTH - bar_width) // 2
        bar_y = HEIGHT - 50
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
        fill_width = int((rm.loading_progress / 100) * bar_width)
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, fill_width, bar_height))

    pygame.display.flip()

# ==========================================
# 🎵 POST-CARGA
# ==========================================
current_track_index = 0
music_loaded = False

if rm.MUSIC_TRACKS:
    try:
        pygame.mixer.music.load(rm.MUSIC_TRACKS[current_track_index]["path"])
        pygame.mixer.music.set_volume(0.22)
        pygame.mixer.music.play(-1)
        music_loaded = True
    except Exception as e:
        print(f"⚠️ Error música: {e}")

def next_track():
    global current_track_index
    if not rm.MUSIC_TRACKS: return
    current_track_index = (current_track_index + 1) % len(rm.MUSIC_TRACKS)
    try:
        pygame.mixer.music.load(rm.MUSIC_TRACKS[current_track_index]["path"])
        pygame.mixer.music.play()
    except: pass

def previous_track():
    global current_track_index
    if not rm.MUSIC_TRACKS: return
    current_track_index = (current_track_index - 1) % len(rm.MUSIC_TRACKS)
    try:
        pygame.mixer.music.load(rm.MUSIC_TRACKS[current_track_index]["path"])
        pygame.mixer.music.play()
    except: pass

# ==========================================
# 🔄 BUCLE PRINCIPAL (MAIN LOOP)
# ==========================================
running = True
target_index = 0
visual_index = 0.0
selected_index = 0
last_axis_time = 0
last_music_change_time = 0
b_button_held = False
b_button_start_time = 0
shutdown_fade = 0

launching = False
launch_start_time = 0
launch_game_data = None
fade_duration = 1000

def start_launch(game):
    global launching, launch_start_time, launch_game_data, fade_duration
    launching = True
    launch_start_time = pygame.time.get_ticks()
    launch_game_data = game
    if music_loaded: pygame.mixer.music.set_volume(0.02)
    if game.get("sound_obj"):
        game["sound_obj"].play()
        fade_duration = int(game["sound_obj"].get_length() * 1000)
    else:
        fade_duration = 1500

while running:
    dt = clock.tick(cfg.FPS)
    current_time = pygame.time.get_ticks()
    
    # --- EVENTOS (Lógica ORIGINAL restaurada) ---
    for e in pygame.event.get():
        if e.type == pygame.QUIT: running = False
        
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE: running = False
            
            if not launching and rm.GAMES:
                if e.key in [pygame.K_RIGHT, pygame.K_d]:
                    target_index += 1
                    if rm.nav_sound: rm.nav_sound.play()
                elif e.key in [pygame.K_LEFT, pygame.K_a]:
                    target_index -= 1
                    if rm.nav_sound: rm.nav_sound.play()
                elif e.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    start_launch(rm.GAMES[selected_index])
            
            if current_time - last_music_change_time > 1000:
                if e.key in [pygame.K_DOWN, pygame.K_s]:
                    next_track(); last_music_change_time = current_time
                elif e.key in [pygame.K_UP, pygame.K_w]:
                    previous_track(); last_music_change_time = current_time
        
        elif e.type == pygame.MOUSEBUTTONDOWN:
            creator_rect = ui.draw_creator_button(screen, rm.custom_font, WIDTH, HEIGHT) # Dummy check
            if e.button == 1 and creator_rect and creator_rect.collidepoint(e.pos):
                webbrowser.open(cfg.YOUTUBE_URL)
        
        elif e.type == pygame.JOYBUTTONDOWN:
            if e.button in [0, 7, 9] and not launching and rm.GAMES:
                start_launch(rm.GAMES[selected_index])
            elif e.button == 1:
                b_button_held = True; b_button_start_time = current_time
        
        elif e.type == pygame.JOYBUTTONUP:
            if e.button == 1: b_button_held = False; shutdown_fade = 0
        
        elif e.type == pygame.JOYHATMOTION:
            if not launching and rm.GAMES:
                if e.value[0] == 1: target_index += 1; rm.nav_sound.play() if rm.nav_sound else None
                elif e.value[0] == -1: target_index -= 1; rm.nav_sound.play() if rm.nav_sound else None
            if current_time - last_music_change_time > 1000:
                if e.value[1] == -1: next_track(); last_music_change_time = current_time
                elif e.value[1] == 1: previous_track(); last_music_change_time = current_time

    # --- JOYSTICK AXIS (Lógica ORIGINAL restaurada) ---
    if not launching and rm.GAMES:
        for j in joysticks:
            if j.get_numaxes() >= 2:
                ax = j.get_axis(0)
                if abs(ax) > cfg.JOYSTICK_DEADZONE and current_time - last_axis_time > 180:
                    target_index += 1 if ax > 0 else -1
                    if rm.nav_sound: rm.nav_sound.play()
                    last_axis_time = current_time
                
                # Control de Música con Eje Vertical
                ay = j.get_axis(1)
                if abs(ay) > cfg.JOYSTICK_DEADZONE and current_time - last_music_change_time > 1000:
                    if ay > 0: next_track()
                    else: previous_track()
                    last_music_change_time = current_time

    # Transición visual
    if rm.GAMES:
        diff = target_index - visual_index
        visual_index = float(target_index) if abs(diff) < 0.005 else visual_index + diff * cfg.TRANSITION_SPEED
        selected_index = int(round(visual_index)) % len(rm.GAMES)

    # Lógica Botón B
    if b_button_held:
        elapsed_hold = current_time - b_button_start_time
        shutdown_fade = min(int((elapsed_hold / 5000) * 255), 255)
        if elapsed_hold >= 5000: running = False
    elif shutdown_fade > 0:
        shutdown_fade = max(0, shutdown_fade - 10)

    # --- DIBUJADO ---
    
    # 1. Video
    if rm.cap and rm.video_surface:
        ret, frame = rm.cap.read()
        if not ret:
            rm.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = rm.cap.read()
        if ret:
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = np.transpose(frame, (1, 0, 2))
            pygame.surfarray.blit_array(rm.video_surface, frame)
            screen.blit(rm.video_surface, (0, 0))
    else:
        screen.fill((20, 20, 20))

    # Overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))

    # 2. Juegos (Usando la función UI original)
    if rm.GAMES and not launching:
        cx, cy = WIDTH // 2, HEIGHT // 2 - 60
        base_idx = int(round(visual_index))
        frac = visual_index - base_idx
        for off in sorted([-2, -1, 0, 1, 2], key=lambda x: -abs(x - frac)):
            ui.draw_game_card(
                screen, 
                rm.GAMES[(base_idx + off) % len(rm.GAMES)], 
                off - frac, 
                cx, cy
            )

    # 3. UI
    ui.draw_music_player(screen, rm.MUSIC_TRACKS, current_track_index, rm.vinyl_original, rm.custom_font)
    creator_rect = ui.draw_creator_button(screen, rm.custom_font, WIDTH, HEIGHT)

    if music_loaded and not pygame.mixer.music.get_busy() and not launching:
        next_track()

    # 4. Shutdown / Launch UI
    if shutdown_fade > 0:
        s_over = pygame.Surface((WIDTH, HEIGHT))
        s_over.fill((0,0,0))
        s_over.set_alpha(shutdown_fade)
        screen.blit(s_over, (0,0))
        if shutdown_fade > 127:
            txt = pygame.font.Font(None, 70).render(f"Cerrando... {int(shutdown_fade/2.55)}%", True, (255,50,50))
            screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2)))

    if launching:
        elapsed = current_time - launch_start_time
        prog = min(elapsed / fade_duration, 1.0)
        
        f_surf = pygame.Surface((WIDTH, HEIGHT))
        f_surf.fill((0,0,0))
        f_surf.set_alpha(int(prog * 255))
        screen.blit(f_surf, (0,0))
        
        if prog > 0.2:
            alpha = int(((prog - 0.2) / 0.8) * 255)
            font_big = pygame.font.Font(None, 90)
            # Restaurado el texto del nombre del juego al lanzar
            txt = font_big.render(f"Iniciando {launch_game_data['nombre']}...", True, (255,255,255))
            txt.set_alpha(alpha)
            screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2)))
            
        if elapsed >= fade_duration:
            launcher.execute_game(launch_game_data, music_loaded)
            launching = False

    pygame.display.flip()

if rm.cap: rm.cap.release()
pygame.quit()
sys.exit()
