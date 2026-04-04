from __future__ import annotations

from dataclasses import dataclass

import pygame

from renderer import LANE_CENTERS, TIP_COLOR, TIP_SHADOW_COLOR, lane_surface_tip_y


# Tip rendering / collision tuning:
# Drawing and collision offsets are split so the coin can sit nicely on the bar
# without forcing gameplay to change.
TIP_WIDTH = 10
TIP_HEIGHT = 10
TIP_COLLISION_Y_OFFSET = 6
TIP_SHADOW_OFFSET = (1, 1)


@dataclass
class Tip:
    x: float
    bar_index: int

    WIDTH = TIP_WIDTH
    HEIGHT = TIP_HEIGHT

    @property
    def rect(self) -> pygame.Rect:
        lane_center_y = LANE_CENTERS[self.bar_index]
        return pygame.Rect(
            round(self.x),
            lane_center_y + TIP_COLLISION_Y_OFFSET,
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
        shadow_rect = rect.move(*TIP_SHADOW_OFFSET)
        pygame.draw.ellipse(surface, TIP_SHADOW_COLOR, shadow_rect)
        pygame.draw.ellipse(surface, TIP_COLOR, rect)
