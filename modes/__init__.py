"""
Rules for game modes and boss behavior presets.

Non-technical summary:
- Defines boss "personalities" (movement speed + attack rhythm).
- Provides helper math to scale modifier frequency as waves increase.
"""

from config import (
    GAME_MODES,
    POWERUP_BAD_TYPES,
    POWERUP_BAD_WEIGHT,
    POWERUP_BOSS_DROP_CHANCE,
    POWERUP_BOSS_POOL,
    POWERUP_GOOD_TYPES,
    POWERUP_GOOD_WEIGHT,
    POWERUP_LEVEL_PENALTY_STEP,
    POWERUP_MIN_CHANCE,
)


# Predefined boss personalities used by tier/wave.
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
    """Return a safe mode value if input mode is unknown."""
    if mode in GAME_MODES:
        return mode
    return GAME_MODES[0]


def boss_personality_for_level(level, game_mode):
    """Pick boss personality tier based on wave and mode."""
    tier = min(len(BOSS_PERSONALITIES) - 1, max(0, (int(level) - 1) // 4))
    personality = dict(BOSS_PERSONALITIES[tier])
    if game_mode == "DAILY":
        # Daily gets a touch more aggression.
        personality["speed"] += 0.3
        personality["cooldown"] = max(90, personality["cooldown"] - 18)
    return personality


def boss_attack_name(pattern):
    """Human-readable labels for boss pattern codes."""
    names = {
        "spread": "spread",
        "rain": "rain",
        "pressure": "pressure",
        "sniper": "sniper shot",
        "mine": "hazard mine",
    }
    return names.get(pattern, pattern)


def normal_brick_modifier_rolls(level, game_mode):
    """Return probability thresholds for special normal-brick modifiers."""
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


def pick_normal_brick_variant(rng, level, game_mode):
    regen_roll, teleport_roll, shield_roll, bomb_roll = normal_brick_modifier_rolls(level, game_mode)
    roll = rng.random()
    if roll < regen_roll:
        return "regen"
    if roll < teleport_roll:
        return "teleport"
    if roll < shield_roll:
        return "shielded"
    if roll < bomb_roll:
        return "timed_bomb"
    return "normal"


def roll_powerup_drop(rng, level, base_chance, boss_level):
    if boss_level:
        if rng.random() > POWERUP_BOSS_DROP_CHANCE:
            return None
        return rng.choice(POWERUP_BOSS_POOL)

    chance = max(POWERUP_MIN_CHANCE, float(base_chance) - (max(1, int(level)) - 1) * POWERUP_LEVEL_PENALTY_STEP)
    if rng.random() > chance:
        return None

    pool = list(POWERUP_GOOD_TYPES) * int(POWERUP_GOOD_WEIGHT) + list(POWERUP_BAD_TYPES) * int(POWERUP_BAD_WEIGHT)
    return rng.choice(pool)
