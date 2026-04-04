from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from random import Random

import pygame

from glass import ReturningGlass
from renderer import (
    GLASS_FILL_COLOR,
    GLASS_FOAM_COLOR,
    GLASS_OUTLINE_COLOR,
    LANE_CENTERS,
    RIGHT_WALL_LEFT,
    lane_surface_glass_y,
)


class PatronState(Enum):
    WALKING = auto()
    RECEIVING = auto()
    DRINKING = auto()
    OFFSCREEN_DRINKING = auto()


@dataclass(frozen=True)
class PatronArchetype:
    name: str
    body_color: pygame.Color
    hat_color: pygame.Color
    walk_speed_multiplier: float
    drink_duration_multiplier: float
    tip_chance: float


STEADY_PATRON = PatronArchetype(
    name="steady",
    body_color=pygame.Color("#D4A843"),
    hat_color=pygame.Color("#8B6914"),
    walk_speed_multiplier=1.0,
    drink_duration_multiplier=1.0,
    tip_chance=0.35,
)

RUSHER_PATRON = PatronArchetype(
    name="rusher",
    body_color=pygame.Color("#C65A32"),
    hat_color=pygame.Color("#6B2E19"),
    walk_speed_multiplier=1.18,
    drink_duration_multiplier=0.9,
    tip_chance=0.18,
)

LINGERER_PATRON = PatronArchetype(
    name="lingerer",
    body_color=pygame.Color("#5E8E5F"),
    hat_color=pygame.Color("#2F5A34"),
    walk_speed_multiplier=0.86,
    drink_duration_multiplier=1.25,
    tip_chance=0.28,
)

BIG_TIPPER_PATRON = PatronArchetype(
    name="big_tipper",
    body_color=pygame.Color("#577BB8"),
    hat_color=pygame.Color("#2E4974"),
    walk_speed_multiplier=0.94,
    drink_duration_multiplier=1.1,
    tip_chance=0.62,
)

PATRON_ARCHETYPES = (
    STEADY_PATRON,
    RUSHER_PATRON,
    LINGERER_PATRON,
    BIG_TIPPER_PATRON,
)


class Patron:
    DRINK_DURATION = 1.1
    RECEIVE_SPEED = 220.0
    DEFAULT_WALK_SPEED = 42.0
    MIN_WALK_SPEED = 34.0
    MAX_WALK_SPEED = 52.0
    BODY_WIDTH = 18
    BODY_HEIGHT = 36
    QUEUE_GAP = 18
    GLASS_WIDTH = 14
    GLASS_HEIGHT = 20
    HAT_WIDTH = 20
    HAT_HEIGHT = 8
    FEET_OFFSET = 16
    LEFT_EDGE_X = 0.0
    REENTRY_X = -BODY_WIDTH
    OFFSCREEN_DRINK_X = -(BODY_WIDTH + GLASS_WIDTH + 8)
    RETURN_GLASS_SPAWN_X = REENTRY_X + BODY_WIDTH
    DRINK_DELAY_VARIATION_MIN = 0.85
    DRINK_DELAY_VARIATION_MAX = 1.15
    SHORT_PUSHBACK_DISTANCE = 40.0
    SHORT_MIN_VISIBLE_X = 88.0

    def __init__(
        self,
        bar_index: int = 0,
        start_x: float = 0.0,
        walk_speed: float | None = None,
        drink_duration: float | None = None,
        archetype: PatronArchetype = STEADY_PATRON,
        shove_weights: tuple[float, float, float] = (0.50, 0.35, 0.15),
    ) -> None:
        self.bar_index = bar_index
        self.x = start_x
        self.walk_speed = self.DEFAULT_WALK_SPEED if walk_speed is None else walk_speed
        self.drink_duration = (
            self.DRINK_DURATION if drink_duration is None else drink_duration
        )
        self.archetype = archetype
        self.state = PatronState.WALKING
        self.drink_timer = 0.0
        self.active_drink_duration = self.drink_duration
        self.served_fill_ratio = 1.0
        self.hit_tap_wall = False
        self.pending_returning_glass: ReturningGlass | None = None
        self.long_shove_weight = shove_weights[0]
        self.offscreen_shove_weight = shove_weights[1]
        self.short_shove_weight = shove_weights[2]
        self.receive_target_x = self.LEFT_EDGE_X
        self.reenter_after_drink = False

    @property
    def lane_center_y(self) -> int:
        return LANE_CENTERS[self.bar_index]

    @property
    def max_x(self) -> int:
        return RIGHT_WALL_LEFT - self.BODY_WIDTH

    def update(self, dt: float, max_walk_x: float | None = None) -> None:
        if self.state is PatronState.WALKING:
            walk_limit = self.max_x if max_walk_x is None else min(self.max_x, max_walk_x)
            self.x = min(walk_limit, self.x + (self.walk_speed * dt))
        elif self.state is PatronState.RECEIVING:
            self.x = max(self.receive_target_x, self.x - (self.RECEIVE_SPEED * dt))
            if self.x == self.receive_target_x:
                if self.reenter_after_drink:
                    self.state = PatronState.OFFSCREEN_DRINKING
                else:
                    self.state = PatronState.DRINKING
                self.active_drink_duration = self.drink_duration * _patron_behavior_rng.uniform(
                    self.DRINK_DELAY_VARIATION_MIN,
                    self.DRINK_DELAY_VARIATION_MAX,
                )
                self.drink_timer = self.active_drink_duration
        elif self.state is PatronState.DRINKING:
            self.drink_timer = max(0.0, self.drink_timer - dt)
            if self.drink_timer == 0.0:
                return_glass_x = float(self.body_rect.right)
                self.pending_returning_glass = ReturningGlass(
                    x=return_glass_x,
                    bar_index=self.bar_index,
                )
                self.state = PatronState.WALKING
        elif self.state is PatronState.OFFSCREEN_DRINKING:
            self.drink_timer = max(0.0, self.drink_timer - dt)
            if self.drink_timer == 0.0:
                return_glass_x = float(self.RETURN_GLASS_SPAWN_X)
                self.pending_returning_glass = ReturningGlass(
                    x=return_glass_x,
                    bar_index=self.bar_index,
                )
                self.x = self.REENTRY_X
                self.state = PatronState.WALKING

        if self.body_rect.right >= RIGHT_WALL_LEFT:
            self.hit_tap_wall = True

    @property
    def body_rect(self) -> pygame.Rect:
        feet_y = self.lane_center_y + self.FEET_OFFSET
        return pygame.Rect(
            round(self.x),
            feet_y - self.BODY_HEIGHT,
            self.BODY_WIDTH,
            self.BODY_HEIGHT,
        )

    @property
    def can_receive_beer(self) -> bool:
        return self.state is PatronState.WALKING

    @property
    def held_glass_fill_ratio(self) -> float:
        if self.state is PatronState.RECEIVING:
            return self.served_fill_ratio
        if self.state is not PatronState.DRINKING:
            return 0.0
        if self.active_drink_duration <= 0.0:
            return 0.0
        return self.served_fill_ratio * (self.drink_timer / self.active_drink_duration)

    def receive_beer(self, fill_ratio: float = 1.0) -> None:
        self.state = PatronState.RECEIVING
        self.drink_timer = 0.0
        self.active_drink_duration = self.drink_duration
        self.served_fill_ratio = max(0.0, min(1.0, fill_ratio))
        self.receive_target_x, self.reenter_after_drink = self._choose_receive_target()

    def consume_hit_tap_wall(self) -> bool:
        hit_wall = self.hit_tap_wall
        self.hit_tap_wall = False
        return hit_wall

    def consume_pending_returning_glass(self) -> ReturningGlass | None:
        pending_returning_glass = self.pending_returning_glass
        self.pending_returning_glass = None
        return pending_returning_glass

    @property
    def tip_chance(self) -> float:
        return self.archetype.tip_chance

    @property
    def blocks_spawn_entry(self) -> bool:
        return self.state is not PatronState.OFFSCREEN_DRINKING

    def draw(self, surface: pygame.Surface) -> None:
        body_rect = self.body_rect
        hat_rect = pygame.Rect(
            body_rect.centerx - (self.HAT_WIDTH // 2),
            body_rect.top - self.HAT_HEIGHT,
            self.HAT_WIDTH,
            self.HAT_HEIGHT,
        )

        pygame.draw.rect(surface, self.archetype.body_color, body_rect)
        pygame.draw.rect(surface, self.archetype.hat_color, hat_rect)

    def draw_held_glass(self, surface: pygame.Surface) -> None:
        if self.state not in (PatronState.RECEIVING, PatronState.DRINKING):
            return
        self._draw_held_glass(surface, self.body_rect)

    def _draw_held_glass(
        self,
        surface: pygame.Surface,
        body_rect: pygame.Rect,
    ) -> None:
        glass_rect = pygame.Rect(
            body_rect.right,
            lane_surface_glass_y(self.bar_index, self.GLASS_HEIGHT),
            self.GLASS_WIDTH,
            self.GLASS_HEIGHT,
        )
        pygame.draw.rect(surface, GLASS_OUTLINE_COLOR, glass_rect, 2)

        fill_ratio = max(0.0, min(1.0, self.held_glass_fill_ratio))
        if fill_ratio > 0.0:
            inner_width = self.GLASS_WIDTH - 4
            inner_height = self.GLASS_HEIGHT - 4
            fill_height = max(1, round(inner_height * fill_ratio))
            fill_rect = pygame.Rect(
                glass_rect.left + 2,
                glass_rect.bottom - 2 - fill_height,
                inner_width,
                fill_height,
            )
            pygame.draw.rect(surface, GLASS_FILL_COLOR, fill_rect)

        if fill_ratio >= 0.99:
            foam_rect = pygame.Rect(
                glass_rect.left + 1,
                glass_rect.top + 1,
                self.GLASS_WIDTH - 2,
                4,
            )
            pygame.draw.rect(surface, GLASS_FOAM_COLOR, foam_rect)

    def _choose_receive_target(self) -> tuple[float, bool]:
        roll = _patron_behavior_rng.random()
        long_cutoff = self.long_shove_weight
        offscreen_cutoff = long_cutoff + self.offscreen_shove_weight
        if roll < long_cutoff:
            return min(self.LEFT_EDGE_X, self.x), False
        if roll < offscreen_cutoff:
            return self.OFFSCREEN_DRINK_X, True

        short_target_x = max(self.SHORT_MIN_VISIBLE_X, self.x - self.SHORT_PUSHBACK_DISTANCE)
        if short_target_x >= self.x:
            short_target_x = max(self.LEFT_EDGE_X, self.x - 18.0)
        return min(self.x, short_target_x), False


def build_walk_speed_rng() -> Random:
    return Random(1983)


_patron_behavior_rng = Random(1985)
