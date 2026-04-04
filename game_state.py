"""
Persistence and progression helpers.

Non-technical summary:
- Handles save files (profile + high score).
- Computes rewards and leaderboard updates.
- Encodes/decodes Daily share codes and ghost storage.
"""

import json
import os
from datetime import date


def default_profile():
    """Return a complete default profile structure for new players."""
    return {
        "high_score": 0,
        "settings": {
            "master_volume": 0.7,
            "sfx_volume": 0.9,
            "music_volume": 0.6,
            "bgm_enabled": True,
            "ghost_replay": True,
            "controls": "ARROWS",
            "fullscreen": False,
        },
        "economy": {
            "xp": 0,
            "currency": 0,
        },
        "loadout": {
            "selected_paddle_skin": "classic",
            "selected_trail": "none",
            "selected_background": "default",
            "owned_paddle_skins": ["classic"],
            "owned_trails": ["none"],
            "owned_backgrounds": ["default"],
        },
        "stats": {
            "runs_started": 0,
            "runs_completed": 0,
            "campaign_wins": 0,
            "daily_runs": 0,
            "daily_best_score": 0,
            "daily_best_date": "",
            "bosses_defeated": 0,
            "bricks_broken": 0,
            "best_level_reached": 1,
            "lifetime_score": 0,
        },
        "leaderboards": {
            "CAMPAIGN": [],
            "DAILY": [],
        },
        "ghosts": {},
        "tutorial": {
            "moved_once": False,
            "fired_laser_once": False,
        },
    }


def load_high_score(path):
    """Read high score file and safely return 0 on any file issue."""
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return int(data.get("high_score", 0))
    except (ValueError, OSError, json.JSONDecodeError):
        return 0


def save_high_score(path, value):
    """Write high score to disk; ignore write failures to avoid hard crashes."""
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump({"high_score": int(value)}, file)
    except OSError:
        pass


def load_profile(path, legacy_high_score):
    """
    Read profile file and merge it with defaults.

    Why merge:
    - Older save files may miss newly added fields.
    - Defaults keep the game forward-compatible.
    """
    profile = default_profile()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
            if isinstance(data, dict):
                profile.update({k: v for k, v in data.items() if k in profile and not isinstance(v, dict)})
                if isinstance(data.get("settings"), dict):
                    profile["settings"].update(data["settings"])
                if isinstance(data.get("stats"), dict):
                    profile["stats"].update(data["stats"])
                if isinstance(data.get("economy"), dict):
                    profile["economy"].update(data["economy"])
                if isinstance(data.get("loadout"), dict):
                    profile["loadout"].update(data["loadout"])
                if isinstance(data.get("leaderboards"), dict):
                    profile["leaderboards"].update(data["leaderboards"])
                if isinstance(data.get("ghosts"), dict):
                    profile["ghosts"].update(data["ghosts"])
                if isinstance(data.get("tutorial"), dict):
                    profile["tutorial"].update(data["tutorial"])
        except (ValueError, OSError, json.JSONDecodeError):
            pass

    profile["high_score"] = max(int(profile.get("high_score", 0)), int(legacy_high_score))
    return profile


def save_profile(path, profile):
    """Persist full profile JSON."""
    try:
        with open(path, "w", encoding="utf-8") as file:
            json.dump(profile, file, indent=2)
    except OSError:
        pass


def add_run_rewards(profile, score, level):
    """Grant XP and currency after a run."""
    econ = profile.setdefault("economy", default_profile()["economy"])
    xp_gain = int(score // 18 + level * 12)
    currency_gain = int(score // 45 + level * 6)
    econ["xp"] = int(econ.get("xp", 0)) + xp_gain
    econ["currency"] = int(econ.get("currency", 0)) + currency_gain
    return xp_gain, currency_gain


def update_leaderboard(profile, game_mode, score, level, daily_label):
    """Insert run result into top-10 list for the chosen mode."""
    boards = profile.setdefault("leaderboards", {"CAMPAIGN": [], "DAILY": []})
    board = boards.setdefault(game_mode, [])
    board.append(
        {
            "score": int(score),
            "level": int(level),
            "date": date.today().isoformat(),
            "seed": daily_label if game_mode == "DAILY" else "",
        }
    )
    board.sort(key=lambda item: item["score"], reverse=True)
    del board[10:]


def build_daily_share_code(daily_label, level):
    """Create a copy/paste code players can share for Daily seeds."""
    return f"DAILY-{daily_label}-{int(level)}"


def parse_daily_share_code(code):
    """Parse and validate shared Daily code text."""
    if not isinstance(code, str):
        return None
    normalized = code.strip().upper()
    if not normalized.startswith("DAILY-"):
        return None
    rest = normalized[6:]
    parts = rest.rsplit("-", 1)
    if len(parts) != 2:
        return None
    label, level_str = parts
    if not label:
        return None
    try:
        level = int(level_str)
    except ValueError:
        return None
    if level <= 0:
        return None
    return label, level


def daily_label_to_seed(label):
    """Turn day label text into deterministic numeric seed."""
    return sum(ord(ch) for ch in str(label))


def get_daily_ghost(profile, daily_label):
    """Fetch stored ghost for a given Daily label if valid."""
    ghosts = profile.setdefault("ghosts", {})
    ghost = ghosts.get(daily_label)
    if not isinstance(ghost, dict):
        return None
    trace = ghost.get("trace")
    if not isinstance(trace, list) or not trace:
        return None
    return ghost


def update_daily_ghost(profile, daily_label, score, level, trace, step, max_saved=30):
    """
    Save best ghost for a Daily label.

    Rule:
    - Replace only when new score is better-or-equal.
    """
    ghosts = profile.setdefault("ghosts", {})
    existing = ghosts.get(daily_label)
    if isinstance(existing, dict) and int(existing.get("score", 0)) > int(score):
        return False

    ghosts[daily_label] = {
        "score": int(score),
        "level": int(level),
        "step": max(1, int(step)),
        "trace": trace,
    }

    if len(ghosts) > max_saved:
        for key in sorted(ghosts.keys()):
            if key != daily_label and len(ghosts) > max_saved:
                del ghosts[key]
    return True
