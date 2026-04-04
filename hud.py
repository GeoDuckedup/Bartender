from __future__ import annotations

import pygame

from renderer import (
    HUD_BACKGROUND_COLOR,
    HUD_BORDER_COLOR,
    HUD_HEIGHT,
    HUD_TEXT_COLOR,
    LOGICAL_WIDTH,
)


class HUDRenderer:
    def __init__(self) -> None:
        self.main_font = pygame.font.SysFont("couriernew", 16, bold=True)
        self.center_font = pygame.font.SysFont("couriernew", 12, bold=True)

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
            (0, HUD_HEIGHT - 1),
            (LOGICAL_WIDTH, HUD_HEIGHT - 1),
            2,
        )

        self._blit_text(
            surface,
            f"LIVES {lives:02d}",
            self.main_font,
            x=12,
            y=HUD_HEIGHT // 2,
            anchor="midleft",
        )
        self._blit_text(
            surface,
            f"LEVEL {current_level:02d}",
            self.center_font,
            x=LOGICAL_WIDTH // 2,
            y=12,
            anchor="center",
        )
        self._blit_text(
            surface,
            f"SERVED {served:02d}/{target:02d}",
            self.center_font,
            x=LOGICAL_WIDTH // 2,
            y=29,
            anchor="center",
        )
        self._blit_text(
            surface,
            f"SCORE {score:06d}",
            self.main_font,
            x=LOGICAL_WIDTH - 12,
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
