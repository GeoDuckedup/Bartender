from __future__ import annotations

from enum import Enum, auto

import pygame

from glass import FlyingGlass, TapGlass
from renderer import (
    BAR_COUNT,
    BARTENDER_APRON_COLOR,
    BARTENDER_BODY_COLOR,
    BARTENDER_HEAD_COLOR,
    BARTENDER_WALK_MAX_X,
    BARTENDER_WALK_MIN_X,
    LANE_CENTERS,
    TAP_HOME_X,
    TAP_GLASS_X,
)


class PourState(Enum):
    IDLE = auto()
    POURING = auto()


class Bartender:
    WALK_SPEED = 150.0
    BODY_WIDTH = 20
    BODY_HEIGHT = 40
    HEAD_WIDTH = 18
    HEAD_HEIGHT = 14
    APRON_WIDTH = 10
    APRON_HEIGHT = 28
    FEET_OFFSET = 16

    def __init__(self) -> None:
        self.bar_index = 0
        self.x = float(TAP_HOME_X)
        self.tap_glass = TapGlass()
        self.flying_glasses: list[FlyingGlass] = []
        self.missed_flying_glass = False
        self.pour_state = PourState.IDLE

    @property
    def lane_center_y(self) -> int:
        return LANE_CENTERS[self.bar_index]

    @property
    def is_at_tap(self) -> bool:
        return abs(self.x - TAP_HOME_X) < 0.5

    @property
    def is_pouring(self) -> bool:
        return self.pour_state is PourState.POURING

    @property
    def body_rect(self) -> pygame.Rect:
        feet_y = self.lane_center_y + self.FEET_OFFSET
        body_left = round(self.x)
        return pygame.Rect(
            body_left,
            feet_y - self.BODY_HEIGHT,
            self.BODY_WIDTH,
            self.BODY_HEIGHT,
        )

    @property
    def catch_rect(self) -> pygame.Rect:
        body_rect = self.body_rect
        return body_rect.inflate(10, 6)

    def move_up(self) -> None:
        self.bar_index = (self.bar_index - 1) % BAR_COUNT
        self.x = float(TAP_HOME_X)
        self.stop_walking()
        self._clear_glass_if_away()

    def move_down(self) -> None:
        self.bar_index = (self.bar_index + 1) % BAR_COUNT
        self.x = float(TAP_HOME_X)
        self.stop_walking()
        self._clear_glass_if_away()

    def walk_left(self, dt: float) -> None:
        self.x = max(BARTENDER_WALK_MIN_X, self.x - (self.WALK_SPEED * dt))
        self._clear_glass_if_away()

    def walk_right(self, dt: float) -> None:
        self.x = min(BARTENDER_WALK_MAX_X, self.x + (self.WALK_SPEED * dt))
        self._clear_glass_if_away()

    def stop_walking(self) -> None:
        return

    def start_pour(self) -> None:
        if self.pour_state is not PourState.IDLE:
            return

        self.x = float(TAP_HOME_X)
        self.stop_walking()
        self.tap_glass.reset()
        self.pour_state = PourState.POURING

    def release_pour(self) -> None:
        if self.pour_state is not PourState.POURING:
            return

        if self.tap_glass.is_full:
            self.flying_glasses.append(
                FlyingGlass(
                    x=float(TAP_GLASS_X),
                    bar_index=self.bar_index,
                )
            )

        self.pour_state = PourState.IDLE
        self.tap_glass.reset()

    def cancel_pour(self) -> None:
        if self.pour_state is not PourState.POURING:
            return

        self.pour_state = PourState.IDLE
        self.tap_glass.reset()

    def update_pour(self, dt: float) -> None:
        if self.pour_state is PourState.POURING:
            self.tap_glass.update_fill(dt)

        active_glasses: list[FlyingGlass] = []
        for flying_glass in self.flying_glasses:
            flying_glass.update(dt)
            if flying_glass.is_offscreen:
                self.missed_flying_glass = True
                continue
            active_glasses.append(flying_glass)
        self.flying_glasses = active_glasses

    def consume_missed_flying_glass(self) -> bool:
        missed_flying_glass = self.missed_flying_glass
        self.missed_flying_glass = False
        return missed_flying_glass

    def draw_flying_glasses(self, surface: pygame.Surface) -> None:
        for flying_glass in self.flying_glasses:
            flying_glass.draw(surface)

    def draw_tap_glass(self, surface: pygame.Surface) -> None:
        if self.pour_state is PourState.POURING and self.is_at_tap:
            self.tap_glass.draw(surface, self.bar_index)

    def _clear_glass_if_away(self) -> None:
        if self.pour_state is PourState.POURING and not self.is_at_tap:
            self.cancel_pour()

    def draw(self, surface: pygame.Surface) -> None:
        body_rect = self.body_rect
        head_rect = pygame.Rect(
            body_rect.centerx - (self.HEAD_WIDTH // 2),
            body_rect.top - self.HEAD_HEIGHT,
            self.HEAD_WIDTH,
            self.HEAD_HEIGHT,
        )
        apron_rect = pygame.Rect(
            body_rect.centerx - (self.APRON_WIDTH // 2),
            body_rect.centery - (self.APRON_HEIGHT // 2) + 2,
            self.APRON_WIDTH,
            self.APRON_HEIGHT,
        )

        pygame.draw.rect(surface, BARTENDER_BODY_COLOR, body_rect)
        pygame.draw.rect(surface, BARTENDER_APRON_COLOR, apron_rect)
        pygame.draw.rect(surface, BARTENDER_HEAD_COLOR, head_rect)
