from __future__ import annotations

from enum import Enum, auto

import pygame

from glass import FlyingGlass, TapGlass, draw_glass_with_fill
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


# Bartender movement / timing tuning:
# Keep gameplay-facing bartender movement here.
BARTENDER_WALK_SPEED = 150.0

# Bartender body tuning:
# These dimensions affect the rendered body and collision footprint.
BARTENDER_BODY_WIDTH = 20
BARTENDER_BODY_HEIGHT = 40
BARTENDER_HEAD_WIDTH = 18
BARTENDER_HEAD_HEIGHT = 14
BARTENDER_APRON_WIDTH = 10
BARTENDER_APRON_HEIGHT = 28
BARTENDER_FEET_OFFSET = 16
BARTENDER_APRON_Y_OFFSET = 2
BARTENDER_CATCH_RECT_PADDING = (10, 6)
BARTENDER_HAT_WIDTH = 22
BARTENDER_HAT_HEIGHT = 8
BARTENDER_HAT_BRIM_HEIGHT = 3
BARTENDER_HAT_CROWN_INSET = 4
BARTENDER_HAT_Y_OFFSET = 2
BARTENDER_HAT_COLOR = pygame.Color("#2E2B25")
BARTENDER_BOWTIE_WIDTH = 12
BARTENDER_BOWTIE_HEIGHT = 6
BARTENDER_BOWTIE_CENTER_SIZE = 4
BARTENDER_BOWTIE_Y_OFFSET = 8
BARTENDER_BOWTIE_COLOR = pygame.Color("#A3242B")

# Bartender serve animation tuning:
# This entire block is visual-only. It should never change the actual
# timing of when the beer is launched, only how the serve reads on screen.
SERVE_VISUAL_DURATION = 0.2
SERVE_LEFT_HAND_LINGER_DURATION = 0.6
SERVE_HOLD_RIGHT_FRACTION = 0.22
SERVE_MOTION_FRACTION = 0.62
SERVE_ARM_THICKNESS = 8
SERVE_HAND_SIZE = 10
SERVE_RIGHT_GLASS_OFFSET_X = BARTENDER_BODY_WIDTH - 2
SERVE_LEFT_GLASS_OFFSET_X = -3
SERVE_ARM_START_OFFSET_X = BARTENDER_BODY_WIDTH - 4
SERVE_ARM_Y_OFFSET = 18
SERVE_ARM_REACH_MULTIPLIER = 1.1
SERVE_OUTLINE_THICKNESS = 2
SERVE_GLASS_PADDING = 2
SERVE_GLASS_FOAM_HEIGHT = 4


class PourState(Enum):
    IDLE = auto()
    POURING = auto()


class Bartender:
    WALK_SPEED = BARTENDER_WALK_SPEED
    SERVE_VISUAL_DURATION = SERVE_VISUAL_DURATION
    SERVE_LEFT_HAND_LINGER_DURATION = SERVE_LEFT_HAND_LINGER_DURATION
    SERVE_HOLD_RIGHT_FRACTION = SERVE_HOLD_RIGHT_FRACTION
    SERVE_MOTION_FRACTION = SERVE_MOTION_FRACTION
    BODY_WIDTH = BARTENDER_BODY_WIDTH
    BODY_HEIGHT = BARTENDER_BODY_HEIGHT
    HEAD_WIDTH = BARTENDER_HEAD_WIDTH
    HEAD_HEIGHT = BARTENDER_HEAD_HEIGHT
    APRON_WIDTH = BARTENDER_APRON_WIDTH
    APRON_HEIGHT = BARTENDER_APRON_HEIGHT
    FEET_OFFSET = BARTENDER_FEET_OFFSET
    ARM_THICKNESS = SERVE_ARM_THICKNESS
    HAND_SIZE = SERVE_HAND_SIZE
    RIGHT_GLASS_OFFSET_X = SERVE_RIGHT_GLASS_OFFSET_X
    LEFT_GLASS_OFFSET_X = SERVE_LEFT_GLASS_OFFSET_X
    ARM_START_OFFSET_X = SERVE_ARM_START_OFFSET_X
    ARM_Y_OFFSET = SERVE_ARM_Y_OFFSET

    def __init__(self) -> None:
        self.bar_index = 0
        self.x = float(TAP_HOME_X)
        self.tap_glass = TapGlass()
        self.walk_speed = self.WALK_SPEED
        self.catch_rect_padding = BARTENDER_CATCH_RECT_PADDING
        self.flying_glass_speed = FlyingGlass.speed
        self.flying_glasses: list[FlyingGlass] = []
        self.missed_flying_glass = False
        self.has_hat = False
        self.has_bowtie = False
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
        return body_rect.inflate(*self.catch_rect_padding)

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
        self.x = max(BARTENDER_WALK_MIN_X, self.x - (self.walk_speed * dt))
        self._clear_glass_if_away()

    def walk_right(self, dt: float) -> None:
        self.x = min(BARTENDER_WALK_MAX_X, self.x + (self.walk_speed * dt))
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
                speed=self.flying_glass_speed,
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

    def draw_flying_glasses(
        self,
        surface: pygame.Surface,
        *,
        fill_color: pygame.Color | None = None,
    ) -> None:
        for flying_glass in self.flying_glasses:
            if (
                self.is_serving_visually
                and flying_glass is self.serve_visual_glass
                and self._serve_elapsed_fraction() < self.SERVE_MOTION_FRACTION
            ):
                continue
            flying_glass.draw(surface, fill_color=fill_color)

    def draw_tap_glass(
        self,
        surface: pygame.Surface,
        *,
        fill_color: pygame.Color | None = None,
    ) -> None:
        if self.pour_state is PourState.POURING and self.is_at_tap:
            body_rect = self.body_rect
            glass_left = self._right_glass_left(body_rect)
            self.tap_glass.draw(surface, self.bar_index, left=glass_left, fill_color=fill_color)
            self._draw_arm(
                surface,
                shoulder_x=body_rect.left + self.ARM_START_OFFSET_X,
                hand_x=glass_left + 5,
                arm_y=body_rect.top + self.ARM_Y_OFFSET,
            )

    def draw_serve_visual(
        self,
        surface: pygame.Surface,
        *,
        fill_color: pygame.Color | None = None,
    ) -> None:
        if self.is_serving_visually and self.serve_visual_glass is not None:
            elapsed_fraction = self._serve_elapsed_fraction()
            motion_progress = self._serve_motion_progress(elapsed_fraction)
            glass_left = round(
                self.serve_visual_start_x
                + ((self.serve_visual_end_x - self.serve_visual_start_x) * motion_progress)
            )
            if elapsed_fraction < self.SERVE_MOTION_FRACTION:
                glass_rect = pygame.Rect(
                    glass_left,
                    self.serve_visual_glass.rect.top,
                    TapGlass.WIDTH,
                    TapGlass.HEIGHT,
                )
                draw_glass_with_fill(
                    surface,
                    glass_rect,
                    fill_ratio=1.0,
                    show_top_foam=True,
                    fill_color=fill_color,
                )
            self._draw_arm(
                surface,
                shoulder_x=round(
                    self.serve_visual_shoulder_x
                    + (
                        (glass_left - self.serve_visual_shoulder_x)
                        * min(1.0, motion_progress * SERVE_ARM_REACH_MULTIPLIER)
                    )
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
            body_rect.centery - (self.APRON_HEIGHT // 2) + BARTENDER_APRON_Y_OFFSET,
            self.APRON_WIDTH,
            self.APRON_HEIGHT,
        )

        pygame.draw.rect(surface, BARTENDER_BODY_COLOR, body_rect)
        pygame.draw.rect(surface, BARTENDER_APRON_COLOR, apron_rect)
        pygame.draw.rect(surface, BARTENDER_HEAD_COLOR, head_rect)
        if self.has_bowtie:
            self._draw_bowtie(surface, body_rect)
        if self.has_hat:
            self._draw_hat(surface, head_rect)

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

    def _draw_hat(self, surface: pygame.Surface, head_rect: pygame.Rect) -> None:
        brim_rect = pygame.Rect(
            head_rect.centerx - (BARTENDER_HAT_WIDTH // 2),
            head_rect.top - BARTENDER_HAT_Y_OFFSET,
            BARTENDER_HAT_WIDTH,
            BARTENDER_HAT_BRIM_HEIGHT,
        )
        crown_rect = pygame.Rect(
            brim_rect.left + BARTENDER_HAT_CROWN_INSET,
            brim_rect.top - BARTENDER_HAT_HEIGHT,
            brim_rect.width - (BARTENDER_HAT_CROWN_INSET * 2),
            BARTENDER_HAT_HEIGHT,
        )
        pygame.draw.rect(surface, BARTENDER_HAT_COLOR, crown_rect)
        pygame.draw.rect(surface, BARTENDER_HAT_COLOR, brim_rect)

    def _draw_bowtie(self, surface: pygame.Surface, body_rect: pygame.Rect) -> None:
        center_y = body_rect.top + BARTENDER_BOWTIE_Y_OFFSET
        center_x = body_rect.centerx
        left_wing = [
            (center_x - (BARTENDER_BOWTIE_CENTER_SIZE // 2), center_y),
            (center_x - (BARTENDER_BOWTIE_WIDTH // 2), center_y - (BARTENDER_BOWTIE_HEIGHT // 2)),
            (center_x - (BARTENDER_BOWTIE_WIDTH // 2), center_y + (BARTENDER_BOWTIE_HEIGHT // 2)),
        ]
        right_wing = [
            (center_x + (BARTENDER_BOWTIE_CENTER_SIZE // 2), center_y),
            (center_x + (BARTENDER_BOWTIE_WIDTH // 2), center_y - (BARTENDER_BOWTIE_HEIGHT // 2)),
            (center_x + (BARTENDER_BOWTIE_WIDTH // 2), center_y + (BARTENDER_BOWTIE_HEIGHT // 2)),
        ]
        center_rect = pygame.Rect(
            center_x - (BARTENDER_BOWTIE_CENTER_SIZE // 2),
            center_y - (BARTENDER_BOWTIE_HEIGHT // 2),
            BARTENDER_BOWTIE_CENTER_SIZE,
            BARTENDER_BOWTIE_HEIGHT,
        )
        pygame.draw.polygon(surface, BARTENDER_BOWTIE_COLOR, left_wing)
        pygame.draw.polygon(surface, BARTENDER_BOWTIE_COLOR, right_wing)
        pygame.draw.rect(surface, BARTENDER_BOWTIE_COLOR, center_rect)

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
