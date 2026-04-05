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
FROSTED_GLASS_BACK_COLOR = pygame.Color("#9FA7B0")
FROSTED_GLASS_TOP_FROTH_COLOR = pygame.Color("#C7CDD3")
FROSTED_GLASS_BOTTOM_FROTH_COLOR = pygame.Color("#EEE9DD")
GLASS_TOP_FROTH_HEIGHT = 2
GLASS_BOTTOM_FROTH_HEIGHT = 4
GREEN_BEER_FILL_COLOR = pygame.Color("#4FAE3C")
WINE_BEER_FILL_COLOR = pygame.Color("#9E2B4A")

# Pour / travel tuning:
# These are gameplay-facing speeds for fill, outgoing mugs, and returning empties.
TAP_FILL_DURATION = 0.20
FLYING_GLASS_SPEED = 190.0
RETURNING_GLASS_SPEED = 40.0

# Collision-only vertical alignment:
# Drawing uses renderer surface anchors, but collisions still use this
# logical offset so gameplay can stay stable while visuals evolve.
COLLISION_GLASS_BASELINE_OFFSET = 10


def draw_glass_with_fill(
    surface: pygame.Surface,
    glass_rect: pygame.Rect,
    *,
    fill_ratio: float,
    show_top_foam: bool,
    fill_color: pygame.Color | None = None,
) -> None:
    pygame.draw.rect(surface, GLASS_OUTLINE_COLOR, glass_rect, GLASS_OUTLINE_THICKNESS)

    inner_rect = pygame.Rect(
        glass_rect.left + GLASS_INNER_PADDING,
        glass_rect.top + GLASS_INNER_PADDING,
        glass_rect.width - (GLASS_INNER_PADDING * 2),
        glass_rect.height - (GLASS_INNER_PADDING * 2),
    )
    if inner_rect.width <= 0 or inner_rect.height <= 0:
        return

    # Frosted backing so the mug reads as translucent glass behind the beer.
    pygame.draw.rect(surface, FROSTED_GLASS_BACK_COLOR, inner_rect)

    top_froth_rect = pygame.Rect(
        inner_rect.left,
        inner_rect.top,
        inner_rect.width,
        min(GLASS_TOP_FROTH_HEIGHT, inner_rect.height),
    )
    pygame.draw.rect(surface, FROSTED_GLASS_TOP_FROTH_COLOR, top_froth_rect)

    bottom_froth_rect = pygame.Rect(
        inner_rect.left,
        inner_rect.bottom - min(GLASS_BOTTOM_FROTH_HEIGHT, inner_rect.height),
        inner_rect.width,
        min(GLASS_BOTTOM_FROTH_HEIGHT, inner_rect.height),
    )
    pygame.draw.rect(surface, FROSTED_GLASS_BOTTOM_FROTH_COLOR, bottom_froth_rect)

    clamped_fill_ratio = max(0.0, min(1.0, fill_ratio))
    if clamped_fill_ratio > 0.0:
        fill_height = max(1, round(inner_rect.height * clamped_fill_ratio))
        fill_rect = pygame.Rect(
            inner_rect.left,
            inner_rect.bottom - fill_height,
            inner_rect.width,
            fill_height,
        )
        pygame.draw.rect(surface, GLASS_FILL_COLOR if fill_color is None else fill_color, fill_rect)

    if show_top_foam and clamped_fill_ratio >= FULL_FOAM_THRESHOLD:
        foam_rect = pygame.Rect(
            glass_rect.left + 1,
            glass_rect.top + 1,
            glass_rect.width - GLASS_OUTLINE_THICKNESS,
            GLASS_FOAM_HEIGHT,
        )
        pygame.draw.rect(surface, GLASS_FOAM_COLOR, foam_rect)


class TapGlass:
    FILL_RATE = 1.0 / TAP_FILL_DURATION
    WIDTH = GLASS_WIDTH
    HEIGHT = GLASS_HEIGHT

    def __init__(self) -> None:
        self.fill_ratio = 0.0
        self.fill_rate = self.FILL_RATE

    @property
    def is_full(self) -> bool:
        return self.fill_ratio >= 1.0

    def update_fill(self, dt: float) -> None:
        self.fill_ratio = min(1.0, self.fill_ratio + (self.fill_rate * dt))

    def reset(self) -> None:
        self.fill_ratio = 0.0

    def draw(
        self,
        surface: pygame.Surface,
        bar_index: int,
        *,
        left: float | None = None,
        fill_color: pygame.Color | None = None,
    ) -> None:
        glass_rect = pygame.Rect(
            TAP_GLASS_X if left is None else round(left),
            lane_surface_glass_y(bar_index, self.HEIGHT),
            self.WIDTH,
            self.HEIGHT,
        )
        draw_glass_with_fill(
            surface,
            glass_rect,
            fill_ratio=self.fill_ratio,
            show_top_foam=True,
            fill_color=fill_color,
        )


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

    def draw(self, surface: pygame.Surface, *, fill_color: pygame.Color | None = None) -> None:
        glass_rect = pygame.Rect(
            round(self.x),
            lane_surface_glass_y(self.bar_index, self.HEIGHT),
            self.WIDTH,
            self.HEIGHT,
        )
        draw_glass_with_fill(
            surface,
            glass_rect,
            fill_ratio=self.fill_ratio,
            show_top_foam=True,
            fill_color=fill_color,
        )


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
        draw_glass_with_fill(
            surface,
            draw_rect,
            fill_ratio=0.0,
            show_top_foam=False,
        )
