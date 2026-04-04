"""Ball entity and collision behavior."""

import math

import pygame


class Ball:
    """Represents one moving ball in the arena."""

    def __init__(self, x, y, radius, color, speed=6):
        # Position + look.
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color

        # Base speed value used when scaling difficulty/powerups.
        self.speed = speed

        # Start with a slight horizontal angle so gameplay begins dynamically.
        self.dx = speed * 0.6
        self.dy = -speed

    def move(self):
        """Move the ball by its velocity for one frame."""
        self.x += self.dx
        self.y += self.dy

    def draw(self, screen):
        """Render the ball as a filled circle."""
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)

    def bounce_wall(self, screen_width, screen_height, wall_sound):
        """Bounce on left/right/top walls and play impact SFX."""
        # Left/right wall bounce.
        if self.x - self.radius <= 0 or self.x + self.radius >= screen_width:
            self.dx *= -1
            if wall_sound:
                wall_sound.play()

        # Top wall bounce.
        if self.y - self.radius <= 0:
            self.dy *= -1
            if wall_sound:
                wall_sound.play()

    def bounce_paddle(self, paddle_rect, paddle_sound):
        """Bounce from paddle and steer angle based on hit position."""
        if paddle_rect.collidepoint(self.x, self.y + self.radius) and self.dy > 0:
            # Hitting paddle edges gives steeper side angles.
            relative = (self.x - paddle_rect.centerx) / (paddle_rect.width / 2)
            relative = max(-1.0, min(1.0, relative))
            angle = relative * math.radians(65)
            speed = max(self.speed, math.hypot(self.dx, self.dy))
            self.dx = speed * math.sin(angle)
            self.dy = -abs(speed * math.cos(angle))
            if paddle_sound:
                paddle_sound.play()
            return True
        return False

    def collide_with_rect(self, rect):
        """Circle-vs-rectangle collision with side-aware bounce response."""
        closest_x = max(rect.left, min(self.x, rect.right))
        closest_y = max(rect.top, min(self.y, rect.bottom))
        dx = self.x - closest_x
        dy = self.y - closest_y
        if dx * dx + dy * dy > self.radius * self.radius:
            return False

        overlap_left = abs((self.x + self.radius) - rect.left)
        overlap_right = abs(rect.right - (self.x - self.radius))
        overlap_top = abs((self.y + self.radius) - rect.top)
        overlap_bottom = abs(rect.bottom - (self.y - self.radius))
        min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

        # Flip horizontal or vertical direction based on nearest side.
        if min_overlap in (overlap_left, overlap_right):
            self.dx *= -1
        else:
            self.dy *= -1
        return True

    def apply_speed_scale(self, scale):
        """Scale velocity and stored base speed together."""
        self.dx *= scale
        self.dy *= scale
        self.speed = max(3, self.speed * scale)

    def reset(self, x, y):
        """Put the ball back at a spawn point with default launch direction."""
        self.x = x
        self.y = y
        self.dx = self.speed * 0.6
        self.dy = -self.speed
