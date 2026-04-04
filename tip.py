from __future__ import annotations

from dataclasses import dataclass

import pygame

from renderer import LANE_CENTERS, TIP_COLOR, TIP_SHADOW_COLOR, lane_surface_tip_y


@dataclass
class Tip:
    x: float
    bar_index: int

    WIDTH = 10
    HEIGHT = 10

    @property
    def rect(self) -> pygame.Rect:
        lane_center_y = LANE_CENTERS[self.bar_index]
        return pygame.Rect(
            round(self.x),
            lane_center_y + 6,
            self.WIDTH,
            self.HEIGHT,
        )

    def draw(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(
            round(self.x),
            lane_surface_tip_y(self.bar_index, self.HEIGHT),
            self.WIDTH,
            self.HEIGHT,
        )
        shadow_rect = rect.move(1, 1)
        pygame.draw.ellipse(surface, TIP_SHADOW_COLOR, shadow_rect)
        pygame.draw.ellipse(surface, TIP_COLOR, rect)
