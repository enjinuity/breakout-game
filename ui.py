"""
Small UI drawing helpers.

Non-technical summary:
- Keeps repeated button drawing style in one place.
- If you want all buttons to look different, edit this file.
"""

import pygame


def draw_button(surface, rect, label, font, hover=False):
    """Draw one rounded button with hover highlight and centered text."""
    fill = (220, 220, 220) if hover else (180, 180, 180)
    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, (30, 30, 30), rect, 2, border_radius=8)
    txt = font.render(label, True, (20, 20, 20))
    surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
