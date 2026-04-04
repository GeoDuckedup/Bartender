from __future__ import annotations

import pygame

from renderer import (
    HUD_BACKGROUND_COLOR,
    HUD_BORDER_COLOR,
    HUD_HEIGHT,
    HUD_TEXT_COLOR,
    LOGICAL_WIDTH,
)


# HUD layout / typography tuning:
# Keep all HUD spacing and type sizes here so UI tweaks stay out of draw logic.
HUD_MAIN_FONT_SIZE = 16
HUD_CENTER_FONT_SIZE = 12
HUD_SIDE_PADDING = 12
HUD_LEVEL_Y = 12
HUD_SERVED_Y = 29
HUD_BORDER_Y = HUD_HEIGHT - 1
HUD_BORDER_THICKNESS = 2


class HUDRenderer:
    def __init__(self) -> None:
        self.main_font = pygame.font.SysFont("couriernew", HUD_MAIN_FONT_SIZE, bold=True)
        self.center_font = pygame.font.SysFont("couriernew", HUD_CENTER_FONT_SIZE, bold=True)

    def draw(
        self,
        surface: pygame.Surface,
        *,
        lives: int,
        current_level: int,
        served: int = 0,
        target: int = 8,
        score: int = 0,
    ) -> None:
        hud_rect = pygame.Rect(0, 0, LOGICAL_WIDTH, HUD_HEIGHT)
        pygame.draw.rect(surface, HUD_BACKGROUND_COLOR, hud_rect)
        pygame.draw.line(
            surface,
            HUD_BORDER_COLOR,
            (0, HUD_BORDER_Y),
            (LOGICAL_WIDTH, HUD_BORDER_Y),
            HUD_BORDER_THICKNESS,
        )

        self._blit_text(
            surface,
            f"LIVES {lives:02d}",
            self.main_font,
            x=HUD_SIDE_PADDING,
            y=HUD_HEIGHT // 2,
            anchor="midleft",
        )
        self._blit_text(
            surface,
            f"LEVEL {current_level:02d}",
            self.center_font,
            x=LOGICAL_WIDTH // 2,
            y=HUD_LEVEL_Y,
            anchor="center",
        )
        self._blit_text(
            surface,
            f"SERVED {served:02d}/{target:02d}",
            self.center_font,
            x=LOGICAL_WIDTH // 2,
            y=HUD_SERVED_Y,
            anchor="center",
        )
        self._blit_text(
            surface,
            f"SCORE {score:06d}",
            self.main_font,
            x=LOGICAL_WIDTH - HUD_SIDE_PADDING,
            y=HUD_HEIGHT // 2,
            anchor="midright",
        )

    def _blit_text(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        *,
        x: int,
        y: int,
        anchor: str,
    ) -> None:
        text_surface = font.render(text, True, HUD_TEXT_COLOR)
        text_rect = text_surface.get_rect()
        setattr(text_rect, anchor, (x, y))

        surface.blit(text_surface, text_rect)
