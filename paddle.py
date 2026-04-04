"""Paddle entity controlled by player input."""

import pygame


class Paddle:
    """The horizontal bar the player uses to keep balls in play."""

    def __init__(self, x, y, width, height, color):
        # Rectangle is used for both drawing and collision checks.
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color
        self.speed = 7

    def move(self, keys, screen_width):
        """Move left/right with keyboard while staying on-screen."""
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.speed

        if keys[pygame.K_RIGHT] and self.rect.right < screen_width:
            self.rect.x += self.speed

    def draw(self, screen):
        """Render paddle rectangle."""
        pygame.draw.rect(screen, self.color, self.rect)
