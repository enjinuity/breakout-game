"""Falling pickup/hazard entities."""

import pygame


class PowerUp:
    """Represents one falling item the paddle can collect."""

    def __init__(self, x, y, width, height, type_):
        # Collision box + position.
        self.rect = pygame.Rect(x, y, width, height)

        # Effect identity, movement speed, and active-state flag.
        self.type = type_
        self.dy = 3
        self.active = True

        # Negative pickups are hazards, positive ones are bonuses.
        self.negative = type_ in {"small", "fast"}

        # Short text shown on pickup blocks.
        self.label = {
            "life": "1UP",
            "big": "BIG",
            "multi": "MB",
            "laser": "LAS",
            "slow": "SLO",
            "sticky": "STK",
            "shield": "SHD",
            "small": "SML",
            "fast": "FST",
        }.get(type_, "?")

        # Color coding by effect type.
        self.color = {
            "life": (40, 220, 90),
            "big": (40, 140, 255),
            "multi": (255, 220, 60),
            "laser": (255, 80, 80),
            "slow": (120, 255, 255),
            "sticky": (230, 120, 255),
            "shield": (80, 255, 180),
            "small": (255, 110, 110),
            "fast": (255, 60, 30),
        }.get(type_, (255, 255, 255))

    def update(self, screen_height):
        """Drop downward and deactivate once out of screen bounds."""
        self.rect.y += self.dy
        if self.rect.top > int(screen_height):
            self.active = False

    def draw(self, screen, font=None):
        """Render pickup rectangle and optional text label."""
        pygame.draw.rect(screen, self.color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
        if font:
            txt = font.render(self.label, True, (0, 0, 0))
            screen.blit(txt, (self.rect.centerx - txt.get_width() // 2, self.rect.centery - txt.get_height() // 2))
