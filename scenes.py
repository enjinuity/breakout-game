import sys

import pygame

from config import GAME_MODES, HEIGHT, WIDTH
from game_state import parse_daily_share_code


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

        if event.key == pygame.K_p:
            game.paused = not game.paused
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
