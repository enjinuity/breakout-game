import importlib
import json
import os
import tempfile
import unittest


class ProfileModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        cls.main = importlib.import_module("main")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prev_cwd = os.getcwd()
        os.chdir(self.tmp.name)

    def tearDown(self):
        os.chdir(self.prev_cwd)
        self.tmp.cleanup()

    def test_profile_save_creates_expected_sections(self):
        game = self.main.Game()
        game.save_profile()
        self.assertTrue(os.path.exists("player_profile.json"))
        with open("player_profile.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("economy", data)
        self.assertIn("loadout", data)
        self.assertIn("leaderboards", data)
        self.assertIn("ghosts", data)
        self.assertIn("tutorial", data)

    def test_mode_cycle(self):
        game = self.main.Game()
        original = game.game_mode
        game.update_mode(1)
        self.assertNotEqual(original, game.game_mode)
        game.update_mode(-1)
        self.assertEqual(original, game.game_mode)


if __name__ == "__main__":
    unittest.main()
