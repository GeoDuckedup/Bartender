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
    GLASS_FILL_COLOR,
    GLASS_FOAM_COLOR,
    GLASS_OUTLINE_COLOR,
    LANE_CENTERS,
    lane_surface_glass_y,
    TAP_HOME_X,
    TAP_GLASS_X,
)


class PourState(Enum):
    IDLE = auto()
    POURING = auto()


class Bartender:
    WALK_SPEED = 150.0
    SERVE_VISUAL_DURATION = 0.2
    SERVE_LEFT_HAND_LINGER_DURATION = 0.6
    SERVE_HOLD_RIGHT_FRACTION = 0.22
    SERVE_MOTION_FRACTION = 0.62
    BODY_WIDTH = 20
    BODY_HEIGHT = 40
    HEAD_WIDTH = 18
    HEAD_HEIGHT = 14
    APRON_WIDTH = 10
    APRON_HEIGHT = 28
    FEET_OFFSET = 16
    ARM_THICKNESS = 8
    HAND_SIZE = 10
    RIGHT_GLASS_OFFSET_X = BODY_WIDTH - 2
    LEFT_GLASS_OFFSET_X = -3
    ARM_START_OFFSET_X = BODY_WIDTH - 4
    ARM_Y_OFFSET = 18

    def __init__(self) -> None:
        self.bar_index = 0
        self.x = float(TAP_HOME_X)
        self.tap_glass = TapGlass()
        self.flying_glasses: list[FlyingGlass] = []
        self.missed_flying_glass = False
        self.pour_state = PourState.IDLE
        self.serve_visual_timer = 0.0
        self.serve_visual_bar_index = 0
        self.serve_visual_start_x = 0.0
        self.serve_visual_end_x = 0.0
        self.serve_visual_shoulder_x = 0.0
        self.serve_visual_arm_y = 0
        self.serve_visual_glass: FlyingGlass | None = None
        self.serve_linger_timer = 0.0

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
    def is_serving_visually(self) -> bool:
        return self.serve_visual_timer > 0.0

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
        self.serve_visual_timer = 0.0
        self.serve_visual_glass = None
        self.serve_linger_timer = 0.0
        self.tap_glass.reset()
        self.pour_state = PourState.POURING

    def release_pour(self) -> None:
        if self.pour_state is not PourState.POURING:
            return

        if self.tap_glass.is_full:
            body_rect = self.body_rect
            launched_glass = FlyingGlass(
                x=float(TAP_GLASS_X),
                bar_index=self.bar_index,
            )
            self.flying_glasses.append(launched_glass)
            self.serve_visual_timer = self.SERVE_VISUAL_DURATION
            self.serve_visual_bar_index = self.bar_index
            self.serve_visual_start_x = float(self._right_glass_left(body_rect))
            self.serve_visual_end_x = float(self._left_glass_left(body_rect))
            self.serve_visual_shoulder_x = float(body_rect.left + self.ARM_START_OFFSET_X)
            self.serve_visual_arm_y = body_rect.top + self.ARM_Y_OFFSET
            self.serve_visual_glass = launched_glass
            self.serve_linger_timer = self.SERVE_LEFT_HAND_LINGER_DURATION

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
        if self.serve_visual_timer > 0.0:
            self.serve_visual_timer = max(0.0, self.serve_visual_timer - dt)
            if self.serve_visual_timer == 0.0:
                self.serve_visual_glass = None
        if self.serve_linger_timer > 0.0:
            self.serve_linger_timer = max(0.0, self.serve_linger_timer - dt)

        active_glasses: list[FlyingGlass] = []
        for flying_glass in self.flying_glasses:
            flying_glass.update(dt)
            if flying_glass.is_offscreen:
                self.missed_flying_glass = True
                if flying_glass is self.serve_visual_glass:
                    self.serve_visual_glass = None
                continue
            active_glasses.append(flying_glass)
        self.flying_glasses = active_glasses

    def consume_missed_flying_glass(self) -> bool:
        missed_flying_glass = self.missed_flying_glass
        self.missed_flying_glass = False
        return missed_flying_glass

    def draw_flying_glasses(self, surface: pygame.Surface) -> None:
        for flying_glass in self.flying_glasses:
            if (
                self.is_serving_visually
                and flying_glass is self.serve_visual_glass
                and self._serve_elapsed_fraction() < self.SERVE_MOTION_FRACTION
            ):
                continue
            flying_glass.draw(surface)

    def draw_tap_glass(self, surface: pygame.Surface) -> None:
        if self.pour_state is PourState.POURING and self.is_at_tap:
            body_rect = self.body_rect
            glass_left = self._right_glass_left(body_rect)
            self.tap_glass.draw(surface, self.bar_index, left=glass_left)
            self._draw_arm(
                surface,
                shoulder_x=body_rect.left + self.ARM_START_OFFSET_X,
                hand_x=glass_left + 5,
                arm_y=body_rect.top + self.ARM_Y_OFFSET,
            )

    def draw_serve_visual(self, surface: pygame.Surface) -> None:
        if self.is_serving_visually and self.serve_visual_glass is not None:
            elapsed_fraction = self._serve_elapsed_fraction()
            motion_progress = self._serve_motion_progress(elapsed_fraction)
            glass_left = round(
                self.serve_visual_start_x
                + ((self.serve_visual_end_x - self.serve_visual_start_x) * motion_progress)
            )
            if elapsed_fraction < self.SERVE_MOTION_FRACTION:
                glass_top = lane_surface_glass_y(self.serve_visual_bar_index, TapGlass.HEIGHT)
                glass_rect = pygame.Rect(glass_left, glass_top, TapGlass.WIDTH, TapGlass.HEIGHT)
                pygame.draw.rect(surface, GLASS_OUTLINE_COLOR, glass_rect, 2)
                fill_rect = pygame.Rect(
                    glass_rect.left + 2,
                    glass_rect.top + 2,
                    TapGlass.WIDTH - 4,
                    TapGlass.HEIGHT - 4,
                )
                pygame.draw.rect(surface, GLASS_FILL_COLOR, fill_rect)
                foam_rect = pygame.Rect(
                    glass_rect.left + 1,
                    glass_rect.top + 1,
                    TapGlass.WIDTH - 2,
                    4,
                )
                pygame.draw.rect(surface, GLASS_FOAM_COLOR, foam_rect)
            self._draw_arm(
                surface,
                shoulder_x=round(
                    self.serve_visual_shoulder_x
                    + ((glass_left - self.serve_visual_shoulder_x) * min(1.0, motion_progress * 1.1))
                ),
                hand_x=glass_left + 5,
                arm_y=self.serve_visual_arm_y,
            )
            return

        if self.serve_linger_timer > 0.0:
            self._draw_arm(
                surface,
                shoulder_x=self._left_glass_left(self.body_rect) - 6,
                hand_x=self._left_glass_left(self.body_rect) + 5,
                arm_y=self.body_rect.top + self.ARM_Y_OFFSET,
            )

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

    def _right_glass_left(self, body_rect: pygame.Rect) -> int:
        return body_rect.left + self.RIGHT_GLASS_OFFSET_X

    def _left_glass_left(self, body_rect: pygame.Rect) -> int:
        return body_rect.left + self.LEFT_GLASS_OFFSET_X

    def _draw_arm(
        self,
        surface: pygame.Surface,
        *,
        shoulder_x: int,
        hand_x: int,
        arm_y: int,
    ) -> None:
        left = min(shoulder_x, hand_x)
        width = max(self.ARM_THICKNESS, abs(hand_x - shoulder_x))
        arm_rect = pygame.Rect(left, arm_y, width, self.ARM_THICKNESS)
        hand_rect = pygame.Rect(
            hand_x - (self.HAND_SIZE // 2),
            arm_y - ((self.HAND_SIZE - self.ARM_THICKNESS) // 2),
            self.HAND_SIZE,
            self.HAND_SIZE,
        )
        pygame.draw.rect(surface, BARTENDER_HEAD_COLOR, arm_rect)
        pygame.draw.rect(surface, BARTENDER_HEAD_COLOR, hand_rect)

    def _serve_elapsed_fraction(self) -> float:
        if self.SERVE_VISUAL_DURATION <= 0.0:
            return 1.0
        return 1.0 - (self.serve_visual_timer / self.SERVE_VISUAL_DURATION)

    def _serve_motion_progress(self, elapsed_fraction: float) -> float:
        if elapsed_fraction <= self.SERVE_HOLD_RIGHT_FRACTION:
            return 0.0
        motion_window = self.SERVE_MOTION_FRACTION - self.SERVE_HOLD_RIGHT_FRACTION
        if motion_window <= 0.0:
            return 1.0
        return min(1.0, (elapsed_fraction - self.SERVE_HOLD_RIGHT_FRACTION) / motion_window)
