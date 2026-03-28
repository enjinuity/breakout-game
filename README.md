# Breakout Game — CSC222 Mini Project

A classic Breakout-style game implemented in Python using Pygame.  
Created as part of the CSC222 Game Development mini-project (2024 Edition).

## 🎮 Features
- Improved ball collision response (side-aware brick bounce + paddle angle control)
- Multiple level layouts with progression and increasing difficulty
- Difficulty presets (Easy / Normal / Hard) with different lives/speed/drop-rate balance
- Brick variants: normal, strong (2 hits), unbreakable, explosive (AOE break)
- Powerups: extra life, bigger paddle, multiball, laser, slow-motion, sticky paddle, shield
- Hazard drops: smaller paddle and faster ball
- Combo scoring multiplier + high-score persistence (`high_score.json`)
- High score now autosaves immediately when beaten
- Menu + pause + game-over states, volume controls, alternative movement keys
- Dedicated Settings screen (master/SFX/music levels, controls preset, fullscreen, BGM)
- Campaign mode with a proper completion state
- Boss waves every 3 levels (moving boss + hazard drops + boss HP bar)
- Round start countdown + contextual control hints
- Menu now shows BGM status with toggle and playback fallback
- Visual polish: particles, screen shake, level intro flash, transition fade
- Sound effects with optional looping music support (`assets/sounds/bgm.wav` if provided)

## 🚀 How to Run
1. Install pygame:
   ```bash
   pip install pygame
2. Run the game:
   ```bash
   python3 main.py

Requires Python 3.x and Pygame installed

## 🎯 Controls
- `Left / Right` to move paddle
- `A / D` to switch to alternate movement keys
- `Space` to launch attached ball
- `F` to fire laser (when laser charges are active)
- `P` to pause/unpause gameplay
- `S` open settings from menu
- `O` open settings while paused
- `R` while paused to restart run
- `Q` while paused to return to menu
- `M / N` volume up/down
- `B` toggle background music
- `Up / Down` in menu to change difficulty
- `Enter` start/restart
- `Esc` return to menu (or quit from menu)

## 🗂️ Folder Structure

breakout-game/
├── main.py
├── paddle.py
├── ball.py
├── brick.py
├── powerup.py
├── assets/
│   └── sounds/
│       ├── brick_hit.wav
│       ├── paddle_hit.wav
│       ├── wall_hit.wav
│       ├── lose_life.wav
│       ├── win.wav
│       └── game_over.wav


Benison Ebeshi.

2nd-year Computer Science Student.

FULafia

GitHub: @Enjinuity
