"""
Main game runtime.

Non-technical reading guide:
1. `Game.__init__` prepares settings, progress, and starting objects.
2. `tick()` runs every frame and updates gameplay logic.
3. `render()` draws the current screen (menu, gameplay, settings, etc.).
4. Helper methods below are grouped by responsibility:
   saves/settings, run flow, gameplay systems, drawing, and input handling.
"""

import math
import random
import sys
from datetime import date

try:
    import pygame
except ImportError:
    import sys
    print("pygame is not installed. Please install it with: pip install pygame")
    sys.exit(1)

import scenes as scenes_module

from audio import apply_audio_volume, init_audio, load_game_sounds, start_music_loop
from ball import Ball
from brick import Brick
from config import (
    BALL_TRAILS,
    BOSS_LEVEL_INTERVAL,
    CAMPAIGN_LEVELS,
    DAILY_BOSS_INTERVAL,
    DAILY_LAYOUT_COLS,
    DAILY_LAYOUT_ROWS,
    DAILY_LAYOUT_THRESHOLDS,
    DIFFICULTY_CONFIG,
    GHOST_MAX_FRAMES,
    GHOST_RECORD_STEP,
    GAME_MODES,
    HEIGHT,
    HIGH_SCORE_FILE,
    HUD_HEIGHT,
    LEVEL_LAYOUTS,
    MUSIC_PATH,
    PADDLE_SKINS,
    PROFILE_FILE,
    SHOP_PRICES,
    WIDTH,
)
from game_state import (
    add_run_rewards,
    build_daily_share_code,
    daily_label_to_seed,
    default_profile,
    get_daily_ghost,
    load_high_score as load_high_score_data,
    load_profile as load_profile_data,
    parse_daily_share_code,
    save_high_score as save_high_score_data,
    save_profile as save_profile_data,
    update_daily_ghost,
    update_leaderboard as update_profile_leaderboard,
)
from modes import boss_attack_name, boss_personality_for_level, pick_normal_brick_variant, roll_powerup_drop
from paddle import Paddle
from powerup import PowerUp
from ui import draw_button

pygame.init()
init_audio()

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Breakout: Arcade Edition")
CLOCK = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 24)
SMALL_FONT = pygame.font.SysFont("arial", 18)
BIG_FONT = pygame.font.SysFont("arial", 56)
SOUNDS = load_game_sounds()



class BaseScene:
    def handle_event(self, _game, _event):
        return

    def update(self, _game, _keys):
        return

    def draw(self, _game, _surf):
        return


class MenuScene(BaseScene):
    def handle_event(self, game, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in game.menu_buttons.items():
                if rect.collidepoint(event.pos):
                    if key == "START":
                        game.start_new_game()
                    elif key == "SHOP":
                        game.set_game_state("SHOP")
                    elif key == "BOARD":
                        game.set_game_state("LEADERBOARD")
                    elif key == "SHARE":
                        game.daily_share_input = ""
                        game.daily_share_input_message = ""
                        game.set_game_state("SEED_INPUT")
                    elif key == "SETTINGS":
                        game.open_settings("MENU")
                    elif key == "QUIT":
                        game.finalize_run()
                        game.save_high_score()
                        pygame.quit()
                        sys.exit()
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            game.finalize_run()
            game.save_high_score()
            pygame.quit()
            sys.exit()
        if event.key == pygame.K_UP:
            game.update_difficulty(-1)
        elif event.key == pygame.K_DOWN:
            game.update_difficulty(1)
        elif event.key == pygame.K_LEFT:
            game.update_mode(-1)
        elif event.key == pygame.K_RIGHT:
            game.update_mode(1)
        elif event.key == pygame.K_s:
            game.open_settings("MENU")
        elif event.key == pygame.K_h:
            game.set_game_state("SHOP")
        elif event.key == pygame.K_l:
            game.set_game_state("LEADERBOARD")
        elif event.key == pygame.K_g:
            game.daily_share_input = ""
            game.daily_share_input_message = ""
            game.set_game_state("SEED_INPUT")
        elif event.key == pygame.K_RETURN:
            game.start_new_game()

    def draw(self, game, surf):
        game.draw_menu(surf)


class ShopScene(BaseScene):
    def handle_event(self, game, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, cat, item, owned, _ in getattr(game, "shop_cards", []):
                if rect.collidepoint(event.pos):
                    load = game.loadout()
                    selected_key = "selected_background" if cat == "bg" else "selected_paddle_skin" if cat == "paddle" else "selected_trail"
                    if owned:
                        load[selected_key] = item
                        game.save_profile()
                        game.set_power_message(f"Equipped {item}")
                    else:
                        ok, msg = game.buy_item(f"{cat}:{item}")
                        if ok:
                            load[selected_key] = item
                            game.save_profile()
                        game.set_power_message(msg)
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.set_game_state("MENU")

    def draw(self, game, surf):
        game.draw_shop(surf)


class LeaderboardScene(BaseScene):
    def handle_event(self, game, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.set_game_state("MENU")

    def draw(self, game, surf):
        game.draw_leaderboard(surf)


class SeedInputScene(BaseScene):
    def handle_event(self, game, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            game.set_game_state("MENU")
            return
        if event.key == pygame.K_BACKSPACE:
            game.daily_share_input = game.daily_share_input[:-1]
            return
        if event.key == pygame.K_RETURN:
            parsed = parse_daily_share_code(game.daily_share_input)
            if parsed:
                label, level = parsed
                game.daily_seed_override_label = label
                game.daily_seed_override_level = level
                game.daily_share_input_message = f"Loaded code for {label} (shared from wave {level})."
                game.mode_index = GAME_MODES.index("DAILY")
                game.game_mode = "DAILY"
                game.set_game_state("MENU")
            else:
                game.daily_share_input_message = "Invalid code format."
            return
        if event.unicode and len(event.unicode) == 1 and event.unicode.isprintable():
            if len(game.daily_share_input) < 40 and (event.unicode.isalnum() or event.unicode in "-_"):
                game.daily_share_input += event.unicode.upper()

    def draw(self, game, surf):
        game.draw_seed_input(surf)


class RunSummaryScene(BaseScene):
    def handle_event(self, game, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for key, rect in game.summary_buttons.items():
                if rect.collidepoint(event.pos):
                    if key == "MENU":
                        game.set_game_state("MENU")
                    elif key == "RETRY":
                        game.start_new_game()
            return

        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            game.set_game_state("MENU")
        elif event.key == pygame.K_RETURN:
            game.start_new_game()

    def draw(self, game, surf):
        game.draw_run_summary(surf)


class SettingsScene(BaseScene):
    def apply_adjustment(self, game, direction):
        if game.settings_index == 0:
            game.volume = max(0.0, min(1.0, game.volume + direction * 0.05))
            game.apply_volume()
            game.save_profile()
        elif game.settings_index == 1:
            game.sfx_volume = max(0.0, min(1.0, game.sfx_volume + direction * 0.05))
            game.apply_volume()
            game.save_profile()
        elif game.settings_index == 2:
            game.music_volume = max(0.0, min(1.0, game.music_volume + direction * 0.05))
            game.apply_volume()
            game.save_profile()
        elif game.settings_index == 3:
            game.toggle_bgm()
        elif game.settings_index == 4:
            game.toggle_ghost_replay()
        elif game.settings_index == 5:
            game.toggle_controls_preset()
        elif game.settings_index == 6:
            game.toggle_fullscreen()

    def apply_confirm(self, game):
        if game.settings_index == 3:
            game.toggle_bgm()
        elif game.settings_index == 4:
            game.toggle_ghost_replay()
        elif game.settings_index == 5:
            game.toggle_controls_preset()
        elif game.settings_index == 6:
            game.toggle_fullscreen()
        elif game.settings_index == 7:
            game.game_state = game.settings_return_state

    def handle_event(self, game, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for idx, minus_rect, plus_rect in getattr(game, "settings_clickables", []):
                if minus_rect.collidepoint(event.pos):
                    game.settings_index = idx
                    self.apply_adjustment(game, -1)
                if plus_rect.collidepoint(event.pos):
                    game.settings_index = idx
                    self.apply_adjustment(game, 1)
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            game.game_state = game.settings_return_state
            return

        if event.key == pygame.K_UP:
            game.settings_index = (game.settings_index - 1) % 8
        elif event.key == pygame.K_DOWN:
            game.settings_index = (game.settings_index + 1) % 8
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.apply_adjustment(game, -1 if event.key == pygame.K_LEFT else 1)
        elif event.key == pygame.K_RETURN:
            self.apply_confirm(game)

    def draw(self, game, surf):
        game.draw_settings(surf)


class PlayingScene(BaseScene):
    def handle_event(self, game, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            game.game_state = "MENU"
            game.paused = False
            return

        if event.key == pygame.K_p and not game.paused:
            game.paused = True
            return
        if event.key == pygame.K_p and game.paused:
            game.paused = False
            return

        if game.paused and event.key == pygame.K_r:
            game.start_new_game()
            return
        if game.paused and event.key == pygame.K_q:
            game.finalize_run()
            game.game_state = "MENU"
            game.paused = False
            return
        if game.paused and event.key == pygame.K_o:
            game.open_settings("PLAYING")
            return

        if event.key == pygame.K_m:
            game.volume = min(1.0, game.volume + 0.1)
            game.apply_volume()
            game.save_profile()
            return
        if event.key == pygame.K_n:
            game.volume = max(0.0, game.volume - 0.1)
            game.apply_volume()
            game.save_profile()
            return
        if event.key == pygame.K_b:
            game.toggle_bgm()
            return

        if event.key == pygame.K_f and not game.paused:
            game.fire_laser()
            game.profile["tutorial"]["fired_laser_once"] = True
            game.save_profile()

    def update(self, game, keys):
        if game.paused:
            return

        moved_this_frame = False
        if keys[game.left_key] and game.paddle.rect.left > 0:
            game.paddle.rect.x -= game.paddle.speed
            moved_this_frame = True
        if keys[game.right_key] and game.paddle.rect.right < WIDTH:
            game.paddle.rect.x += game.paddle.speed
            moved_this_frame = True

        if game.controller:
            axis = game.controller.get_axis(0)
            if abs(axis) > 0.2:
                game.paddle.rect.x += int(axis * game.paddle.speed * 1.4)
                moved_this_frame = True
            game.paddle.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
            if game.ball_attached and game.round_start_countdown <= 0 and game.controller.get_button(0):
                game.ball_attached = False
                game.run_shots += 1
            if game.controller.get_button(1):
                game.fire_laser()

        if moved_this_frame and not game.profile["tutorial"].get("moved_once", False):
            game.profile["tutorial"]["moved_once"] = True
            game.save_profile()

        if game.hit_freeze_frames > 0:
            game.hit_freeze_frames -= 1
            game.update_particles()
        else:
            game.update_balls(keys)
            game.update_boss_mechanics()
            game.update_boss_projectiles()
            game.update_brick_modifiers()
            game.update_brick_collisions()
            game.update_powerups()
            game.update_combo()
            game.update_particles()

        if game.round_start_countdown > 0:
            game.round_start_countdown -= 1
        if game.tutorial_timer > 0:
            game.tutorial_timer -= 1
        if game.sticky_timer > 0:
            game.sticky_timer -= 1
            if game.sticky_timer == 0:
                game.sticky_active = False
        if game.big_paddle_timer > 0:
            game.big_paddle_timer -= 1
            if game.big_paddle_timer == 0:
                center = game.paddle.rect.centerx
                game.paddle.rect.width = game.default_paddle_width
                game.paddle.rect.centerx = center
                game.paddle.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

        if game.slow_timer > 0:
            game.slow_timer -= 1
            if game.slow_timer == 0:
                for ball in game.balls:
                    ball.apply_speed_scale(1.25)

        if game.power_message_timer > 0:
            game.power_message_timer -= 1
        if game.level_flash_timer > 0:
            game.level_flash_timer -= 1

        if game.laser_cooldown > 0:
            game.laser_cooldown -= 1
        if game.laser_flash_timer > 0:
            game.laser_flash_timer -= 1

        if game.shake_frames > 0:
            game.shake_frames -= 1
        else:
            game.shake_strength = 0
            game.shake_total_frames = 0

        if game.impact_flash_alpha > 0:
            game.impact_flash_alpha = max(0, game.impact_flash_alpha - 14)

        game.record_ghost_frame()
        game.run_frame += 1

        if game.has_cleared_level():
            game.go_to_next_level()

    def draw(self, game, surf):
        game.draw_world(surf)
        game.draw_hud(surf)
        if game.paused:
            game.draw_paused(surf)


class GameOverScene(BaseScene):
    def handle_event(self, game, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            game.set_game_state("MENU")
        elif event.key == pygame.K_RETURN:
            game.start_new_game()

    def draw(self, game, surf):
        game.draw_world(surf)
        game.draw_hud(surf)
        game.draw_game_over(surf)


class CampaignWinScene(BaseScene):
    def handle_event(self, game, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            game.set_game_state("MENU")
        elif event.key == pygame.K_RETURN:
            game.start_new_game()

    def draw(self, game, surf):
        game.draw_world(surf)
        game.draw_hud(surf)
        game.draw_campaign_win(surf)


class Game:
    """Owns all game state and coordinates update + drawing each frame."""

    def __init__(self):
        # --- Audio/user preference values ---
        self.volume = 0.7
        self.sfx_volume = 0.9
        self.music_volume = 0.6
        self.high_score = self.load_high_score()

        # --- Control bindings ---
        self.left_key = pygame.K_LEFT
        self.right_key = pygame.K_RIGHT

        # --- Difficulty + mode selections ---
        self.difficulty_order = ["EASY", "NORMAL", "HARD"]
        self.difficulty_index = 1
        self.difficulty = self.difficulty_order[self.difficulty_index]
        self.mode_index = 0
        self.game_mode = GAME_MODES[self.mode_index]
        self.ball_speed_base = DIFFICULTY_CONFIG[self.difficulty]["speed"]
        self.powerup_base_chance = DIFFICULTY_CONFIG[self.difficulty]["drop_chance"]
        self.level_speed_step = DIFFICULTY_CONFIG[self.difficulty]["speed_step"]
        self.score_mult = DIFFICULTY_CONFIG[self.difficulty]["score_mult"]

        # --- UI/scene state ---
        self.game_state = "MENU"
        self.transition_alpha = 255
        self.transition_target = "MENU"
        self.paused = False
        self.settings_index = 0
        self.settings_return_state = "MENU"
        self.fullscreen = False
        self.menu_buttons = {}
        self.shop_index = 0
        self.summary_buttons = {}
        self.leaderboard_scroll = 0

        # --- Visual effects ---
        self.shake_frames = 0
        self.shake_strength = 0
        self.shake_total_frames = 0
        self.shake_phase = 0.0
        self.particles = []

        # --- Active power-up/combat state ---
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

        # --- Score combo state ---
        self.combo = 0
        self.combo_timer = 0

        # --- Run/progression state ---
        self.level = 1
        self.level_flash_timer = 0
        self.round_start_countdown = 0
        self.tutorial_timer = 480
        self.bgm_enabled = True
        self.ghost_replay_enabled = True
        self.bgm_loaded = False
        self.bgm_channel = None
        self.bgm_error = ""
        self.boss_brick = None
        self.boss_direction = 1
        self.boss_attack_timer = 0
        self.boss_projectiles = []
        self.boss_pattern_index = 0
        self.run_active = False
        self.daily_seed = 0
        self.daily_label = ""
        self.daily_seed_override_label = ""
        self.daily_seed_override_level = 1
        self.daily_share_input = ""
        self.daily_share_input_message = ""
        self.ghost_record_step = GHOST_RECORD_STEP
        self.ghost_max_frames = GHOST_MAX_FRAMES
        self.ghost_record_trace = []
        self.ghost_playback = None
        self.run_frame = 0
        self.last_run_summary = {}
        self.run_shots = 0
        self.run_hits = 0
        self.run_projectiles_spawned = 0
        self.run_projectiles_hit = 0
        self.run_combo_peak = 0
        self.hit_freeze_frames = 0
        self.impact_flash_alpha = 0
        self.boss_personality = None

        # Load persistent profile and apply saved settings before building the run.
        self.profile = self.load_profile()
        self.apply_profile_settings()
        if self.fullscreen:
            global SCREEN
            info = pygame.display.Info()
            SCREEN = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
            pygame.display.set_caption("Breakout: Arcade Edition")

        self.reset_run(full_reset=True)
        self.apply_volume()
        self.try_start_music()
        self.init_controller()
        self.scenes = {
            "MENU": scenes_module.MenuScene(),
            "SHOP": scenes_module.ShopScene(),
            "LEADERBOARD": scenes_module.LeaderboardScene(),
            "SEED_INPUT": scenes_module.SeedInputScene(),
            "RUN_SUMMARY": scenes_module.RunSummaryScene(),
            "SETTINGS": scenes_module.SettingsScene(),
            "PLAYING": scenes_module.PlayingScene(),
            "GAME_OVER": scenes_module.GameOverScene(),
            "CAMPAIGN_WIN": scenes_module.CampaignWinScene(),
        }

    def default_profile(self):
        """Return default profile schema (delegates to helper module)."""
        return default_profile()

    def load_profile(self):
        """Load profile from disk and merge it with defaults."""
        return load_profile_data(PROFILE_FILE, self.load_high_score())

    def init_controller(self):
        """Attach first connected gamepad, if available."""
        self.controller = None
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.controller = pygame.joystick.Joystick(0)
            self.controller.init()

    def save_profile(self):
        """Save current profile/settings/high score to disk."""
        self.profile["high_score"] = int(self.high_score)
        self.profile["settings"] = {
            "master_volume": self.volume,
            "sfx_volume": self.sfx_volume,
            "music_volume": self.music_volume,
            "bgm_enabled": self.bgm_enabled,
            "ghost_replay": self.ghost_replay_enabled,
            "controls": self.controls_label(),
            "fullscreen": self.fullscreen,
        }
        save_profile_data(PROFILE_FILE, self.profile)
        self.save_high_score()

    def apply_profile_settings(self):
        """Apply persisted settings values to runtime variables."""
        settings = self.profile.get("settings", {})
        self.high_score = max(int(self.high_score), int(self.profile.get("high_score", 0)))
        self.volume = float(settings.get("master_volume", self.volume))
        self.sfx_volume = float(settings.get("sfx_volume", self.sfx_volume))
        self.music_volume = float(settings.get("music_volume", self.music_volume))
        self.bgm_enabled = bool(settings.get("bgm_enabled", self.bgm_enabled))
        self.ghost_replay_enabled = bool(settings.get("ghost_replay", self.ghost_replay_enabled))
        if settings.get("controls", "ARROWS") == "WASD":
            self.left_key = pygame.K_a
            self.right_key = pygame.K_d
        else:
            self.left_key = pygame.K_LEFT
            self.right_key = pygame.K_RIGHT
        self.fullscreen = bool(settings.get("fullscreen", self.fullscreen))

    def load_high_score(self):
        """Read high score save file."""
        return load_high_score_data(HIGH_SCORE_FILE)

    def save_high_score(self):
        """Write high score save file."""
        save_high_score_data(HIGH_SCORE_FILE, self.high_score)

    def play_sound(self, name):
        """Play one short sound effect by key."""
        sound = SOUNDS.get(name)
        if sound:
            sound.play()

    def apply_volume(self):
        """Push volume settings to loaded sounds/music."""
        apply_audio_volume(
            SOUNDS,
            self.volume,
            self.sfx_volume,
            self.music_volume,
            self.bgm_enabled,
            self.bgm_channel,
        )

    def try_start_music(self):
        """Attempt to start looping BGM and keep error info for UI."""
        self.bgm_loaded, self.bgm_channel, self.bgm_error = start_music_loop(MUSIC_PATH)

    def update_difficulty(self, direction):
        """Cycle difficulty and refresh balancing values."""
        self.difficulty_index = (self.difficulty_index + direction) % len(self.difficulty_order)
        self.difficulty = self.difficulty_order[self.difficulty_index]
        config = DIFFICULTY_CONFIG[self.difficulty]
        self.ball_speed_base = config["speed"]
        self.powerup_base_chance = config["drop_chance"]
        self.level_speed_step = config["speed_step"]
        self.score_mult = config["score_mult"]

    def update_mode(self, direction):
        """Cycle game mode (Campaign/Daily)."""
        self.mode_index = (self.mode_index + direction) % len(GAME_MODES)
        self.game_mode = GAME_MODES[self.mode_index]

    def daily_seed_for_today(self):
        """Generate deterministic seed label/value for today's Daily run."""
        today = date.today().isoformat()
        self.daily_label = today
        return daily_label_to_seed(today)

    def toggle_bgm(self):
        """Turn background music on/off."""
        self.bgm_enabled = not self.bgm_enabled
        self.apply_volume()
        self.save_profile()

    def toggle_controls_preset(self):
        """Switch between Arrow keys and WASD movement presets."""
        if self.left_key == pygame.K_LEFT:
            self.left_key = pygame.K_a
            self.right_key = pygame.K_d
        else:
            self.left_key = pygame.K_LEFT
            self.right_key = pygame.K_RIGHT
        self.save_profile()

    def toggle_ghost_replay(self):
        """Enable/disable Daily ghost recording + playback."""
        self.ghost_replay_enabled = not self.ghost_replay_enabled
        if not self.ghost_replay_enabled:
            self.ghost_playback = None
        elif self.game_mode == "DAILY" and self.daily_label:
            self.ghost_playback = get_daily_ghost(self.profile, self.daily_label)
        self.save_profile()

    def controls_label(self):
        """Return current keyboard preset label for UI display."""
        return "ARROWS" if self.left_key == pygame.K_LEFT else "WASD"

    def loadout(self):
        """Convenience accessor for loadout section in profile."""
        return self.profile.setdefault("loadout", self.default_profile()["loadout"])

    def economy(self):
        """Convenience accessor for economy section in profile."""
        return self.profile.setdefault("economy", self.default_profile()["economy"])

    def set_game_state(self, state):
        """Change active scene (menu, play, settings, etc.)."""
        self.game_state = state

    def player_currency(self):
        """Return player currency total as integer."""
        return int(self.economy().get("currency", 0))

    def add_rewards_for_run(self):
        """Apply run-end XP/currency rewards."""
        return add_run_rewards(self.profile, self.score, self.level)

    def update_leaderboard(self):
        """Insert current run into mode leaderboard."""
        update_profile_leaderboard(self.profile, self.game_mode, self.score, self.level, self.daily_label)

    def buy_item(self, item_key):
        """Try to buy one shop item and return (success, message)."""
        load = self.loadout()
        econ = self.economy()
        cost = SHOP_PRICES.get(item_key)
        if cost is None:
            return False, "Unknown"
        if int(econ.get("currency", 0)) < cost:
            return False, "Not enough currency"

        category, item = item_key.split(":")
        if category == "paddle":
            owned = load.setdefault("owned_paddle_skins", ["classic"])
        elif category == "trail":
            owned = load.setdefault("owned_trails", ["none"])
        elif category == "bg":
            owned = load.setdefault("owned_backgrounds", ["default"])
        else:
            return False, "Invalid item"

        if item in owned:
            return False, "Owned"

        econ["currency"] = int(econ.get("currency", 0)) - cost
        owned.append(item)
        self.save_profile()
        return True, f"Unlocked {item}"

    def toggle_fullscreen(self):
        """Toggle fullscreen display mode."""
        global SCREEN
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            info = pygame.display.Info()
            SCREEN = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        else:
            SCREEN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Breakout: Arcade Edition")
        self.save_profile()

    def open_settings(self, return_state):
        """Open settings scene and remember where to return."""
        self.settings_return_state = return_state
        self.settings_index = 0
        self.game_state = "SETTINGS"

    def finalize_run(self):
        """Close out the active run, grant rewards, and build summary stats."""
        if not self.run_active:
            return
        stats = self.profile["stats"]
        stats["runs_completed"] = int(stats.get("runs_completed", 0)) + 1
        stats["lifetime_score"] = int(stats.get("lifetime_score", 0)) + int(self.score)
        stats["best_level_reached"] = max(int(stats.get("best_level_reached", 1)), int(self.level))
        if self.game_mode == "DAILY":
            best = int(stats.get("daily_best_score", 0))
            if self.score > best:
                stats["daily_best_score"] = int(self.score)
                stats["daily_best_date"] = self.daily_label or date.today().isoformat()
        xp_gain, currency_gain = self.add_rewards_for_run()
        self.update_leaderboard()
        ghost_saved = False
        if self.game_mode == "DAILY" and self.ghost_replay_enabled and self.daily_label and self.ghost_record_trace:
            ghost_saved = update_daily_ghost(
                self.profile,
                self.daily_label,
                self.score,
                self.level,
                self.ghost_record_trace,
                self.ghost_record_step,
            )
        dodged = max(0, self.run_projectiles_spawned - self.run_projectiles_hit)
        accuracy = 0 if self.run_shots == 0 else min(100, int((self.run_hits / max(1, self.run_shots)) * 100))
        self.last_run_summary = {
            "score": int(self.score),
            "level": int(self.level),
            "mode": self.game_mode,
            "xp_gain": xp_gain,
            "currency_gain": currency_gain,
            "combo_peak": int(self.run_combo_peak),
            "accuracy": accuracy,
            "projectiles_dodged": dodged,
            "daily_share": build_daily_share_code(self.daily_label, self.level) if self.game_mode == "DAILY" else "",
            "ghost_saved": ghost_saved,
        }
        self.run_active = False
        self.save_profile()
        self.set_game_state("RUN_SUMMARY")

    def start_new_game(self):
        """Start a fresh run using current menu selections."""
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
        if self.game_mode == "DAILY":
            self.profile["stats"]["daily_runs"] = int(self.profile["stats"].get("daily_runs", 0)) + 1
            if self.daily_seed_override_label:
                self.daily_label = self.daily_seed_override_label
                self.daily_seed = daily_label_to_seed(self.daily_label)
                self.daily_seed_override_label = ""
            else:
                self.daily_seed = self.daily_seed_for_today()
        else:
            self.daily_seed = 0
            self.daily_label = ""
        self.ghost_playback = (
            get_daily_ghost(self.profile, self.daily_label)
            if self.game_mode == "DAILY" and self.ghost_replay_enabled
            else None
        )
        self.save_profile()
        self.run_shots = 0
        self.run_hits = 0
        self.run_projectiles_spawned = 0
        self.run_projectiles_hit = 0
        self.run_combo_peak = 0
        self.ghost_record_trace = []
        self.run_frame = 0
        self.reset_run(full_reset=True)

    def reset_run(self, full_reset):
        """Reset board entities and temporary effects for next life/level/run."""
        if full_reset:
            self.score = 0
            self.lives = getattr(self, "starting_lives", DIFFICULTY_CONFIG[self.difficulty]["lives"])
            self.level = 1
            self.ball_speed_base = DIFFICULTY_CONFIG[self.difficulty]["speed"]
            self.powerup_base_chance = DIFFICULTY_CONFIG[self.difficulty]["drop_chance"]
            self.level_speed_step = DIFFICULTY_CONFIG[self.difficulty]["speed_step"]
            self.score_mult = DIFFICULTY_CONFIG[self.difficulty]["score_mult"]
            self.tutorial_timer = 480

        load = self.loadout()
        paddle_skin = load.get("selected_paddle_skin", "classic")
        paddle_color = PADDLE_SKINS.get(paddle_skin, (255, 255, 255))
        self.paddle = Paddle(x=WIDTH // 2 - 70, y=HEIGHT - 35, width=140, height=15, color=paddle_color)
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
        self.boss_personality = None
        self.boss_direction = 1
        self.boss_attack_timer = max(120, 300 - self.level * 10)
        self.boss_projectiles = []
        self.boss_pattern_index = 0

    def is_boss_level(self, level):
        """Return True when this level should spawn a boss wave."""
        interval = DAILY_BOSS_INTERVAL if self.game_mode == "DAILY" else BOSS_LEVEL_INTERVAL
        return level % interval == 0

    def create_boss_wave(self, level):
        """Create boss brick plus support guards for boss levels."""
        bricks = []
        self.boss_personality = boss_personality_for_level(level, self.game_mode)
        boss_hits = 14 + level * 2 + int(self.boss_personality["speed"] * 1.5)
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
        self.set_power_message(f"Boss personality: {self.boss_personality['name']}")

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

    def create_daily_layout(self, level):
        """Generate deterministic Daily brick layout from seed + level."""
        rng = random.Random(self.daily_seed + level * 7919)
        layout = []
        for _ in range(DAILY_LAYOUT_ROWS):
            row_chars = []
            for _ in range(DAILY_LAYOUT_COLS):
                roll = rng.random()
                chosen = "N"
                for threshold, code in DAILY_LAYOUT_THRESHOLDS:
                    if roll < threshold:
                        chosen = code
                        break
                row_chars.append(chosen)
            layout.append("".join(row_chars))
        return layout

    def create_bricks(self, level):
        """Build all bricks for the current level/wave."""
        if self.is_boss_level(level):
            return self.create_boss_wave(level)

        if self.game_mode == "DAILY":
            layout = self.create_daily_layout(level)
        else:
            layout = LEVEL_LAYOUTS[(level - 1) % len(LEVEL_LAYOUTS)]
        bricks = []
        rows = len(layout)
        cols = len(layout[0])
        margin_x = 40
        top = HUD_HEIGHT + 20
        usable_w = WIDTH - margin_x * 2
        brick_w = usable_w // cols
        brick_h = 26
        self.brick_grid_top = top
        self.brick_grid_left = margin_x
        self.brick_cell_w = brick_w
        self.brick_cell_h = brick_h

        for row in range(rows):
            for col in range(cols):
                code = layout[row][col]
                if code == ".":
                    continue
                x = margin_x + col * brick_w
                y = top + row * brick_h

                if code == "N":
                    color = (90 + row * 15, 130 + col * 5, 220)
                    variant = pick_normal_brick_variant(random, level, self.game_mode)
                    if variant == "regen":
                        bricks.append(Brick(x, y, brick_w - 2, brick_h - 2, color, points=70, hits=2, brick_type="regen"))
                    elif variant == "teleport":
                        bricks.append(Brick(x, y, brick_w - 2, brick_h - 2, color, points=80, hits=2, brick_type="teleport"))
                    elif variant == "shielded":
                        bricks.append(Brick(x, y, brick_w - 2, brick_h - 2, color, points=90, hits=2, brick_type="shielded"))
                    elif variant == "timed_bomb":
                        bricks.append(Brick(x, y, brick_w - 2, brick_h - 2, color, points=110, hits=1, brick_type="timed_bomb", bomb_timer=560 - level * 10))
                    else:
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
        """Spawn one known powerup/hazard type."""
        self.powerups.append(PowerUp(x, y, 26, 20, power_type))

    def spawn_powerup(self, x, y):
        """Roll random powerup/hazard drop based on mode and level."""
        power_type = roll_powerup_drop(random, self.level, self.powerup_base_chance, self.is_boss_level(self.level))
        if power_type:
            self.powerups.append(PowerUp(x, y, 26, 20, power_type))

    def spawn_particles(self, x, y, color, count=10, layer=1):
        """Create short-lived particles for impact feedback."""
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
                    "layer": layer,
                }
            )

    def add_shake(self, strength, frames):
        """Request a camera shake burst."""
        if frames >= self.shake_frames:
            self.shake_total_frames = frames
        self.shake_strength = max(self.shake_strength, strength)
        self.shake_frames = max(self.shake_frames, frames)

    def explode_neighbors(self, source_brick):
        """Damage nearby bricks for explosive effects."""
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

    def detonate_bomb(self, source_brick):
        """Force timed bomb explosion and return points gained."""
        if source_brick.destroyed:
            return 0
        source_brick.destroyed = True
        self.spawn_particles(source_brick.rect.centerx, source_brick.rect.centery, (255, 90, 90), count=18)
        gained = source_brick.points
        gained += self.explode_neighbors(source_brick)
        self.add_shake(6, 12)
        return gained

    def set_power_message(self, text):
        """Show short center-screen status text for recent effects."""
        self.power_message = text
        self.power_message_timer = 140

    def award_points(self, points):
        """Apply score multiplier and update high score if needed."""
        gained = int(points * self.score_mult)
        self.score += gained
        if self.score > self.high_score:
            self.high_score = self.score
            self.save_high_score()
        return gained

    def apply_powerup(self, powerup):
        """Apply gameplay effect for collected powerup/hazard."""
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
        """Fire paddle laser upward to damage nearest aligned brick."""
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
        """Advance and cull active particles."""
        next_particles = []
        for p in self.particles:
            p["x"] += p["dx"]
            p["y"] += p["dy"]
            p["dy"] += 0.08
            p["life"] -= 1
            if p["life"] > 0:
                next_particles.append(p)
        self.particles = next_particles

    def record_ghost_frame(self):
        """Record sparse ghost samples for Daily replay."""
        if self.game_mode != "DAILY" or not self.run_active or not self.ghost_replay_enabled:
            return
        if self.run_frame % self.ghost_record_step != 0:
            return
        max_samples = max(1, self.ghost_max_frames // self.ghost_record_step)
        if len(self.ghost_record_trace) >= max_samples:
            return
        ball_pos = None
        if self.balls and not self.ball_attached:
            ball = self.balls[0]
            ball_pos = [round(float(ball.x), 1), round(float(ball.y), 1)]
        self.ghost_record_trace.append(
            {
                "p": int(self.paddle.rect.centerx),
                "b": ball_pos,
            }
        )

    def ghost_frame_snapshot(self):
        """Read ghost sample for current frame, if available."""
        if self.game_mode != "DAILY" or not self.ghost_replay_enabled or not self.ghost_playback:
            return None
        trace = self.ghost_playback.get("trace", [])
        if not trace:
            return None
        step = max(1, int(self.ghost_playback.get("step", 1)))
        idx = min(len(trace) - 1, self.run_frame // step)
        if idx < 0:
            return None
        return trace[idx]

    def spawn_boss_pattern(self, pattern):
        """Spawn projectiles/hazards for one boss attack pattern."""
        if not self.boss_brick:
            return 0
        spawned = 0
        if pattern == "spread":
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
                spawned += 1
        elif pattern == "rain":
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
                spawned += 1
        elif pattern == "sniper":
            dx = (self.paddle.rect.centerx - self.boss_brick.rect.centerx) * 0.018
            self.boss_projectiles.append(
                {
                    "x": self.boss_brick.rect.centerx,
                    "y": self.boss_brick.rect.bottom + 8,
                    "dx": dx,
                    "dy": 5.2 + self.level * 0.10,
                    "r": 8,
                    "color": (255, 210, 120),
                }
            )
            spawned += 1
        elif pattern == "mine":
            self.boss_projectiles.append(
                {
                    "x": self.boss_brick.rect.centerx,
                    "y": self.boss_brick.rect.bottom + 8,
                    "dx": random.uniform(-1.0, 1.0),
                    "dy": 2.4 + self.level * 0.06,
                    "r": 11,
                    "color": (210, 110, 255),
                }
            )
            self.spawn_specific_powerup(self.boss_brick.rect.centerx, self.boss_brick.rect.bottom + 6, random.choice(["small", "fast"]))
            spawned += 1
        else:
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
            spawned += 1
        return spawned

    def update_boss_mechanics(self):
        """Move boss and trigger timed attack patterns."""
        if not self.boss_brick or self.boss_brick.destroyed:
            return

        personality = self.boss_personality or boss_personality_for_level(self.level, self.game_mode)
        speed = personality["speed"] + self.level * 0.08
        self.boss_brick.rect.x += speed * self.boss_direction
        min_x = 80
        max_x = WIDTH - 80 - self.boss_brick.rect.width
        if self.boss_brick.rect.x <= min_x or self.boss_brick.rect.x >= max_x:
            self.boss_direction *= -1
            self.boss_brick.rect.x = max(min_x, min(self.boss_brick.rect.x, max_x))

        self.boss_attack_timer -= 1
        if self.boss_attack_timer <= 0:
            patterns = personality.get("patterns", ["spread", "rain", "pressure"])
            pattern = patterns[self.boss_pattern_index % len(patterns)]
            spawned = self.spawn_boss_pattern(pattern)
            self.set_power_message(f"{personality['name']} attack: {boss_attack_name(pattern)}")
            self.boss_pattern_index += 1
            self.boss_attack_timer = max(72, int(personality["cooldown"] - self.level * 6))
            self.run_projectiles_spawned += spawned

    def update_boss_projectiles(self):
        """Move boss projectiles and resolve paddle hits."""
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
                self.run_projectiles_hit += 1
                if self.shield_active:
                    self.shield_active = False
                    self.spawn_particles(int(proj["x"]), int(proj["y"]), (80, 240, 170), count=8)
                else:
                    self.apply_powerup(PowerUp(self.paddle.rect.centerx, self.paddle.rect.y, 20, 20, random.choice(["small", "fast"])))
                    self.spawn_particles(int(proj["x"]), int(proj["y"]), proj["color"], count=10)
                continue

            next_projectiles.append(proj)

        self.boss_projectiles = next_projectiles

    def update_brick_modifiers(self):
        """Tick special brick timers (regen + timed bombs)."""
        for brick in self.bricks:
            if brick.destroyed:
                continue
            if brick.brick_type == "regen":
                brick.regen_timer -= 1
                if brick.regen_timer <= 0:
                    if brick.hits < brick.max_hits:
                        brick.hits += 1
                    brick.regen_timer = 260
            elif brick.brick_type == "timed_bomb":
                brick.bomb_timer -= 1
                if brick.bomb_timer <= 0:
                    self.award_points(self.detonate_bomb(brick))

    def update_combo(self):
        """Decay combo when player goes too long without scoring hits."""
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0

    def update_balls(self, keys):
        """Move balls, resolve paddle/wall/life-loss behavior."""
        if self.ball_attached and self.balls:
            self.balls[0].x = self.paddle.rect.centerx
            self.balls[0].y = self.paddle.rect.top - self.balls[0].radius

        if self.ball_attached and keys[pygame.K_SPACE] and self.round_start_countdown <= 0:
            self.ball_attached = False
            self.run_shots += 1

        for ball in self.balls:
            if self.ball_attached:
                break
            ball.move()
            trail_name = self.loadout().get("selected_trail", "none")
            trail_color = BALL_TRAILS.get(trail_name)
            if trail_color:
                self.particles.append(
                    {
                        "x": ball.x,
                        "y": ball.y,
                        "dx": random.uniform(-0.5, 0.5),
                        "dy": random.uniform(0.2, 1.1),
                        "life": random.randint(8, 14),
                        "color": trail_color,
                        "size": random.randint(1, 2),
                        "layer": 0,
                    }
                )
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
        """Resolve ball-brick collisions and brick special effects."""
        for ball in list(self.balls):
            for brick in self.bricks:
                if brick.destroyed:
                    continue
                if not ball.collide_with_rect(brick.rect):
                    continue

                if brick.unbreakable:
                    self.play_sound("wall")
                    self.add_shake(2, 4)
                    break

                destroyed = brick.hit()
                self.run_hits += 1
                self.hit_freeze_frames = 2
                self.impact_flash_alpha = min(180, self.impact_flash_alpha + 90)
                self.play_sound("brick")
                self.spawn_particles(brick.rect.centerx, brick.rect.centery, brick.base_color, count=8)

                if destroyed:
                    self.combo += 1
                    self.combo_timer = 90
                    self.run_combo_peak = max(self.run_combo_peak, self.combo)
                    points = int(brick.points * (1 + self.combo * 0.15))
                    if brick.brick_type == "timed_bomb":
                        points = self.detonate_bomb(brick)
                    self.award_points(points)
                    self.profile["stats"]["bricks_broken"] = int(self.profile["stats"].get("bricks_broken", 0)) + 1
                    self.spawn_powerup(brick.rect.centerx, brick.rect.centery)

                    if brick.brick_type == "explosive":
                        self.award_points(self.explode_neighbors(brick))
                    elif brick.brick_type == "boss":
                        self.set_power_message("Boss destroyed")
                        self.add_shake(8, 22)
                        self.boss_brick = None
                        self.boss_projectiles = []
                        self.profile["stats"]["bosses_defeated"] = int(self.profile["stats"].get("bosses_defeated", 0)) + 1
                        self.save_profile()
                    else:
                        self.add_shake(3, 7)
                elif brick.brick_type == "teleport":
                    # Teleport to another grid location when not destroyed.
                    new_col = random.randint(0, 9)
                    new_row = random.randint(0, 5)
                    brick.rect.x = self.brick_grid_left + new_col * self.brick_cell_w
                    brick.rect.y = self.brick_grid_top + new_row * self.brick_cell_h
                    self.spawn_particles(brick.rect.centerx, brick.rect.centery, (170, 120, 255), count=10)
                break

    def update_powerups(self):
        """Update falling powerups and apply effects on pickup."""
        for powerup in self.powerups:
            powerup.update(HEIGHT)
            if powerup.rect.colliderect(self.paddle.rect):
                self.apply_powerup(powerup)
                powerup.active = False
                self.spawn_particles(powerup.rect.centerx, powerup.rect.centery, powerup.color, count=8)

        self.powerups = [p for p in self.powerups if p.active]

    def has_cleared_level(self):
        """Check whether all breakable bricks are gone."""
        return all(brick.destroyed or brick.unbreakable for brick in self.bricks)

    def go_to_next_level(self):
        """Advance to next level or end run if campaign is complete."""
        if self.game_mode == "CAMPAIGN" and self.level >= CAMPAIGN_LEVELS:
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
        """Draw particles in layer order (background to foreground)."""
        for p in sorted(self.particles, key=lambda item: item.get("layer", 1)):
            pygame.draw.circle(surf, p["color"], (int(p["x"]), int(p["y"])), p["size"])

    def draw_hud(self, surf):
        """Draw top HUD info (score, lives, mode, status tags)."""
        pygame.draw.rect(surf, (16, 20, 28), (0, 0, WIDTH, HUD_HEIGHT))
        score_text = FONT.render(f"Score: {self.score}", True, (240, 240, 240))
        lives_text = FONT.render(f"Lives: {self.lives}", True, (240, 240, 240))
        if self.game_mode == "CAMPAIGN":
            level_text = FONT.render(f"Level: {self.level}/{CAMPAIGN_LEVELS}", True, (240, 240, 240))
        else:
            level_text = FONT.render(f"Wave: {self.level}  Seed: {self.daily_label}", True, (240, 240, 240))
        hi_text = SMALL_FONT.render(f"High: {self.high_score}", True, (200, 200, 200))
        diff_text = SMALL_FONT.render(f"{self.game_mode} | {self.difficulty} x{self.score_mult:.1f}", True, (180, 220, 255))

        surf.blit(score_text, (14, 6))
        surf.blit(lives_text, (180, 6))
        surf.blit(level_text, (330, 6))
        surf.blit(hi_text, (14, 38))
        surf.blit(diff_text, (180, 38))
        if self.game_mode == "DAILY" and self.ghost_playback:
            ghost_text = SMALL_FONT.render("Ghost: ON", True, (170, 220, 255))
            surf.blit(ghost_text, (WIDTH - 110, 38))

        if self.combo > 1:
            combo_text = FONT.render(f"Combo x{self.combo}", True, (255, 210, 80))
            surf.blit(combo_text, (470, 32))

        if self.laser_charges > 0:
            laser_text = SMALL_FONT.render(f"Laser: {self.laser_charges}", True, (255, 120, 120))
            surf.blit(laser_text, (WIDTH - 130, 38))
        if self.sticky_timer > 0:
            st = SMALL_FONT.render(f"Sticky: {self.sticky_timer // 60}s", True, (220, 170, 255))
            surf.blit(st, (14, HEIGHT - 24))
        if self.big_paddle_timer > 0:
            bp = SMALL_FONT.render(f"Big Paddle: {self.big_paddle_timer // 60}s", True, (160, 220, 255))
            surf.blit(bp, (170, HEIGHT - 24))
        if self.is_boss_level(self.level) and self.boss_brick and not self.boss_brick.destroyed:
            name = self.boss_personality["name"] if self.boss_personality else "Boss"
            boss_tag = SMALL_FONT.render(f"BOSS: {name}", True, (255, 130, 130))
            surf.blit(boss_tag, (WIDTH - boss_tag.get_width() - 10, 6))

    def draw_world(self, surf):
        """Draw active gameplay scene (background, entities, effects)."""
        # Layered background with loadout variants.
        bg = self.loadout().get("selected_background", "default")
        if bg == "sunset":
            for i in range(0, HEIGHT, 24):
                color = (30 + i // 8, 18 + i // 14, 20 + i // 18)
                pygame.draw.rect(surf, color, (0, i, WIDTH, 24))
        elif bg == "grid":
            surf.fill((12, 16, 28))
            for x in range(0, WIDTH, 40):
                pygame.draw.line(surf, (24, 36, 52), (x, 0), (x, HEIGHT), 1)
            for y in range(0, HEIGHT, 40):
                pygame.draw.line(surf, (24, 36, 52), (0, y), (WIDTH, y), 1)
        else:
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

        ghost = self.ghost_frame_snapshot()
        if ghost:
            ghost_layer = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            gx = int(ghost.get("p", self.paddle.rect.centerx))
            grect = self.paddle.rect.copy()
            grect.centerx = gx
            grect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
            pygame.draw.rect(ghost_layer, (170, 220, 255, 90), grect, border_radius=4)
            bpos = ghost.get("b")
            if isinstance(bpos, list) and len(bpos) == 2:
                pygame.draw.circle(ghost_layer, (170, 220, 255, 100), (int(bpos[0]), int(bpos[1])), 9)
            surf.blit(ghost_layer, (0, 0))

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
            if not self.profile.get("tutorial", {}).get("moved_once", False):
                hint_text = "Tip: Move paddle with arrows/A-D (or controller stick)."
            elif not self.profile.get("tutorial", {}).get("fired_laser_once", False):
                hint_text = "Tip: Press F (or controller B) when laser charges are active."
            else:
                hint_text = "Tip: hit paddle edges to control bounce angle."
            hint = SMALL_FONT.render(hint_text, True, (210, 210, 210))
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
        """Draw main menu with mode/difficulty/status/buttons."""
        for i in range(0, HEIGHT, 20):
            pygame.draw.rect(surf, (12 + i // 30, 14 + i // 30, 22 + i // 18), (0, i, WIDTH, 20))

        title = BIG_FONT.render("Breakout Arcade", True, (240, 240, 240))
        subtitle = FONT.render("A real brick-breaker with progression", True, (200, 220, 255))
        hi = FONT.render(f"High Score: {self.high_score}", True, (255, 220, 120))
        diff = FONT.render(f"Difficulty: {self.difficulty}", True, (150, 230, 255))
        mode = FONT.render(f"Mode: {self.game_mode}", True, (150, 255, 210))
        diff_help = SMALL_FONT.render("Use UP/DOWN to change difficulty", True, (200, 200, 200))
        mode_help = SMALL_FONT.render("Use LEFT/RIGHT to change mode", True, (200, 200, 200))
        bgm_state = "ON" if self.bgm_enabled and self.bgm_loaded else "OFF"
        bgm = SMALL_FONT.render(f"BGM: {bgm_state} (B to toggle)", True, (190, 220, 190))
        stats = self.profile.get("stats", {})
        stats_line = SMALL_FONT.render(
            f"Runs: {stats.get('runs_completed', 0)}  Wins: {stats.get('campaign_wins', 0)}  Bosses: {stats.get('bosses_defeated', 0)}",
            True,
            (190, 190, 220),
        )
        daily_line = SMALL_FONT.render(
            f"Daily Best: {stats.get('daily_best_score', 0)} ({stats.get('daily_best_date', 'n/a')})",
            True,
            (170, 220, 255),
        )
        econ = self.economy()
        econ_line = SMALL_FONT.render(f"XP: {econ.get('xp', 0)}   Currency: {econ.get('currency', 0)}", True, (255, 220, 150))
        if self.bgm_error:
            bgm_note = SMALL_FONT.render(f"BGM note: {self.bgm_error}", True, (220, 160, 160))
        else:
            bgm_note = None

        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 70))
        surf.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 140))
        surf.blit(hi, (WIDTH // 2 - hi.get_width() // 2, 188))
        surf.blit(mode, (WIDTH // 2 - mode.get_width() // 2, 234))
        surf.blit(diff, (WIDTH // 2 - diff.get_width() // 2, 272))
        surf.blit(mode_help, (WIDTH // 2 - mode_help.get_width() // 2, 316))
        surf.blit(diff_help, (WIDTH // 2 - diff_help.get_width() // 2, 340))
        surf.blit(bgm, (WIDTH // 2 - bgm.get_width() // 2, 368))
        surf.blit(econ_line, (WIDTH // 2 - econ_line.get_width() // 2, 396))
        surf.blit(stats_line, (WIDTH // 2 - stats_line.get_width() // 2, 420))
        surf.blit(daily_line, (WIDTH // 2 - daily_line.get_width() // 2, 444))
        if bgm_note:
            surf.blit(bgm_note, (WIDTH // 2 - bgm_note.get_width() // 2, 470))

        button_specs = [
            ("START", "Start Run"),
            ("SHOP", "Shop / Loadout"),
            ("BOARD", "Leaderboard"),
            ("SHARE", "Daily Code"),
            ("SETTINGS", "Settings"),
            ("QUIT", "Quit"),
        ]
        self.menu_buttons = {}
        btn_w, btn_h = 190, 38
        per_row = 3
        total_row_w = btn_w * per_row + 12 * (per_row - 1)
        x0 = WIDTH // 2 - total_row_w // 2
        y0 = HEIGHT - 104
        mouse = getattr(self, "mouse_world_pos", (-10_000, -10_000))
        for i, (key, label) in enumerate(button_specs):
            row = i // per_row
            col = i % per_row
            rect = pygame.Rect(x0 + col * (btn_w + 12), y0 + row * (btn_h + 8), btn_w, btn_h)
            self.menu_buttons[key] = rect
            hover = rect.collidepoint(mouse)
            draw_button(surf, rect, label, SMALL_FONT, hover)
        if self.daily_share_input_message:
            share_note = SMALL_FONT.render(self.daily_share_input_message, True, (170, 230, 255))
            surf.blit(share_note, (WIDTH // 2 - share_note.get_width() // 2, HEIGHT - 140))

    def draw_seed_input(self, surf):
        """Draw screen where player can paste Daily share code."""
        surf.fill((12, 16, 28))
        title = BIG_FONT.render("Daily Share Code", True, (245, 245, 245))
        hint = SMALL_FONT.render("Paste code like DAILY-2026-04-04-5 then press ENTER. ESC to return.", True, (205, 205, 205))
        text = FONT.render(self.daily_share_input or "_", True, (255, 220, 150))
        box = pygame.Rect(120, HEIGHT // 2 - 24, WIDTH - 240, 56)
        pygame.draw.rect(surf, (34, 38, 52), box, border_radius=8)
        pygame.draw.rect(surf, (210, 210, 210), box, 2, border_radius=8)
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 140))
        surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 210))
        surf.blit(text, (box.x + 12, box.y + 12))
        if self.daily_share_input_message:
            msg = SMALL_FONT.render(self.daily_share_input_message, True, (170, 230, 255))
            surf.blit(msg, (WIDTH // 2 - msg.get_width() // 2, box.bottom + 24))

    def draw_game_over(self, surf):
        """Draw game over overlay text."""
        over = BIG_FONT.render("Game Over", True, (255, 100, 100))
        score = FONT.render(f"Score: {self.score}", True, (240, 240, 240))
        again = SMALL_FONT.render("Press ENTER to restart or ESC for menu", True, (220, 220, 220))

        surf.blit(over, (WIDTH // 2 - over.get_width() // 2, HEIGHT // 2 - 60))
        surf.blit(score, (WIDTH // 2 - score.get_width() // 2, HEIGHT // 2 + 6))
        surf.blit(again, (WIDTH // 2 - again.get_width() // 2, HEIGHT // 2 + 40))

    def draw_campaign_win(self, surf):
        """Draw campaign completion overlay."""
        win = BIG_FONT.render("Campaign Complete", True, (140, 255, 170))
        score = FONT.render(f"Final Score: {self.score}", True, (240, 240, 240))
        again = SMALL_FONT.render("Press ENTER to play again or ESC for menu", True, (220, 220, 220))

        surf.blit(win, (WIDTH // 2 - win.get_width() // 2, HEIGHT // 2 - 60))
        surf.blit(score, (WIDTH // 2 - score.get_width() // 2, HEIGHT // 2 + 6))
        surf.blit(again, (WIDTH // 2 - again.get_width() // 2, HEIGHT // 2 + 40))

    def draw_paused(self, surf):
        """Draw pause overlay and pause controls help."""
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 135))
        surf.blit(overlay, (0, 0))
        txt = BIG_FONT.render("Paused", True, (255, 255, 255))
        opts = SMALL_FONT.render("P resume | O settings | R restart run | Q menu", True, (220, 220, 220))
        surf.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT // 2 - 40))
        surf.blit(opts, (WIDTH // 2 - opts.get_width() // 2, HEIGHT // 2 + 20))

    def draw_settings(self, surf):
        """Draw settings menu and +/- click areas."""
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
            ("Ghost Replay", "ON" if self.ghost_replay_enabled else "OFF"),
            ("Controls", self.controls_label()),
            ("Fullscreen", "ON" if self.fullscreen else "OFF"),
            ("Back", "Return"),
        ]

        y = 210
        self.settings_clickables = []
        for idx, (label, value) in enumerate(items):
            selected = idx == self.settings_index
            color = (255, 230, 140) if selected else (230, 230, 230)
            line = FONT.render(f"{label}: {value}", True, color)
            surf.blit(line, (WIDTH // 2 - line.get_width() // 2, y))
            minus_rect = pygame.Rect(WIDTH // 2 - 220, y + 4, 28, 28)
            plus_rect = pygame.Rect(WIDTH // 2 + 192, y + 4, 28, 28)
            pygame.draw.rect(surf, (110, 110, 130), minus_rect, border_radius=5)
            pygame.draw.rect(surf, (110, 110, 130), plus_rect, border_radius=5)
            mtxt = SMALL_FONT.render("-", True, (245, 245, 245))
            ptxt = SMALL_FONT.render("+", True, (245, 245, 245))
            surf.blit(mtxt, (minus_rect.centerx - mtxt.get_width() // 2, minus_rect.centery - mtxt.get_height() // 2))
            surf.blit(ptxt, (plus_rect.centerx - ptxt.get_width() // 2, plus_rect.centery - ptxt.get_height() // 2))
            self.settings_clickables.append((idx, minus_rect, plus_rect))
            y += 46

    def draw_shop(self, surf):
        """Draw shop/loadout cards for cosmetics."""
        surf.fill((16, 18, 28))
        title = BIG_FONT.render("Shop & Loadout", True, (245, 245, 245))
        econ = self.economy()
        balance = FONT.render(f"Currency: {econ.get('currency', 0)}  XP: {econ.get('xp', 0)}", True, (255, 220, 140))
        hint = SMALL_FONT.render("Click to buy/equip. ESC to return to menu.", True, (210, 210, 210))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 60))
        surf.blit(balance, (WIDTH // 2 - balance.get_width() // 2, 132))
        surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 168))

        self.shop_cards = []
        entries = [
            ("paddle", "neon"), ("paddle", "sunset"),
            ("trail", "ember"), ("trail", "frost"),
            ("bg", "grid"), ("bg", "sunset"),
        ]
        load = self.loadout()
        y = 220
        for idx, (cat, item) in enumerate(entries):
            key = f"{cat}:{item}"
            price = SHOP_PRICES[key]
            owned_key = "owned_backgrounds" if cat == "bg" else "owned_paddle_skins" if cat == "paddle" else "owned_trails"
            selected_key = "selected_background" if cat == "bg" else "selected_paddle_skin" if cat == "paddle" else "selected_trail"
            owned = item in load.get(owned_key, [])
            selected = load.get(selected_key) == item
            status = "Selected" if selected else "Owned" if owned else f"Buy {price}"
            rect = pygame.Rect(140 + (idx % 2) * 320, y + (idx // 2) * 84, 280, 70)
            self.shop_cards.append((rect, cat, item, owned, selected))
            color = (80, 150, 100) if selected else (70, 70, 90) if owned else (110, 90, 60)
            pygame.draw.rect(surf, color, rect, border_radius=8)
            pygame.draw.rect(surf, (220, 220, 220), rect, 2, border_radius=8)
            label = FONT.render(f"{cat.upper()} : {item}", True, (245, 245, 245))
            stext = SMALL_FONT.render(status, True, (250, 220, 170))
            surf.blit(label, (rect.x + 12, rect.y + 10))
            surf.blit(stext, (rect.x + 12, rect.y + 40))

    def draw_leaderboard(self, surf):
        """Draw top-10 local leaderboard lists by mode."""
        surf.fill((14, 16, 26))
        title = BIG_FONT.render("Leaderboard", True, (245, 245, 245))
        hint = SMALL_FONT.render("Top 10 per mode. ESC to return.", True, (210, 210, 210))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 56))
        surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 122))

        boards = self.profile.get("leaderboards", {})
        y0 = 170
        for i, mode in enumerate(GAME_MODES):
            x = 80 + i * 410
            mode_title = FONT.render(mode, True, (170, 230, 255))
            surf.blit(mode_title, (x, y0))
            entries = boards.get(mode, [])
            for rank in range(10):
                if rank < len(entries):
                    e = entries[rank]
                    seed = f" [{e.get('seed')}]" if e.get("seed") else ""
                    text = SMALL_FONT.render(
                        f"{rank+1:02d}. {e.get('score',0)} pts L{e.get('level',1)} {e.get('date','')}{seed}",
                        True,
                        (220, 220, 220),
                    )
                else:
                    text = SMALL_FONT.render(f"{rank+1:02d}. ---", True, (110, 110, 130))
                surf.blit(text, (x, y0 + 34 + rank * 26))

    def draw_run_summary(self, surf):
        """Draw post-run stat summary and action buttons."""
        surf.fill((20, 14, 24))
        title = BIG_FONT.render("Run Summary", True, (255, 245, 255))
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 70))
        data = self.last_run_summary or {}
        lines = [
            f"Mode: {data.get('mode', self.game_mode)}",
            f"Score: {data.get('score', 0)}",
            f"Level/Wave reached: {data.get('level', 1)}",
            f"XP gained: {data.get('xp_gain', 0)}",
            f"Currency gained: {data.get('currency_gain', 0)}",
            f"Combo peak: {data.get('combo_peak', 0)}",
            f"Accuracy: {data.get('accuracy', 0)}%",
            f"Projectiles dodged: {data.get('projectiles_dodged', 0)}",
        ]
        if data.get("daily_share"):
            lines.append(f"Daily share code: {data.get('daily_share')}")
        if data.get("ghost_saved"):
            lines.append("Ghost replay updated for this Daily seed.")

        y = 170
        for line in lines:
            t = FONT.render(line, True, (230, 230, 230))
            surf.blit(t, (WIDTH // 2 - t.get_width() // 2, y))
            y += 40

        self.summary_buttons = {
            "MENU": pygame.Rect(WIDTH // 2 - 220, HEIGHT - 82, 200, 46),
            "RETRY": pygame.Rect(WIDTH // 2 + 20, HEIGHT - 82, 200, 46),
        }
        mouse = getattr(self, "mouse_world_pos", (-10_000, -10_000))
        for key, rect in self.summary_buttons.items():
            hover = rect.collidepoint(mouse)
            draw_button(surf, rect, "Back to Menu" if key == "MENU" else "Run Again", SMALL_FONT, hover)

    def draw_transition(self, surf):
        """Draw fade overlay used during scene transitions."""
        if self.transition_alpha <= 0:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(self.transition_alpha)
        surf.blit(overlay, (0, 0))

    def update_transition(self):
        """Advance transition alpha each frame."""
        if self.transition_target != self.game_state:
            self.transition_alpha = min(255, self.transition_alpha + 28)
            if self.transition_alpha >= 250:
                self.transition_target = self.game_state
        else:
            self.transition_alpha = max(0, self.transition_alpha - 20)

    def handle_events(self):
        """Process keyboard/mouse/window events and route by current scene."""
        global SCREEN
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                SCREEN = pygame.display.set_mode((max(640, event.w), max(480, event.h)), pygame.RESIZABLE)
                pygame.display.set_caption("Breakout: Arcade Edition")
                continue

            if event.type == pygame.QUIT:
                self.finalize_run()
                self.save_high_score()
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and self.game_state != "SETTINGS":
                if event.key == pygame.K_m:
                    self.volume = min(1.0, self.volume + 0.1)
                    self.apply_volume()
                    self.save_profile()
                    continue
                if event.key == pygame.K_n:
                    self.volume = max(0.0, self.volume - 0.1)
                    self.apply_volume()
                    self.save_profile()
                    continue
                if event.key == pygame.K_b:
                    self.toggle_bgm()
                    continue

            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP) and "pos" in event.dict:
                world_pos = self.window_to_world(event.dict.get("pos"))
                if world_pos is None:
                    continue
                payload = dict(event.dict)
                payload["pos"] = world_pos
                event = pygame.event.Event(event.type, **payload)

            scene = self.scenes.get(self.game_state)
            if scene:
                scene.handle_event(self, event)

    def tick(self):
        """Run one full game frame: input -> update -> render."""
        self.handle_events()
        keys = pygame.key.get_pressed()
        scene = self.scenes.get(self.game_state)
        if scene:
            scene.update(self, keys)

        self.render()

    def render(self):
        """Render current scene to off-screen world then scale to window."""
        self.mouse_world_pos = self.window_to_world(pygame.mouse.get_pos()) or (-10_000, -10_000)
        world = pygame.Surface((WIDTH, HEIGHT))
        scene = self.scenes.get(self.game_state)
        if scene:
            scene.draw(self, world)
        else:
            self.draw_world(world)
            self.draw_hud(world)

        self.update_transition()
        self.draw_transition(world)
        if self.impact_flash_alpha > 0:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(self.impact_flash_alpha)))
            world.blit(flash, (0, 0))

        shake_x = 0
        shake_y = 0
        if self.shake_frames > 0 and self.shake_total_frames > 0:
            progress = 1.0 - (self.shake_frames / self.shake_total_frames)
            envelope = max(0.0, 1.0 - progress) ** 2
            amp = self.shake_strength * envelope
            self.shake_phase += 0.65
            shake_x = math.sin(self.shake_phase * 1.7) * amp
            shake_y = math.cos(self.shake_phase * 2.2) * amp * 0.7

        SCREEN.fill((0, 0, 0))
        screen_w, screen_h = SCREEN.get_size()
        scale = min(screen_w / WIDTH, screen_h / HEIGHT)
        target_w = max(1, int(WIDTH * scale))
        target_h = max(1, int(HEIGHT * scale))

        if target_w == WIDTH and target_h == HEIGHT:
            frame = world
        else:
            frame = pygame.transform.smoothscale(world, (target_w, target_h))

        offset_x = (screen_w - target_w) // 2
        offset_y = (screen_h - target_h) // 2
        SCREEN.blit(frame, (offset_x + int(shake_x * scale), offset_y + int(shake_y * scale)))
        pygame.display.flip()

    def window_to_world(self, pos):
        screen_w, screen_h = SCREEN.get_size()
        scale = min(screen_w / WIDTH, screen_h / HEIGHT)
        target_w = max(1, int(WIDTH * scale))
        target_h = max(1, int(HEIGHT * scale))
        offset_x = (screen_w - target_w) // 2
        offset_y = (screen_h - target_h) // 2
        x, y = pos
        if x < offset_x or x >= offset_x + target_w or y < offset_y or y >= offset_y + target_h:
            return None
        wx = int((x - offset_x) / scale)
        wy = int((y - offset_y) / scale)
        wx = max(0, min(WIDTH - 1, wx))
        wy = max(0, min(HEIGHT - 1, wy))
        return wx, wy


def main():
    game = Game()
    while True:
        game.tick()
        CLOCK.tick(60)


if __name__ == "__main__":
    main()
