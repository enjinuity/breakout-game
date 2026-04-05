"""
Central place for game tuning values.

Non-technical summary:
- If you want to change how the game feels, this is usually the first file to edit.
- Numbers here control screen size, difficulty balance, unlocks, and progression pacing.
"""

# Base window size for the designed game canvas.
WIDTH, HEIGHT = 900, 640
# Top strip used for score/lives/level info.
HUD_HEIGHT = 64

# Save files used for persistent progress.
HIGH_SCORE_FILE = "high_score.json"
PROFILE_FILE = "player_profile.json"
# Background music file path.
MUSIC_PATH = "assets/sounds/bgm.wav"

# Hand-authored campaign brick layouts.
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

# Difficulty presets that adjust risk/reward.
DIFFICULTY_CONFIG = {
    "EASY": {"lives": 5, "speed": 5.4, "drop_chance": 0.30, "speed_step": 0.45, "score_mult": 0.9},
    "NORMAL": {"lives": 3, "speed": 6.0, "drop_chance": 0.24, "speed_step": 0.55, "score_mult": 1.0},
    "HARD": {"lives": 2, "speed": 6.6, "drop_chance": 0.20, "speed_step": 0.65, "score_mult": 1.2},
}

CAMPAIGN_LEVELS = 9
BOSS_LEVEL_INTERVAL = 3
DAILY_BOSS_INTERVAL = 4
GAME_MODES = ["CAMPAIGN", "DAILY"]
# Record one ghost sample every N frames.
GHOST_RECORD_STEP = 2
# Upper safety limit so ghost data does not grow forever.
GHOST_MAX_FRAMES = 18000

# Cosmetic unlock catalogs.
PADDLE_SKINS = {
    "classic": (255, 255, 255),
    "neon": (80, 255, 210),
    "sunset": (255, 170, 90),
}
BALL_TRAILS = {
    "none": None,
    "ember": (255, 120, 80),
    "frost": (140, 220, 255),
}
BACKGROUNDS = ["default", "grid", "sunset"]
# Shop item prices (currency earned from runs).
SHOP_PRICES = {
    "paddle:neon": 150,
    "paddle:sunset": 250,
    "trail:ember": 120,
    "trail:frost": 180,
    "bg:grid": 200,
    "bg:sunset": 260,
}

DAILY_LAYOUT_ROWS = 6
DAILY_LAYOUT_COLS = 10
DAILY_LAYOUT_THRESHOLDS = (
    (0.10, "."),
    (0.63, "N"),
    (0.83, "S"),
    (0.92, "E"),
    (1.00, "U"),
)

POWERUP_BOSS_DROP_CHANCE = 0.12
POWERUP_BOSS_POOL = ("laser", "slow", "shield", "small", "fast")
POWERUP_LEVEL_PENALTY_STEP = 0.03
POWERUP_MIN_CHANCE = 0.12
POWERUP_GOOD_TYPES = ("multi", "big", "life", "laser", "slow", "sticky", "shield")
POWERUP_BAD_TYPES = ("small", "fast")
POWERUP_GOOD_WEIGHT = 8
POWERUP_BAD_WEIGHT = 3
