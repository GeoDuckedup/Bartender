from __future__ import annotations

from dataclasses import dataclass
from random import Random

import pygame


USE_SPRITES = False

# Window / timing:
# Core render target sizes and frame rate.
LOGICAL_WIDTH = 400
LOGICAL_HEIGHT = 300
WINDOW_SCALE = 2
WINDOW_WIDTH = LOGICAL_WIDTH * WINDOW_SCALE
WINDOW_HEIGHT = LOGICAL_HEIGHT * WINDOW_SCALE
FPS = 60

# Scene layout:
# These define the playable stage geometry and the visible bar object.
HUD_HEIGHT = 52
PLAYFIELD_TOP_GAP = 16
PLAYFIELD_TOP = HUD_HEIGHT + PLAYFIELD_TOP_GAP
PLAYFIELD_HEIGHT = LOGICAL_HEIGHT - PLAYFIELD_TOP
BAR_COUNT = 4
BAR_HEIGHT = 48
BAR_DECK_HEIGHT = 4
BAR_FRONT_HEIGHT = 18
BAR_BOTTOM_TRIM_HEIGHT = 8
BAR_DRAW_OFFSET_Y = 10
BAR_LEFT = 0
RIGHT_WALL_WIDTH = 52
RIGHT_WALL_LEFT = LOGICAL_WIDTH - RIGHT_WALL_WIDTH
SERVICE_STRIP_WIDTH = 20
BAR_RIGHT = RIGHT_WALL_LEFT - SERVICE_STRIP_WIDTH
BAR_WIDTH = BAR_RIGHT - BAR_LEFT
GRAIN_LINE_COUNT = 5
BAR_SPACING = (PLAYFIELD_HEIGHT - (BAR_COUNT * BAR_HEIGHT)) // (BAR_COUNT + 1)
BAR_GRAIN_INSET_X = 10
BAR_KNOT_MARGIN_Y = 10
BAR_FRONT_GRAIN_OFFSETS = (4, 8, 12)

# Palette:
# Keep scene colors centralized so stage look can be tuned quickly.
BACKGROUND_COLOR = pygame.Color("#2C1A0E")
HUD_BACKGROUND_COLOR = pygame.Color("#1A1008")
HUD_BORDER_COLOR = pygame.Color("#6B3A1F")
HUD_TEXT_COLOR = pygame.Color("#F5F0E8")
BAR_DECK_COLOR = pygame.Color("#D88A3B")
BAR_FRONT_COLOR = pygame.Color("#BF6D28")
BAR_RAIL_COLOR = pygame.Color("#6B3A1F")
BAR_GRAIN_COLOR = pygame.Color("#B5611F")
RIGHT_WALL_COLOR = pygame.Color("#2B3D6B")
KEG_BODY_COLOR = pygame.Color("#A9682C")
KEG_FACE_COLOR = pygame.Color("#C27A34")
KEG_BAND_COLOR = pygame.Color("#6B3A1F")
KEG_SHADOW_COLOR = pygame.Color("#5A2E14")
TAP_HOUSING_COLOR = pygame.Color("#A9682C")
TAP_HOUSING_INSET_COLOR = pygame.Color("#6B3A1F")
TAP_SPOUT_COLOR = pygame.Color("#C87941")
TAP_HANDLE_COLOR = pygame.Color("#A0522D")
BARTENDER_BODY_COLOR = pygame.Color("#F5F0E8")
BARTENDER_APRON_COLOR = pygame.Color("#8B6914")
BARTENDER_HEAD_COLOR = pygame.Color("#F5D5A0")
GLASS_OUTLINE_COLOR = pygame.Color("#CCCCCC")
GLASS_FILL_COLOR = pygame.Color("#E8A020")
GLASS_FOAM_COLOR = pygame.Color("#F5F0E8")
TIP_COLOR = pygame.Color("#F0C419")
TIP_SHADOW_COLOR = pygame.Color("#9C6A09")

# Lane anchors:
# These are the reusable positional anchors other files should rely on
# instead of hardcoding bar-relative math.
BAR_TOPS = [
    PLAYFIELD_TOP + (BAR_SPACING * (index + 1)) + (BAR_HEIGHT * index)
    for index in range(BAR_COUNT)
]
LANE_CENTERS = [top + (BAR_HEIGHT // 2) for top in BAR_TOPS]
TAP_HOME_X = BAR_RIGHT
BARTENDER_WALK_MIN_X = BAR_LEFT
BARTENDER_WALK_MAX_X = TAP_HOME_X
TAP_GLASS_X = BAR_RIGHT - 14

# Keg / tap geometry:
# These shapes stay visual-only and should continue to align with the
# service strip on the right side of the playfield.
KEG_WIDTH = 26
KEG_HEIGHT = 42
KEG_RIGHT_MARGIN = 8
KEG_ASSEMBLY_Y_OFFSET = -6
KEG_FACE_INSET = 3
KEG_BAND_HEIGHT = 4
KEG_BAND_INSET = 1
KEG_FOOT_WIDTH = 6
KEG_FOOT_HEIGHT = 4
KEG_FOOT_INSET = 4
TAP_HOUSING_WIDTH = 12
TAP_HOUSING_HEIGHT = 34
TAP_HOUSING_OFFSET_X = 4
TAP_HOUSING_INSET = 3
TAP_SPOUT_LENGTH = 18
TAP_SPOUT_HEIGHT = 6
TAP_SPOUT_Y_OFFSET = 5
TAP_HANDLE_WIDTH = 10
TAP_HANDLE_HEIGHT = 5
TAP_HANDLE_OFFSET_X = 6
TAP_HANDLE_Y_OFFSET = -5


@dataclass(frozen=True)
class BarDecoration:
    grain_offsets: tuple[int, ...]


def _build_bar_decorations() -> tuple[BarDecoration, ...]:
    rng = Random(1983)
    decorations: list[BarDecoration] = []
    for _ in range(BAR_COUNT):
        grain_offsets = tuple(
            rng.randint(BAR_KNOT_MARGIN_Y, BAR_HEIGHT - BAR_KNOT_MARGIN_Y)
            for _ in range(GRAIN_LINE_COUNT)
        )
        decorations.append(
            BarDecoration(
                grain_offsets=grain_offsets,
            )
        )
    return tuple(decorations)


BAR_DECORATIONS = _build_bar_decorations()


def bar_surface_y(bar_index: int) -> int:
    return BAR_TOPS[bar_index] + BAR_DRAW_OFFSET_Y


def lane_surface_glass_y(bar_index: int, glass_height: int) -> int:
    return bar_surface_y(bar_index) - (glass_height // 2)


def lane_surface_tip_y(bar_index: int, tip_height: int) -> int:
    return bar_surface_y(bar_index) - (tip_height // 3)


class SceneRenderer:
    def draw_scene(self, surface: pygame.Surface) -> None:
        if USE_SPRITES:
            self.draw_procedural_scene(surface)
            return

        self.draw_procedural_scene(surface)

    def draw_procedural_scene(self, surface: pygame.Surface) -> None:
        self.draw_scene_backdrop(surface)
        self.draw_bar_fronts(surface)

    def draw_scene_backdrop(self, surface: pygame.Surface) -> None:
        self.draw_background(surface)
        self.draw_right_wall(surface)
        self.draw_taps(surface)

    def draw_background(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND_COLOR)

    def draw_bar_fronts(self, surface: pygame.Surface) -> None:
        for index, top in enumerate(BAR_TOPS):
            rect = pygame.Rect(BAR_LEFT, top, BAR_WIDTH, BAR_HEIGHT)
            self.draw_bar_front(surface, rect, BAR_DECORATIONS[index])

    def draw_bar_front(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        decoration: BarDecoration,
    ) -> None:
        deck_rect = pygame.Rect(
            rect.left,
            rect.top + BAR_DRAW_OFFSET_Y,
            rect.width,
            BAR_DECK_HEIGHT,
        )
        front_rect = pygame.Rect(
            rect.left,
            deck_rect.bottom,
            rect.width,
            BAR_FRONT_HEIGHT,
        )
        bottom_trim = pygame.Rect(
            rect.left,
            front_rect.bottom,
            rect.width,
            BAR_BOTTOM_TRIM_HEIGHT,
        )
        pygame.draw.rect(surface, BAR_DECK_COLOR, deck_rect)
        pygame.draw.rect(surface, BAR_FRONT_COLOR, front_rect)
        pygame.draw.rect(surface, BAR_RAIL_COLOR, bottom_trim)
        pygame.draw.line(
            surface,
            BAR_RAIL_COLOR,
            (deck_rect.left, deck_rect.top),
            (deck_rect.right, deck_rect.top),
            2,
        )
        pygame.draw.line(
            surface,
            BAR_RAIL_COLOR,
            (front_rect.left, front_rect.top),
            (front_rect.right, front_rect.top),
            2,
        )

        for offset in BAR_FRONT_GRAIN_OFFSETS:
            y = min(front_rect.bottom - 2, front_rect.top + offset)
            pygame.draw.line(
                surface,
                BAR_GRAIN_COLOR,
                (front_rect.left + BAR_GRAIN_INSET_X, y),
                (front_rect.right - BAR_GRAIN_INSET_X, y),
                1,
            )

    def draw_right_wall(self, surface: pygame.Surface) -> None:
        return

    def draw_taps(self, surface: pygame.Surface) -> None:
        for center_y in LANE_CENTERS:
            self.draw_tap(surface, center_y)

    def draw_tap(self, surface: pygame.Surface, center_y: int) -> None:
        assembly_center_y = center_y + KEG_ASSEMBLY_Y_OFFSET
        keg_rect = pygame.Rect(
            LOGICAL_WIDTH - KEG_RIGHT_MARGIN - KEG_WIDTH,
            assembly_center_y - (KEG_HEIGHT // 2),
            KEG_WIDTH,
            KEG_HEIGHT,
        )
        keg_shadow_rect = keg_rect.move(2, 1)
        keg_face_rect = keg_rect.inflate(-(KEG_FACE_INSET * 2), -(KEG_FACE_INSET * 2))
        top_band_rect = pygame.Rect(
            keg_rect.left + KEG_BAND_INSET,
            keg_rect.top + 4,
            keg_rect.width - (KEG_BAND_INSET * 2),
            KEG_BAND_HEIGHT,
        )
        bottom_band_rect = pygame.Rect(
            keg_rect.left + KEG_BAND_INSET,
            keg_rect.bottom - 4 - KEG_BAND_HEIGHT,
            keg_rect.width - (KEG_BAND_INSET * 2),
            KEG_BAND_HEIGHT,
        )
        center_band_rect = pygame.Rect(
            keg_rect.left + KEG_BAND_INSET,
            keg_rect.centery - (KEG_BAND_HEIGHT // 2),
            keg_rect.width - (KEG_BAND_INSET * 2),
            KEG_BAND_HEIGHT,
        )
        left_foot_rect = pygame.Rect(
            keg_rect.left + KEG_FOOT_INSET,
            keg_rect.bottom - 1,
            KEG_FOOT_WIDTH,
            KEG_FOOT_HEIGHT,
        )
        right_foot_rect = pygame.Rect(
            keg_rect.right - KEG_FOOT_INSET - KEG_FOOT_WIDTH,
            keg_rect.bottom - 1,
            KEG_FOOT_WIDTH,
            KEG_FOOT_HEIGHT,
        )
        tap_housing_rect = pygame.Rect(
            keg_rect.left - TAP_HOUSING_WIDTH,
            assembly_center_y - (TAP_HOUSING_HEIGHT // 2),
            TAP_HOUSING_WIDTH,
            TAP_HOUSING_HEIGHT,
        )
        inset_width = tap_housing_rect.width - (TAP_HOUSING_INSET * 2)
        inset_height = tap_housing_rect.height - (TAP_HOUSING_INSET * 2)
        tap_inset_rect = pygame.Rect(
            tap_housing_rect.right - TAP_HOUSING_INSET - inset_width,
            tap_housing_rect.top + TAP_HOUSING_INSET,
            inset_width,
            inset_height,
        )
        mirrored_spout_length = max(0, keg_rect.left - tap_housing_rect.right)
        spout_rect = pygame.Rect(
            tap_housing_rect.right,
            assembly_center_y + TAP_SPOUT_Y_OFFSET,
            mirrored_spout_length,
            TAP_SPOUT_HEIGHT,
        )
        handle_rect = pygame.Rect(
            tap_housing_rect.left - 2,
            tap_housing_rect.top + TAP_HANDLE_Y_OFFSET,
            TAP_HANDLE_WIDTH,
            TAP_HANDLE_HEIGHT,
        )

        pygame.draw.rect(surface, KEG_SHADOW_COLOR, keg_shadow_rect, border_radius=6)
        pygame.draw.rect(surface, KEG_BODY_COLOR, keg_rect, border_radius=6)
        pygame.draw.rect(surface, KEG_FACE_COLOR, keg_face_rect, border_radius=4)
        pygame.draw.rect(surface, KEG_BAND_COLOR, top_band_rect, border_radius=2)
        pygame.draw.rect(surface, KEG_BAND_COLOR, center_band_rect, border_radius=2)
        pygame.draw.rect(surface, KEG_BAND_COLOR, bottom_band_rect, border_radius=2)
        pygame.draw.rect(surface, KEG_SHADOW_COLOR, left_foot_rect)
        pygame.draw.rect(surface, KEG_SHADOW_COLOR, right_foot_rect)
        stave_x_positions = (
            keg_face_rect.left + 5,
            keg_face_rect.centerx,
            keg_face_rect.right - 5,
        )
        for stave_x in stave_x_positions:
            pygame.draw.line(
                surface,
                KEG_SHADOW_COLOR,
                (stave_x, keg_face_rect.top + 2),
                (stave_x, keg_face_rect.bottom - 2),
                1,
            )

        pygame.draw.rect(surface, TAP_HOUSING_COLOR, tap_housing_rect)
        pygame.draw.rect(surface, TAP_HOUSING_INSET_COLOR, tap_inset_rect)
        pygame.draw.rect(surface, TAP_SPOUT_COLOR, spout_rect)
        pygame.draw.rect(surface, TAP_HANDLE_COLOR, handle_rect)
