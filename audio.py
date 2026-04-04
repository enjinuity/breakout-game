"""
Audio helper functions.

Non-technical summary:
- Keeps music and sound logic out of `main.py`.
- Tries to fail safely: if audio breaks on a machine, gameplay still runs.
"""

import os

import pygame


def init_audio():
    """Start the audio system once at boot."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return True
    except pygame.error:
        # Audio is optional for playability, so we do not crash the game.
        return False


def load_sound(path):
    """Load one sound effect file and return None if unsupported."""
    try:
        return pygame.mixer.Sound(path)
    except pygame.error:
        return None


def load_game_sounds():
    """Load all one-shot sound effects used in gameplay."""
    return {
        "brick": load_sound("assets/sounds/brick_hit.wav"),
        "paddle": load_sound("assets/sounds/paddle_hit.wav"),
        "wall": load_sound("assets/sounds/wall_hit.wav"),
        "lose_life": load_sound("assets/sounds/lose_life.wav"),
        "win": load_sound("assets/sounds/win.wav"),
        "game_over": load_sound("assets/sounds/game_over.wav"),
    }


def apply_audio_volume(sounds, master_volume, sfx_volume, music_volume, bgm_enabled, bgm_channel=None):
    """Apply current volume sliders to SFX and music channels."""
    sfx_mix = master_volume * sfx_volume
    for sound in sounds.values():
        if sound:
            sound.set_volume(sfx_mix)

    bgm_mix = master_volume * music_volume if bgm_enabled else 0.0
    if pygame.mixer.get_init():
        pygame.mixer.music.set_volume(bgm_mix)
    if bgm_channel:
        bgm_channel.set_volume(bgm_mix)


def start_music_loop(music_path):
    """Start looping BGM, with fallback path for systems that reject streamed music."""
    if not pygame.mixer.get_init():
        return False, None, "Audio mixer unavailable"

    if not os.path.exists(music_path):
        return False, None, "bgm.wav not found"

    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(music_path)
        pygame.mixer.music.play(-1)
        return True, None, ""
    except pygame.error:
        # Fallback for environments/codecs where music stream load fails.
        bgm_sound = load_sound(music_path)
        if bgm_sound:
            channel = bgm_sound.play(-1)
            if channel is not None:
                return True, channel, ""
            return False, None, "BGM channel unavailable"
        return False, None, "BGM format unsupported"
