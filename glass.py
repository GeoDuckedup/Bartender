from __future__ import annotations

from dataclasses import dataclass

import pygame

from renderer import (
    LOGICAL_WIDTH,
    GLASS_FILL_COLOR,
    GLASS_FOAM_COLOR,
    GLASS_OUTLINE_COLOR,
    LANE_CENTERS,
    lane_surface_glass_y,
    TAP_GLASS_X,
)


# Tap / mug tuning:
# Shared mug dimensions and outline/fill proportions live here.
GLASS_WIDTH = 14
GLASS_HEIGHT = 20
GLASS_OUTLINE_THICKNESS = 2
GLASS_INNER_PADDING = 2
GLASS_FOAM_HEIGHT = 4
FULL_FOAM_THRESHOLD = 0.99

# Pour / travel tuning:
# These are gameplay-facing speeds for fill, outgoing mugs, and returning empties.
TAP_FILL_DURATION = 0.3
FLYING_GLASS_SPEED = 210.0
RETURNING_GLASS_SPEED = 67.2

# Collision-only vertical alignment:
# Drawing uses renderer surface anchors, but collisions still use this
# logical offset so gameplay can stay stable while visuals evolve.
COLLISION_GLASS_BASELINE_OFFSET = 10


class TapGlass:
    FILL_RATE = 1.0 / TAP_FILL_DURATION
    WIDTH = GLASS_WIDTH
    HEIGHT = GLASS_HEIGHT

    def __init__(self) -> None:
        self.fill_ratio = 0.0

    @property
    def is_full(self) -> bool:
        return self.fill_ratio >= 1.0

    def update_fill(self, dt: float) -> None:
        self.fill_ratio = min(1.0, self.fill_ratio + (self.FILL_RATE * dt))

    def reset(self) -> None:
        self.fill_ratio = 0.0

    def draw(
        self,
        surface: pygame.Surface,
        bar_index: int,
        *,
        left: float | None = None,
    ) -> None:
        glass_rect = pygame.Rect(
            TAP_GLASS_X if left is None else round(left),
            lane_surface_glass_y(bar_index, self.HEIGHT),
            self.WIDTH,
            self.HEIGHT,
        )
        pygame.draw.rect(surface, GLASS_OUTLINE_COLOR, glass_rect, GLASS_OUTLINE_THICKNESS)

        if self.fill_ratio > 0.0:
            inner_width = self.WIDTH - (GLASS_INNER_PADDING * 2)
            inner_height = self.HEIGHT - (GLASS_INNER_PADDING * 2)
            fill_height = max(1, round(inner_height * self.fill_ratio))
            fill_rect = pygame.Rect(
                glass_rect.left + GLASS_INNER_PADDING,
                glass_rect.bottom - GLASS_INNER_PADDING - fill_height,
                inner_width,
                fill_height,
            )
            pygame.draw.rect(surface, GLASS_FILL_COLOR, fill_rect)

        if self.is_full:
            foam_rect = pygame.Rect(
                glass_rect.left + 1,
                glass_rect.top + 1,
                self.WIDTH - GLASS_OUTLINE_THICKNESS,
                GLASS_FOAM_HEIGHT,
            )
            pygame.draw.rect(surface, GLASS_FOAM_COLOR, foam_rect)


@dataclass
class FlyingGlass:
    x: float
    bar_index: int
    fill_ratio: float = 1.0
    speed: float = FLYING_GLASS_SPEED

    WIDTH = GLASS_WIDTH
    HEIGHT = GLASS_HEIGHT

    def update(self, dt: float) -> None:
        self.x -= self.speed * dt

    @property
    def rect(self) -> pygame.Rect:
        lane_center_y = LANE_CENTERS[self.bar_index]
        return pygame.Rect(
            round(self.x),
            lane_center_y - self.HEIGHT + COLLISION_GLASS_BASELINE_OFFSET,
            self.WIDTH,
            self.HEIGHT,
        )

    @property
    def is_offscreen(self) -> bool:
        return self.x + self.WIDTH < 0

    def draw(self, surface: pygame.Surface) -> None:
        glass_rect = pygame.Rect(
            round(self.x),
            lane_surface_glass_y(self.bar_index, self.HEIGHT),
            self.WIDTH,
            self.HEIGHT,
        )
        pygame.draw.rect(surface, GLASS_OUTLINE_COLOR, glass_rect, GLASS_OUTLINE_THICKNESS)

        clamped_fill_ratio = max(0.0, min(1.0, self.fill_ratio))
        if clamped_fill_ratio > 0.0:
            inner_width = self.WIDTH - (GLASS_INNER_PADDING * 2)
            inner_height = self.HEIGHT - (GLASS_INNER_PADDING * 2)
            fill_height = max(1, round(inner_height * clamped_fill_ratio))
            fill_rect = pygame.Rect(
                glass_rect.left + GLASS_INNER_PADDING,
                glass_rect.bottom - GLASS_INNER_PADDING - fill_height,
                inner_width,
                fill_height,
            )
            pygame.draw.rect(surface, GLASS_FILL_COLOR, fill_rect)

        if clamped_fill_ratio >= FULL_FOAM_THRESHOLD:
            foam_rect = pygame.Rect(
                glass_rect.left + 1,
                glass_rect.top + 1,
                self.WIDTH - GLASS_OUTLINE_THICKNESS,
                GLASS_FOAM_HEIGHT,
            )
            pygame.draw.rect(surface, GLASS_FOAM_COLOR, foam_rect)


@dataclass
class ReturningGlass:
    x: float
    bar_index: int
    speed: float = RETURNING_GLASS_SPEED

    WIDTH = GLASS_WIDTH
    HEIGHT = GLASS_HEIGHT

    def update(self, dt: float) -> None:
        self.x += self.speed * dt

    @property
    def rect(self) -> pygame.Rect:
        lane_center_y = LANE_CENTERS[self.bar_index]
        return pygame.Rect(
            round(self.x),
            lane_center_y - self.HEIGHT + COLLISION_GLASS_BASELINE_OFFSET,
            self.WIDTH,
            self.HEIGHT,
        )

    @property
    def is_offscreen(self) -> bool:
        return self.x > LOGICAL_WIDTH

    def draw(self, surface: pygame.Surface) -> None:
        draw_rect = pygame.Rect(
            round(self.x),
            lane_surface_glass_y(self.bar_index, self.HEIGHT),
            self.WIDTH,
            self.HEIGHT,
        )
        pygame.draw.rect(surface, GLASS_OUTLINE_COLOR, draw_rect, GLASS_OUTLINE_THICKNESS)
