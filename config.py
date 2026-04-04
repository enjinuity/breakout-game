WIDTH, HEIGHT = 900, 640
HUD_HEIGHT = 64

HIGH_SCORE_FILE = "high_score.json"
PROFILE_FILE = "player_profile.json"
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
DAILY_BOSS_INTERVAL = 4
GAME_MODES = ["CAMPAIGN", "DAILY"]
GHOST_RECORD_STEP = 2
GHOST_MAX_FRAMES = 18000

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
SHOP_PRICES = {
    "paddle:neon": 150,
    "paddle:sunset": 250,
    "trail:ember": 120,
    "trail:frost": 180,
    "bg:grid": 200,
    "bg:sunset": 260,
}
