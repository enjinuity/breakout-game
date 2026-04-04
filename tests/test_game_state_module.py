"""Unit tests for standalone save/progression helpers in game_state.py."""

import os
import tempfile
import unittest

from game_state import (
    add_run_rewards,
    build_daily_share_code,
    daily_label_to_seed,
    get_daily_ghost,
    load_high_score,
    load_profile,
    parse_daily_share_code,
    save_high_score,
    save_profile,
    update_daily_ghost,
    update_leaderboard,
)


class GameStateModuleTests(unittest.TestCase):
    """Verifies profile I/O, rewards math, leaderboard behavior, and ghost storage."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.profile_path = os.path.join(self.tmp.name, "player_profile.json")
        self.high_path = os.path.join(self.tmp.name, "high_score.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_profile_round_trip(self):
        profile = load_profile(self.profile_path, 0)
        profile["economy"]["currency"] = 99
        save_profile(self.profile_path, profile)
        loaded = load_profile(self.profile_path, 0)
        self.assertEqual(loaded["economy"]["currency"], 99)
        self.assertIn("ghosts", loaded)

    def test_high_score_round_trip(self):
        save_high_score(self.high_path, 1234)
        self.assertEqual(load_high_score(self.high_path), 1234)

    def test_rewards_and_leaderboard(self):
        profile = load_profile(self.profile_path, 0)
        xp_gain, currency_gain = add_run_rewards(profile, score=900, level=4)
        self.assertGreater(xp_gain, 0)
        self.assertGreater(currency_gain, 0)

        for i in range(15):
            update_leaderboard(profile, "CAMPAIGN", score=100 + i, level=1 + i % 3, daily_label="")
        self.assertEqual(len(profile["leaderboards"]["CAMPAIGN"]), 10)
        self.assertGreaterEqual(profile["leaderboards"]["CAMPAIGN"][0]["score"], profile["leaderboards"]["CAMPAIGN"][-1]["score"])

    def test_daily_share_parse(self):
        code = build_daily_share_code("2026-04-04", 7)
        parsed = parse_daily_share_code(code)
        self.assertEqual(parsed, ("2026-04-04", 7))
        self.assertIsNone(parse_daily_share_code("INVALID-CODE"))

    def test_daily_seed(self):
        self.assertEqual(daily_label_to_seed("ABC"), ord("A") + ord("B") + ord("C"))

    def test_daily_ghost_save_and_fetch(self):
        profile = load_profile(self.profile_path, 0)
        trace = [{"p": 450, "b": [300.0, 240.0]}, {"p": 460, "b": None}]
        saved = update_daily_ghost(profile, "2026-04-04", 1200, 6, trace, 2)
        self.assertTrue(saved)
        ghost = get_daily_ghost(profile, "2026-04-04")
        self.assertIsNotNone(ghost)
        self.assertEqual(ghost["score"], 1200)

        worse = update_daily_ghost(profile, "2026-04-04", 1100, 5, trace, 2)
        self.assertFalse(worse)


if __name__ == "__main__":
    unittest.main()
