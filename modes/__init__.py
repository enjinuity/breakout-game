from config import GAME_MODES


BOSS_PERSONALITIES = [
    {
        "name": "Sentinel",
        "speed": 1.8,
        "cooldown": 220,
        "patterns": ["spread", "rain", "pressure"],
    },
    {
        "name": "Trickster",
        "speed": 2.3,
        "cooldown": 180,
        "patterns": ["sniper", "rain", "spread", "pressure"],
    },
    {
        "name": "Berserker",
        "speed": 2.9,
        "cooldown": 148,
        "patterns": ["spread", "mine", "rain", "sniper", "pressure"],
    },
]


def clamp_mode(mode):
    if mode in GAME_MODES:
        return mode
    return GAME_MODES[0]


def boss_personality_for_level(level, game_mode):
    tier = min(len(BOSS_PERSONALITIES) - 1, max(0, (int(level) - 1) // 4))
    personality = dict(BOSS_PERSONALITIES[tier])
    if game_mode == "DAILY":
        # Daily gets a touch more aggression.
        personality["speed"] += 0.3
        personality["cooldown"] = max(90, personality["cooldown"] - 18)
    return personality


def boss_attack_name(pattern):
    names = {
        "spread": "spread",
        "rain": "rain",
        "pressure": "pressure",
        "sniper": "sniper shot",
        "mine": "hazard mine",
    }
    return names.get(pattern, pattern)


def normal_brick_modifier_rolls(level, game_mode):
    # Returns ascending thresholds for regen, teleport, shielded, timed_bomb.
    # Late waves lean harder into modifiers.
    level_boost = min(0.06, max(0.0, (int(level) - 1) * 0.005))
    daily_boost = 0.02 if game_mode == "DAILY" else 0.0
    base = 0.06 + level_boost + daily_boost
    return (
        base,
        base + 0.05,
        base + 0.09,
        base + 0.12,
    )
