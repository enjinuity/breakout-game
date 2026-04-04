"""Brick entity types and damage rules."""

import pygame


class Brick:
    """Represents one breakable or special-purpose brick on the board."""

    def __init__(self, x, y, width, height, color, points, hits=1, brick_type="normal", bomb_timer=0):
        # Rectangle used for collision + drawing.
        self.rect = pygame.Rect(x, y, width, height)

        # Visual and scoring properties.
        self.base_color = color
        self.color = color
        self.destroyed = False
        self.points = points

        # Health and behavior flags.
        self.hits = hits
        self.max_hits = hits
        self.brick_type = brick_type
        self.unbreakable = brick_type == "unbreakable"
        self.shield_active = brick_type == "shielded"

        # Timers used by special bricks.
        self.regen_timer = 260
        self.bomb_timer = bomb_timer if bomb_timer else 520

    def draw(self, screen):
        """Render brick with color/state styling by brick type."""
        if not self.destroyed:
            color = self.color
            if self.brick_type == "strong":
                # Strong bricks fade as they lose health.
                health_ratio = max(0.3, self.hits / max(1, self.max_hits))
                color = tuple(int(c * health_ratio) for c in self.base_color)
            elif self.brick_type == "unbreakable":
                color = (120, 120, 120)
            elif self.brick_type == "explosive":
                color = (255, 140, 0)
            elif self.brick_type == "boss":
                # Boss color shifts to communicate remaining health.
                health_ratio = max(0.15, self.hits / max(1, self.max_hits))
                color = (255, int(80 + 110 * health_ratio), int(80 + 90 * health_ratio))
            elif self.brick_type == "regen":
                color = (80, 220, 120)
            elif self.brick_type == "teleport":
                color = (170, 120, 255)
            elif self.brick_type == "timed_bomb":
                color = (255, 90, 90)
            elif self.brick_type == "shielded":
                color = (80, 170, 255)

            pygame.draw.rect(screen, color, self.rect)
            pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
            if self.shield_active:
                # Extra outline shows shield layer still active.
                pygame.draw.rect(screen, (220, 255, 255), self.rect, 3)

    def hit(self):
        """Apply one hit and return True if the brick is destroyed now."""
        if self.unbreakable or self.destroyed:
            return False

        if self.shield_active:
            # First hit removes shield instead of health.
            self.shield_active = False
            return False

        self.hits -= 1
        if self.hits <= 0:
            self.destroyed = True
            return True
        return False
