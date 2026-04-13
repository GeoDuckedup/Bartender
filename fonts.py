from __future__ import annotations

from pathlib import Path

import pygame


REPO_ROOT = Path(__file__).resolve().parent
BUNDLED_MONO_FONT_PATH = REPO_ROOT / "assets" / "fonts" / "SourceCodePro-Bold.ttf"


def load_ui_font(size: int) -> pygame.font.Font:
    if BUNDLED_MONO_FONT_PATH.exists():
        return pygame.font.Font(str(BUNDLED_MONO_FONT_PATH), size)
    return pygame.font.Font(None, size)
