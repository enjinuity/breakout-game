import pygame

class Brick:
    def __init__(self, x, y, width, height, color, points, hits=1, brick_type="normal"):
        # Create a rectangle to represent the brick
        self.rect = pygame.Rect(x, y, width, height)

        self.base_color = color
        self.color = color
        self.destroyed = False
        self.points = points
        self.hits = hits
        self.max_hits = hits
        self.brick_type = brick_type
        self.unbreakable = brick_type == "unbreakable"

    def draw(self, screen):
        # Only draw the brick if it hasn't been destroyed
        if not self.destroyed:
            color = self.color
            if self.brick_type == "strong":
                # Fade strong bricks as they lose health.
                health_ratio = max(0.3, self.hits / max(1, self.max_hits))
                color = tuple(int(c * health_ratio) for c in self.base_color)
            elif self.brick_type == "unbreakable":
                color = (120, 120, 120)
            elif self.brick_type == "explosive":
                color = (255, 140, 0)

            pygame.draw.rect(screen, color, self.rect)                # Fill
            pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)         # Black border

    def hit(self):
        """Apply a hit and return True when destroyed by this hit."""
        if self.unbreakable or self.destroyed:
            return False

        self.hits -= 1
        if self.hits <= 0:
            self.destroyed = True
            return True
        return False
