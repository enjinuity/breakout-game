import json
import math
import os
import random
import sys

import pygame

from ball import Ball
from brick import Brick
from paddle import Paddle
from powerup import PowerUp

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 900, 640
HUD_HEIGHT = 40
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Breakout: Arcade Edition")
CLOCK = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 24)
SMALL_FONT = pygame.font.SysFont("arial", 18)
BIG_FONT = pygame.font.SysFont("arial", 56)

HIGH_SCORE_FILE = "high_score.json"
PROFILE_FILE = "player_profile.json"


def load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except pygame.error:
        return None


SOUNDS = {
    "brick": load_sound("assets/sounds/brick_hit.wav"),
    "paddle": load_sound("assets/sounds/paddle_hit.wav"),
    "wall": load_sound("assets/sounds/wall_hit.wav"),
    "lose_life": load_sound("assets/sounds/lose_life.wav"),
    "win": load_sound("assets/sounds/win.wav"),
    "game_over": load_sound("assets/sounds/game_over.wav"),
}

MUSIC_PATH = "assets/sounds/bgm.wav"


LEVEL_LAYOUTS = [
    [
        "..........",
        "NNNNNNNNNN",
        "NNNNNNNNNN",
        "SSSSSSSSSS",
        "NNNNNNNNNN",
    ],
    [
        "..U....U..",
        ".NSSSSSSN.",
        "NNEE..EENN",
        ".NSSSSSSN.",
        "..U....U..",
    ],
    [
        "SUSUSUSUSU",
        "ENNNNNNNNE",
        "NSSSEESSSN",
        "ENNNNNNNNE",
        "SUSUSUSUSU",
    ],
]

DIFFICULTY_CONFIG = {
    "EASY": {"lives": 5, "speed": 5.4, "drop_chance": 0.30, "speed_step": 0.45, "score_mult": 0.9},
    "NORMAL": {"lives": 3, "speed": 6.0, "drop_chance": 0.24, "speed_step": 0.55, "score_mult": 1.0},
    "HARD": {"lives": 2, "speed": 6.6, "drop_chance": 0.20, "speed_step": 0.65, "score_mult": 1.2},
}

CAMPAIGN_LEVELS = 9
BOSS_LEVEL_INTERVAL = 3


class Game:
    def __init__(self):
        self.volume = 0.7
        self.sfx_volume = 0.9
        self.music_volume = 0.6
        self.high_score = self.load_high_score()

        self.left_key = pygame.K_LEFT
        self.right_key = pygame.K_RIGHT

        self.difficulty_order = ["EASY", "NORMAL", "HARD"]
        self.difficulty_index = 1
        self.difficulty = self.difficulty_order[self.difficulty_index]
        self.ball_speed_base = DIFFICULTY_CONFIG[self.difficulty]["speed"]
        self.powerup_base_chance = DIFFICULTY_CONFIG[self.difficulty]["drop_chance"]
        self.level_speed_step = DIFFICULTY_CONFIG[self.difficulty]["speed_step"]
        self.score_mult = DIFFICULTY_CONFIG[self.difficulty]["score_mult"]

        self.game_state = "MENU"
        self.transition_alpha = 255
        self.transition_target = "MENU"
        self.paused = False
        self.settings_index = 0
        self.settings_return_state = "MENU"
        self.fullscreen = False

        self.shake_frames = 0
        self.shake_strength = 0
        self.particles = []

        self.laser_charges = 0
        self.laser_cooldown = 0
        self.laser_flash_timer = 0
        self.laser_x = 0
        self.shield_active = False
        self.sticky_active = False
        self.sticky_timer = 0
        self.slow_timer = 0
        self.big_paddle_timer = 0
        self.power_message = ""
        self.power_message_timer = 0

        self.combo = 0
        self.combo_timer = 0

        self.level = 1
        self.level_flash_timer = 0
        self.round_start_countdown = 0
        self.tutorial_timer = 480
        self.bgm_enabled = True
        self.bgm_loaded = False
        self.bgm_channel = None
        self.bgm_error = ""
        self.boss_brick = None
        self.boss_direction = 1
        self.boss_attack_timer = 0
        self.boss_projectiles = []
        self.boss_pattern_index = 0
        self.run_active = False

        self.profile = self.load_profile()
        self.apply_profile_settings()
        if self.fullscreen:
            global SCREEN
            SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
            pygame.display.set_caption("Breakout: Arcade Edition")

        self.reset_run(full_reset=True)
        self.apply_volume()
        self.try_start_music()

    def default_profile(self):
        return {
            "high_score": 0,
            "settings": {
                "master_volume": 0.7,
                "sfx_volume": 0.9,
                "music_volume": 0.6,
                "bgm_enabled": True,
                "controls": "ARROWS",
                "fullscreen": False,
            },
            "stats": {
                "runs_started": 0,
                "runs_completed": 0,
                "campaign_wins": 0,
                "bosses_defeated": 0,
                "bricks_broken": 0,
                "best_level_reached": 1,
                "lifetime_score": 0,
            },
        }

    def load_profile(self):
        profile = self.default_profile()
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, "r", encoding="utf-8") as file:
                    data = json.load(file)
                if isinstance(data, dict):
                    profile.update({k: v for k, v in data.items() if k in profile and isinstance(v, dict) is False})
                    if isinstance(data.get("settings"), dict):
                        profile["settings"].update(data["settings"])
                    if isinstance(data.get("stats"), dict):
                        profile["stats"].update(data["stats"])
            except (ValueError, OSError, json.JSONDecodeError):
                pass

        legacy_high = self.load_high_score()
        profile["high_score"] = max(int(profile.get("high_score", 0)), legacy_high)
        return profile

    def save_profile(self):
        self.profile["high_score"] = int(self.high_score)
        self.profile["settings"] = {
            "master_volume": self.volume,
            "sfx_volume": self.sfx_volume,
            "music_volume": self.music_volume,
            "bgm_enabled": self.bgm_enabled,
            "controls": self.controls_label(),
            "fullscreen": self.fullscreen,
        }
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as file:
                json.dump(self.profile, file, indent=2)
        except OSError:
            pass
        self.save_high_score()

    def apply_profile_settings(self):
        settings = self.profile.get("settings", {})
        self.high_score = max(int(self.high_score), int(self.profile.get("high_score", 0)))
        self.volume = float(settings.get("master_volume", self.volume))
        self.sfx_volume = float(settings.get("sfx_volume", self.sfx_volume))
        self.music_volume = float(settings.get("music_volume", self.music_volume))
        self.bgm_enabled = bool(settings.get("bgm_enabled", self.bgm_enabled))
        if settings.get("controls", "ARROWS") == "WASD":
            self.left_key = pygame.K_a
            self.right_key = pygame.K_d
        else:
            self.left_key = pygame.K_LEFT
            self.right_key = pygame.K_RIGHT
        self.fullscreen = bool(settings.get("fullscreen", self.fullscreen))

    def load_high_score(self):
        if not os.path.exists(HIGH_SCORE_FILE):
            return 0
        try:
            with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
            return int(data.get("high_score", 0))
        except (ValueError, OSError, json.JSONDecodeError):
            return 0

    def save_high_score(self):
        try:
            with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as file:
                json.dump({"high_score": self.high_score}, file)
        except OSError:
            pass

    def play_sound(self, name):
        sound = SOUNDS.get(name)
        if sound:
            sound.play()

    def apply_volume(self):
        sfx_mix = self.volume * self.sfx_volume
        for sound in SOUNDS.values():
            if sound:
                sound.set_volume(sfx_mix)
        bgm_volume = self.volume * self.music_volume if self.bgm_enabled else 0.0
        pygame.mixer.music.set_volume(bgm_volume)
        if self.bgm_channel:
            self.bgm_channel.set_volume(bgm_volume)

    def try_start_music(self):
        if os.path.exists(MUSIC_PATH):
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(MUSIC_PATH)
                pygame.mixer.music.play(-1)
                self.bgm_loaded = True
                self.bgm_error = ""
            except pygame.error:
                # Fallback for environments/codecs where music stream load fails.
                bgm_sound = load_sound(MUSIC_PATH)
                if bgm_sound:
                    self.bgm_channel = bgm_sound.play(-1)
                    self.bgm_loaded = self.bgm_channel is not None
                    self.bgm_error = "" if self.bgm_loaded else "BGM channel unavailable"
                else:
                    self.bgm_loaded = False
                    self.bgm_error = "BGM format unsupported"
        else:
            self.bgm_loaded = False
            self.bgm_error = "bgm.wav not found"

    def update_difficulty(self, direction):
        self.difficulty_index = (self.difficulty_index + direction) % len(self.difficulty_order)
        self.difficulty = self.difficulty_order[self.difficulty_index]
        config = DIFFICULTY_CONFIG[self.difficulty]
        self.ball_speed_base = config["speed"]
        self.powerup_base_chance = config["drop_chance"]
        self.level_speed_step = config["speed_step"]
        self.score_mult = config["score_mult"]

    def toggle_bgm(self):
        self.bgm_enabled = not self.bgm_enabled
        self.apply_volume()
        self.save_profile()

    def toggle_controls_preset(self):
        if self.left_key == pygame.K_LEFT:
            self.left_key = pygame.K_a
            self.right_key = pygame.K_d
        else:
            self.left_key = pygame.K_LEFT
            self.right_key = pygame.K_RIGHT
        self.save_profile()

    def controls_label(self):
        return "ARROWS" if self.left_key == pygame.K_LEFT else "WASD"

    def toggle_fullscreen(self):
        global SCREEN
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        else:
            SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Breakout: Arcade Edition")
        self.save_profile()

    def open_settings(self, return_state):
        self.settings_return_state = return_state
        self.settings_index = 0
        self.game_state = "SETTINGS"

    def finalize_run(self):
        if not self.run_active:
            return
        stats = self.profile["stats"]
        stats["runs_completed"] = int(stats.get("runs_completed", 0)) + 1
        stats["lifetime_score"] = int(stats.get("lifetime_score", 0)) + int(self.score)
        stats["best_level_reached"] = max(int(stats.get("best_level_reached", 1)), int(self.level))
        self.run_active = False
        self.save_profile()

    def start_new_game(self):
        if self.run_active:
            self.finalize_run()
        config = DIFFICULTY_CONFIG[self.difficulty]
        self.starting_lives = config["lives"]
        self.ball_speed_base = config["speed"]
        self.powerup_base_chance = config["drop_chance"]
        self.level_speed_step = config["speed_step"]
        self.score_mult = config["score_mult"]
        self.game_state = "PLAYING"
        self.paused = False
        self.run_active = True
        self.profile["stats"]["runs_started"] = int(self.profile["stats"].get("runs_started", 0)) + 1
        self.save_profile()
        self.reset_run(full_reset=True)

    def reset_run(self, full_reset):
        if full_reset:
            self.score = 0
            self.lives = getattr(self, "starting_lives", DIFFICULTY_CONFIG[self.difficulty]["lives"])
            self.level = 1
            self.ball_speed_base = DIFFICULTY_CONFIG[self.difficulty]["speed"]
            self.powerup_base_chance = DIFFICULTY_CONFIG[self.difficulty]["drop_chance"]
            self.level_speed_step = DIFFICULTY_CONFIG[self.difficulty]["speed_step"]
            self.score_mult = DIFFICULTY_CONFIG[self.difficulty]["score_mult"]
            self.tutorial_timer = 480

        self.paddle = Paddle(x=WIDTH // 2 - 70, y=HEIGHT - 35, width=140, height=15, color=(255, 255, 255))
        self.default_paddle_width = 140
        self.ball_attached = True
        self.balls = [Ball(WIDTH // 2, HEIGHT - 50, 10, (255, 70, 70), speed=self.ball_speed_base)]
        self.bricks = self.create_bricks(self.level)
        self.powerups = []

        self.combo = 0
        self.combo_timer = 0
        self.laser_charges = 0
        self.shield_active = False
        self.sticky_active = False
        self.sticky_timer = 0
        self.big_paddle_timer = 0
        self.slow_timer = 0
        self.level_flash_timer = 120
        self.round_start_countdown = 150
        self.boss_brick = None
        self.boss_direction = 1
        self.boss_attack_timer = max(120, 300 - self.level * 10)
        self.boss_projectiles = []
        self.boss_pattern_index = 0

    def is_boss_level(self, level):
        return level % BOSS_LEVEL_INTERVAL == 0

    def create_boss_wave(self, level):
        bricks = []
        boss_hits = 16 + level * 2
        boss_width = 260
        boss_height = 38
        boss_x = WIDTH // 2 - boss_width // 2
        boss_y = HUD_HEIGHT + 34
        self.boss_brick = Brick(
            boss_x,
            boss_y,
            boss_width,
            boss_height,
            (255, 110, 110),
            points=1500 + level * 120,
            hits=boss_hits,
            brick_type="boss",
        )
        bricks.append(self.boss_brick)

        # Guards to keep boss waves from being one-hit trivial.
        guard_w = 72
        guard_h = 24
        left_start = WIDTH // 2 - 260
        right_start = WIDTH // 2 + 188
        for i in range(3):
            y = HUD_HEIGHT + 96 + i * 30
            bricks.append(Brick(left_start, y, guard_w, guard_h, (90, 200, 240), points=110, hits=2, brick_type="strong"))
            bricks.append(Brick(right_start, y, guard_w, guard_h, (90, 200, 240), points=110, hits=2, brick_type="strong"))
        return bricks

    def create_bricks(self, level):
        if self.is_boss_level(level):
            return self.create_boss_wave(level)

        layout = LEVEL_LAYOUTS[(level - 1) % len(LEVEL_LAYOUTS)]
        bricks = []
        rows = len(layout)
        cols = len(layout[0])
        margin_x = 40
        top = HUD_HEIGHT + 20
        usable_w = WIDTH - margin_x * 2
        brick_w = usable_w // cols
        brick_h = 26

        for row in range(rows):
            for col in range(cols):
                code = layout[row][col]
                if code == ".":
                    continue
                x = margin_x + col * brick_w
                y = top + row * brick_h

                if code == "N":
                    color = (90 + row * 15, 130 + col * 5, 220)
                    bricks.append(Brick(x, y, brick_w - 2, brick_h - 2, color, points=40 + (rows - row) * 8))
                elif code == "S":
                    color = (80, 220, 190)
                    bricks.append(Brick(x, y, brick_w - 2, brick_h - 2, color, points=100, hits=2, brick_type="strong"))
                elif code == "U":
                    bricks.append(Brick(x, y, brick_w - 2, brick_h - 2, (140, 140, 140), points=0, hits=999, brick_type="unbreakable"))
                elif code == "E":
                    bricks.append(Brick(x, y, brick_w - 2, brick_h - 2, (255, 150, 60), points=80, hits=1, brick_type="explosive"))
        return bricks

    def spawn_specific_powerup(self, x, y, power_type):
        self.powerups.append(PowerUp(x, y, 26, 20, power_type))

    def spawn_powerup(self, x, y):
        if self.is_boss_level(self.level):
            # Boss waves are tighter; fewer freebies and more pressure.
            if random.random() > 0.12:
                return
            boss_pool = ["laser", "slow", "shield", "small", "fast"]
            self.spawn_specific_powerup(x, y, random.choice(boss_pool))
            return
        level_penalty = (self.level - 1) * 0.03
        chance = max(0.12, self.powerup_base_chance - level_penalty)
        if random.random() > chance:
            return

        good = ["multi", "big", "life", "laser", "slow", "sticky", "shield"]
        bad = ["small", "fast"]
        pool = good * 8 + bad * 3
        power_type = random.choice(pool)
        self.powerups.append(PowerUp(x, y, 26, 20, power_type))

    def spawn_particles(self, x, y, color, count=10):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1.2, 4.0)
            self.particles.append(
                {
                    "x": x,
                    "y": y,
                    "dx": math.cos(angle) * speed,
                    "dy": math.sin(angle) * speed,
                    "life": random.randint(12, 24),
                    "color": color,
                    "size": random.randint(2, 4),
                }
            )

    def explode_neighbors(self, source_brick):
        destroyed_points = 0
        for brick in self.bricks:
            if brick.destroyed or brick.unbreakable:
                continue
            if brick is source_brick:
                continue
            if brick.rect.centerx in range(source_brick.rect.left - source_brick.rect.width, source_brick.rect.right + source_brick.rect.width + 1) and brick.rect.centery in range(source_brick.rect.top - source_brick.rect.height, source_brick.rect.bottom + source_brick.rect.height + 1):
                if brick.hit():
                    destroyed_points += brick.points
                    self.spawn_particles(brick.rect.centerx, brick.rect.centery, brick.base_color, count=6)
                    self.spawn_powerup(brick.rect.centerx, brick.rect.centery)
        return destroyed_points

    def set_power_message(self, text):
        self.power_message = text
        self.power_message_timer = 140

    def award_points(self, points):
        gained = int(points * self.score_mult)
        self.score += gained
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
        return gained

    def apply_powerup(self, powerup):
        ptype = powerup.type

        if ptype == "multi":
            for direction in (-1, 1):
                base = self.balls[0] if self.balls else Ball(self.paddle.rect.centerx, self.paddle.rect.top - 10, 10, (255, 255, 80), speed=self.ball_speed_base)
                new_ball = Ball(self.paddle.rect.centerx, self.paddle.rect.top - 10, 10, (255, 255, 80), speed=max(self.ball_speed_base, base.speed))
                new_ball.dx = direction * (abs(base.dx) + 1.5)
                new_ball.dy = -abs(base.dy)
                self.balls.append(new_ball)
            self.set_power_message("Multiball activated")

        elif ptype == "big":
            new_width = min(220, self.paddle.rect.width + 35)
            center = self.paddle.rect.centerx
            self.paddle.rect.width = new_width
            self.paddle.rect.centerx = center
            self.big_paddle_timer = 900
            self.set_power_message("Paddle size up")

        elif ptype == "life":
            self.lives = min(9, self.lives + 1)
            self.set_power_message("Extra life")

        elif ptype == "laser":
            self.laser_charges = min(25, self.laser_charges + 8)
            self.set_power_message("Laser paddle online")

        elif ptype == "slow":
            self.slow_timer = 480
            for ball in self.balls:
                ball.apply_speed_scale(0.8)
            self.set_power_message("Slow motion")

        elif ptype == "sticky":
            self.sticky_active = True
            self.sticky_timer = 900
            self.set_power_message("Sticky paddle")

        elif ptype == "shield":
            self.shield_active = True
            self.set_power_message("Bottom shield ready")

        elif ptype == "small":
            new_width = max(80, self.paddle.rect.width - 30)
            center = self.paddle.rect.centerx
            self.paddle.rect.width = new_width
            self.paddle.rect.centerx = center
            self.big_paddle_timer = 0
            self.set_power_message("Hazard: paddle shrunk")

        elif ptype == "fast":
            for ball in self.balls:
                ball.apply_speed_scale(1.2)
            self.set_power_message("Hazard: ball speed up")

    def fire_laser(self):
        if self.laser_charges <= 0 or self.laser_cooldown > 0:
            return

        self.laser_charges -= 1
        self.laser_cooldown = 14
        beam_x = self.paddle.rect.centerx
        self.laser_flash_timer = 5
        self.laser_x = beam_x

        nearest = None
        nearest_distance = HEIGHT
        for brick in self.bricks:
            if brick.destroyed or brick.unbreakable:
                continue
            if brick.rect.left <= beam_x <= brick.rect.right:
                distance = self.paddle.rect.top - brick.rect.bottom
                if 0 <= distance < nearest_distance:
                    nearest = brick
                    nearest_distance = distance

        if nearest:
            destroyed = nearest.hit()
            self.play_sound("brick")
            self.spawn_particles(nearest.rect.centerx, nearest.rect.centery, (255, 80, 80), count=10)
            if destroyed:
                self.award_points(nearest.points)
                if nearest.brick_type == "explosive":
                    self.award_points(self.explode_neighbors(nearest))
                self.spawn_powerup(nearest.rect.centerx, nearest.rect.centery)

    def update_particles(self):
        next_particles = []
        for p in self.particles:
            p["x"] += p["dx"]
            p["y"] += p["dy"]
            p["dy"] += 0.08
            p["life"] -= 1
            if p["life"] > 0:
                next_particles.append(p)
        self.particles = next_particles

    def update_boss_mechanics(self):
        if not self.boss_brick or self.boss_brick.destroyed:
            return

        # Move the boss horizontally to make this feel like a wave event.
        speed = 2 + self.level // 3
        self.boss_brick.rect.x += speed * self.boss_direction
        min_x = 80
        max_x = WIDTH - 80 - self.boss_brick.rect.width
        if self.boss_brick.rect.x <= min_x or self.boss_brick.rect.x >= max_x:
            self.boss_direction *= -1
            self.boss_brick.rect.x = max(min_x, min(self.boss_brick.rect.x, max_x))

        # Boss periodically launches hazard drops.
        self.boss_attack_timer -= 1
        if self.boss_attack_timer <= 0:
            pattern = self.boss_pattern_index % 3
            if pattern == 0:
                # Triple spread shots.
                for off in (-80, 0, 80):
                    self.boss_projectiles.append(
                        {
                            "x": self.boss_brick.rect.centerx + off,
                            "y": self.boss_brick.rect.bottom + 6,
                            "dx": off * 0.008,
                            "dy": 3.6 + self.level * 0.1,
                            "r": 7,
                            "color": (255, 120, 120),
                        }
                    )
                self.set_power_message("Boss attack: spread")
            elif pattern == 1:
                # Vertical rain line.
                for off in (-120, -60, 0, 60, 120):
                    self.boss_projectiles.append(
                        {
                            "x": self.boss_brick.rect.centerx + off,
                            "y": self.boss_brick.rect.bottom + 4,
                            "dx": 0,
                            "dy": 4.0 + self.level * 0.08,
                            "r": 6,
                            "color": (255, 90, 70),
                        }
                    )
                self.set_power_message("Boss attack: rain")
            else:
                # Pressure drop + single hazard powerup.
                hazard = random.choice(["small", "fast"])
                self.spawn_specific_powerup(self.boss_brick.rect.centerx, self.boss_brick.rect.bottom + 4, hazard)
                self.boss_projectiles.append(
                    {
                        "x": self.boss_brick.rect.centerx,
                        "y": self.boss_brick.rect.bottom + 8,
                        "dx": 0,
                        "dy": 4.8 + self.level * 0.12,
                        "r": 9,
                        "color": (255, 160, 80),
                    }
                )
                self.set_power_message("Boss attack: pressure")

            self.boss_pattern_index += 1
            self.boss_attack_timer = max(78, 230 - self.level * 8)

    def update_boss_projectiles(self):
        if not self.boss_projectiles:
            return

        next_projectiles = []
        for proj in self.boss_projectiles:
            proj["x"] += proj["dx"]
            proj["y"] += proj["dy"]
            if proj["y"] > HEIGHT + proj["r"]:
                continue

            rect = pygame.Rect(int(proj["x"] - proj["r"]), int(proj["y"] - proj["r"]), proj["r"] * 2, proj["r"] * 2)
            if rect.colliderect(self.paddle.rect):
                if self.shield_active:
                    self.shield_active = False
                    self.spawn_particles(int(proj["x"]), int(proj["y"]), (80, 240, 170), count=8)
                else:
                    self.apply_powerup(PowerUp(self.paddle.rect.centerx, self.paddle.rect.y, 20, 20, random.choice(["small", "fast"])))
                    self.spawn_particles(int(proj["x"]), int(proj["y"]), proj["color"], count=10)
                continue

            next_projectiles.append(proj)

        self.boss_projectiles = next_projectiles

    def update_combo(self):
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0

    def update_balls(self, keys):
        if self.ball_attached and self.balls:
            self.balls[0].x = self.paddle.rect.centerx
            self.balls[0].y = self.paddle.rect.top - self.balls[0].radius

        if self.ball_attached and keys[pygame.K_SPACE] and self.round_start_countdown <= 0:
            self.ball_attached = False

        for ball in self.balls:
            if self.ball_attached:
                break
            ball.move()
            ball.bounce_wall(WIDTH, HEIGHT, SOUNDS["wall"])
            paddle_hit = ball.bounce_paddle(self.paddle.rect, SOUNDS["paddle"])
            if paddle_hit and self.sticky_active:
                self.ball_attached = True
                self.balls = [ball]
                ball.dx = ball.speed * 0.6
                ball.dy = -ball.speed
                break

            # Shield saves one miss.
            if ball.y - ball.radius > HEIGHT:
                if self.shield_active:
                    self.shield_active = False
                    ball.y = HEIGHT - 50
                    ball.dy = -abs(ball.dy)
                    self.play_sound("wall")
                else:
                    ball.y = HEIGHT + 100

        self.balls = [b for b in self.balls if b.y - b.radius <= HEIGHT + 10]

        if not self.balls:
            self.lives -= 1
            self.play_sound("lose_life")
            if self.lives <= 0:
                self.play_sound("game_over")
                self.game_state = "GAME_OVER"
                if self.score > self.high_score:
                    self.high_score = self.score
                    self.save_high_score()
                self.finalize_run()
                return

            self.ball_attached = True
            self.balls = [Ball(WIDTH // 2, HEIGHT - 50, 10, (255, 70, 70), speed=self.ball_speed_base)]
            self.sticky_active = False
            self.round_start_countdown = 120

    def update_brick_collisions(self):
        for ball in list(self.balls):
            for brick in self.bricks:
                if brick.destroyed:
                    continue
                if not ball.collide_with_rect(brick.rect):
                    continue

                if brick.unbreakable:
                    self.play_sound("wall")
                    self.shake_frames = 4
                    self.shake_strength = 2
                    break

                destroyed = brick.hit()
                self.play_sound("brick")
                self.spawn_particles(brick.rect.centerx, brick.rect.centery, brick.base_color, count=8)

                if destroyed:
                    self.combo += 1
                    self.combo_timer = 90
                    points = int(brick.points * (1 + self.combo * 0.15))
                    self.award_points(points)
                    self.profile["stats"]["bricks_broken"] = int(self.profile["stats"].get("bricks_broken", 0)) + 1
                    self.spawn_powerup(brick.rect.centerx, brick.rect.centery)

                    if brick.brick_type == "explosive":
                        self.award_points(self.explode_neighbors(brick))
                    elif brick.brick_type == "boss":
                        self.set_power_message("Boss destroyed")
                        self.shake_frames = 18
                        self.shake_strength = 6
                        self.boss_brick = None
                        self.boss_projectiles = []
                        self.profile["stats"]["bosses_defeated"] = int(self.profile["stats"].get("bosses_defeated", 0)) + 1
                        self.save_profile()
                    else:
                        self.shake_frames = 5
                        self.shake_strength = 3
                break

    def update_powerups(self):
        for powerup in self.powerups:
            powerup.update()
            if powerup.rect.colliderect(self.paddle.rect):
                self.apply_powerup(powerup)
                powerup.active = False
                self.spawn_particles(powerup.rect.centerx, powerup.rect.centery, powerup.color, count=8)

        self.powerups = [p for p in self.powerups if p.active]

    def has_cleared_level(self):
        return all(brick.destroyed or brick.unbreakable for brick in self.bricks)

    def go_to_next_level(self):
        if self.level >= CAMPAIGN_LEVELS:
            self.game_state = "CAMPAIGN_WIN"
            self.play_sound("win")
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()
            self.profile["stats"]["campaign_wins"] = int(self.profile["stats"].get("campaign_wins", 0)) + 1
            self.finalize_run()
            return

        self.level += 1
        self.profile["stats"]["best_level_reached"] = max(
            int(self.profile["stats"].get("best_level_reached", 1)),
            int(self.level),
        )
        self.ball_speed_base = min(10.0, self.ball_speed_base + self.level_speed_step)
        self.powerup_base_chance = max(0.1, self.powerup_base_chance - 0.02)
        self.reset_run(full_reset=False)
        if self.is_boss_level(self.level):
            self.set_power_message("Boss wave incoming")
        self.play_sound("win")

    def draw_particles(self, surf):
        for p in self.particles:
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), p["size"])

    def draw_hud(self, surf):
        pygame.draw.rect(surf, (16, 20, 28), (0, 0, WIDTH, HUD_HEIGHT))
        score_text = FONT.render(f"Score: {self.score}", True, (240, 240, 240))
        lives_text = FONT.render(f"Lives: {self.lives}", True, (240, 240, 240))
        level_text = FONT.render(f"Level: {self.level}/{CAMPAIGN_LEVELS}", True, (240, 240, 240))
        hi_text = SMALL_FONT.render(f"High: {self.high_score}", True, (200, 200, 200))
        diff_text = SMALL_FONT.render(f"{self.difficulty} x{self.score_mult:.1f}", True, (180, 220, 255))

        surf.blit(score_text, (14, 8))
        surf.blit(lives_text, (210, 8))
        surf.blit(level_text, (360, 8))
        surf.blit(hi_text, (500, 11))
        surf.blit(diff_text, (590, 11))

        if self.combo > 1:
            combo_text = FONT.render(f"Combo x{self.combo}", True, (255, 210, 80))
            surf.blit(combo_text, (620, 8))

        if self.laser_charges > 0:
            laser_text = SMALL_FONT.render(f"Laser: {self.laser_charges}", True, (255, 120, 120))
            surf.blit(laser_text, (760, 11))
        if self.sticky_timer > 0:
            st = SMALL_FONT.render(f"Sticky: {self.sticky_timer // 60}s", True, (220, 170, 255))
            surf.blit(st, (14, HEIGHT - 24))
        if self.big_paddle_timer > 0:
            bp = SMALL_FONT.render(f"Big Paddle: {self.big_paddle_timer // 60}s", True, (160, 220, 255))
            surf.blit(bp, (170, HEIGHT - 24))
        if self.is_boss_level(self.level) and self.boss_brick and not self.boss_brick.destroyed:
            boss_tag = SMALL_FONT.render("BOSS WAVE", True, (255, 130, 130))
            surf.blit(boss_tag, (WIDTH - 124, HEIGHT - 24))

    def draw_world(self, surf):
        # Layered background with motion for atmosphere.
        for i in range(0, HEIGHT, 32):
            color = (8 + i // 24, 10 + i // 18, 18 + i // 14)
            pygame.draw.rect(surf, color, (0, i, WIDTH, 32))

        if self.shield_active:
            pygame.draw.rect(surf, (80, 240, 170), (0, HEIGHT - 8, WIDTH, 8))

        if self.laser_flash_timer > 0:
            pygame.draw.line(surf, (255, 80, 80), (self.laser_x, self.paddle.rect.top), (self.laser_x, HUD_HEIGHT + 4), 3)

        for brick in self.bricks:
            brick.draw(surf)

        for powerup in self.powerups:
            powerup.draw(surf, SMALL_FONT)

        for proj in self.boss_projectiles:
            pygame.draw.circle(surf, proj["color"], (int(proj["x"]), int(proj["y"])), proj["r"])
            pygame.draw.circle(surf, (20, 20, 20), (int(proj["x"]), int(proj["y"])), proj["r"], 2)

        self.paddle.draw(surf)
        for ball in self.balls:
            ball.draw(surf)

        if self.ball_attached and self.balls and self.round_start_countdown <= 0:
            ball = self.balls[0]
            aim_end = (int(ball.x + ball.dx * 12), int(ball.y + ball.dy * 12))
            pygame.draw.line(surf, (160, 200, 255), (int(ball.x), int(ball.y)), aim_end, 2)

        self.draw_particles(surf)

        if self.power_message_timer > 0:
            msg = FONT.render(self.power_message, True, (240, 240, 240))
            surf.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT - 68))

        if self.ball_attached and self.round_start_countdown <= 0:
            tip = SMALL_FONT.render("Press SPACE to launch", True, (230, 230, 230))
            surf.blit(tip, (WIDTH // 2 - tip.get_width() // 2, HEIGHT - 46))

        if self.round_start_countdown > 0:
            seconds = max(1, (self.round_start_countdown + 59) // 60)
            ready = BIG_FONT.render(str(seconds), True, (255, 255, 255))
            surf.blit(ready, (WIDTH // 2 - ready.get_width() // 2, HEIGHT // 2 - 20))

        if self.tutorial_timer > 0 and self.level == 1:
            hint = SMALL_FONT.render("Tip: hit paddle edges to control bounce angle. F uses laser when charged.", True, (210, 210, 210))
            surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT - 24))

        if self.level_flash_timer > 0:
            text = BIG_FONT.render(f"Level {self.level}", True, (255, 255, 255))
            alpha = min(255, self.level_flash_timer * 4)
            overlay = pygame.Surface((text.get_width(), text.get_height()), pygame.SRCALPHA)
            overlay.blit(text, (0, 0))
            overlay.set_alpha(alpha)
            surf.blit(overlay, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 30))

        if self.boss_brick and not self.boss_brick.destroyed:
            max_w = 340
            bar_x = WIDTH // 2 - max_w // 2
            bar_y = HUD_HEIGHT + 8
            ratio = self.boss_brick.hits / max(1, self.boss_brick.max_hits)
            pygame.draw.rect(surf, (30, 30, 30), (bar_x, bar_y, max_w, 14))
            pygame.draw.rect(surf, (255, 90, 90), (bar_x + 2, bar_y + 2, int((max_w - 4) * ratio), 10))
            pygame.draw.rect(surf, (220, 220, 220), (bar_x, bar_y, max_w, 14), 2)
            label = SMALL_FONT.render("BOSS", True, (255, 220, 220))
            surf.blit(label, (bar_x - 50, bar_y - 2))

    def draw_menu(self, surf):
        for i in range(0, HEIGHT, 20):
            pygame.draw.rect(surf, (12 + i // 30, 14 + i // 30, 22 + i // 18), (0, i, WIDTH, 20))

        title = BIG_FONT.render("Breakout Arcade", True, (240, 240, 240))
        subtitle = FONT.render("Press ENTER to Start | S for Settings", True, (200, 220, 255))
        settings = SMALL_FONT.render("Left/Right (or A/D): move | Space: launch | F: laser | P: pause", True, (180, 180, 180))
        controls = SMALL_FONT.render("M/N master volume | B BGM toggle | ESC quits", True, (180, 180, 180))
        hi = FONT.render(f"High Score: {self.high_score}", True, (255, 220, 120))
        diff = FONT.render(f"Difficulty: {self.difficulty}", True, (150, 230, 255))
        diff_help = SMALL_FONT.render("Use UP/DOWN to change difficulty", True, (200, 200, 200))
        bgm_state = "ON" if self.bgm_enabled and self.bgm_loaded else "OFF"
        bgm = SMALL_FONT.render(f"BGM: {bgm_state} (B to toggle)", True, (190, 220, 190))
        stats = self.profile.get("stats", {})
        stats_line = SMALL_FONT.render(
            f"Runs: {stats.get('runs_completed', 0)}  Wins: {stats.get('campaign_wins', 0)}  Bosses: {stats.get('bosses_defeated', 0)}",
            True,
            (190, 190, 220),
        )
        if self.bgm_error:
            bgm_note = SMALL_FONT.render(f"BGM note: {self.bgm_error}", True, (220, 160, 160))
        else:
            bgm_note = None

        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 120))
        surf.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, HEIGHT // 2 - 28))
        surf.blit(hi, (WIDTH // 2 - hi.get_width() // 2, HEIGHT // 2 + 18))
        surf.blit(diff, (WIDTH // 2 - diff.get_width() // 2, HEIGHT // 2 + 54))
        surf.blit(diff_help, (WIDTH // 2 - diff_help.get_width() // 2, HEIGHT // 2 + 86))
        surf.blit(bgm, (WIDTH // 2 - bgm.get_width() // 2, HEIGHT // 2 + 114))
        surf.blit(stats_line, (WIDTH // 2 - stats_line.get_width() // 2, HEIGHT // 2 + 164))
        if bgm_note:
            surf.blit(bgm_note, (WIDTH // 2 - bgm_note.get_width() // 2, HEIGHT // 2 + 138))
        surf.blit(settings, (WIDTH // 2 - settings.get_width() // 2, HEIGHT - 50))
        surf.blit(controls, (WIDTH // 2 - controls.get_width() // 2, HEIGHT - 74))

    def draw_game_over(self, surf):
        over = BIG_FONT.render("Game Over", True, (255, 100, 100))
        score = FONT.render(f"Score: {self.score}", True, (240, 240, 240))
        again = SMALL_FONT.render("Press ENTER to restart or ESC for menu", True, (220, 220, 220))

        surf.blit(over, (WIDTH // 2 - over.get_width() // 2, HEIGHT // 2 - 60))
        surf.blit(score, (WIDTH // 2 - score.get_width() // 2, HEIGHT // 2 + 6))
        surf.blit(again, (WIDTH // 2 - again.get_width() // 2, HEIGHT // 2 + 40))

    def draw_campaign_win(self, surf):
        win = BIG_FONT.render("Campaign Complete", True, (140, 255, 170))
        score = FONT.render(f"Final Score: {self.score}", True, (240, 240, 240))
        again = SMALL_FONT.render("Press ENTER to play again or ESC for menu", True, (220, 220, 220))

        surf.blit(win, (WIDTH // 2 - win.get_width() // 2, HEIGHT // 2 - 60))
        surf.blit(score, (WIDTH // 2 - score.get_width() // 2, HEIGHT // 2 + 6))
        surf.blit(again, (WIDTH // 2 - again.get_width() // 2, HEIGHT // 2 + 40))

    def draw_paused(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 135))
        surf.blit(overlay, (0, 0))
        txt = BIG_FONT.render("Paused", True, (255, 255, 255))
        opts = SMALL_FONT.render("P resume | O settings | R restart run | Q menu", True, (220, 220, 220))
        surf.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 40))
        surf.blit(opts, (WIDTH // 2 - opts.get_width() // 2, HEIGHT // 2 + 20))

    def draw_settings(self, surf):
        for i in range(0, HEIGHT, 24):
            pygame.draw.rect(surf, (10 + i // 28, 12 + i // 34, 20 + i // 24), (0, i, WIDTH, 24))

        title = BIG_FONT.render("Settings", True, (240, 240, 240))
        hint = SMALL_FONT.render("UP/DOWN select | LEFT/RIGHT adjust | ENTER toggle/select | ESC back", True, (200, 200, 200))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))
        surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 148))

        items = [
            ("Master Volume", f"{int(self.volume * 100)}%"),
            ("SFX Volume", f"{int(self.sfx_volume * 100)}%"),
            ("Music Volume", f"{int(self.music_volume * 100)}%"),
            ("Background Music", "ON" if self.bgm_enabled else "OFF"),
            ("Controls", self.controls_label()),
            ("Fullscreen", "ON" if self.fullscreen else "OFF"),
            ("Back", "Return"),
        ]

        y = 210
        for idx, (label, value) in enumerate(items):
            selected = idx == self.settings_index
            color = (255, 230, 140) if selected else (230, 230, 230)
            line = FONT.render(f"{label}: {value}", True, color)
            surf.blit(line, (WIDTH // 2 - line.get_width() // 2, y))
            y += 46

    def draw_transition(self, surf):
        if self.transition_alpha <= 0:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(self.transition_alpha)
        surf.blit(overlay, (0, 0))

    def update_transition(self):
        if self.transition_target != self.game_state:
            self.transition_alpha = min(255, self.transition_alpha + 28)
            if self.transition_alpha >= 250:
                self.transition_target = self.game_state
        else:
            self.transition_alpha = max(0, self.transition_alpha - 20)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.finalize_run()
                self.save_high_score()
                pygame.quit()
                sys.exit()

            if event.type != pygame.KEYDOWN:
                continue

            if self.game_state == "SETTINGS":
                if event.key == pygame.K_ESCAPE:
                    self.game_state = self.settings_return_state
                    continue

                if event.key == pygame.K_UP:
                    self.settings_index = (self.settings_index - 1) % 7
                elif event.key == pygame.K_DOWN:
                    self.settings_index = (self.settings_index + 1) % 7
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    direction = -1 if event.key == pygame.K_LEFT else 1
                    if self.settings_index == 0:
                        self.volume = max(0.0, min(1.0, self.volume + direction * 0.05))
                        self.apply_volume()
                        self.save_profile()
                    elif self.settings_index == 1:
                        self.sfx_volume = max(0.0, min(1.0, self.sfx_volume + direction * 0.05))
                        self.apply_volume()
                        self.save_profile()
                    elif self.settings_index == 2:
                        self.music_volume = max(0.0, min(1.0, self.music_volume + direction * 0.05))
                        self.apply_volume()
                        self.save_profile()
                    elif self.settings_index == 3:
                        self.toggle_bgm()
                    elif self.settings_index == 4:
                        self.toggle_controls_preset()
                    elif self.settings_index == 5:
                        self.toggle_fullscreen()
                elif event.key == pygame.K_RETURN:
                    if self.settings_index == 3:
                        self.toggle_bgm()
                    elif self.settings_index == 4:
                        self.toggle_controls_preset()
                    elif self.settings_index == 5:
                        self.toggle_fullscreen()
                    elif self.settings_index == 6:
                        self.game_state = self.settings_return_state
                continue

            if event.key == pygame.K_ESCAPE:
                if self.game_state == "PLAYING":
                    self.game_state = "MENU"
                    self.paused = False
                elif self.game_state in {"GAME_OVER", "CAMPAIGN_WIN"}:
                    self.game_state = "MENU"
                elif self.game_state == "MENU":
                    self.finalize_run()
                    self.save_high_score()
                    pygame.quit()
                    sys.exit()

            if self.game_state == "MENU" and event.key == pygame.K_UP:
                self.update_difficulty(-1)
            if self.game_state == "MENU" and event.key == pygame.K_DOWN:
                self.update_difficulty(1)
            if self.game_state == "MENU" and event.key == pygame.K_s:
                self.open_settings("MENU")

            if event.key == pygame.K_RETURN:
                if self.game_state == "MENU":
                    self.start_new_game()
                elif self.game_state in {"GAME_OVER", "CAMPAIGN_WIN"}:
                    self.start_new_game()

            if event.key == pygame.K_p and self.game_state == "PLAYING":
                self.paused = not self.paused

            if self.game_state == "PLAYING" and self.paused and event.key == pygame.K_r:
                self.start_new_game()
            if self.game_state == "PLAYING" and self.paused and event.key == pygame.K_q:
                self.finalize_run()
                self.game_state = "MENU"
                self.paused = False
            if self.game_state == "PLAYING" and self.paused and event.key == pygame.K_o:
                self.open_settings("PLAYING")

            if event.key == pygame.K_m:
                self.volume = min(1.0, self.volume + 0.1)
                self.apply_volume()
                self.save_profile()
            if event.key == pygame.K_n:
                self.volume = max(0.0, self.volume - 0.1)
                self.apply_volume()
                self.save_profile()
            if event.key == pygame.K_b:
                self.toggle_bgm()

            if event.key == pygame.K_f and self.game_state == "PLAYING" and not self.paused:
                self.fire_laser()

    def tick(self):
        self.handle_events()

        keys = pygame.key.get_pressed()

        if self.game_state == "PLAYING" and not self.paused:
            if keys[self.left_key] and self.paddle.rect.left > 0:
                self.paddle.rect.x -= self.paddle.speed
            if keys[self.right_key] and self.paddle.rect.right < WIDTH:
                self.paddle.rect.x += self.paddle.speed

            self.update_balls(keys)
            self.update_boss_mechanics()
            self.update_boss_projectiles()
            self.update_brick_collisions()
            self.update_powerups()
            self.update_combo()
            self.update_particles()

            if self.round_start_countdown > 0:
                self.round_start_countdown -= 1
            if self.tutorial_timer > 0:
                self.tutorial_timer -= 1
            if self.sticky_timer > 0:
                self.sticky_timer -= 1
                if self.sticky_timer == 0:
                    self.sticky_active = False
            if self.big_paddle_timer > 0:
                self.big_paddle_timer -= 1
                if self.big_paddle_timer == 0:
                    center = self.paddle.rect.centerx
                    self.paddle.rect.width = self.default_paddle_width
                    self.paddle.rect.centerx = center
                    self.paddle.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

            if self.slow_timer > 0:
                self.slow_timer -= 1
                if self.slow_timer == 0:
                    for ball in self.balls:
                        ball.apply_speed_scale(1.25)

            if self.power_message_timer > 0:
                self.power_message_timer -= 1
            if self.level_flash_timer > 0:
                self.level_flash_timer -= 1
            if self.laser_cooldown > 0:
                self.laser_cooldown -= 1
            if self.laser_flash_timer > 0:
                self.laser_flash_timer -= 1
            if self.shake_frames > 0:
                self.shake_frames -= 1

            if self.has_cleared_level():
                self.go_to_next_level()

        self.render()

    def render(self):
        world = pygame.Surface((WIDTH, HEIGHT))

        if self.game_state == "MENU":
            self.draw_menu(world)
        elif self.game_state == "SETTINGS":
            self.draw_settings(world)
        elif self.game_state == "GAME_OVER":
            self.draw_world(world)
            self.draw_hud(world)
            self.draw_game_over(world)
        elif self.game_state == "CAMPAIGN_WIN":
            self.draw_world(world)
            self.draw_hud(world)
            self.draw_campaign_win(world)
        else:
            self.draw_world(world)
            self.draw_hud(world)
            if self.paused:
                self.draw_paused(world)

        self.update_transition()
        self.draw_transition(world)

        shake_x = random.randint(-self.shake_strength, self.shake_strength) if self.shake_frames > 0 else 0
        shake_y = random.randint(-self.shake_strength, self.shake_strength) if self.shake_frames > 0 else 0

        SCREEN.fill((0, 0, 0))
        SCREEN.blit(world, (shake_x, shake_y))
        pygame.display.flip()


def main():
    game = Game()
    while True:
        game.tick()
        CLOCK.tick(60)


if __name__ == "__main__":
    main()
