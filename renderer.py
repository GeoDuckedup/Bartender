from __future__ import annotations

from dataclasses import dataclass
from random import Random

import pygame


USE_SPRITES = False

LOGICAL_WIDTH = 400
LOGICAL_HEIGHT = 300
WINDOW_SCALE = 2
WINDOW_WIDTH = LOGICAL_WIDTH * WINDOW_SCALE
WINDOW_HEIGHT = LOGICAL_HEIGHT * WINDOW_SCALE
FPS = 60

HUD_HEIGHT = 44
PLAYFIELD_TOP = HUD_HEIGHT
PLAYFIELD_HEIGHT = LOGICAL_HEIGHT - HUD_HEIGHT
BAR_COUNT = 4
BAR_HEIGHT = 48
BAR_DECK_HEIGHT = 6
BAR_FRONT_HEIGHT = 22
BAR_BOTTOM_TRIM_HEIGHT = 10
BAR_VISUAL_HEIGHT = BAR_DECK_HEIGHT + BAR_FRONT_HEIGHT + BAR_BOTTOM_TRIM_HEIGHT
BAR_LEFT = 0
RIGHT_WALL_WIDTH = 52
RIGHT_WALL_LEFT = LOGICAL_WIDTH - RIGHT_WALL_WIDTH
SERVICE_STRIP_WIDTH = 20
BAR_RIGHT = RIGHT_WALL_LEFT - SERVICE_STRIP_WIDTH
BAR_WIDTH = BAR_RIGHT - BAR_LEFT
GRAIN_LINE_COUNT = 5
BAR_SPACING = (PLAYFIELD_HEIGHT - (BAR_COUNT * BAR_HEIGHT)) // (BAR_COUNT + 1)

BACKGROUND_COLOR = pygame.Color("#2C1A0E")
HUD_BACKGROUND_COLOR = pygame.Color("#1A1008")
HUD_BORDER_COLOR = pygame.Color("#6B3A1F")
HUD_TEXT_COLOR = pygame.Color("#F5F0E8")
BAR_MAIN_COLOR = pygame.Color("#C4722A")
BAR_DECK_COLOR = pygame.Color("#D88A3B")
BAR_FRONT_COLOR = pygame.Color("#BF6D28")
BAR_RAIL_COLOR = pygame.Color("#6B3A1F")
BAR_GRAIN_COLOR = pygame.Color("#B5611F")
BAR_KNOT_COLOR = pygame.Color("#8B4513")
RIGHT_WALL_COLOR = pygame.Color("#2B3D6B")
TAP_COLOR = pygame.Color("#C87941")
TAP_HANDLE_COLOR = pygame.Color("#A0522D")
BARTENDER_BODY_COLOR = pygame.Color("#F5F0E8")
BARTENDER_APRON_COLOR = pygame.Color("#8B6914")
BARTENDER_HEAD_COLOR = pygame.Color("#F5D5A0")
PATRON_BODY_COLOR = pygame.Color("#D4A843")
PATRON_HAT_COLOR = pygame.Color("#8B6914")
GLASS_OUTLINE_COLOR = pygame.Color("#CCCCCC")
GLASS_FILL_COLOR = pygame.Color("#E8A020")
GLASS_FOAM_COLOR = pygame.Color("#F5F0E8")
TIP_COLOR = pygame.Color("#F0C419")
TIP_SHADOW_COLOR = pygame.Color("#9C6A09")

BAR_TOPS = [
    PLAYFIELD_TOP + (BAR_SPACING * (index + 1)) + (BAR_HEIGHT * index)
    for index in range(BAR_COUNT)
]
BAR_FRONT_TOPS = [top + BAR_DECK_HEIGHT for top in BAR_TOPS]
LANE_CENTERS = [top + (BAR_HEIGHT // 2) for top in BAR_TOPS]
TAP_HOME_X = BAR_RIGHT
BARTENDER_WALK_MIN_X = BAR_LEFT
BARTENDER_WALK_MAX_X = TAP_HOME_X
TAP_GLASS_X = BAR_RIGHT - 14
GLASS_SURFACE_OVERLAP = 10
TIP_SURFACE_OVERLAP = 4


@dataclass(frozen=True)
class BarDecoration:
    grain_offsets: tuple[int, ...]
    knot_rects: tuple[pygame.Rect, ...]


def _build_bar_decorations() -> tuple[BarDecoration, ...]:
    rng = Random(1983)
    decorations: list[BarDecoration] = []
    for _ in range(BAR_COUNT):
        grain_offsets = tuple(
            rng.randint(10, BAR_HEIGHT - 10) for _ in range(GRAIN_LINE_COUNT)
        )
        knot_count = rng.randint(2, 3)
        knot_rects = []
        for _ in range(knot_count):
            knot_width = rng.randint(10, 18)
            knot_height = rng.randint(4, 8)
            x = rng.randint(24, BAR_WIDTH - 40)
            y = rng.randint(10, BAR_HEIGHT - knot_height - 10)
            knot_rects.append(pygame.Rect(x, y, knot_width, knot_height))
        decorations.append(
            BarDecoration(
                grain_offsets=grain_offsets,
                knot_rects=tuple(knot_rects),
            )
        )
    return tuple(decorations)


BAR_DECORATIONS = _build_bar_decorations()


def bar_front_top_y(bar_index: int) -> int:
    return BAR_FRONT_TOPS[bar_index]


def lane_surface_glass_y(bar_index: int, glass_height: int) -> int:
    return bar_front_top_y(bar_index) - (glass_height - GLASS_SURFACE_OVERLAP)


def lane_surface_tip_y(bar_index: int, tip_height: int) -> int:
    return bar_front_top_y(bar_index) - (tip_height - TIP_SURFACE_OVERLAP)


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
        self.draw_bar_backs(surface)
        self.draw_right_wall(surface)
        self.draw_taps(surface)

    def draw_background(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND_COLOR)

    def draw_bar_backs(self, surface: pygame.Surface) -> None:
        for index, top in enumerate(BAR_TOPS):
            rect = pygame.Rect(BAR_LEFT, top, BAR_WIDTH, BAR_HEIGHT)
            self.draw_bar_back(surface, rect, BAR_DECORATIONS[index])

    def draw_bar_fronts(self, surface: pygame.Surface) -> None:
        for index, top in enumerate(BAR_TOPS):
            rect = pygame.Rect(BAR_LEFT, top, BAR_WIDTH, BAR_HEIGHT)
            self.draw_bar_front(surface, rect, BAR_DECORATIONS[index])

    def draw_bar_back(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        decoration: BarDecoration,
    ) -> None:
        deck_rect = pygame.Rect(rect.left, rect.top, rect.width, BAR_DECK_HEIGHT)
        pygame.draw.rect(surface, BAR_DECK_COLOR, deck_rect)

        top_rail = pygame.Rect(rect.left, rect.top, rect.width, 4)
        pygame.draw.rect(surface, BAR_RAIL_COLOR, top_rail)
        pygame.draw.line(
            surface,
            BAR_GRAIN_COLOR,
            (deck_rect.left + 10, deck_rect.bottom - 1),
            (deck_rect.right - 10, deck_rect.bottom - 1),
            1,
        )

    def draw_bar_front(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        decoration: BarDecoration,
    ) -> None:
        front_rect = pygame.Rect(rect.left, rect.top + BAR_DECK_HEIGHT, rect.width, BAR_FRONT_HEIGHT)
        bottom_trim = pygame.Rect(
            rect.left,
            front_rect.bottom,
            rect.width,
            BAR_BOTTOM_TRIM_HEIGHT,
        )
        pygame.draw.rect(surface, BAR_FRONT_COLOR, front_rect)
        pygame.draw.rect(surface, BAR_RAIL_COLOR, bottom_trim)
        pygame.draw.line(
            surface,
            BAR_RAIL_COLOR,
            (front_rect.left, front_rect.top),
            (front_rect.right, front_rect.top),
            2,
        )

        for offset in (5, 10, 15):
            y = min(front_rect.bottom - 4, front_rect.top + offset)
            pygame.draw.line(
                surface,
                BAR_GRAIN_COLOR,
                (front_rect.left + 10, y),
                (front_rect.right - 10, y),
                1,
            )

        for knot_rect in decoration.knot_rects:
            knot_y = front_rect.top + 4 + (knot_rect.y % max(1, front_rect.height - knot_rect.height - 8))
            shifted_rect = pygame.Rect(
                knot_rect.left + rect.left,
                knot_y,
                knot_rect.width,
                knot_rect.height,
            )
            pygame.draw.ellipse(surface, BAR_KNOT_COLOR, shifted_rect)

    def draw_right_wall(self, surface: pygame.Surface) -> None:
        wall_rect = pygame.Rect(
            RIGHT_WALL_LEFT,
            PLAYFIELD_TOP,
            RIGHT_WALL_WIDTH,
            PLAYFIELD_HEIGHT,
        )
        pygame.draw.rect(surface, RIGHT_WALL_COLOR, wall_rect)

    def draw_taps(self, surface: pygame.Surface) -> None:
        for center_y in LANE_CENTERS:
            self.draw_tap(surface, center_y)

    def draw_tap(self, surface: pygame.Surface, center_y: int) -> None:
        stem_left = RIGHT_WALL_LEFT + RIGHT_WALL_WIDTH - 16
        stem = pygame.Rect(stem_left, center_y - 16, 8, 32)
        spout = pygame.Rect(RIGHT_WALL_LEFT, center_y + 4, stem_left + 8 - RIGHT_WALL_LEFT, 8)
        handle = pygame.Rect(stem_left - 8, center_y - 12, 12, 6)
        pygame.draw.rect(surface, TAP_COLOR, stem)
        pygame.draw.rect(surface, TAP_COLOR, spout)
        pygame.draw.rect(surface, TAP_HANDLE_COLOR, handle)
