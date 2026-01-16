# -*- coding: utf-8 -*-
import pygame
import numpy as np
from config import *

# --- Funciones Gráficas Auxiliares ---
def round_image_corners(image, radius):
    rect = image.get_rect()
    mask = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255), rect, border_radius=radius)
    result = image.copy()
    result.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return result

def draw_game_card(screen, game, position_offset, center_x, center_y):
    dist = abs(position_offset)
    scale_factor = 1.0 / (1.0 + (dist * 1.0))
    alpha = max(0, 255 - int(dist * 100))
    if alpha <= 5: return

    x_spacing_base = 750
    current_spacing = x_spacing_base * scale_factor
    x_pos = center_x + (position_offset * current_spacing)
    y_offset = (dist ** 2) * 80
    y_pos = center_y - y_offset
    
    # Icono
    icon = game["icon_img"]
    iw, ih = icon.get_size()
    scaled_iw = int(iw * scale_factor)
    scaled_ih = int(ih * scale_factor)
    
    if scaled_iw > 1:
        final_icon = pygame.transform.smoothscale(icon, (scaled_iw, scaled_ih))
        radius = 40 if dist < 0.2 else 20
        final_icon = round_image_corners(final_icon, radius)
        final_icon.set_alpha(alpha)
        
        icon_rect = final_icon.get_rect(center=(x_pos, y_pos))
        
        if dist < 1.5: # Sombra
            shadow = pygame.Surface((scaled_iw + 20, scaled_ih + 20), pygame.SRCALPHA)
            pygame.draw.rect(shadow, (0, 0, 0, 100), shadow.get_rect(), border_radius=radius+5)
            screen.blit(shadow, (icon_rect.x - 10, icon_rect.y + 10))
        
        screen.blit(final_icon, icon_rect)

        # Logo
        logo = game["logo_img"]
        lw, lh = logo.get_size()
        logo_scale = scale_factor * 1.54
        slw, slh = int(lw * logo_scale), int(lh * logo_scale)
        
        if slw > 1:
            final_logo = pygame.transform.smoothscale(logo, (slw, slh))
            final_logo.set_alpha(alpha)
            
            logo_y = icon_rect.bottom + (scaled_ih * 0.15)
            logo_rect = final_logo.get_rect(center=(x_pos, logo_y))
            
            if dist < 1.0: # Sombra logo
                ls = pygame.Surface((slw + 40, slh // 2), pygame.SRCALPHA)
                pygame.draw.ellipse(ls, (0, 0, 0, 160), ls.get_rect())
                screen.blit(ls, (logo_rect.centerx - (slw//2) - 20, logo_rect.centery - 10))

            screen.blit(final_logo, logo_rect)

def draw_creator_button(screen, custom_font, width, height):
    mouse_pos = pygame.mouse.get_pos()
    full_text = f"By {CREATOR_USERNAME}"
    # Verificar si font es None por seguridad
    if not custom_font: return None
    
    total_width = sum([custom_font.render(c, True, (255,255,255)).get_width() for c in full_text])
    
    start_x = width - total_width - 50
    start_y = height - 50
    text_rect = pygame.Rect(start_x, start_y - 35, total_width, 45)
    is_hovered = text_rect.collidepoint(mouse_pos)
    
    cx = start_x
    for i, char in enumerate(full_text):
        col = MARIO64_COLORS[i % len(MARIO64_COLORS)]
        ls = custom_font.render(char, True, col)
        ss = custom_font.render(char, True, (0,0,0))
        screen.blit(ss, (cx + 3, start_y + 3))
        screen.blit(ls, (cx, start_y + (-5 if is_hovered else 0)))
        cx += ls.get_width()
    
    if is_hovered:
        pygame.draw.line(screen, (255, 255, 255, 200), (start_x, start_y + 40), (start_x + total_width, start_y + 40), 2)
    return text_rect

# Variables de estado para el vinilo (se mantienen globales al módulo para persistencia)
vinyl_rotation = 0
vinyl_pulse_phase = 0

def draw_music_player(screen, tracks, current_index, vinyl_original, custom_font):
    global vinyl_rotation, vinyl_pulse_phase
    if not tracks or not vinyl_original or not custom_font: return
    
    vinyl_pulse_phase += 0.15
    pulse_scale = 1.0 + (np.sin(vinyl_pulse_phase) * 0.08)
    vinyl_rotation = (vinyl_rotation + VINYL_ROTATION_SPEED) % 360
    
    cs = int(VINYL_SIZE * pulse_scale)
    sv = pygame.transform.smoothscale(vinyl_original, (cs, cs))
    rv = pygame.transform.rotate(sv, vinyl_rotation)
    
    dx, dy = VINYL_MARGIN + VINYL_SIZE // 2, VINYL_MARGIN + VINYL_SIZE // 2
    d_rect = rv.get_rect(center=(dx, dy))
    
    # Sombra disco
    ss = cs + 10
    ssurf = pygame.Surface((ss, ss), pygame.SRCALPHA)
    pygame.draw.circle(ssurf, (0, 0, 0, 100), (ss//2, ss//2), ss//2)
    screen.blit(ssurf, ssurf.get_rect(center=(dx+5, dy+5)))
    screen.blit(rv, d_rect)
    
    # Texto
    track = tracks[current_index]
    tx, ty = dx + VINYL_SIZE // 2 + 20, dy - 15
    
    # Borde texto
    for ox, oy in [(-2,-2),(-2,0),(-2,2),(0,-2),(0,2),(2,-2),(2,0),(2,2)]:
        screen.blit(custom_font.render(track["name"], True, (0,0,0)), (tx+ox, ty+oy))
        screen.blit(custom_font.render(f"{current_index+1}/{len(tracks)}", True, (0,0,0)), (tx+ox, ty+50+oy))
        
    screen.blit(custom_font.render(track["name"], True, (255,255,255)), (tx, ty))
    screen.blit(custom_font.render(f"{current_index+1}/{len(tracks)}", True, (255,255,255)), (tx, ty+50))
